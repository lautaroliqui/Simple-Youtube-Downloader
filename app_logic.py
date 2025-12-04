import yt_dlp
import os
import configparser
import threading
from tkinter import messagebox
import sys
import re
import shutil
import zipfile
import requests
from io import BytesIO

CONFIG_FILE = "config.ini"
config = configparser.ConfigParser()

# Expresión regular para eliminar códigos ANSI
ANSI_ESCAPE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

# Excepción personalizada para manejar la cancelación de la descarga
class DownloadCancelledError(Exception):
    pass

# --- NUEVA CLASE: GESTOR DE FFMPEG ---
class FFmpegManager:
    """Se encarga de verificar y descargar FFmpeg de forma portable."""
    
    # URL oficial de las builds recomendadas para yt-dlp
    FFMPEG_URL = "https://github.com/yt-dlp/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
    
    def __init__(self):
        # Carpeta local 'bin' donde guardaremos los ejecutables dentro del proyecto
        self.bin_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'bin')
        self.ffmpeg_exe = os.path.join(self.bin_dir, 'ffmpeg.exe')
        self.ffprobe_exe = os.path.join(self.bin_dir, 'ffprobe.exe')

    def get_ffmpeg_path(self):
        """
        Retorna la ruta del directorio que contiene ffmpeg.exe si existe localmente.
        Si no, retorna None (para que el sistema use el PATH global).
        """
        if os.path.exists(self.ffmpeg_exe):
            return self.bin_dir
        return None

    def is_installed(self):
        """Verifica si FFmpeg está en la carpeta local o en el sistema."""
        local_check = os.path.exists(self.ffmpeg_exe)
        system_check = shutil.which("ffmpeg") is not None
        return local_check or system_check

    def install_ffmpeg(self, progress_callback=None):
        """Descarga y extrae ffmpeg en la carpeta local 'bin'."""
        try:
            if not os.path.exists(self.bin_dir):
                os.makedirs(self.bin_dir)

            if progress_callback:
                progress_callback("Descargando herramientas necesarias (FFmpeg)...")

            # Descargar ZIP en memoria
            response = requests.get(self.FFMPEG_URL, stream=True)
            response.raise_for_status()
            
            # Extraer solo los .exe necesarios
            if progress_callback:
                progress_callback("Instalando componentes...")

            with zipfile.ZipFile(BytesIO(response.content)) as zf:
                for file in zf.namelist():
                    filename = os.path.basename(file)
                    # Buscamos ffmpeg.exe y ffprobe.exe dentro del zip (pueden estar en subcarpetas)
                    if filename.lower() == "ffmpeg.exe":
                        with open(self.ffmpeg_exe, 'wb') as f_out:
                            f_out.write(zf.read(file))
                    elif filename.lower() == "ffprobe.exe":
                        with open(self.ffprobe_exe, 'wb') as f_out:
                            f_out.write(zf.read(file))
            
            return True, "Instalación completada."

        except Exception as e:
            return False, f"Error al descargar componentes: {str(e)}"


