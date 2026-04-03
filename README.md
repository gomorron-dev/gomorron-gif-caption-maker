# Gomorron Caption Maker 💜

[cite_start]**Gomorron Caption Maker** is a professional-grade desktop application designed for high-efficiency media captioning[cite: 1]. [cite_start]It provides a sleek, minimalistic interface to quickly overlay bold, impact-style text onto images, GIFs, and videos while maintaining precise control over typography and output quality.

![Preview](preview.png)

## Core Features

* [cite_start]**Multi-Format Support:** Seamlessly process static images, animated GIFs, and various video formats including MP4, MOV, AVI, and WebM[cite: 1, 4].
* [cite_start]**Intelligent Typography:** Features automatic font scaling and intelligent text wrapping to ensure captions remain perfectly legible across any resolution.
* [cite_start]**High-Performance Rendering:** Utilizes a multi-threaded architecture to ensure the UI remains responsive even during intensive video frame extraction.
* [cite_start]**Dynamic Theming:** Includes professionally curated color profiles such as Dark, Light, Mocha, and Midnight Blue to suit your aesthetic.
* [cite_start]**Production-Ready Output:** Built-in LZW compression estimation and scaling tools help you manage file sizes for social media compatibility.
* [cite_start]**Clipboard Integration:** Supports "Ctrl+V" for instant image pasting and a dedicated feature to copy finished GIFs directly to your clipboard.

---

## Technical Stack

[cite_start]The tool is engineered with a robust Python stack designed for reliability and performance:
* [cite_start]**UI Framework:** PySide6 (Qt for Python) for a modern, hardware-accelerated interface.
* [cite_start]**Image Processing:** Pillow (PIL) for advanced frame manipulation, font rendering, and compositing.
* [cite_start]**Video Engine:** Integrated `ffmpeg` via `imageio-ffmpeg` for high-fidelity frame extraction.

---

## Installation & Deployment

### Running from Source
1.  [cite_start]Ensure Python 3.9+ is installed[cite: 4].
2.  Install the required dependencies:
    ```bash
    pip install PySide6 Pillow imageio-ffmpeg
    ```
3.  Launch the application:
    ```bash
    python main.py
    ```

### Building the Executable
[cite_start]To compile the project into a standalone, portable executable without a console window, use the provided PyInstaller specification[cite: 5, 8]:

```bash
pyinstaller GomorronCaptionMaker.spec
