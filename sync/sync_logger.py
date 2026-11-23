import os
import sys
from datetime import datetime

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

LOGS_PATH = os.path.join(BASE_DIR, "logs")


class LogManager:
    def __init__(self):
        os.makedirs(LOGS_PATH, exist_ok=True)
        marca = datetime.now().strftime("%d%m%Y_%H%M%S")
        self.ruta = os.path.join(LOGS_PATH, f"sincronizacion_{marca}.log")
        self._escribir("INICIO", f"Archivo de log creado: {self.ruta}")

    def _escribir(self, nivel, mensaje):
        linea = f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] [{nivel}] {mensaje}"
        with open(self.ruta, "a", encoding="utf-8") as f:
            f.write(linea + "\n")

    def info(self, mensaje):
        self._escribir("INFO", mensaje)

    def error(self, mensaje):
        self._escribir("ERROR", mensaje)

    def cerrar(self, mensaje):
        self._escribir("FIN", mensaje)