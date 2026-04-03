# Gomorron Caption Maker 💜

**Gomorron Caption Maker** is a professional-grade desktop application designed for high-efficiency media captioning. It provides a sleek, minimalistic interface to quickly overlay bold, impact-style text onto images, GIFs, and videos while maintaining precise control over typography and output quality.

![Preview](preview.png)

## Core Features

- **Multi-Format Support:** Seamlessly process static images, animated GIFs, and various video formats including MP4, MOV, AVI, and WebM.
- **Intelligent Typography:** Features automatic font scaling and intelligent text wrapping to ensure captions remain perfectly legible across any resolution.
- **High-Performance Rendering:** Utilizes a multi-threaded architecture to ensure the UI remains responsive even during intensive video frame extraction.
- **Dynamic Theming:** Includes professionally curated color profiles such as Dark, Light, Mocha, and Midnight Blue to suit your aesthetic.
- **Production-Ready Output:** Built-in LZW compression estimation and scaling tools help you manage file sizes for social media compatibility.
- **Clipboard Integration:** Supports "Ctrl+V" for instant image pasting and a dedicated feature to copy finished GIFs directly to your clipboard.

---

## Technical Stack

The tool is engineered with a robust Python stack designed for reliability and performance:
- **UI Framework:** PySide6 (Qt for Python) for a modern, hardware-accelerated interface.
- **Image Processing:** Pillow (PIL) for advanced frame manipulation, font rendering, and compositing.
- **Video Engine:** Integrated `ffmpeg` via `imageio-ffmpeg` for high-fidelity frame extraction.

---

## Installation & Deployment

### Running from Source
1.  Ensure Python 3.9+ is installed[cite: 4].
2.  Install the required dependencies:
    ```bash
    pip install PySide6 Pillow imageio-ffmpeg
    ```
3.  Launch the application:
    ```bash
    python main.py
    ```

### Building the Executable
To compile the project into a standalone, portable executable without a console window, use the provided PyInstaller specification:

```bash
pyinstaller GomorronCaptionMaker.spec
