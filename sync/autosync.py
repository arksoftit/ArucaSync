import os
import sys
import json
import pyodbc
from datetime import datetime
from arucasyncdb import ArucaSyncDBManager

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

CONFIG_PATH = os.path.join(BASE_DIR, "config", "conexiones.json")
AUTOSYNC_CONFIG_PATH = os.path.join(BASE_DIR, "config", "autosync_config.json")

from dbconnection import DBConnectionManager
from remoteconnection import RemoteDBManager
from sync_down import SyncDown
from sync_status import StatusSynchronizer
from sync_data import COLUMNAS_MAP, MAPA_TABLAS, mapear_tablas, FILTROS_TABLAS
from sync_logger import LogManager

TABLAS_MONITOREO = {
    "SdetalleCompra": [5, 6, 7, 8],
    "SdetalleInv": [1, 2, 3, 4],
    "SdetalleVenta": [9, 10, 11, 12, 13]
}

def inicializar_monitor_control(conn_dbisam, db_manager, fecha_desde, fecha_hasta, logger):
    conn_sqlite = db_manager._conectar()
    cursor_sqlite = conn_sqlite.cursor()
    cursor_sqlite.execute("SELECT COUNT(*) FROM sync_monitor_control WHERE mon_tablename IN ('SdetalleCompra', 'SdetalleInv', 'SdetalleVenta')")
    if cursor_sqlite.fetchone()[0] > 0:
        cursor_sqlite.close()
        conn_sqlite.close()
        logger.info("Monitor de control ya inicializado. Se omite poblado inicial.")
        return

    cursor_dbisam = conn_dbisam.cursor()
    for tabla, tipos in TABLAS_MONITOREO.items():
        tipos_str = ",".join(str(t) for t in tipos)
        query = f"""
            SELECT FDI_TIPOOPERACION, COUNT(*) AS TotalRegistros,
                   MAX(FDI_DOCUMENTO) AS UltimoDocumento,
                   MAX(FDI_FECHAOPERACION) AS UltimaFecha
            FROM {tabla}
            WHERE FDI_FECHAOPERACION BETWEEN '{fecha_desde}' AND '{fecha_hasta}'
            AND FDI_TIPOOPERACION IN ({tipos_str})
            GROUP BY FDI_TIPOOPERACION
        """
        try:
            cursor_dbisam.execute(query)
            filas = cursor_dbisam.fetchall()
            for fila in filas:
                tipo_op, total_reg, ultimo_doc, ultima_fecha = fila
                cursor_sqlite.execute("""
                    INSERT INTO sync_monitor_control
                    (mon_tablename, mon_tipo_transaccion, mon_total_registros, mon_lastupdatedate, mon_lastdocument, mon_lastdocumentdate)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (tabla, tipo_op, total_reg, str(ultima_fecha) if ultima_fecha else "", str(ultimo_doc) if ultimo_doc else "", str(ultima_fecha) if ultima_fecha else ""))
            conn_sqlite.commit()
            logger.info(f"Monitor inicializado para {tabla}: {len(filas)} tipos de operación registrados.")
        except Exception as e:
            logger.error(f"Error inicializando monitor para {tabla}: {e}")
    cursor_dbisam.close()
    cursor_sqlite.close()
    conn_sqlite.close()

def main():
    if not os.path.exists(AUTOSYNC_CONFIG_PATH):
        print("No existe el archivo de configuración de automatización.")
        return

    with open(AUTOSYNC_CONFIG_PATH, "r", encoding="utf-8") as f:
        config = json.load(f)

    ahora = datetime.now()
    hora_actual_str = ahora.strftime("%H:%M")
    hora_inicio = config.get("hora_inicio", "07:00")
    hora_fin = config.get("hora_fin", "20:00")
    if not (hora_inicio <= hora_actual_str <= hora_fin):
        print(f"Fuera de rango. Hora actual: {hora_actual_str}. Rango: {hora_inicio} - {hora_fin}.")
        return

    logger = LogManager()
    logger.info(f"Inicio de automatización. Hora: {hora_actual_str}.")

    manager = DBConnectionManager(CONFIG_PATH)
    cfg_remota = RemoteDBManager().load_config()
    if not cfg_remota:
        logger.error("No hay configuración remota.")
        return

    tablas_sub = config.get("tablas_subida", [])
    tablas_baj = config.get("tablas_bajada", [])

    f_desde_sub = config.get("fecha_desde_sub", "")
    f_hasta_sub = config.get("fecha_hasta_sub", "")

    db_manager = ArucaSyncDBManager()

    ok_init, msg_init, conn_init = manager.open_connection()
    if ok_init:
        conn_init.setdecoding(pyodbc.SQL_CHAR, encoding='latin-1')
        conn_init.setencoding(encoding='latin-1')
        inicializar_monitor_control(conn_init, db_manager, f_desde_sub, f_hasta_sub, logger)

    logger.info("Iniciando proceso de Subida...")
    for tabla_destino in tablas_sub:
        origen = None
        for orig, dest in MAPA_TABLAS.items():
            if dest[0] == tabla_destino:
                origen = orig
                break
        if origen:
            try:
                ok, msg, conn_local = manager.open_connection()
                if not ok:
                    raise Exception(msg)
                conn_local.setdecoding(pyodbc.SQL_CHAR, encoding='latin-1')
                conn_local.setencoding(encoding='latin-1')
                pares = COLUMNAS_MAP[tabla_destino][origen]
                columnas_origen = [orig_col for _, orig_col in pares]
                filtro = FILTROS_TABLAS.get(origen, "")
                filtro_fecha = ""
                if tabla_destino in ["arc_transacciones", "arc_detalletranvtas"] and f_desde_sub and f_hasta_sub:
                    if origen == "SOperacionInv":
                        filtro_fecha = f"FTI_FECHAEMISION >= '{f_desde_sub}' AND FTI_FECHAEMISION <= '{f_hasta_sub}'"
                    elif origen == "SDetalleVenta":
                        filtro_fecha = f"FDI_FECHAOPERACION >= '{f_desde_sub}' AND FDI_FECHAOPERACION <= '{f_hasta_sub}'"
                consulta = f"SELECT {', '.join(columnas_origen)} FROM {origen}"
                if filtro and filtro_fecha:
                    consulta += f" WHERE {filtro} AND {filtro_fecha}"
                elif filtro:
                    consulta += f" WHERE {filtro}"
                elif filtro_fecha:
                    consulta += f" WHERE {filtro_fecha}"
                cursor = conn_local.cursor()
                cursor.execute(consulta)
                filas = cursor.fetchall()
                cursor.close()
                machine = os.environ.get('COMPUTERNAME', 'AUTOSYNC')
                user = os.environ.get('USERNAME', 'AUTOSYNC')
                columnas_destino, filas_mapeadas = mapear_tablas(origen, filas, machine, user)
                remoto = RemoteDBManager()
                conn_remota = remoto.connect(cfg_remota["server"], cfg_remota["port"], cfg_remota["database"], cfg_remota["username"], cfg_remota["password"], cfg_remota["ssl"])
                nuevos, actualizados = remoto.upsert_data(conn_remota, tabla_destino, MAPA_TABLAS[origen][1], columnas_destino, filas_mapeadas, machine=machine, user=user)
                conn_remota.close()
                logger.info(f"Subida {tabla_destino}: {nuevos} nuevos, {actualizados} actualizados.")
            except Exception as e:
                logger.error(f"Error subiendo {tabla_destino}: {str(e)}")

    try:
        ok, msg, conn_local_db = manager.open_connection()
        if ok:
            conn_local_db.setdecoding(pyodbc.SQL_CHAR, encoding='latin-1')
            conn_local_db.setencoding(encoding='latin-1')
            conn_local_db.setdecoding(pyodbc.SQL_WCHAR, encoding='latin-1')
            cursor_db = conn_local_db.cursor()
            cursor_db.execute("SELECT FT_CODIGOPRODUCTO, FT_CODIGODEPOSITO, FT_EXISTENCIA FROM SinvDep")
            registros_sinvdep = cursor_db.fetchall()
            cursor_db.close()
            db_manager.actualizar_existencia_transito_lote(registros_sinvdep)
            logger.info(f"Sincronización de Existencia Tránsito (SinvDep): {len(registros_sinvdep)} registros procesados localmente.")
    except Exception as e:
        logger.error(f"Error procesando existencia de tránsito desde SinvDep: {str(e)}")

    logger.info("Iniciando proceso de Bajada...")
    f_desde_baj = config.get("fecha_desde_baj", "")
    f_hasta_baj = config.get("fecha_hasta_baj", "")
    sync_down = SyncDown(manager, cfg_remota)
    if "arc_clientes" in tablas_baj:
        try:
            cant = sync_down.bajar_clientes()
            logger.info(f"Bajada Clientes: {cant} insertados.")
        except Exception as e:
            logger.error(f"Error bajada Clientes: {str(e)}")
    if "arc_transacciones" in tablas_baj and "arc_detalletranvtas" in tablas_baj:
        try:
            cant = sync_down.bajar_transacciones(fecha_desde=f_desde_baj, fecha_hasta=f_hasta_baj)
            logger.info(f"Bajada Transacciones: {cant} insertados.")
        except Exception as e:
            logger.error(f"Error bajada Transacciones: {str(e)}")
    if "arc_transacciones" in tablas_baj:
        try:
            sync_status = StatusSynchronizer(manager, cfg_remota)
            cant_estados = sync_status.actualizar_estados(sync_status.obtener_cambios_pendientes())
            logger.info(f"Actualización Estados: {cant_estados} actualizados.")
        except Exception as e:
            logger.error(f"Error actualización estados: {str(e)}")

    manager.disconnect()
    logger.cerrar("Automatización completada.")

if __name__ == "__main__":
    main()