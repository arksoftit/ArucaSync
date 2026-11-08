import tkinter as tk
from tkinter import ttk, messagebox
from arucasyncdb import ArucaSyncDBManager
from dialog_main_browser import DialogMainBrowser

class DialogUsers(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Gestión de Usuarios")
        self.geometry("720x580")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        parent.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (720 // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (580 // 2)
        self.geometry(f"+{x}+{y}")

        self.current_username = None
        self.db = ArucaSyncDBManager()

        self._create_widgets()

    def _create_widgets(self):
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        frame_general = ttk.Labelframe(main_frame, text="Datos del Usuario", padding=10)
        frame_general.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        ttk.Label(frame_general, text="Código (ID/Cédula):").grid(row=0, column=0, sticky="w", pady=3)
        self.ent_codigo = ttk.Entry(frame_general, width=25)
        self.ent_codigo.grid(row=0, column=1, padx=5, pady=3, sticky="w")

        ttk.Label(frame_general, text="Usuario:").grid(row=1, column=0, sticky="w", pady=3)
        self.ent_username = ttk.Entry(frame_general, width=25)
        self.ent_username.grid(row=1, column=1, padx=5, pady=3, sticky="w")

        ttk.Label(frame_general, text="Contraseña:").grid(row=2, column=0, sticky="w", pady=3)
        self.ent_password = ttk.Entry(frame_general, width=25, show="*")
        self.ent_password.grid(row=2, column=1, padx=5, pady=3, sticky="w")

        ttk.Label(frame_general, text="Descripción:").grid(row=3, column=0, sticky="w", pady=3)
        self.ent_descripcion = ttk.Entry(frame_general, width=50)
        self.ent_descripcion.grid(row=3, column=1, columnspan=2, padx=5, pady=3, sticky="ew")

        ttk.Label(frame_general, text="Email:").grid(row=4, column=0, sticky="w", pady=3)
        self.ent_email = ttk.Entry(frame_general, width=40)
        self.ent_email.grid(row=4, column=1, columnspan=2, padx=5, pady=3, sticky="ew")

        ttk.Label(frame_general, text="Teléfono:").grid(row=5, column=0, sticky="w", pady=3)
        self.ent_telefono = ttk.Entry(frame_general, width=25)
        self.ent_telefono.grid(row=5, column=1, padx=5, pady=3, sticky="w")

        ttk.Label(frame_general, text="Cargo:").grid(row=6, column=0, sticky="w", pady=3)
        self.ent_cargo = ttk.Entry(frame_general, width=40)
        self.ent_cargo.grid(row=6, column=1, columnspan=2, padx=5, pady=3, sticky="ew")

        ttk.Label(frame_general, text="Estado:").grid(row=7, column=0, sticky="w", pady=3)
        self.cmb_estado = ttk.Combobox(frame_general, values=["Activo", "Inactivo"], state="readonly", width=15)
        self.cmb_estado.grid(row=7, column=1, padx=5, pady=3, sticky="w")
        self.cmb_estado.set("Activo")

        ttk.Label(frame_general, text="Rol:").grid(row=8, column=0, sticky="w", pady=3)
        self.cmb_rol = ttk.Combobox(frame_general, values=["Superusuario", "Administrador"], state="readonly", width=15)
        self.cmb_rol.grid(row=8, column=1, padx=5, pady=3, sticky="w")
        self.cmb_rol.set("Administrador")

        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=1, column=0, sticky="ew", pady=15, padx=10)

        ttk.Button(btn_frame, text="Guardar", command=self._guardar).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Editar", command=self._editar).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Borrar", command=self._borrar).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Cancelar", command=self._cancelar).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Salir", command=self._salir).pack(side=tk.RIGHT, padx=5)

    def _guardar(self):
        try:
            codigo = self.ent_codigo.get().strip()
            username = self.ent_username.get().strip()
            password = self.ent_password.get()
            descripcion = self.ent_descripcion.get().strip()
            email = self.ent_email.get().strip()
            telefono = self.ent_telefono.get().strip()
            cargo = self.ent_cargo.get().strip()
            estado = 0 if self.cmb_estado.get() == "Activo" else 1
            role = self.cmb_rol.get()

            if not username:
                messagebox.showwarning("Advertencia", "El campo 'Usuario' es obligatorio.")
                return

            if self.current_username is None:
                if not password:
                    messagebox.showwarning("Advertencia", "Debe asignar una contraseña al nuevo usuario.")
                    return
                self.db.crear_usuario(username, password, role, email, codigo, descripcion, estado, telefono, cargo)
            else:
                self.db.actualizar_usuario(self.current_username, username, password, role, email, codigo, descripcion, estado, telefono, cargo)

            messagebox.showinfo("Éxito", "Usuario guardado correctamente.")
            self._limpiar_campos()
        except Exception as e:
            messagebox.showerror("Error en Guardar", f"{type(e).__name__}: {e}")

    def _editar(self):
        config_users = {
            'titulo': 'Seleccionar Usuario para Editar',
            'tabla': 'app_users',
            'columnas': [
                ('Código', 'codigo', 120),
                ('Usuario', 'username', 150),
                ('Descripción', 'descripcion', 250),
                ('Estado', 'estado', 100),
                ('Rol', 'role', 150)
            ],
            'campos_busqueda': [
                ('Código', 'codigo'),
                ('Usuario', 'username'),
                ('Descripción', 'descripcion')
            ],
            'id_field': 'username',
            'orden_por': 'codigo ASC'
        }
        dialog = DialogMainBrowser(self, config_users)
        self.wait_window(dialog)
        if dialog.resultado:
            self.current_username = dialog.resultado['id']
            self._cargar_datos(self.current_username)

    def _cargar_datos(self, username):
        try:
            u = self.db.obtener_usuario(username)
            if not u:
                messagebox.showwarning("Advertencia", "Usuario no encontrado.")
                self._limpiar_campos()
                return

            self.ent_username.delete(0, tk.END)
            self.ent_username.insert(0, u[0] or "")
            self.ent_password.delete(0, tk.END)
            self.cmb_rol.set(u[2] if u[2] else "Administrador")
            self.ent_email.delete(0, tk.END)
            self.ent_email.insert(0, u[3] or "")
            self.ent_codigo.delete(0, tk.END)
            self.ent_codigo.insert(0, u[4] or "")
            self.ent_descripcion.delete(0, tk.END)
            self.ent_descripcion.insert(0, u[5] or "")
            self.cmb_estado.set("Inactivo" if u[6] == 1 else "Activo")
            self.ent_telefono.delete(0, tk.END)
            self.ent_telefono.insert(0, u[7] or "")
            self.ent_cargo.delete(0, tk.END)
            self.ent_cargo.insert(0, u[8] or "")
        except Exception as e:
            messagebox.showerror("Error al Cargar", f"{type(e).__name__}: {e}")

    def _borrar(self):
        config_users = {
            'titulo': 'Seleccionar Usuario para Borrar',
            'tabla': 'app_users',
            'columnas': [
                ('Código', 'codigo', 120),
                ('Usuario', 'username', 150),
                ('Descripción', 'descripcion', 250),
                ('Estado', 'estado', 100),
                ('Rol', 'role', 150)
            ],
            'campos_busqueda': [
                ('Código', 'codigo'),
                ('Usuario', 'username'),
                ('Descripción', 'descripcion')
            ],
            'id_field': 'username',
            'orden_por': 'codigo ASC'
        }
        dialog = DialogMainBrowser(self, config_users)
        self.wait_window(dialog)
        if dialog.resultado:
            username = dialog.resultado['id']
            if messagebox.askyesno("Confirmar Borrado", f"¿Eliminar el usuario '{username}'? Esta acción no se puede deshacer."):
                self.db.eliminar_usuario(username)
                messagebox.showinfo("Éxito", "Usuario eliminado correctamente.")
                self._limpiar_campos()

    def _cancelar(self):
        if any([self.ent_codigo.get(), self.ent_username.get(), self.ent_password.get(), self.ent_descripcion.get(), self.ent_email.get(), self.ent_telefono.get(), self.ent_cargo.get()]):
            if not messagebox.askyesno("Confirmar Cancelar", "¿Descartar todos los cambios?"):
                return
        self._limpiar_campos()

    def _salir(self):
        if messagebox.askyesno("Confirmar Salida", "¿Cerrar este diálogo?"):
            self.destroy()

    def _limpiar_campos(self):
        self.ent_codigo.delete(0, tk.END)
        self.ent_username.delete(0, tk.END)
        self.ent_password.delete(0, tk.END)
        self.ent_descripcion.delete(0, tk.END)
        self.ent_email.delete(0, tk.END)
        self.ent_telefono.delete(0, tk.END)
        self.ent_cargo.delete(0, tk.END)
        self.cmb_estado.set("Activo")
        self.cmb_rol.set("Administrador")
        self.current_username = None