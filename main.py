import os
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from dbconnection import DBConnectionManager, ORIGENES
from dialog_conexiones import DialogConexiones
from dialog_conexion_remota import DialogConexionRemota
from remoteconnection import RemoteDBManager
from sync_data import COLUMNAS_MAP, mapear_clientes
from sync_logger import LogManager
from system_info import (
    APP_DATE,
    APP_DEVELOPER,
    get_app_version,
    get_current_user,
    get_date_audit,
    get_machine_name,
)

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "conexiones.json")

COLUMNAS_VISOR = {
    "SClientes": [
        ("FC_CODIGO", "Código"),
        ("FC_DESCRIPCION", "Razón Social"),
        ("FC_RIF", "RIF"),
        ("FC_STATUS", "Status"),
        ("FC_DIRECCION1", "Dirección Fiscal"),
        ("FC_DIRECCION2", "Dirección Postal"),
        ("FC_TELEFONO", "Teléfono Ppal"),
        ("FC_TELEFAX", "Teléfono Alternativo"),
        ("FC_CONTACTO", "Persona Contacto"),
    ],
    "TClientes": [
        ("CLT_CODIGO", "Código"),
        ("CLT_DESCRIPCION", "Razón Social"),
        ("CLT_RIF", "RIF"),
        ("CLT_STATUS", "Status"),
        ("CLT_DIRECCION1", "Dirección Fiscal"),
        ("CLT_DIRECCION2", "Dirección Postal"),
        ("CLT_TELEFONO", "Teléfono Ppal"),
        ("CLT_TELEFAX", "Teléfono Alternativo"),
        ("CLT_CONTACTO", "Persona Contacto"),
    ],
}


