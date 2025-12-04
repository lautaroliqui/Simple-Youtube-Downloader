import os
import sys
import customtkinter as ctk
from tkinter import filedialog, messagebox, Toplevel
import threading
import webbrowser
from app_logic import AppLogic

class YouTubeDownloaderApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("YouTube Downloader by LiquiDev")
        self.geometry("700x450")
        self.minsize(600, 400)
        
        # --- Configurar icono de la ventana ---
        if hasattr(sys, '_MEIPASS'):
            icon_path = os.path.join(sys._MEIPASS, 'L.ico')
        else:
            icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'L.ico')

        try:
            if os.path.exists(icon_path):
                self.iconbitmap(icon_path)
        except ctk.TclError as e:
            print(f"Error al establecer el icono de la ventana: {e}")

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=0)
        self.grid_rowconfigure(3, weight=0)

        # --- Variables ---
        self.entrada_url = ctk.StringVar()
        self.estado_descarga = ctk.StringVar(value="Listo para descargar.")
        self.ruta_descarga = ctk.StringVar()
        
        # Variables relacionadas con playlist para el diálogo
        self.es_playlist_var = ctk.BooleanVar(value=False)
        self.playlist_start_var = ctk.StringVar(value="")
        self.playlist_end_var = ctk.StringVar(value="")
        
        # Nuevas variables para el diálogo de playlist y cancelación
        self.playlist_confirm_result = threading.Event()
        self.playlist_dialog_instance = None
        self.cancel_event = threading.Event()

        # --- Lógica de la aplicación ---
        self.app_logic = AppLogic(
            estado_descarga_var=self.estado_descarga,
            progress_bar_widget=None,
            ruta_descarga_var=self.ruta_descarga,
            entrada_url_var=self.entrada_url,
            es_playlist_var=self.es_playlist_var,
            playlist_start_var=self.playlist_start_var,
            playlist_end_var=self.playlist_end_var,
            root_window=self,
            cancel_event=self.cancel_event
        )
        self.app_logic.cargar_configuracion()

        self.ruta_descarga.set(self.app_logic.ruta_descarga_var.get())
        if not self.ruta_descarga.get():
            self.ruta_descarga.set(self.app_logic.get_user_videos_dir())

        self.create_widgets()
        self.app_logic.progress_bar_widget = self.progress_bar
        
        # Configurar la función de cierre de la ventana
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def create_widgets(self):
        # --- Frame Principal de Entrada ---
        frame_entrada = ctk.CTkFrame(self, corner_radius=10)
        frame_entrada.pack(pady=(10, 20), padx=20, fill="both", expand=True)

        label_url = ctk.CTkLabel(frame_entrada, text="URL del Video/Playlist de YouTube:", font=ctk.CTkFont(size=14, weight="bold"))
        label_url.pack(pady=(10, 5), padx=10, anchor="w")

        frame_url_with_paste = ctk.CTkFrame(frame_entrada, fg_color="transparent")
        frame_url_with_paste.pack(pady=(0, 10), padx=10, fill="x", expand=True)

        self.button_paste = ctk.CTkButton(frame_url_with_paste, text="Pegar", command=self.paste_url, width=80, corner_radius=8)
        self.button_paste.pack(side=ctk.LEFT, padx=(0, 5))

        self.entry_url = ctk.CTkEntry(frame_url_with_paste, textvariable=self.entrada_url, placeholder_text="Pega el enlace aquí...", corner_radius=8)
        self.entry_url.pack(side=ctk.LEFT, fill="x", expand=True)

        # --- Selección de Carpeta de Destino ---
        frame_destino = ctk.CTkFrame(self, corner_radius=10)
        frame_destino.pack(pady=(0, 20), padx=20, fill="x")

        label_ruta = ctk.CTkLabel(frame_destino, text="Carpeta de Destino:", font=ctk.CTkFont(size=12, weight="bold"))
        label_ruta.grid(row=0, column=0, padx=10, pady=5, sticky="w")

        self.entry_ruta = ctk.CTkEntry(frame_destino, textvariable=self.ruta_descarga, placeholder_text="Selecciona la carpeta de descarga...", corner_radius=8)
        self.entry_ruta.grid(row=0, column=1, padx=(0, 5), pady=5, sticky="ew")

        self.button_examinar = ctk.CTkButton(frame_destino, text="Examinar", command=self.seleccionar_carpeta, corner_radius=8)
        self.button_examinar.grid(row=0, column=2, padx=(0, 10), pady=5, sticky="e")

        frame_destino.grid_columnconfigure(1, weight=1)

        # --- Botones de Descarga y Cancelar ---
        frame_botones_accion = ctk.CTkFrame(self, fg_color="transparent")
        frame_botones_accion.pack(pady=(0, 10), padx=20, fill="x")
        frame_botones_accion.grid_columnconfigure(0, weight=1)
        frame_botones_accion.grid_columnconfigure(1, weight=1)

        self.button_descargar = ctk.CTkButton(frame_botones_accion, text="Descargar", command=self.iniciar_descarga_hilo, font=ctk.CTkFont(size=16, weight="bold"), corner_radius=10)
        self.button_descargar.grid(row=0, column=0, padx=(0, 5), sticky="ew")

        self.button_cancelar = ctk.CTkButton(frame_botones_accion, text="Cancelar", command=self.cancelar_descarga, font=ctk.CTkFont(size=16, weight="bold"), corner_radius=10, hover_color="#c0392b", state="disabled")
        self.button_cancelar.grid(row=0, column=1, padx=(5, 0), sticky="ew")

        # --- Barra de Progreso y Estado ---
        self.progress_bar = ctk.CTkProgressBar(self, orientation="horizontal", progress_color="#1F6AA5", corner_radius=8)
        self.progress_bar.pack(pady=(0, 5), padx=20, fill="x")
        self.progress_bar.set(0)

        self.label_estado = ctk.CTkLabel(self, textvariable=self.estado_descarga, font=ctk.CTkFont(size=12), text_color="#3498db")
        self.label_estado.pack(pady=(0, 10), padx=20, fill="x")

        # --- Footer SIMPLIFICADO ---
        frame_footer = ctk.CTkFrame(self, fg_color="transparent")
        frame_footer.pack(pady=(10, 10), padx=20, fill="x")

        # Se mantiene solo el texto, se han eliminado los botones de LinkedIn y GitHub
        label_footer = ctk.CTkLabel(frame_footer, text="Desarrollado con ❤️ por LiquiDev", font=ctk.CTkFont(size=11, slant="italic"), text_color="#7f8c8d")
        label_footer.pack(side=ctk.BOTTOM, padx=(0, 10))

    def open_link(self, url):
        webbrowser.open_new(url)

    def iniciar_descarga_hilo(self):
        url = self.entrada_url.get()
        if not url:
            messagebox.showwarning("Advertencia", "Por favor, introduce una URL de YouTube.")
            return

        self.deshabilitar_interfaz()
        self.cancel_event.clear()
        threading.Thread(target=self._check_and_download, args=(url,)).start()

    def cancelar_descarga(self):
        self.cancel_event.set()
        self.estado_descarga.set("Cancelando descarga...")
        self.deshabilitar_interfaz(cancelando=True)

    def on_closing(self):
        if self.button_descargar.cget("state") == "disabled" and not self.cancel_event.is_set():
            if messagebox.askyesno("Cerrar aplicación", "¿Estás seguro de que quieres cerrar la aplicación? La descarga en curso se cancelará."):
                self.cancelar_descarga()
                self.destroy()
        else:
            self.destroy()

    def _check_and_download(self, url):
        self.playlist_confirm_result.clear()
        
        is_playlist, num_videos = self.app_logic.check_url_type_blocking(url)

        if self.cancel_event.is_set():
            self.after(0, self.habilitar_interfaz)
            self.after(0, lambda: self.estado_descarga.set("Descarga cancelada."))
            return

        if is_playlist:
            self.after(0, lambda: self.show_playlist_dialog(num_videos))
            self.playlist_confirm_result.wait()
            
            if self.playlist_dialog_instance and self.playlist_dialog_instance.confirmed_download:
                self.app_logic.es_playlist_var.set(True)
                self._run_download_task()
            else:
                self.after(0, self.habilitar_interfaz)
                self.after(0, lambda: self.estado_descarga.set("Descarga de playlist cancelada."))
        else:
            self.app_logic.es_playlist_var.set(False)
            self._run_download_task()

    def _run_download_task(self):
        self.app_logic.descargar_video_task()
        self.after(0, self.habilitar_interfaz)

    def seleccionar_carpeta(self):
        directorio_seleccionado = filedialog.askdirectory()
        if directorio_seleccionado:
            self.ruta_descarga.set(directorio_seleccionado)
            self.app_logic.guardar_configuracion(directorio_seleccionado)

    def paste_url(self):
        try:
            clipboard_content = self.clipboard_get()
            self.entrada_url.set(clipboard_content)
        except Exception as e:
            messagebox.showerror("Error al pegar", f"No se pudo acceder al portapapeles o está vacío: {e}")

    def deshabilitar_interfaz(self, cancelando=False):
        self.button_descargar.configure(state="disabled")
        self.button_examinar.configure(state="disabled")
        self.entry_url.configure(state="disabled")
        self.button_paste.configure(state="disabled")
        if not cancelando:
            self.button_cancelar.configure(state="normal")
        else:
            self.button_cancelar.configure(state="disabled")

    def habilitar_interfaz(self):
        self.button_descargar.configure(state="normal")
        self.button_examinar.configure(state="normal")
        self.entry_url.configure(state="normal")
        self.button_paste.configure(state="normal")
        self.button_cancelar.configure(state="disabled")
        
    def show_playlist_dialog(self, num_videos):
        self.playlist_dialog_instance = PlaylistConfirmationDialog(self, num_videos)
        self.playlist_dialog_instance.grab_set()
        self.wait_window(self.playlist_dialog_instance)
        self.playlist_confirm_result.set()

