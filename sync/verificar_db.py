import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "sync_control.db")

def verificar_estructura():
    if not os.path.exists(DB_PATH):
        print(f"No se encontró la base de datos en la ruta: {DB_PATH}")
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tablas = cursor.fetchall()
    
    print("--- Tablas encontradas en sync_control.db ---")
    for tabla in tablas:
        print(f"- {tabla[0]}")
        cursor.execute(f"PRAGMA table_info({tabla[0]});")
        columnas = cursor.fetchall()
        for col in columnas:
            print(f"    * {col[1]} ({col[2]})")
            
    conn.close()

if __name__ == "__main__":
    verificar_estructura()