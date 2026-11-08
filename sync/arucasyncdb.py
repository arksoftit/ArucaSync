import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "sync_control.db")

class ArucaSyncDBManager:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self._crear_tablas()

    def _conectar(self):
        return sqlite3.connect(self.db_path)

    def _crear_tablas(self):
        with self._conectar() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sync_control (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    documento TEXT NOT NULL,
                    tipo INTEGER NOT NULL,
                    status_bajado INTEGER NOT NULL,
                    fecha_bajada TEXT NOT NULL,
                    UNIQUE(documento, tipo)
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS app_users (
                    username TEXT PRIMARY KEY,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)
            
            conn.commit()

    def registrar_bajada(self, documento, tipo, status_bajado):
        fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self._conectar() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO sync_control (documento, tipo, status_bajado, fecha_bajada)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(documento, tipo) DO UPDATE SET
                    status_bajado = excluded.status_bajado,
                    fecha_bajada = excluded.fecha_bajada
            """, (documento, tipo, status_bajado, fecha))
            conn.commit()

    def obtener_transacciones_bajadas(self):
        with self._conectar() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT documento, tipo, status_bajado FROM sync_control")
            return cursor.fetchall()
            
    def actualizar_status_bajado(self, documento, tipo, nuevo_status):
        with self._conectar() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE sync_control 
                SET status_bajado = ? 
                WHERE documento = ? AND tipo = ?
            """, (nuevo_status, documento, tipo))
            conn.commit()