class PlaylistConfirmationDialog(ctk.CTkToplevel):
    def __init__(self, master, num_videos):
        super().__init__(master)
        self.master = master
        self.num_videos = num_videos
        self.confirmed_download = False

        self.title("Confirmar Descarga de Playlist")
        self.geometry("400x180")
        self.transient(master)
        self.grab_set()

        self.update_idletasks()
        x = master.winfo_x() + (master.winfo_width() // 2) - (self.winfo_width() // 2)
        y = master.winfo_y() + (master.winfo_height() // 2) - (self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)

        label_message = ctk.CTkLabel(self, text=f"¡Atención! Has pegado el link de una playlist con {self.num_videos} videos.\n\n¿Deseas continuar con la descarga de todos los videos?",
                                     font=ctk.CTkFont(size=14, weight="bold"), wraplength=350, justify="center")
        label_message.pack(pady=20, padx=20, fill="both", expand=True)

        frame_buttons = ctk.CTkFrame(self, fg_color="transparent")
        frame_buttons.pack(pady=(0, 15), padx=20, fill="x")
        frame_buttons.grid_columnconfigure(0, weight=1)
        frame_buttons.grid_columnconfigure(1, weight=1)

        button_yes = ctk.CTkButton(frame_buttons, text="Deseo Continuar", command=self.on_yes, corner_radius=8)
        button_yes.grid(row=0, column=0, padx=(0, 10), sticky="e")

        button_no = ctk.CTkButton(frame_buttons, text="Cancelar", command=self.on_no, fg_color="red", hover_color="#c0392b", corner_radius=8)
        button_no.grid(row=0, column=1, padx=(10, 0), sticky="w")

        self.protocol("WM_DELETE_WINDOW", self.on_no)

    def on_yes(self):
        self.confirmed_download = True
        self.destroy()

    def on_no(self):
        self.confirmed_download = False
        self.destroy()