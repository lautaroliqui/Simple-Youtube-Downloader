import customtkinter as ctk
from gui_components import YouTubeDownloaderApp

# --- Configuración de CustomTkinter (global) ---
ctk.set_appearance_mode("System")  # "System" (default), "Dark", "Light"
ctk.set_default_color_theme("blue")  # "blue" (default), "green", "dark-blue"

if __name__ == "__main__":
    app = YouTubeDownloaderApp()
    app.mainloop()