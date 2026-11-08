import tkinter as tk
from tkinter import ttk, messagebox
from remoteconnection import RemoteDBManager
from sync_status import StatusSynchronizer
import threading

class DialogSyncStatus(tk.Toplevel):
    def __init__(self, parent, manager_local):
        super().__init__(parent)
        self.title("Sincronizar Cambios de Estado desde DBISAM")
        self.geometry("850x450")
        self.manager_local = manager_local
        self.cambios_pendientes = []

        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (self.winfo_width() // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")

        marco = ttk.Frame(self, padding=10)
        marco.pack(fill=tk.BOTH, expand=True)

        frame_superior = ttk.Frame(marco)
        frame_superior.pack(fill=tk.X, pady=(0, 10))

        self.btn_cargar = ttk.Button(frame_superior, text="Cargar Procesados", command=self._cargar_procesados)
        self.btn_cargar.pack(side=tk.LEFT, padx=5)

        self.btn_actualizar = ttk.Button(frame_superior, text="Actualizar Estados a PostgreSQL", command=self._ejecutar_actualizacion, state=tk.DISABLED)
        self.btn_actualizar.pack(side=tk.LEFT, padx=5)

        self.lbl_estado = ttk.Label(frame_superior, text="")
        self.lbl_estado.pack(side=tk.LEFT, padx=10)

        self.tree = ttk.Treeview(marco, columns=("documento", "cliente", "fecha", "status_ant", "status_act"), show="headings")
        
        self.tree.heading("documento", text="Documento")
        self.tree.heading("cliente", text="Cliente")
        self.tree.heading("fecha", text="Fecha Emisión")
        self.tree.heading("status_ant", text="Status Anterior")
        self.tree.heading("status_act", text="Status Actual")
        
        self.tree.column("documento", width=130, stretch=False)
        self.tree.column("cliente", width=250, stretch=True)
        self.tree.column("fecha", width=100, stretch=False)
        self.tree.column("status_ant", width=100, stretch=False)
        self.tree.column("status_act", width=100, stretch=False)
        
        vsb = ttk.Scrollbar(marco, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

    def _traducir_status(self, status_num):
        mapa = {1: "1 (Procesada)", 2: "2 (Espera)", 3: "3 (Eliminada)", 4: "4 (Tránsito)", 5: "5 (Anulada)"}
        return mapa.get(status_num, str(status_num))

    def _cargar_procesados(self):
        cfg = RemoteDBManager().load_config()
        if not cfg:
            messagebox.showwarning("Atención", "No hay configuración remota.", parent=self)
            return

        self.btn_cargar.config(state=tk.DISABLED)
        self.btn_actualizar.config(state=tk.DISABLED)
        self.lbl_estado.config(text="Consultando cambios en DBISAM...")
        self.tree.delete(*self.tree.get_children())
        self.cambios_pendientes = []

        threading.Thread(target=self._proceso_carga, args=(cfg,), daemon=True).start()

    def _proceso_carga(self, cfg):
        try:
            sincronizador = StatusSynchronizer(self.manager_local, cfg)
            self.cambios_pendientes = sincronizador.obtener_cambios_pendientes()
            self.after(0, self._fin_carga)
        except Exception as e:
            self.after(0, self._error, str(e))

    def _fin_carga(self):
        self.tree.delete(*self.tree.get_children())
        
        for c in self.cambios_pendientes:
            self.tree.insert("", tk.END, values=(
                c["documento"],
                c["cliente"],
                c["fecha"],
                self._traducir_status(c["status_anterior"]),
                self._traducir_status(c["status_actual"])
            ))

        cantidad = len(self.cambios_pendientes)
        self.lbl_estado.config(text=f"{cantidad} transacciones con cambios de estado.")
        
        if cantidad > 0:
            self.btn_actualizar.config(state=tk.NORMAL)
        
        self.btn_cargar.config(state=tk.NORMAL)

    def _ejecutar_actualizacion(self):
        if not self.cambios_pendientes:
            return

        self.btn_actualizar.config(state=tk.DISABLED)
        self.btn_cargar.config(state=tk.DISABLED)
        self.lbl_estado.config(text="Actualizando PostgreSQL...")
        
        cfg = RemoteDBManager().load_config()
        threading.Thread(target=self._proceso_actualizacion, args=(cfg,), daemon=True).start()

    def _proceso_actualizacion(self, cfg):
        try:
            sincronizador = StatusSynchronizer(self.manager_local, cfg)
            cantidad = sincronizador.actualizar_estados(self.cambios_pendientes)
            self.after(0, self._fin_actualizacion, cantidad)
        except Exception as e:
            self.after(0, self._error, str(e))

    def _fin_actualizacion(self, cantidad):
        self.lbl_estado.config(text=f"Completado: {cantidad} estados actualizados.")
        messagebox.showinfo("Éxito", f"Se actualizaron {cantidad} estados en PostgreSQL.", parent=self)
        self._cargar_procesados()

    def _error(self, mensaje):
        self.lbl_estado.config(text="Error en el proceso")
        messagebox.showerror("Error", mensaje, parent=self)
        self.btn_cargar.config(state=tk.NORMAL)
        if self.cambios_pendientes:
            self.btn_actualizar.config(state=tk.NORMAL)