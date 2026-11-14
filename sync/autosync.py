import os
import sys
import json
import pyodbc
from datetime import datetime

# Detectar si está compilado como .exe o ejecutándose como script
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

    logger.info("Iniciando proceso de Subida...")
    f_desde_sub = config.get("fecha_desde_sub", "")
    f_hasta_sub = config.get("fecha_hasta_sub", "")

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

    # Sincronización de existencias de tránsito desde SinvDep (DBISAM -> SQLite local)
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
            conn_local_db.close()

            from arucasyncdb import ArucaSyncDBManager
            db_manager = ArucaSyncDBManager()
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

    logger.cerrar("Automatización completada.")

if __name__ == "__main__":
    main()