class AppLogic:
    def __init__(self, estado_descarga_var, progress_bar_widget, ruta_descarga_var, entrada_url_var, es_playlist_var, playlist_start_var, playlist_end_var, root_window, cancel_event):
        self.estado_descarga_var = estado_descarga_var
        self.progress_bar_widget = progress_bar_widget
        self.ruta_descarga_var = ruta_descarga_var
        self.entrada_url_var = entrada_url_var
        self.es_playlist_var = es_playlist_var
        self.playlist_start_var = playlist_start_var
        self.playlist_end_var = playlist_end_var
        self.root_window = root_window
        self.cancel_event = cancel_event

        self.total_playlist_videos = 0
        self.playlist_title = ""
        
        # Inicializamos el gestor de FFmpeg
        self.ffmpeg_manager = FFmpegManager()

        self.cargar_configuracion()

    def cargar_configuracion(self):
        config.read(CONFIG_FILE)
        if 'Settings' in config and 'last_download_path' in config['Settings']:
            self.ruta_descarga_var.set(
                config['Settings']['last_download_path'])

    def guardar_configuracion(self, path):
        if 'Settings' not in config:
            config['Settings'] = {}
        config['Settings']['last_download_path'] = path
        with open(CONFIG_FILE, 'w') as f:
            config.write(f)

    def get_user_videos_dir(self):
        home = os.path.expanduser("~")
        video_dirs = [
            os.path.join(home, "Videos"),
            os.path.join(home, "Vídeos"),
            os.path.join(home, "My Videos")
        ]
        for d in video_dirs:
            if os.path.isdir(d):
                return d
        return os.path.join(home, "Videos")
    
    # Función auxiliar para limpiar los caracteres de escape ANSI
    def _clean_ansi(self, text):
        return ANSI_ESCAPE.sub('', text)

    # --- FUNCIÓN DE LIMPIEZA DE ARCHIVOS TEMPORALES ---
    def _limpiar_archivos_temporales(self, carpeta_destino, es_playlist=False, playlist_title=""):
        try:
            target_dir = os.path.join(carpeta_destino, playlist_title) if es_playlist and playlist_title else carpeta_destino
            
            # Buscar y eliminar archivos temporales
            if os.path.exists(target_dir):
                for filename in os.listdir(target_dir):
                    if filename.endswith(".part") or filename.endswith(".ytdl"):
                        file_path = os.path.join(target_dir, filename)
                        os.remove(file_path)
                        print(f"Archivo temporal eliminado: {file_path}")
            
            # Si es una playlist, también eliminar la carpeta vacía si no tiene archivos completos
            if es_playlist and playlist_title and os.path.exists(target_dir) and not os.listdir(target_dir):
                os.rmdir(target_dir)
                print(f"Directorio de playlist vacío eliminado: {target_dir}")
        except Exception as e:
            print(f"Error al limpiar archivos temporales: {e}")
    
    def check_url_type_blocking(self, url):
        self.root_window.after(0, lambda: self.estado_descarga_var.set("Verificando tipo de URL..."))
        
        try:
            ydl_opts = {
                'quiet': True,
                'extract_flat': True,
                'force_generic_extractor': False,
                'verbose': False,
                'logtostderr': False,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)

                if info.get('_type') == 'playlist':
                    entries = info.get('entries', [])
                    num_videos = len(entries) if entries else 0
                    self.total_playlist_videos = num_videos

                    self.playlist_title = info.get('title', 'Unknown_Playlist').strip()
                    self.playlist_title = re.sub(r'[\\/:*?"<>|]', '', self.playlist_title)
                    self.playlist_title = self.playlist_title.replace(' ', '_')
                    self.playlist_title = self.playlist_title.replace('__', '_')
                    self.playlist_title = self.playlist_title.strip('_')

                    return True, num_videos
                else:
                    self.total_playlist_videos = 0
                    self.playlist_title = ""
                    return False, 0
        except yt_dlp.utils.DownloadError as e:
            error_msg = f"Error al verificar URL (inválida/inaccesible): {self._clean_ansi(str(e))}"
            self.root_window.after(0, lambda: self.estado_descarga_var.set(error_msg))
            self.root_window.after(0, lambda: messagebox.showerror("Error de URL", error_msg))
            self.root_window.after(0, self.root_window.habilitar_interfaz) 
            return False, 0
        except Exception as e:
            error_msg = f"Error inesperado al verificar URL: {self._clean_ansi(str(e))}"
            self.root_window.after(0, lambda: self.estado_descarga_var.set(error_msg))
            self.root_window.after(0, lambda: messagebox.showerror("Error", error_msg))
            self.root_window.after(0, self.root_window.habilitar_interfaz)
            return False, 0

    def hook_progreso(self, d):
        # Levantamos la excepción personalizada si se ha solicitado la cancelación
        if self.cancel_event.is_set():
            raise DownloadCancelledError("Descarga cancelada por el usuario.")
            
        if d['status'] == 'downloading':
            total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate')
            downloaded_bytes = d.get('downloaded_bytes')

            if total_bytes and downloaded_bytes is not None:
                progress_value = (downloaded_bytes / total_bytes)
                self.root_window.after(0, lambda: self.progress_bar_widget.set(progress_value))
            
            p_raw = d.get('_percent_str', 'N/A')
            s_raw = d.get('_speed_str', 'N/A')
            e_raw = d.get('_eta_str', 'N/A')

            p = self._clean_ansi(p_raw)
            s = self._clean_ansi(s_raw)
            e = self._clean_ansi(e_raw)

            playlist_info = ""
            if self.es_playlist_var.get() and self.total_playlist_videos > 0:
                current_index = d.get('info_dict', {}).get('playlist_index')
                if current_index:
                    playlist_info = f" ({current_index} de {self.total_playlist_videos})"

            video_title = d.get('info_dict', {}).get('title', '...')
            display_title = self._clean_ansi(video_title)
            
            self.root_window.after(0, lambda: self.estado_descarga_var.set(f"Descargando{playlist_info}: '{display_title}' - {p} a {s} ETA: {e}"))
        
        elif d['status'] == 'finished':
            video_title = d.get('info_dict', {}).get('title', 'video')
            playlist_finished_info = ""
            if self.es_playlist_var.get() and self.total_playlist_videos > 0:
                current_index = d.get('info_dict', {}).get('playlist_index')
                if current_index:
                    playlist_finished_info = f" ({current_index} de {self.total_playlist_videos})"

            self.root_window.after(0, lambda: self.estado_descarga_var.set(f"Post-procesando '{video_title}'{playlist_finished_info} (esto puede tardar)..."))
            self.root_window.after(0, lambda: self.progress_bar_widget.set(1.0))
            
        elif d['status'] == 'error':
            self.root_window.after(0, lambda: self.estado_descarga_var.set(
                f"Error durante la descarga: {self._clean_ansi(d.get('error', 'Desconocido'))}"))
            self.root_window.after(0, lambda: self.progress_bar_widget.set(0.0))

    def descargar_video_task(self):
        url = self.entrada_url_var.get()
        carpeta_destino = self.ruta_descarga_var.get()
        es_playlist = self.es_playlist_var.get()
        playlist_start = self.playlist_start_var.get()
        playlist_end = self.playlist_end_var.get()
        
        if not url:
            self.root_window.after(0, lambda: messagebox.showwarning("Advertencia", "Por favor, introduce una URL de YouTube."))
            return "habilitar_interfaz"
        if not carpeta_destino:
            self.root_window.after(0, lambda: messagebox.showwarning("Advertencia", "Por favor, selecciona una carpeta de destino."))
            return "habilitar_interfaz"

        # --- VERIFICACIÓN E INSTALACIÓN DE FFMPEG ---
        if not self.ffmpeg_manager.is_installed():
            self.root_window.after(0, lambda: self.estado_descarga_var.set("Descargando componentes necesarios (FFmpeg)..."))
            
            # Callback para actualizar el texto del estado desde el hilo
            def update_status(msg):
                self.root_window.after(0, lambda: self.estado_descarga_var.set(msg))

            exito, mensaje = self.ffmpeg_manager.install_ffmpeg(progress_callback=update_status)
            
            if not exito:
                self.root_window.after(0, lambda: messagebox.showerror("Error de Dependencias", mensaje))
                return "habilitar_interfaz"

        # Obtenemos la ruta local si existe, o None si usa la del sistema
        ffmpeg_local_path = self.ffmpeg_manager.get_ffmpeg_path()
        # ---------------------------------------------

        self.root_window.after(0, lambda: self.estado_descarga_var.set(f"Preparando descarga ({'Playlist' if es_playlist else 'Video'})..."))
        self.root_window.after(0, lambda: self.progress_bar_widget.set(0.0))

        ydl_opts = {
            'outtmpl': os.path.join(carpeta_destino, '%(title)s.%(ext)s'),
            'progress_hooks': [self.hook_progreso],
            'restrictfilenames': True,
            'postprocessors': [],
            'verbose': False,
            'logtostderr': False,
            'noplaylist': not es_playlist,
            'compat_opts': set(),
            'embed_thumbnail': True,
            'embed_metadata': True,
            # 'ffmpeg_location': YA NO ESTÁ HARDCODEADO AQUÍ
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best',
            'merge_output_format': 'mp4',
            'ignoreerrors': True, # Se mantiene siempre en True para manejar videos eliminados.
        }

        # Si estamos usando nuestra versión portable, le decimos a yt-dlp dónde está
        if ffmpeg_local_path:
            ydl_opts['ffmpeg_location'] = ffmpeg_local_path

        if es_playlist:
            try:
                start_num = int(playlist_start) if playlist_start else None
                end_num = int(playlist_end) if playlist_end else None

                if start_num is not None and start_num <= 0:
                    self.root_window.after(0, lambda: messagebox.showwarning("Advertencia", "El número de inicio de la playlist debe ser mayor que 0."))
                    return "habilitar_interfaz"
                if end_num is not None and end_num <= 0:
                    self.root_window.after(0, lambda: messagebox.showwarning("Advertencia", "El número de fin de la playlist debe ser mayor que 0."))
                    return "habilitar_interfaz"
                if start_num is not None and end_num is not None and start_num > end_num:
                    self.root_window.after(0, lambda: messagebox.showwarning("Advertencia", "El número de inicio no puede ser mayor que el de fin."))
                    return "habilitar_interfaz"
            except ValueError:
                self.root_window.after(0, lambda: messagebox.showwarning("Advertencia", "El rango de la playlist debe ser un número válido."))
                return "habilitar_interfaz"
            
            ydl_opts['playlist_start'] = start_num
            ydl_opts['playlist_end'] = end_num
            # Aquí se define el outtmpl para las playlists
            ydl_opts['outtmpl'] = os.path.join(carpeta_destino, self.playlist_title, '%(title)s.%(ext)s')
            
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            self.root_window.after(0, lambda: self.estado_descarga_var.set(
                f"¡Descarga completa! Archivo(s) guardado(s) en: {carpeta_destino}"))
            self.root_window.after(0, lambda: self.entrada_url_var.set(""))
            self.guardar_configuracion(carpeta_destino)
            return "habilitar_interfaz"
        
        except DownloadCancelledError:
            self.root_window.after(0, lambda: self.estado_descarga_var.set("Descarga cancelada."))
            self.root_window.after(0, lambda: self.progress_bar_widget.set(0.0))
            return "habilitar_interfaz"
        
        except yt_dlp.utils.DownloadError as e:
            error_message = f"Error de descarga: {self._clean_ansi(str(e))}"
            self.root_window.after(0, lambda: self.estado_descarga_var.set(error_message))
            self.root_window.after(0, lambda: messagebox.showerror("Error de Descarga", error_message))
            print(error_message, file=sys.stderr)
            return "habilitar_interfaz"
        
        except Exception as e:
            error_message = f"Ocurrió un error inesperado: {self._clean_ansi(str(e))}"
            self.root_window.after(0, lambda: self.estado_descarga_var.set(error_message))
            self.root_window.after(0, lambda: messagebox.showerror("Error", error_message))
            print(error_message, file=sys.stderr)
            return "habilitar_interfaz"
        finally:
            # --- Lógica de limpieza en el bloque `finally` ---
            self._limpiar_archivos_temporales(
                carpeta_destino, 
                es_playlist=es_playlist,
                playlist_title=self.playlist_title
            )