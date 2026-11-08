import pyodbc
import pg8000.dbapi
import os
from datetime import datetime
from arucasyncdb import ArucaSyncDBManager

LOGS_PATH = os.path.join(os.path.dirname(__file__), "..", "logs")

class StatusSynchronizer:
    def __init__(self, manager_local, config_remota):
        self.manager_local = manager_local
        self.config_remota = config_remota
        self.db_local = ArucaSyncDBManager()
        
        os.makedirs(LOGS_PATH, exist_ok=True)
        marca = datetime.now().strftime("%d%m%Y_%H%M%S")
        self.log_path = os.path.join(LOGS_PATH, f"sync_estados_{marca}.log")
        self._log("INICIO", "Archivo de log de estados creado.")

    def _log(self, nivel, mensaje):
        linea = f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] [{nivel}] {mensaje}"
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(linea + "\n")

    def _conectar_remoto(self):
        return pg8000.dbapi.connect(
            host=self.config_remota["server"],
            port=int(self.config_remota["port"]),
            database=self.config_remota["database"],
            user=self.config_remota["username"],
            password=self.config_remota["password"],
            ssl_context=None
        )

    def obtener_cambios_pendientes(self):
        self._log("INFO", "Buscando transacciones con cambios de estado...")
        
        cambios = []
        transacciones_locales = self.db_local.obtener_transacciones_bajadas()
        
        if not transacciones_locales:
            return cambios

        ok, msg, conn_local = self.manager_local.open_connection()
        if not ok:
            self._log("ERROR", f"Error conexión DBISAM: {msg}")
            return cambios

        conn_local.setdecoding(pyodbc.SQL_CHAR, encoding='latin-1')
        conn_local.setencoding(encoding='latin-1')
        cursor_local = conn_local.cursor()

        remoto = self._conectar_remoto()
        cursor_remoto = remoto.cursor()

        try:
            for doc, tipo, status_bajado in transacciones_locales:
                cursor_local.execute(
                    "SELECT FTI_STATUS FROM SOperacionInv WHERE FTI_DOCUMENTO = ? AND FTI_TIPO = ?",
                    (doc, tipo)
                )
                fila = cursor_local.fetchone()

                if fila:
                    status_dbism = fila[0]
                    if status_dbism != status_bajado:
                        cursor_remoto.execute(
                            "SELECT trn_personacontacto, trn_fechaemision FROM public.arc_transacciones WHERE trn_documento = %s AND trn_tipo = %s",
                            (doc, tipo)
                        )
                        pg_fila = cursor_remoto.fetchone()
                        cliente = pg_fila[0] if pg_fila else "Desconocido"
                        fecha = pg_fila[1].strftime('%Y-%m-%d') if pg_fila and pg_fila[1] else ""
                        
                        cambios.append({
                            "documento": doc,
                            "tipo": tipo,
                            "cliente": cliente,
                            "fecha": fecha,
                            "status_anterior": status_bajado,
                            "status_actual": status_dbism
                        })
            return cambios

        except Exception as e:
            self._log("ERROR", f"Error al buscar cambios: {str(e)}")
            return []
        finally:
            cursor_local.close()
            cursor_remoto.close()
            remoto.close()

    def actualizar_estados(self, lista_cambios):
        if not lista_cambios:
            return 0

        self._log("INFO", f"Iniciando actualización de {len(lista_cambios)} estados en PostgreSQL...")

        ok, msg, conn_local = self.manager_local.open_connection()
        if not ok:
            self._log("ERROR", f"Error conexión DBISAM: {msg}")
            return 0

        conn_local.setdecoding(pyodbc.SQL_CHAR, encoding='latin-1')
        conn_local.setencoding(encoding='latin-1')
        cursor_local = conn_local.cursor()

        remoto = self._conectar_remoto()
        cursor_remoto = remoto.cursor()

        contador = 0

        try:
            for item in lista_cambios:
                doc = item["documento"]
                tipo = item["tipo"]
                nuevo_status = item["status_actual"]

                cursor_remoto.execute(
                    "UPDATE public.arc_transacciones SET trn_status = %s WHERE trn_documento = %s AND trn_tipo = %s",
                    (nuevo_status, doc, tipo)
                )
                cursor_remoto.execute(
                    "UPDATE public.arc_detalletranvtas SET dtv_status = %s WHERE dtv_documento = %s AND dtv_tipooperacion = %s",
                    (nuevo_status, doc, tipo)
                )
                
                self.db_local.actualizar_status_bajado(doc, tipo, nuevo_status)
                contador += 1

            remoto.commit()
            self._log("FIN", f"Actualización completada. Registros actualizados: {contador}.")
            return contador

        except Exception as e:
            remoto.rollback()
            self._log("ERROR", f"Error al actualizar estados: {str(e)}")
            raise e
        finally:
            cursor_local.close()
            cursor_remoto.close()
            remoto.close()