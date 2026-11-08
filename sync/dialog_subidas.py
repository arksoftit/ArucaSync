import tkinter as tk
from tkinter import ttk, messagebox
import threading
from dbconnection import DBConnectionManager, ORIGENES
from remoteconnection import RemoteDBManager
from sync_data import COLUMNAS_MAP, MAPA_TABLAS, mapear_tablas, FILTROS_TABLAS, COLUMNAS_VISOR
from sync_logger import LogManager
from system_info import get_current_user, get_machine_name

class DialogSubidas(tk.Toplevel):
    def __init__(self, parent, manager):
        super().__init__(parent)
        self.title("Subir datos desde DBISAM")
        self.geometry("1000x600")
        self.manager = manager
        self.logger = None

        # Centrar la ventana
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (self.winfo_width() // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")

        # Controles superiores
        superior = ttk.Frame(self, padding=10)
        superior.pack(fill=tk.X)
        
        ttk.Label(superior, text="Tabla origen:").pack(side=tk.LEFT)
        self.cbo_origen = ttk.Combobox(superior, values=list(ORIGENES), state="readonly", width=20)
        self.cbo_origen.pack(side=tk.LEFT, padx=5)
        self.cbo_origen.set(ORIGENES[0])
        
        self.btn_cargar = ttk.Button(superior, text="Cargar", command=self._cargar)
        self.btn_cargar.pack(side=tk.LEFT, padx=5)
        
        self.btn_limpiar = ttk.Button(superior, text="Limpiar", command=self._limpiar_treeview)
        self.btn_limpiar.pack(side=tk.LEFT, padx=5)
        
        self.lbl_estado = ttk.Label(superior, text="")
        self.lbl_estado.pack(side=tk.LEFT, padx=15)

        # Controles inferiores
        frame_acciones = ttk.Frame(self, height=60)
        frame_acciones.pack(fill=tk.X, side=tk.BOTTOM, padx=10, pady=(0, 10))
        frame_acciones.pack_propagate(False)
        
        self.btn_sincronizar_datos = ttk.Button(frame_acciones, text="Sincronizar Datos", command=self._sincronizar_datos)
        self.btn_sincronizar_datos.pack(side=tk.LEFT, padx=5)

        self.barra_progreso = ttk.Progressbar(self, orient="horizontal", mode="determinate", maximum=100)
        self.barra_progreso.pack(fill=tk.X, side=tk.BOTTOM, padx=10, pady=(0, 5))

        # Treeview
        contenedor = ttk.Frame(self, padding=(10, 0, 10, 10))
        contenedor.pack(fill=tk.BOTH, expand=True)
        
        self.tree = ttk.Treeview(contenedor, show="headings")
        vsb = ttk.Scrollbar(contenedor, orient=tk.VERTICAL, command=self.tree.yview)
        hsb = ttk.Scrollbar(contenedor, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        
        contenedor.rowconfigure(0, weight=1)
        contenedor.columnconfigure(0, weight=1)

    def _sort_treeview(self, col, reverse):
        filas = [(self.tree.set(item, col), item) for item in self.tree.get_children("")]
        filas.sort(reverse=reverse)
        for index, (_, item) in enumerate(filas):
            self.tree.move(item, "", index)
        self.tree.heading(col, command=lambda: self._sort_treeview(col, not reverse))

    def _limpiar_treeview(self):
        self.tree.delete(*self.tree.get_children())

    def _cargar(self):
        origen = self.cbo_origen.get()
        ok, msg, conn = self.manager.open_connection()
        if not ok:
            messagebox.showerror("Conexión", msg, parent=self)
            return
        self.btn_cargar.config(state=tk.DISABLED)
        self.cbo_origen.config(state=tk.DISABLED)
        self.lbl_estado.config(text=f"Cargando {origen}...")
        threading.Thread(target=self._leer_origen, args=(origen, conn), daemon=True).start()

    def _leer_origen(self, origen, conn):
        try:
            columnas = [col for col, _ in COLUMNAS_VISOR[origen]]
            filtro = FILTROS_TABLAS.get(origen, "")
            if filtro:
                consulta = f"SELECT {', '.join(columnas)} FROM {origen} WHERE {filtro}"
            else:
                consulta = f"SELECT {', '.join(columnas)} FROM {origen}"
            cursor = conn.cursor()
            cursor.execute(consulta)
            filas = cursor.fetchall()
            cursor.close()
            self.after(0, self._poblar, origen, filas)
        except Exception as e:
            self.after(0, self._error_carga, str(e))

    def _poblar(self, origen, filas):
        ordenables = ("Código", "Descripción", "Razón Social", "RIF", "Status")
        self.tree.delete(*self.tree.get_children())
        definicion = COLUMNAS_VISOR[origen]
        self.tree["columns"] = tuple(col for col, _ in definicion)
        for col, encabezado in definicion:
            self.tree.heading(col, text=encabezado)
            if encabezado in ordenables:
                self.tree.heading(col, command=lambda c=col: self._sort_treeview(c, False))
            self.tree.column(col, width=120, stretch=False)
        for fila in filas:
            self.tree.insert("", tk.END, values=tuple("" if v is None else v for v in fila))
        self.lbl_estado.config(text=f"{origen}: {len(filas)} registros")
        self._habilitar_carga()

    def _error_carga(self, msg):
        self.lbl_estado.config(text="")
        messagebox.showerror("Error de lectura", msg, parent=self)
        self._habilitar_carga()

    def _habilitar_carga(self):
        self.btn_cargar.config(state=tk.NORMAL)
        self.cbo_origen.config(state="readonly")
        self.btn_sincronizar_datos.config(state=tk.NORMAL)

    def _sincronizar_datos(self):
        origen = self.cbo_origen.get()
        cfg = RemoteDBManager().load_config()
        if not cfg:
            messagebox.showwarning("Sincronización", "No hay configuración remota guardada.", parent=self)
            return
        tabla_destino, columnas_conflicto = MAPA_TABLAS[origen]
        if tabla_destino not in cfg.get("tablas", []):
            messagebox.showwarning("Sincronización", f"La tabla {tabla_destino} no está seleccionada para sincronizar.", parent=self)
            return
        
        self.logger = LogManager()
        self.logger.info(f"Inicio de sincronización. Origen: {origen}. Equipo: {get_machine_name()}. Usuario: {get_current_user()}.")
        self.barra_progreso["value"] = 0
        self.btn_cargar.config(state=tk.DISABLED)
        self.btn_sincronizar_datos.config(state=tk.DISABLED)
        self.cbo_origen.config(state=tk.DISABLED)
        self.lbl_estado.config(text=f"Sincronizando {origen}...")
        threading.Thread(target=self._ejecutar_sincronizacion, args=(origen, cfg), daemon=True).start()

    def _ejecutar_sincronizacion(self, origen, cfg):
        try:
            ok, msg, conn_local = self.manager.open_connection()
            if not ok:
                self.after(0, self._error_sincronizacion, msg)
                return
            self.logger.info(f"Conexión local establecida con {origen}.")
            tabla_destino, columnas_conflicto = MAPA_TABLAS[origen]
            pares = COLUMNAS_MAP[tabla_destino][origen]
            columnas_origen = [orig_col for _, orig_col in pares]
            
            filtro = FILTROS_TABLAS.get(origen, "")
            if filtro:
                consulta = f"SELECT {', '.join(columnas_origen)} FROM {origen} WHERE {filtro}"
            else:
                consulta = f"SELECT {', '.join(columnas_origen)} FROM {origen}"
            
            cursor = conn_local.cursor()
            cursor.execute(consulta)
            filas = cursor.fetchall()
            cursor.close()
            
            self.logger.info(f"Lectura completada: {len(filas)} filas leídas de {origen}.")
            machine = get_machine_name()
            user = get_current_user()
            columnas_destino, filas_mapeadas = mapear_tablas(origen, filas, machine, user)
            self.logger.info(f"Mapeo completado: {len(filas_mapeadas)} filas preparadas para {tabla_destino}.")
            
            remoto = RemoteDBManager()
            conn_remota = remoto.connect(
                cfg["server"], cfg["port"], cfg["database"],
                cfg["username"], cfg["password"], cfg["ssl"],
            )
            self.logger.info("Conexión remota establecida con Supabase.")
            
            nuevos, actualizados = remoto.upsert_data(
                conn_remota, tabla_destino, columnas_conflicto,
                columnas_destino, filas_mapeadas,
                progreso=self._progreso_lote,
                machine=machine,
                user=user,    
            )
            conn_remota.close()
            self.logger.info(f"Upsert completado. Nuevos: {nuevos}. Actualizados: {actualizados}.")
            self.after(0, self._exito_sincronizacion, origen, len(filas), nuevos, actualizados)
        except Exception as e:
            self.after(0, self._error_sincronizacion, str(e))

    def _progreso_lote(self, procesadas, total):
        self.logger.info(f"Lote procesado: {procesadas}/{total} filas.")
        porcentaje = int(procesadas * 100 / total) if total else 100
        self.after(0, self._actualizar_progreso, procesadas, total, porcentaje)

    def _actualizar_progreso(self, procesadas, total, porcentaje):
        self.barra_progreso["value"] = porcentaje
        self.lbl_estado.config(text=f"Sincronizando... {procesadas}/{total} ({porcentaje}%)")

    def _exito_sincronizacion(self, origen, leidas, nuevos, actualizados):
        self.barra_progreso["value"] = 100
        self.lbl_estado.config(text=f"{origen}: {leidas} leídas | {nuevos} nuevas | {actualizados} actualizadas")
        if self.logger:
            self.logger.cerrar(f"Sincronización exitosa. Leídas: {leidas}. Nuevas: {nuevos}. Actualizadas: {actualizados}.")
        messagebox.showinfo(
            "Sincronización completada",
            f"Origen: {origen}\nLeídas: {leidas}\nNuevas: {nuevos}\nActualizadas: {actualizados}",
            parent=self,
        )
        self._habilitar_carga()

    def _error_sincronizacion(self, msg):
        self.barra_progreso["value"] = 0
        self.lbl_estado.config(text="Error en sincronización")
        if self.logger:
            self.logger.error(f"Fallo en sincronización: {msg}")
            self.logger.cerrar("Sincronización finalizada con error.")
        messagebox.showerror("Sincronización", msg, parent=self)
        self._habilitar_carga()