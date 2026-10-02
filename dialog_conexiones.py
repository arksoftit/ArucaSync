import os
import tkinter as tk
from tkinter import ttk, messagebox

from dbconnection import DBConnectionManager, ORIGENES

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "conexiones.json")


class DialogConexiones(tk.Toplevel):
    def __init__(self, parent, manager=None):
        super().__init__(parent)
        self.title("Conexiones DBISAM por origen")
        self.resizable(False, False)
        self.manager = manager or DBConnectionManager(CONFIG_PATH)
        self.resultado = None

        marco = ttk.Frame(self, padding=10)
        marco.grid()

        ttk.Label(marco, text="Origen:").grid(row=0, column=0, sticky="w", pady=2)
        self.cbo_origen = ttk.Combobox(marco, values=list(ORIGENES), state="readonly", width=30)
        self.cbo_origen.grid(row=0, column=1, pady=2)
        self.cbo_origen.bind("<<ComboboxSelected>>", lambda e: self._cargar_activa())

        ttk.Label(marco, text="DSN:").grid(row=1, column=0, sticky="w", pady=2)
        self.cbo_dsn = ttk.Combobox(marco, values=self.manager.get_dsn_list(), state="readonly", width=30)
        self.cbo_dsn.grid(row=1, column=1, pady=2)

        ttk.Label(marco, text="Usuario:").grid(row=2, column=0, sticky="w", pady=2)
        self.txt_usuario = ttk.Entry(marco, width=32)
        self.txt_usuario.grid(row=2, column=1, pady=2)

        ttk.Label(marco, text="Contraseña:").grid(row=3, column=0, sticky="w", pady=2)
        self.txt_password = ttk.Entry(marco, width=32, show="*")
        self.txt_password.grid(row=3, column=1, pady=2)

        botones = ttk.Frame(marco)
        botones.grid(row=4, column=0, columnspan=2, pady=8)
        ttk.Button(botones, text="Probar conexión", command=self._probar).grid(row=0, column=0, padx=4)
        ttk.Button(botones, text="Guardar", command=self._guardar).grid(row=0, column=1, padx=4)
        ttk.Button(botones, text="Cerrar", command=self.destroy).grid(row=0, column=2, padx=4)

        self.cbo_origen.set(ORIGENES[0])
        self._cargar_activa()

        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (self.winfo_width() // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")

    def _cargar_activa(self):
        origen = self.cbo_origen.get()
        activa = self.manager.get_active_connection(origen)
        if activa:
            self.cbo_dsn.set(activa.get("dsn", ""))
            self.txt_usuario.delete(0, tk.END)
            self.txt_usuario.insert(0, activa.get("usuario", ""))
            self.txt_password.delete(0, tk.END)
            self.txt_password.insert(0, activa.get("password", ""))

    def _probar(self):
        dsn = self.cbo_dsn.get().strip()
        usuario = self.txt_usuario.get().strip()
        password = self.txt_password.get()
        if not dsn:
            messagebox.showwarning("Atención", "Seleccione un DSN.", parent=self)
            return
        ok, msg, conn = self.manager.connect(dsn, usuario, password)
        if ok:
            conn.close()
        messagebox.showinfo("Prueba de conexión", msg, parent=self)

    def _guardar(self):
        dsn = self.cbo_dsn.get().strip()
        usuario = self.txt_usuario.get().strip()
        password = self.txt_password.get()
        origen = self.cbo_origen.get()
        if not dsn:
            messagebox.showwarning("Atención", "Seleccione un DSN.", parent=self)
            return
        self.manager.save_connection(dsn, usuario, password, origen)
        self.resultado = origen
        messagebox.showinfo("Conexión guardada", f"Conexión activa para el origen {origen}.", parent=self)
        self.destroy()