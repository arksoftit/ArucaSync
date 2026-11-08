import sqlite3
import os
import hashlib
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "sync_control.db")

class ArucaSyncDBManager:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self._crear_tablas()

    def _conectar(self):
        return sqlite3.connect(self.db_path)

    def _hash_password(self, password):
        return hashlib.sha256(password.encode()).hexdigest()

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
                    created_at TEXT NOT NULL,
                    email TEXT,
                    codigo TEXT,
                    descripcion TEXT,
                    estado INTEGER DEFAULT 0,
                    telefono TEXT,
                    cargo TEXT
                )
            """)
            
            conn.commit()
            self._crear_superusuario_default()

    def _crear_superusuario_default(self):
        with self._conectar() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM app_users")
            if cursor.fetchone()[0] == 0:
                fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                pwd_hash = self._hash_password("Acr0p0lis")
                cursor.execute("""
                    INSERT INTO app_users (username, password_hash, role, created_at, email, codigo, descripcion, estado, telefono, cargo)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, ("star", pwd_hash, "Superusuario", fecha, "arksoft.sistemas@gmail.com", "V-00000000", "Superusuario por defecto", 0, "", "Administrador de Sistema"))
                conn.commit()

    def validar_usuario(self, username, password):
        with self._conectar() as conn:
            cursor = conn.cursor()
            pwd_hash = self._hash_password(password)
            cursor.execute(
                "SELECT role FROM app_users WHERE LOWER(username) = LOWER(?) AND password_hash = ?", 
                (username, pwd_hash)
            )
            fila = cursor.fetchone()
            if fila:
                return fila[0]
            return None

    def obtener_usuarios(self):
        with self._conectar() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT username, codigo, descripcion, estado, role, email, telefono, cargo 
                FROM app_users ORDER BY codigo ASC
            """)
            return cursor.fetchall()

    def obtener_usuario(self, username):
        with self._conectar() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT username, password_hash, role, email, codigo, descripcion, estado, telefono, cargo 
                FROM app_users WHERE LOWER(username) = LOWER(?)
            """, (username,))
            return cursor.fetchone()

    def crear_usuario(self, username, password, role, email, codigo, descripcion, estado, telefono, cargo):
        with self._conectar() as conn:
            cursor = conn.cursor()
            fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            pwd_hash = self._hash_password(password)
            cursor.execute("""
                INSERT INTO app_users (username, password_hash, role, created_at, email, codigo, descripcion, estado, telefono, cargo)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (username, pwd_hash, role, fecha, email, codigo, descripcion, estado, telefono, cargo))
            conn.commit()

    def actualizar_usuario(self, username_original, username_nuevo, password, role, email, codigo, descripcion, estado, telefono, cargo):
        with self._conectar() as conn:
            cursor = conn.cursor()
            if password:
                pwd_hash = self._hash_password(password)
                cursor.execute("""
                    UPDATE app_users 
                    SET username = ?, password_hash = ?, role = ?, email = ?, codigo = ?, descripcion = ?, estado = ?, telefono = ?, cargo = ?
                    WHERE LOWER(username) = LOWER(?)
                """, (username_nuevo, pwd_hash, role, email, codigo, descripcion, estado, telefono, cargo, username_original))
            else:
                cursor.execute("""
                    UPDATE app_users 
                    SET username = ?, role = ?, email = ?, codigo = ?, descripcion = ?, estado = ?, telefono = ?, cargo = ?
                    WHERE LOWER(username) = LOWER(?)
                """, (username_nuevo, role, email, codigo, descripcion, estado, telefono, cargo, username_original))
            conn.commit()

    def eliminar_usuario(self, username):
        with self._conectar() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM app_users WHERE LOWER(username) = LOWER(?)", (username,))
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