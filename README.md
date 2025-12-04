# YouTube Downloader (Python/CustomTkinter)

Una aplicación de escritorio moderna y ligera para descargar videos y playlists de YouTube. Desarrollada con Python y CustomTkinter.

## 🚀 Características

* **Interfaz Moderna:** GUI limpia y responsiva usando `customtkinter`.
* **Gestión Inteligente de Dependencias:** El software verifica automáticamente si FFmpeg está instalado. Si no lo encuentra, descarga una versión portable (local) automáticamente sin ensuciar el sistema operativo del usuario.
* **Soporte de Playlists:** Detecta enlaces de listas de reproducción completas y permite descargas por lotes con un solo clic.
* **Formatos:** Conversión automática a MP4 para máxima compatibilidad.
* **Multi-hilo:** La interfaz no se congela durante las descargas, manteniendo una experiencia fluida.

## 🛠️ Tecnologías Usadas

* **Python 3.10+**
* **CustomTkinter** (Interfaz Gráfica)
* **yt-dlp** (Motor de descarga robusto)
* **FFmpeg** (Procesamiento multimedia)
* **Requests** (Gestión de descargas internas)

## 📦 Instalación y Uso

1.  **Clonar el repositorio:**
    ```bash
    git clone https://github.com/lautaroliqui/simple-youtube-downloader.git
    cd TU_REPO
    ```

2.  **Instalar dependencias:**
    Se recomienda usar un entorno virtual.
    ```bash
    pip install -r requirements.txt
    ```

3.  **Ejecutar la aplicación:**
    ```bash
    python main.py
    ```

## ⚠️ Nota Legal

Esta herramienta fue creada exclusivamente con fines educativos para el aprendizaje sobre desarrollo de software, manejo de hilos (threading), interfaces gráficas y gestión de archivos en Python.

El usuario es responsable de respetar los Términos de Servicio de YouTube y las leyes de derechos de autor vigentes en su país. El autor no se hace responsable del mal uso de esta herramienta.

## 👤 Autor

**LiquiDev**
