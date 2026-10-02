import json
import os
import ssl
from datetime import datetime

import pg8000.dbapi

REMOTE_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "remotedb.json")


class RemoteDBManager:
    def __init__(self, config_path=REMOTE_CONFIG_PATH):
        self.config_path = config_path
    
    def load_config(self):
        if not os.path.exists(self.config_path):
            return None
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if not content:
                    return None
                return json.loads(content)
        except json.JSONDecodeError:
            return None
        
    def save_config(self, server, port, database, username, password, ssl, tablas):
        datos = {
            "server": server,
            "port": port,
            "database": database,
            "username": username,
            "password": password,
            "ssl": ssl,
            "fecha": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            "tablas": tablas,
        }
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(datos, f, indent=4)
            
    def connect(self, server, port, database, username, password, use_ssl):
        ssl_context = None
        if use_ssl:
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
        
        return pg8000.dbapi.connect(
            host=server,
            port=int(port),
            database=database,
            user=username,
            password=password,
            ssl_context=ssl_context,
        )

    def list_tables(self, conn):
        cursor = conn.cursor()
        cursor.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public' ORDER BY table_name"
        )
        filas = cursor.fetchall()
        cursor.close()
        return [fila[0] for fila in filas]

    def upsert_data(self, conn, tabla, columna_conflicto, columnas, filas,
                    progreso=None, tam_lote=500, machine=None, user=None):
        cursor = conn.cursor()
        if machine is not None:
            cursor.execute("SELECT set_config('app.machine_name', %s, false)", (machine,))
        if user is not None:
            cursor.execute("SELECT set_config('app.user_name', %s, false)", (user,))
        cursor.execute(f"SELECT {columna_conflicto} FROM {tabla}")
        existentes = {fila[0] for fila in cursor.fetchall()}
        indice_conflicto = columnas.index(columna_conflicto)
        actualizables = [
            c for c in columnas
            if c not in (
                columna_conflicto,
                "cli_namemachine",
                "cli_usercreator",
                "cli_lastupdatedate",
                "cli_lastmachine",
                "cli_userlastupdate",
            )
        ]
        set_clause = ", ".join([f"{c} = EXCLUDED.{c}" for c in actualizables])
        fila_placeholders = "(" + ", ".join(["%s"] * len(columnas)) + ")"
        nuevos = 0
        actualizados = 0
        total = len(filas)
        try:
            for inicio in range(0, total, tam_lote):
                lote = filas[inicio:inicio + tam_lote]
                for fila in lote:
                    if fila[indice_conflicto] in existentes:
                        actualizados += 1
                    else:
                        nuevos += 1
                placeholders = ", ".join([fila_placeholders] * len(lote))
                params = [valor for fila in lote for valor in fila]
                sql = (
                    f"INSERT INTO {tabla} ({', '.join(columnas)}) VALUES {placeholders} "
                    f"ON CONFLICT ({columna_conflicto}) DO UPDATE SET {set_clause}"
                )
                cursor.execute(sql, params)
                if progreso:
                    progreso(min(inicio + tam_lote, total), total)
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
        return nuevos, actualizados