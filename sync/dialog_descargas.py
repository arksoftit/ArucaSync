import tkinter as tk
from tkinter import ttk, messagebox
from remoteconnection import RemoteDBManager
from sync_down import SyncDown
import threading

class DialogDescargas(tk.Toplevel):
    def __init__(self, parent, manager_local):
        super().__init__(parent)
        self.title("Descargar Clientes desde Supabase")
        self.geometry("700x450")
        self.manager_local = manager_local
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (self.winfo_width() // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")
        self.clientes_pendientes = []

        marco = ttk.Frame(self, padding=10)
        marco.pack(fill=tk.BOTH, expand=True)

        frame_superior = ttk.Frame(marco)
        frame_superior.pack(fill=tk.X, pady=(0, 10))

        self.btn_cargar = ttk.Button(frame_superior, text="Cargar Pendientes", command=self._cargar_pendientes)
        self.btn_cargar.pack(side=tk.LEFT, padx=5)

        self.btn_descargar = ttk.Button(frame_superior, text="Descargar a DBISAM", command=self._ejecutar_descarga, state=tk.DISABLED)
        self.btn_descargar.pack(side=tk.LEFT, padx=5)

        self.lbl_estado = ttk.Label(frame_superior, text="")
        self.lbl_estado.pack(side=tk.LEFT, padx=10)

        self.tree = ttk.Treeview(marco, columns=("codigo", "descripcion", "rif", "vendedor"), show="headings")
        self.tree.heading("codigo", text="Código")
        self.tree.heading("descripcion", text="Descripción")
        self.tree.heading("rif", text="RIF")
        self.tree.heading("vendedor", text="Vendedor")
        
        self.tree.column("codigo", width=100, stretch=False)
        self.tree.column("descripcion", width=250, stretch=True)
        self.tree.column("rif", width=100, stretch=False)
        self.tree.column("vendedor", width=100, stretch=False)
        
        vsb = ttk.Scrollbar(marco, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

    def _cargar_pendientes(self):
        cfg = RemoteDBManager().load_config()
        if not cfg:
            messagebox.showwarning("Atención", "No hay configuración remota.", parent=self)
            return

        self.btn_cargar.config(state=tk.DISABLED)
        self.lbl_estado.config(text="Consultando Supabase...")
        self.tree.delete(*self.tree.get_children())
        
        try:
            sincronizador = SyncDown(self.manager_local, cfg)
            self.clientes_pendientes = sincronizador.obtener_clientes_pendientes()
            
            for c in self.clientes_pendientes:
                self.tree.insert("", tk.END, values=(c[0], c[1], c[6], c[14]))
            
            self.lbl_estado.config(text=f"{len(self.clientes_pendientes)} clientes pendientes.")
            if self.clientes_pendientes:
                self.btn_descargar.config(state=tk.NORMAL)
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self)
            self.lbl_estado.config(text="")
        finally:
            self.btn_cargar.config(state=tk.NORMAL)

    def _ejecutar_descarga(self):
        if not self.clientes_pendientes:
            return

        self.btn_descargar.config(state=tk.DISABLED)
        self.btn_cargar.config(state=tk.DISABLED)
        self.lbl_estado.config(text="Descargando a DBISAM...")
        
        cfg = RemoteDBManager().load_config()
        threading.Thread(target=self._proceso_bajada, args=(cfg,), daemon=True).start()

    def _proceso_bajada(self, cfg):
        try:
            sincronizador = SyncDown(self.manager_local, cfg)
            cantidad = sincronizador.bajar_clientes()
            self.after(0, self._fin_bajada, cantidad)
        except Exception as e:
            self.after(0, self._error_bajada, str(e))

    def _fin_bajada(self, cantidad):
        self.lbl_estado.config(text=f"Completado: {cantidad} clientes bajados.")
        messagebox.showinfo("Éxito", f"Se descargaron {cantidad} clientes a DBISAM.", parent=self)
        self._cargar_pendientes()

    def _error_bajada(self, error):
        self.lbl_estado.config(text="Error en descarga")
        messagebox.showerror("Error de Descarga", error, parent=self)
        self.btn_cargar.config(state=tk.NORMAL)

class DialogDescargasTransacciones(tk.Toplevel):
    def __init__(self, parent, manager_local):
        super().__init__(parent)
        self.title("Descargar Transacciones desde Supabase")
        self.geometry("800x450")
        self.manager_local = manager_local
        self.transacciones_pendientes = []

        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (self.winfo_width() // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")

        marco = ttk.Frame(self, padding=10)
        marco.pack(fill=tk.BOTH, expand=True)

        frame_superior = ttk.Frame(marco)
        frame_superior.pack(fill=tk.X, pady=(0, 10))

        self.btn_cargar = ttk.Button(frame_superior, text="Cargar Pendientes", command=self._cargar_pendientes)
        self.btn_cargar.pack(side=tk.LEFT, padx=5)

        self.btn_descargar = ttk.Button(frame_superior, text="Descargar a DBISAM", command=self._ejecutar_descarga, state=tk.DISABLED)
        self.btn_descargar.pack(side=tk.LEFT, padx=5)

        self.lbl_estado = ttk.Label(frame_superior, text="")
        self.lbl_estado.pack(side=tk.LEFT, padx=10)

        self.tree = ttk.Treeview(marco, columns=("tipo", "persona", "documento", "items", "bruto", "base", "impuesto", "neto", "status"), show="headings")
        
        self.tree.heading("tipo", text="Tipo")
        self.tree.heading("persona", text="Persona Contacto")
        self.tree.heading("documento", text="Documento")
        self.tree.heading("items", text="Items")
        self.tree.heading("bruto", text="Total Bruto")
        self.tree.heading("base", text="Base Imponible")
        self.tree.heading("impuesto", text="Impuesto")
        self.tree.heading("neto", text="Total Neto")
        self.tree.heading("status", text="Estatus Sync")
        
        self.tree.column("tipo", width=50, stretch=False)
        self.tree.column("persona", width=150, stretch=True)
        self.tree.column("documento", width=100, stretch=False)
        self.tree.column("items", width=50, stretch=False)
        self.tree.column("bruto", width=90, stretch=False)
        self.tree.column("base", width=90, stretch=False)
        self.tree.column("impuesto", width=80, stretch=False)
        self.tree.column("neto", width=90, stretch=False)
        self.tree.column("status", width=80, stretch=False)
        
        vsb = ttk.Scrollbar(marco, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

    def _cargar_pendientes(self):
        cfg = RemoteDBManager().load_config()
        if not cfg:
            messagebox.showwarning("Atención", "No hay configuración remota.", parent=self)
            return

        self.btn_cargar.config(state=tk.DISABLED)
        self.lbl_estado.config(text="Consultando Supabase...")
        self.tree.delete(*self.tree.get_children())
        
        try:
            sincronizador = SyncDown(self.manager_local, cfg)
            self.transacciones_pendientes = sincronizador.obtener_transacciones_pendientes()
            
            for t in self.transacciones_pendientes:
                self.tree.insert("", tk.END, values=(t[0], t[1], t[2], t[3], t[4], t[5], t[6], t[7], t[8]))
            
            self.lbl_estado.config(text=f"{len(self.transacciones_pendientes)} transacciones pendientes.")
            if self.transacciones_pendientes:
                self.btn_descargar.config(state=tk.NORMAL)
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self)
            self.lbl_estado.config(text="")
        finally:
            self.btn_cargar.config(state=tk.NORMAL)

    def _ejecutar_descarga(self):
        if not self.transacciones_pendientes:
            return

        self.btn_descargar.config(state=tk.DISABLED)
        self.btn_cargar.config(state=tk.DISABLED)
        self.lbl_estado.config(text="Descargando a DBISAM...")
        
        cfg = RemoteDBManager().load_config()
        threading.Thread(target=self._proceso_bajada, args=(cfg,), daemon=True).start()

    def _proceso_bajada(self, cfg):
        try:
            sincronizador = SyncDown(self.manager_local, cfg)
            cantidad = sincronizador.bajar_transacciones()
            self.after(0, self._fin_bajada, cantidad)
        except Exception as e:
            self.after(0, self._error_bajada, str(e))

    def _fin_bajada(self, cantidad):
        self.lbl_estado.config(text=f"Completado: {cantidad} transacciones bajadas.")
        messagebox.showinfo("Éxito", f"Se descargaron {cantidad} transacciones a DBISAM.", parent=self)
        self._cargar_pendientes()

    def _error_bajada(self, error):
        self.lbl_estado.config(text="Error en descarga")
        messagebox.showerror("Error de Descarga", error, parent=self)
        self.btn_cargar.config(state=tk.NORMAL)