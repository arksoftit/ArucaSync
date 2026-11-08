import os
from dbconnection import DBConnectionManager
from remoteconnection import RemoteDBManager
from sync_down import SyncDown

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "conexiones.json")
manager = DBConnectionManager(CONFIG_PATH)
cfg = RemoteDBManager().load_config()

sincronizador = SyncDown(manager, cfg)
bajados = sincronizador.bajar_clientes()
print(f"Clientes bajados a DBISAM: {bajados}")