class AppSincronizador(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Sincronizador ArkToolsWeb")
        self._center_window(1000, 600)
        self.manager = DBConnectionManager(CONFIG_PATH)
        self.logger = None
        self.protocol("WM_DELETE_WINDOW", self._salir)

        barra = tk.Menu(self)
        menu_conexiones = tk.Menu(barra, tearoff=0)
        menu_conexiones.add_command(label="Conexión Local", command=self._abrir_dialogo_local)
        menu_conexiones.add_command(label="Conexión Remota", command=self._abrir_dialogo_remoto)
        barra.add_cascade(label="Conexiones", menu=menu_conexiones)
        menu_ayuda = tk.Menu(barra, tearoff=0)
        menu_ayuda.add_command(label="Acerca de...", command=self.mostrar_acerca)
        barra.add_cascade(label="Ayuda", menu=menu_ayuda)
        menu_salida = tk.Menu(barra, tearoff=0)
        menu_salida.add_command(label="Cerrar Aplicación", command=self._confirmar_salida)
        barra.add_cascade(label="Salir", menu=menu_salida)
        self.config(menu=barra)

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

        self._create_status_bar()

        self.frame_acciones = ttk.Frame(self, height=60)
        self.frame_acciones.pack(fill=tk.X, side=tk.BOTTOM, padx=10, pady=(0, 10))
        self.frame_acciones.pack_propagate(False)
        self.btn_sincronizar_datos = ttk.Button(self.frame_acciones, text="Sincronizar Datos", command=self._sincronizar_clientes)
        self.btn_sincronizar_datos.pack(side=tk.LEFT, padx=5)

        self.barra_progreso = ttk.Progressbar(self, orient="horizontal", mode="determinate", maximum=100)
        self.barra_progreso.pack(fill=tk.X, side=tk.BOTTOM, padx=10, pady=(0, 5))

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

        self.actualizar_barra_estado()

    def _center_window(self, width, height):
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")

    def _abrir_dialogo_local(self):
        DialogConexiones(self, manager=self.manager)

    def _abrir_dialogo_remoto(self):
        DialogConexionRemota(self)

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
        ok, msg, conn = self.manager.open_connection(origen)
        if not ok:
            messagebox.showerror("Conexión", msg)
            return
        self.btn_cargar.config(state=tk.DISABLED)
        self.cbo_origen.config(state=tk.DISABLED)
        self.lbl_estado.config(text=f"Cargando {origen}...")
        threading.Thread(target=self._leer_origen, args=(origen, conn), daemon=True).start()

    def _leer_origen(self, origen, conn):
        try:
            columnas = [col for col, _ in COLUMNAS_VISOR[origen]]
            consulta = f"SELECT {', '.join(columnas)} FROM {origen}"
            cursor = conn.cursor()
            cursor.execute(consulta)
            filas = cursor.fetchall()
            cursor.close()
            self.after(0, self._poblar, origen, filas)
        except Exception as e:
            self.after(0, self._error_carga, str(e))

    def _poblar(self, origen, filas):
        ordenables = ("Código", "Razón Social", "RIF", "Status")
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
        messagebox.showerror("Error de lectura", msg)
        self._habilitar_carga()

    def _habilitar_carga(self):
        self.btn_cargar.config(state=tk.NORMAL)
        self.cbo_origen.config(state="readonly")
        self.btn_sincronizar_datos.config(state=tk.NORMAL)

    def _sincronizar_clientes(self):
        origen = self.cbo_origen.get()
        cfg = RemoteDBManager().load_config()
        if not cfg:
            messagebox.showwarning("Sincronización", "No hay configuración remota guardada. Use Conexiones > Conexión Remota.", parent=self)
            return
        if "arc_clientes" not in cfg.get("tablas", []):
            messagebox.showwarning("Sincronización", "La tabla arc_clientes no está seleccionada para sincronizar.", parent=self)
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
            ok, msg, conn_local = self.manager.open_connection(origen)
            if not ok:
                self.after(0, self._error_sincronizacion, msg)
                return
            self.logger.info(f"Conexión local establecida con {origen}.")
            pares = COLUMNAS_MAP["arc_clientes"][origen]
            columnas_origen = [orig_col for _, orig_col in pares]
            consulta = f"SELECT {', '.join(columnas_origen)} FROM {origen}"
            cursor = conn_local.cursor()
            cursor.execute(consulta)
            filas = cursor.fetchall()
            cursor.close()
            self.logger.info(f"Lectura completada: {len(filas)} filas leídas de {origen}.")
            machine = get_machine_name()
            user = get_current_user()
            columnas_destino, filas_mapeadas = mapear_clientes(origen, filas, machine, user)
            self.logger.info(f"Mapeo completado: {len(filas_mapeadas)} filas preparadas para arc_clientes.")
            remoto = RemoteDBManager()
            conn_remota = remoto.connect(
                cfg["server"], cfg["port"], cfg["database"],
                cfg["username"], cfg["password"], cfg["ssl"],
            )
            self.logger.info("Conexión remota establecida con Supabase.")
            nuevos, actualizados = remoto.upsert_data(
                conn_remota, "arc_clientes", "cli_codigo",
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

    def _create_status_bar(self):
        self.status_bar = ttk.Frame(self)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        self.status_var = tk.StringVar()
        self.status_var.set("Iniciando...")
        self.status_label = ttk.Label(
            self.status_bar,
            textvariable=self.status_var,
            relief=tk.SUNKEN,
            anchor=tk.CENTER,
            padding=(5, 2)
        )
        self.status_label.pack(fill=tk.X)

    def actualizar_barra_estado(self):
        try:
            fecha = get_date_audit()
            user = get_current_user()
            equipo = get_machine_name()
            version = get_app_version()
            info_sesion = (
                f" SESIÓN ACTIVA | Usuario: {user} | "
                f"Equipo: {equipo} | Fecha: {fecha} | Versión: {version}"
            )
            self.status_var.set(info_sesion)
        except Exception as e:
            self.status_var.set(f"Error al actualizar barra de estado: {e}")

    def mostrar_acerca(self):
        info_acerca = (
            f"ArkToolsWeb\n"
            f"Versión: {get_app_version()}\n"
            f"Desarrollador: {APP_DEVELOPER}\n"
            f"Fecha: {APP_DATE}\n\n"
            f"Usuario actual: {get_current_user()}\n"
            f"Equipo: {get_machine_name()}\n"
            f"Fecha de auditoría: {get_date_audit()}"
        )
        messagebox.showinfo("Acerca de ArkToolsWeb", info_acerca)

    def _confirmar_salida(self):
        if messagebox.askyesno("Salir", "¿Desea cerrar la aplicación?"):
            self._salir()

    def _salir(self):
        self.manager.disconnect()
        self.destroy()


if __name__ == "__main__":
    app = AppSincronizador()
    app.mainloop()