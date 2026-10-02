import json
import os
import winreg
from datetime import datetime

import pyodbc

ORIGENES = ("SClientes", "TClientes")
APPDATA = {"SClientes": "a2Data", "TClientes": "HBData"}


class DBConnectionManager:
    def __init__(self, config_path):
        self.config_path = config_path
        self.conexiones = {}
        self.dsns = {}

    def get_dsn_list(self):
        dsn_list = []
        keys_to_check = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\ODBC\ODBC.INI\ODBC Data Sources"),
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\ODBC\ODBC.INI\ODBC Data Sources"),
        ]
        for hkey, sub_key_path in keys_to_check:
            try:
                key = winreg.OpenKey(hkey, sub_key_path, 0, winreg.KEY_READ | winreg.KEY_WOW64_32KEY)
                i = 0
                while True:
                    try:
                        name, value, _ = winreg.EnumValue(key, i)
                        if "DBISAM" in value.upper() and name not in dsn_list:
                            dsn_list.append(name)
                        i += 1
                    except OSError:
                        break
                winreg.CloseKey(key)
            except Exception:
                continue
        return dsn_list

    def load_connections(self):
        if not os.path.exists(self.config_path):
            return []
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if not content:
                    return []
                raw = json.loads(content)
        except json.JSONDecodeError:
            return []
        conexiones = []
        for item in raw:
            entry = {k.strip(): (v.strip() if isinstance(v, str) else v) for k, v in item.items()}
            activa = entry.get("Activa", False)
            entry["Activa"] = activa.lower() == "true" if isinstance(activa, str) else bool(activa)
            conexiones.append(entry)
        return conexiones

    def save_connection(self, dsn, usuario, password, origen):
        conexiones = self.load_connections()
        for c in conexiones:
            if c.get("origen") == origen:
                c["Activa"] = False
        conexiones = [c for c in conexiones if not (c["dsn"] == dsn.strip() and c.get("origen") == origen)]
        conexiones.insert(0, {
            "dsn": dsn.strip(),
            "usuario": usuario,
            "password": password,
            "fecha": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            "origen": origen,
            "appdata": APPDATA.get(origen, ""),
            "Activa": True,
        })
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(conexiones[:10], f, indent=4)

    def get_active_connection(self, origen):
        for c in self.load_connections():
            if c.get("Activa") and c.get("origen") == origen:
                return c
        return None

    def connect(self, dsn, usuario, password):
        try:
            conn_str = f"DSN={dsn};UID={usuario};PWD={password};"
            return True, "Conexión exitosa", pyodbc.connect(conn_str, autocommit=True)
        except pyodbc.Error as e:
            return False, str(e), None

    def open_connection(self, origen):
        if origen in self.conexiones:
            return True, f"Conexión {origen} ya abierta", self.conexiones[origen]
        entrada = self.get_active_connection(origen)
        if not entrada:
            return False, f"No hay conexión activa para el origen {origen}", None
        ok, msg, conn = self.connect(entrada["dsn"], entrada["usuario"], entrada["password"])
        if ok:
            self.conexiones[origen] = conn
            self.dsns[origen] = entrada["dsn"]
        return ok, msg, conn

    def get_connection(self, origen):
        return self.conexiones.get(origen)

    def disconnect(self, origen=None):
        if origen is None:
            for conn in self.conexiones.values():
                conn.close()
            self.conexiones.clear()
            self.dsns.clear()
        elif origen in self.conexiones:
            self.conexiones[origen].close()
            del self.conexiones[origen]
            del self.dsns[origen]

    def get_data_directory(self, dsn):
        rutas_registro = [
            f"SOFTWARE\\WOW6432Node\\ODBC\\ODBC.INI\\{dsn}",
            f"SOFTWARE\\ODBC\\ODBC.INI\\{dsn}",
        ]
        for hkey in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
            for ruta in rutas_registro:
                try:
                    with winreg.OpenKey(hkey, ruta, 0, winreg.KEY_READ | winreg.KEY_WOW64_32KEY) as key:
                        for clave in ("CatalogName", "Database", "DatabaseFile"):
                            try:
                                valor, _ = winreg.QueryValueEx(key, clave)
                                if valor and os.path.exists(valor):
                                    if valor.lower().endswith((".db", ".ism", ".dat")):
                                        return os.path.dirname(valor)
                                    return valor
                            except FileNotFoundError:
                                continue
                except (FileNotFoundError, PermissionError):
                    pass
        return None