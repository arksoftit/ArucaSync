import tkinter as tk
from tkinter import ttk, messagebox

from remoteconnection import RemoteDBManager


class DialogConexionRemota(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Conexión Remota PostgreSQL (Supabase)")
        self.resizable(False, False)
        self.manager = RemoteDBManager()
        self.tablas_seleccionadas = []

        marco = ttk.Frame(self, padding=10)
        marco.grid()
        ttk.Label(marco, text="Servidor:").grid(row=0, column=0, sticky="w", pady=2)
        self.txt_server = ttk.Entry(marco, width=40)
        self.txt_server.grid(row=0, column=1, pady=2)
        ttk.Label(marco, text="Puerto:").grid(row=1, column=0, sticky="w", pady=2)
        self.txt_port = ttk.Entry(marco, width=40)
        self.txt_port.grid(row=1, column=1, pady=2)
        ttk.Label(marco, text="Base de datos:").grid(row=2, column=0, sticky="w", pady=2)
        self.txt_database = ttk.Entry(marco, width=40)
        self.txt_database.grid(row=2, column=1, pady=2)
        ttk.Label(marco, text="Usuario:").grid(row=3, column=0, sticky="w", pady=2)
        self.txt_username = ttk.Entry(marco, width=40)
        self.txt_username.grid(row=3, column=1, pady=2)
        ttk.Label(marco, text="Contraseña:").grid(row=4, column=0, sticky="w", pady=2)
        self.txt_password = ttk.Entry(marco, width=40, show="*")
        self.txt_password.grid(row=4, column=1, pady=2)
        self.chk_ssl = tk.BooleanVar(value=True)
        ttk.Checkbutton(marco, text="Usar SSL", variable=self.chk_ssl).grid(row=5, column=1, sticky="w", pady=2)
        botones = ttk.Frame(marco)
        botones.grid(row=6, column=0, columnspan=2, pady=8)
        ttk.Button(botones, text="Probar conexión", command=self._probar).grid(row=0, column=0, padx=4)
        ttk.Button(botones, text="Guardar", command=self._guardar).grid(row=0, column=1, padx=4)
        ttk.Button(botones, text="Cerrar", command=self.destroy).grid(row=0, column=2, padx=4)
        
        self.tree_tablas = ttk.Treeview(marco, columns=("check", "tabla"), show="headings", height=8)
        self.tree_tablas.heading("check", text="Sincronizar")
        self.tree_tablas.heading("tabla", text="Tabla")
        self.tree_tablas.column("check", width=80, stretch=False)
        self.tree_tablas.column("tabla", width=280, stretch=False)
        self.tree_tablas.grid(row=7, column=0, columnspan=2, pady=(0, 4))
        self.tree_tablas.bind("<Button-1>", self._toggle_check)

        cfg = self.manager.load_config()
        if cfg:
            self.txt_server.insert(0, cfg.get("server", ""))
            self.txt_port.insert(0, str(cfg.get("port", "")))
            self.txt_database.insert(0, cfg.get("database", ""))
            self.txt_username.insert(0, cfg.get("username", ""))
            self.txt_password.insert(0, cfg.get("password", ""))
            self.chk_ssl.set(bool(cfg.get("ssl", True)))
            self.tablas_seleccionadas = list(cfg.get("tablas", []))

        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (self.winfo_width() // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")
    
    def _probar(self):
        server = self.txt_server.get().strip()
        port = self.txt_port.get().strip()
        database = self.txt_database.get().strip()
        username = self.txt_username.get().strip()
        password = self.txt_password.get()
        if not server or not port or not database or not username:
            messagebox.showwarning("Atención", "Complete servidor, puerto, base de datos y usuario.", parent=self)
            return
        if not port.isdigit():
            messagebox.showwarning("Atención", "El puerto debe ser numérico.", parent=self)
            return
        try:
            conn = self.manager.connect(server, port, database, username, password, self.chk_ssl.get())
            tablas = self.manager.list_tables(conn)
            conn.close()
        except Exception as e:
            messagebox.showerror("Prueba de conexión", str(e), parent=self)
            return
        self._poblar_tablas(tablas)
        messagebox.showinfo("Prueba de conexión", f"Conexión exitosa. {len(tablas)} tablas en el esquema public.", parent=self)

    def _guardar(self):
        server = self.txt_server.get().strip()
        port = self.txt_port.get().strip()
        database = self.txt_database.get().strip()
        username = self.txt_username.get().strip()
        password = self.txt_password.get()
        if not server or not port or not database or not username:
            messagebox.showwarning("Atención", "Complete servidor, puerto, base de datos y usuario.", parent=self)
            return
        if not port.isdigit():
            messagebox.showwarning("Atención", "El puerto debe ser numérico.", parent=self)
            return
        self.manager.save_config(server, int(port), database, username, password, self.chk_ssl.get(), self.tablas_seleccionadas)
        messagebox.showinfo("Conexión guardada", "Parámetros remotos guardados en remotedb.json.", parent=self)
        self.destroy()
        
    def _poblar_tablas(self, tablas):
        self.tree_tablas.delete(*self.tree_tablas.get_children())
        for nombre in tablas:
            marca = "[X]" if nombre in self.tablas_seleccionadas else "[ ]"
            self.tree_tablas.insert("", tk.END, iid=nombre, values=(marca, nombre))

    def _toggle_check(self, evento):
        fila = self.tree_tablas.identify_row(evento.y)
        columna = self.tree_tablas.identify_column(evento.x)
        if not fila or columna != "#1":
            return
        if fila != "arc_clientes":
            return
        if fila in self.tablas_seleccionadas:
            self.tablas_seleccionadas.remove(fila)
            marca = "[ ]"
        else:
            self.tablas_seleccionadas.append(fila)
            marca = "[X]"
        self.tree_tablas.set(fila, "check", marca)