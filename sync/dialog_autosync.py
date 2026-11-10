import tkinter as tk
from tkinter import ttk, messagebox
import os
import json
from datetime import datetime

class DialogAutosync(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Configuración de Automatización")
        self.geometry("750x650")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        parent.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (750 // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (650 // 2)
        self.geometry(f"+{x}+{y}")

        self.logs_path = os.path.join(os.path.dirname(__file__), "..", "logs")
        self.config_path = os.path.join(os.path.dirname(__file__), "..", "config", "autosync_config.json")

        self.tablas_subida = [
            "arc_clientes", "arc_depositos", "arc_categorias", "arc_inventario", 
            "arc_vendedores", "arc_transacciones", "arc_detalletranvtas", 
            "arc_inv_costos_precios", "arc_existencia_actual", "arc_zonas"
        ]
        self.tablas_bajada = ["arc_clientes", "arc_transacciones", "arc_detalletranvtas"]
        
        self.check_subidas = {}
        self.check_bajadas = {}

        self._create_widgets()
        self._cargar_configuracion()

    def _create_widgets(self):
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self.tab_subidas = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_subidas, text="Subidas")
        self._crear_tab_tablas(self.tab_subidas, self.tablas_subida, self.check_subidas)
        self._crear_rango_fechas(self.tab_subidas, "sub")

        self.tab_bajadas = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_bajadas, text="Bajadas")
        self._crear_tab_tablas(self.tab_bajadas, self.tablas_bajada, self.check_bajadas)
        self._crear_rango_fechas(self.tab_bajadas, "baj")

        self.tab_ciclos = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_ciclos, text="Ciclos")
        self._crear_tab_ciclos(self.tab_ciclos)

        self.tab_logs = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_logs, text="Logs")
        self._crear_tab_logs(self.tab_logs)

        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(btn_frame, text="Guardar Configuración", command=self._guardar).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Salir", command=self.destroy).pack(side=tk.RIGHT, padx=5)

    def _crear_tab_tablas(self, parent, lista_tablas, dict_checks):
        frame_botones = ttk.Frame(parent)
        frame_botones.pack(fill=tk.X, pady=5)
        
        ttk.Button(frame_botones, text="Seleccionar Todo", command=lambda: self._toggle_todo(dict_checks, True)).pack(side=tk.LEFT, padx=5)
        ttk.Button(frame_botones, text="Deseleccionar Todo", command=lambda: self._toggle_todo(dict_checks, False)).pack(side=tk.LEFT, padx=5)

        frame_lista = ttk.Frame(parent, padding=10)
        frame_lista.pack(fill=tk.BOTH, expand=True)

        for i, tabla in enumerate(lista_tablas):
            var = tk.BooleanVar(value=True)
            dict_checks[tabla] = var
            ttk.Checkbutton(frame_lista, text=tabla, variable=var).grid(row=i, column=0, sticky="w", pady=2)

    def _crear_rango_fechas(self, parent, prefijo):
        frame_fechas = ttk.Labelframe(parent, text="Rango de Fechas (Aplica para arc_transacciones y arc_detalletranvtas)", padding=10)
        frame_fechas.pack(fill=tk.X, side=tk.BOTTOM, pady=10, padx=10)

        ttk.Label(frame_fechas, text="Desde (YYYY-MM-DD):").grid(row=0, column=0, sticky="w", padx=5)
        ent_desde = ttk.Entry(frame_fechas, width=15)
        ent_desde.grid(row=0, column=1, padx=5)

        ttk.Label(frame_fechas, text="Hasta (YYYY-MM-DD):").grid(row=0, column=2, sticky="w", padx=5)
        ent_hasta = ttk.Entry(frame_fechas, width=15)
        ent_hasta.grid(row=0, column=3, padx=5)

        if prefijo == "sub":
            self.ent_sub_desde = ent_desde
            self.ent_sub_hasta = ent_hasta
        else:
            self.ent_baj_desde = ent_desde
            self.ent_baj_hasta = ent_hasta

    def _crear_tab_ciclos(self, parent):
        frame_tipo = ttk.Labelframe(parent, text="Tipo de Horario", padding=10)
        frame_tipo.pack(fill=tk.X, pady=5, padx=10)

        self.var_tipo_ciclo = tk.StringVar(value="Diario")
        self.cmb_tipo_ciclo = ttk.Combobox(frame_tipo, textvariable=self.var_tipo_ciclo, 
                                           values=["Cada Hora", "Diario", "Semanal", "Definido por el usuario"], 
                                           state="readonly", width=30)
        self.cmb_tipo_ciclo.pack(anchor="w")
        self.cmb_tipo_ciclo.bind("<<ComboboxSelected>>", self._toggle_ciclo_custom)

        self.frame_temporizador = ttk.Labelframe(parent, text="Temporizador y Rango de Ejecución", padding=10)
        self.frame_temporizador.pack(fill=tk.X, pady=5, padx=10)

        ttk.Label(self.frame_temporizador, text="Temporizador (minutos):").grid(row=0, column=0, sticky="w", pady=5)
        self.cmb_minutos = ttk.Combobox(self.frame_temporizador, values=["5", "10", "15", "30", "60"], width=10, state="readonly")
        self.cmb_minutos.set("10")
        self.cmb_minutos.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        ttk.Label(self.frame_temporizador, text="Límite inferior (HH:MM):").grid(row=1, column=0, sticky="w", pady=5)
        self.ent_hora_inicio = ttk.Entry(self.frame_temporizador, width=10)
        self.ent_hora_inicio.insert(0, "07:00")
        self.ent_hora_inicio.grid(row=1, column=1, padx=5, pady=5, sticky="w")

        ttk.Label(self.frame_temporizador, text="Límite superior (HH:MM):").grid(row=2, column=0, sticky="w", pady=5)
        self.ent_hora_fin = ttk.Entry(self.frame_temporizador, width=10)
        self.ent_hora_fin.insert(0, "20:00")
        self.ent_hora_fin.grid(row=2, column=1, padx=5, pady=5, sticky="w")

        self._toggle_ciclo_custom()

    def _crear_tab_logs(self, parent):
        frame_superior = ttk.Frame(parent)
        frame_superior.pack(fill=tk.X, pady=5, padx=10)
        ttk.Button(frame_superior, text="Actualizar Lista de Logs", command=self._cargar_logs).pack(side=tk.LEFT)

        paned = ttk.PanedWindow(parent, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        frame_izq = ttk.Frame(paned)
        frame_der = ttk.Frame(paned)
        paned.add(frame_izq, weight=1)
        paned.add(frame_der, weight=3)

        self.tree_logs = ttk.Treeview(frame_izq, columns=("archivo",), show="headings", selectmode="browse")
        self.tree_logs.heading("archivo", text="Archivo de Log")
        self.tree_logs.column("archivo", width=200)
        self.tree_logs.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scroll_izq = ttk.Scrollbar(frame_izq, orient=tk.VERTICAL, command=self.tree_logs.yview)
        scroll_izq.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree_logs.configure(yscrollcommand=scroll_izq.set)

        self.txt_contenido = tk.Text(frame_der, wrap=tk.WORD, state=tk.DISABLED)
        self.txt_contenido.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scroll_der = ttk.Scrollbar(frame_der, orient=tk.VERTICAL, command=self.txt_contenido.yview)
        scroll_der.pack(side=tk.RIGHT, fill=tk.Y)
        self.txt_contenido.configure(yscrollcommand=scroll_der.set)

        self.tree_logs.bind("<<TreeviewSelect>>", self._mostrar_log_seleccionado)
        
        self._cargar_logs()

    def _cargar_logs(self):
        for item in self.tree_logs.get_children():
            self.tree_logs.delete(item)
            
        if not os.path.exists(self.logs_path):
            return

        archivos = [f for f in os.listdir(self.logs_path) if f.endswith(".log")]
        archivos.sort(reverse=True)

        for archivo in archivos:
            self.tree_logs.insert("", tk.END, values=(archivo,))

    def _mostrar_log_seleccionado(self, event):
        seleccion = self.tree_logs.selection()
        if not seleccion:
            return
            
        archivo = self.tree_logs.item(seleccion[0])['values'][0]
        ruta_completa = os.path.join(self.logs_path, archivo)

        try:
            with open(ruta_completa, "r", encoding="utf-8") as f:
                contenido = f.read()
                
            self.txt_contenido.config(state=tk.NORMAL)
            self.txt_contenido.delete(1.0, tk.END)
            self.txt_contenido.insert(tk.END, contenido)
            self.txt_contenido.config(state=tk.DISABLED)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo leer el archivo: {e}", parent=self)

    def _toggle_ciclo_custom(self, event=None):
        if self.var_tipo_ciclo.get() == "Definido por el usuario":
            self.cmb_minutos.config(state="readonly")
        else:
            self.cmb_minutos.config(state="disabled")

    def _toggle_todo(self, dict_checks, estado):
        for var in dict_checks.values():
            var.set(estado)

    def _cargar_configuracion(self):
        if not os.path.exists(self.config_path):
            return
            
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            for tabla, var in self.check_subidas.items():
                var.set(tabla in data.get("tablas_subida", []))
                
            for tabla, var in self.check_bajadas.items():
                var.set(tabla in data.get("tablas_bajada", []))
                
            self.var_tipo_ciclo.set(data.get("tipo_ciclo", "Diario"))
            self.cmb_minutos.set(data.get("minutos", "10"))
            self.ent_hora_inicio.delete(0, tk.END)
            self.ent_hora_inicio.insert(0, data.get("hora_inicio", "07:00"))
            self.ent_hora_fin.delete(0, tk.END)
            self.ent_hora_fin.insert(0, data.get("hora_fin", "20:00"))
            
            self.ent_sub_desde.delete(0, tk.END)
            self.ent_sub_desde.insert(0, data.get("fecha_desde_sub", ""))
            self.ent_sub_hasta.delete(0, tk.END)
            self.ent_sub_hasta.insert(0, data.get("fecha_hasta_sub", ""))

            self.ent_baj_desde.delete(0, tk.END)
            self.ent_baj_desde.insert(0, data.get("fecha_desde_baj", ""))
            self.ent_baj_hasta.delete(0, tk.END)
            self.ent_baj_hasta.insert(0, data.get("fecha_hasta_baj", ""))

            self._toggle_ciclo_custom()
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo cargar la configuración previa: {e}", parent=self)

    def _guardar(self):
        try:
            h_inicio = self.ent_hora_inicio.get().strip()
            h_fin = self.ent_hora_fin.get().strip()
            
            datetime.strptime(h_inicio, "%H:%M")
            datetime.strptime(h_fin, "%H:%M")
            
            tablas_sub = [t for t, var in self.check_subidas.items() if var.get()]
            tablas_baj = [t for t, var in self.check_bajadas.items() if var.get()]
            
            config_data = {
                "tablas_subida": tablas_sub,
                "tablas_bajada": tablas_baj,
                "tipo_ciclo": self.var_tipo_ciclo.get(),
                "minutos": self.cmb_minutos.get(),
                "hora_inicio": h_inicio,
                "hora_fin": h_fin,
                "fecha_desde_sub": self.ent_sub_desde.get().strip(),
                "fecha_hasta_sub": self.ent_sub_hasta.get().strip(),
                "fecha_desde_baj": self.ent_baj_desde.get().strip(),
                "fecha_hasta_baj": self.ent_baj_hasta.get().strip()
            }
            
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(config_data, f, indent=4)
                
            messagebox.showinfo("Éxito", "Configuración guardada correctamente.", parent=self)
        except ValueError:
            messagebox.showerror("Error", "Las horas deben tener el formato HH:MM (ej. 07:00, 20:00).", parent=self)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo guardar la configuración: {e}", parent=self)