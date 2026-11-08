import tkinter as tk
from tkinter import ttk, messagebox
from arucasyncdb import ArucaSyncDBManager

class DialogLogin(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Iniciar Sesión - ArucaSync")
        self.resizable(False, False)
        self.db = ArucaSyncDBManager()
        self.autenticado = False
        self.rol_usuario = None

        self.update_idletasks()
        x = parent.winfo_screenwidth() // 2 - 150
        y = parent.winfo_screenheight() // 2 - 100
        self.geometry(f"+{x}+{y}")

        marco = ttk.Frame(self, padding=20)
        marco.pack(fill=tk.BOTH, expand=True)

        ttk.Label(marco, text="Usuario:").grid(row=0, column=0, sticky="w", pady=5)
        self.txt_user = ttk.Entry(marco, width=25)
        self.txt_user.grid(row=0, column=1, pady=5)

        ttk.Label(marco, text="Contraseña:").grid(row=1, column=0, sticky="w", pady=5)
        self.txt_pass = ttk.Entry(marco, width=25, show="*")
        self.txt_pass.grid(row=1, column=1, pady=5)

        btn_frame = ttk.Frame(marco)
        btn_frame.grid(row=2, column=0, columnspan=2, pady=15)
        
        ttk.Button(btn_frame, text="Ingresar", command=self._validar).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Salir", command=self._cancelar).pack(side=tk.LEFT, padx=5)

        self.protocol("WM_DELETE_WINDOW", self._cancelar)
        self.transient(parent)
        self.grab_set()
        self.focus_force()
        self.txt_user.focus_set()
        self.txt_pass.bind('<Return>', lambda e: self._validar())

    def _validar(self):
        usuario = self.txt_user.get().strip()
        password = self.txt_pass.get()

        if not usuario or not password:
            messagebox.showwarning("Atención", "Debe ingresar usuario y contraseña.", parent=self)
            return

        rol = self.db.validar_usuario(usuario, password)

        if rol:
            self.autenticado = True
            self.rol_usuario = rol
            self.destroy()
        else:
            messagebox.showerror("Error", "Usuario o contraseña incorrectos.", parent=self)
            self.txt_pass.delete(0, tk.END)
            self.txt_pass.focus_set()

    def _cancelar(self):
        self.autenticado = False
        self.destroy()