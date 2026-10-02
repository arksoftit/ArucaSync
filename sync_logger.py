import os
from datetime import datetime

LOGS_PATH = os.path.join(os.path.dirname(__file__), "..", "logs")


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