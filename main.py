#!/usr/bin/env python3
"""
Gomorron Caption Maker — by Gomorronmannen 💜
Dark, minimalistic, slick caption GIF / WebP tool.
"""

import os
import sys
import io
import subprocess
import tempfile
import math
from pathlib import Path

from PySide6.QtCore import (
    Qt, QThread, Signal, QObject, QPropertyAnimation,
    QEasingCurve, QTimer, QSize, QPoint, QByteArray
)
from PySide6.QtGui import (
    QPixmap, QFont, QColor, QPalette, QIcon, QDragEnterEvent, QDropEvent,
    QKeySequence, QShortcut, QImage, QPainter, QLinearGradient, QPen,
    QMovie, QImageReader
)
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QCheckBox, QComboBox,
    QFileDialog, QGroupBox, QScrollArea, QSizePolicy, QSpinBox,
    QFrame, QProgressBar, QMessageBox, QSplitter, QSlider,
    QGraphicsOpacityEffect, QDialog, QColorDialog
)
from PIL import Image, ImageDraw, ImageFont, ImageSequence

# ── Output directory ──────────────────────────────────────────────────────────
if getattr(sys, "frozen", False):
    _BASE = Path(sys.executable).parent
else:
    _BASE = Path(__file__).parent

OUTPUT_DIR = _BASE / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

# ── Font search paths ─────────────────────────────────────────────────────────
IMPACT_PATHS = [
    "C:/Windows/Fonts/impact.ttf",
    "C:/Windows/Fonts/Impact.ttf",
    "/Library/Fonts/Impact.ttf",
    "/System/Library/Fonts/Impact.ttf",
    "/usr/share/fonts/truetype/msttcorefonts/Impact.ttf",
    "/usr/share/fonts/truetype/impact.ttf",
    "/usr/share/fonts/Impact.ttf",
    "/usr/local/share/fonts/Impact.ttf",
    str(Path(__file__).parent / "Impact.ttf"),
    str(Path(__file__).parent / "impact.ttf"),
    str(Path(__file__).parent / "fonts" / "Impact.ttf"),
]
FALLBACK_FONTS = [
    "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
]

# ── Themes ────────────────────────────────────────────────────────────────────
THEMES = {
    "Dark": {
        "bg":          "#0d0d0f",
        "panel":       "#111114",
        "card":        "#18181c",
        "border":      "#252528",
        "border_hi":   "#3a3a40",
        "accent":      "#9b5de5",
        "accent2":     "#7b2fd4",
        "accent_glow": "rgba(155,93,229,0.18)",
        "text":        "#f0f0f4",
        "subtext":     "#72727a",
        "success":     "#3ecf8e",
        "error":       "#f43f5e",
        "input_bg":    "#0a0a0c",
    },
    "Light": {
        "bg":          "#f4f4f7",
        "panel":       "#ffffff",
        "card":        "#ebebef",
        "border":      "#d0d0d8",
        "border_hi":   "#aaaabc",
        "accent":      "#7b2fd4",
        "accent2":     "#5a1fa0",
        "accent_glow": "rgba(123,47,212,0.12)",
        "text":        "#18181c",
        "subtext":     "#72727a",
        "success":     "#2aad72",
        "error":       "#d9304e",
        "input_bg":    "#ffffff",
    },
    "Mocha": {
        "bg":          "#1e1b18",
        "panel":       "#252220",
        "card":        "#2e2a27",
        "border":      "#3d3733",
        "border_hi":   "#5c544d",
        "accent":      "#c98a3e",
        "accent2":     "#a56c28",
        "accent_glow": "rgba(201,138,62,0.18)",
        "text":        "#f0ebe4",
        "subtext":     "#8a7e72",
        "success":     "#6daf6d",
        "error":       "#d95f5f",
        "input_bg":    "#18160f",
    },
    "Midnight Blue": {
        "bg":          "#0a0e1a",
        "panel":       "#0f1525",
        "card":        "#141c30",
        "border":      "#1e2840",
        "border_hi":   "#2e3f60",
        "accent":      "#3d8ef0",
        "accent2":     "#2060c0",
        "accent_glow": "rgba(61,142,240,0.18)",
        "text":        "#e8eef8",
        "subtext":     "#6070a0",
        "success":     "#3ecf8e",
        "error":       "#f43f5e",
        "input_bg":    "#070b15",
    },
}

# Active theme (mutable dict, gets updated when theme changes)
C = dict(THEMES["Dark"])

# ── Font utilities ────────────────────────────────────────────────────────────

def find_font(custom=None):
    if custom and os.path.isfile(custom):
        return custom, "impact" in custom.lower()
    for p in IMPACT_PATHS:
        if os.path.isfile(p):
            return p, True
    for p in FALLBACK_FONTS:
        if os.path.isfile(p):
            return p, False
    raise FileNotFoundError("No font found. Place Impact.ttf next to main.py.")


def wrap_text(text, font, max_width):
    words = text.split()
    lines, current = [], ""
    for word in words:
        candidate = (current + " " + word).strip()
        bbox = font.getbbox(candidate)
        if bbox[2] - bbox[0] <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or [text]


def draw_outlined(draw, x, y, text, font, thickness, fg, bg):
    for dx in range(-thickness, thickness + 1):
        for dy in range(-thickness, thickness + 1):
            if dx or dy:
                draw.text((x + dx, y + dy), text, font=font, fill=bg)
    draw.text((x, y), text, font=font, fill=fg)


def render_caption_box(image_width, text, font_size, padding, font_path, is_impact,
                        outline, outline_thickness, uppercase, align="center",
                        bg_color=(255, 255, 255), text_color=(0, 0, 0)):
    """Render a caption strip and return it as an RGB Image.

    align — 'left' | 'center' | 'right'  (controls horizontal text placement)
    """
    if uppercase:
        text = text.upper()
    font = ImageFont.truetype(font_path, font_size)
    inner_width = image_width - 2 * padding
    lines = wrap_text(text, font, inner_width)
    ascent, descent = font.getmetrics()
    line_h = ascent + descent
    spacing = max(4, int(font_size * 0.08))
    total_h = len(lines) * line_h + (len(lines) - 1) * spacing
    box_h = total_h + 2 * padding

    box = Image.new("RGB", (image_width, box_h), bg_color)
    draw = ImageDraw.Draw(box)
    y = padding
    for line in lines:
        bbox = font.getbbox(line)
        text_w = bbox[2] - bbox[0]
        if align == "left":
            x = padding
        elif align == "right":
            x = image_width - text_w - padding
        else:  # center (default)
            x = (image_width - text_w) // 2
        if outline:
            draw_outlined(draw, x, y, line, font, outline_thickness, text_color, bg_color)
        else:
            draw.text((x, y), line, font=font, fill=text_color)
        y += line_h + spacing
    return box


def composite_parts(parts, bg_color=(255, 255, 255)):
    """Stack image parts vertically onto a canvas filled with bg_color."""
    total_h = sum(p.height for p in parts)
    w = parts[0].width
    out = Image.new("RGB", (w, total_h), bg_color)
    y = 0
    for p in parts:
        out.paste(p, (0, y))
        y += p.height
    return out


def hex_to_rgb(hex_str):
    h = hex_str.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def format_size(size_bytes):
    """Human-readable file size: B → KB → MB → GB."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    kb = size_bytes / 1024
    if kb < 1024:
        return f"{kb:.1f} KB"
    mb = kb / 1024
    if mb >= 1000:
        return f"{mb / 1024:.2f} GB"
    return f"{mb:.2f} MB"


# ── ffmpeg resolver (auto-download via imageio-ffmpeg) ────────────────────────

def get_ffmpeg():
    """
    Returns path to ffmpeg binary.
    Priority:
      1. ffmpeg / ffmpeg.exe sitting next to the app (manual override)
      2. imageio-ffmpeg managed binary (auto-downloaded on first use)
      3. ffmpeg on system PATH
    Raises RuntimeError if nothing is found.
    """
    import shutil

    # 1. Next to the exe / script — platform-aware filename
    local_name = "ffmpeg.exe" if sys.platform == "win32" else "ffmpeg"
    local = _BASE / local_name
    if local.is_file():
        return str(local)

    # 2. imageio-ffmpeg (downloads automatically to its cache on first call)
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        pass
    except Exception:
        pass

    # 3. System PATH
    found = shutil.which("ffmpeg")
    if found:
        return found

    raise RuntimeError(
        "ffmpeg not found.\n\n"
        "Install imageio-ffmpeg so it can be downloaded automatically:\n"
        "  pip install imageio-ffmpeg\n\n"
        "Or place ffmpeg next to the app."
    )


# ── Video to frames helper ────────────────────────────────────────────────────

def extract_video_frames(video_path, max_frames=60):
    """Extract up to max_frames from a video using ffmpeg (cross-platform)."""
    import shutil

    ffmpeg = get_ffmpeg()

    # Derive ffprobe path next to ffmpeg — platform-aware extension
    ffprobe_name = "ffprobe.exe" if sys.platform == "win32" else "ffprobe"
    ffprobe = str(Path(ffmpeg).parent / ffprobe_name)
    if not os.path.isfile(ffprobe):
        ffprobe = shutil.which("ffprobe") or ffmpeg

    # Get video duration + fps
    probe_cmd = [
        ffprobe, "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=r_frame_rate,nb_frames,duration",
        "-of", "default=noprint_wrappers=1",
        video_path
    ]

    try:
        result = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=15)
        info_lines = result.stdout.strip().splitlines()
        info = {}
        for ln in info_lines:
            if "=" in ln:
                k, v = ln.split("=", 1)
                info[k.strip()] = v.strip()
        fps_str = info.get("r_frame_rate", "24/1")
        num, den = fps_str.split("/") if "/" in fps_str else (fps_str, "1")
        fps = float(num) / float(den)
        duration = float(info.get("duration", 3))
    except Exception:
        fps = 15.0
        duration = 3.0

    total_frames = int(fps * duration)
    step = max(1, total_frames // max_frames)
    out_fps = fps / step

    tmpdir = tempfile.mkdtemp()
    try:
        frame_pattern = os.path.join(tmpdir, "frame_%04d.png")
        cmd = [
            ffmpeg, "-i", video_path,
            "-vf", f"select='not(mod(n\\,{step}))',setpts=N/FRAME_RATE/TB",
            "-vsync", "0",
            "-frames:v", str(max_frames),
            frame_pattern, "-y", "-loglevel", "error"
        ]
        subprocess.run(cmd, check=True, timeout=60)
        frame_files = sorted(Path(tmpdir).glob("frame_*.png"))
        frames = [Image.open(str(f)).convert("RGBA") for f in frame_files]
        duration_per_frame = int(1000 / max(1, out_fps))
        return frames, [duration_per_frame] * len(frames)
    except Exception:
        import shutil as _shutil
        _shutil.rmtree(tmpdir, ignore_errors=True)
        raise


# ── Worker thread ─────────────────────────────────────────────────────────────

class Worker(QObject):
    finished = Signal(str)
    error    = Signal(str)
    progress = Signal(int)

    def __init__(self, params):
        super().__init__()
        self.params = params

    def run(self):
        try:
            p = self.params
            font_path, is_impact = find_font(p.get("font_custom"))

            is_video   = p.get("is_video", False)
            no_caption = p.get("no_caption", False)
            out_fmt    = p.get("out_format", "GIF").upper()
            max_frames = p.get("max_frames", 60)

            if is_video:
                self.progress.emit(5)
                src_frames_rgba, durations = extract_video_frames(
                    p["input_path"], max_frames=max_frames
                )
            else:
                src = Image.open(p["input_path"])
                src_frames_rgba, durations = [], []
                try:
                    for frame in ImageSequence.Iterator(src):
                        src_frames_rgba.append(frame.convert("RGBA"))
                        durations.append(frame.info.get("duration", 100))
                except EOFError:
                    pass
                if not src_frames_rgba:
                    src_frames_rgba = [src.convert("RGBA")]
                    durations = [100]

            # Convert RGBA → RGB (composite onto white background)
            rgb_frames = []
            for f in src_frames_rgba:
                bg = Image.new("RGB", f.size, (255, 255, 255))
                bg.paste(f, mask=f.split()[3] if f.mode == "RGBA" else None)
                rgb_frames.append(bg)
            src_frames = rgb_frames

            img_w = src_frames[0].width
            if p.get("auto_size"):
                font_size = max(28, int(img_w * 0.085))
                padding   = max(10, int(img_w * 0.03))
            else:
                font_size = p["font_size"]
                padding   = p["padding"]

            bg_color   = hex_to_rgb(p.get("bg_color",   "#ffffff"))
            text_color = hex_to_rgb(p.get("text_color", "#000000"))

            kw = dict(
                font_size=font_size, padding=padding,
                font_path=font_path, is_impact=is_impact,
                outline=p["outline"],
                outline_thickness=p.get("outline_thickness", 2),
                uppercase=p["uppercase"],
                align=p.get("align", "center"),
                bg_color=bg_color, text_color=text_color,
            )

            if no_caption:
                top_box = None
                bot_box = None
            else:
                top_box = render_caption_box(img_w, p["top_text"], **kw) if p["top_text"].strip() else None
                bot_box = render_caption_box(img_w, p["bot_text"], **kw) if p["bot_text"].strip() else None

            # Compression: scale down frames
            compress = p.get("compress_pct", 100)
            if compress < 100:
                scale = compress / 100.0
                new_w = max(16, int(img_w * scale))
                new_frames = []
                for f in src_frames:
                    new_h = int(f.height * scale)
                    new_frames.append(f.resize((new_w, new_h), Image.LANCZOS))
                src_frames = new_frames
                img_w = new_w
                if top_box:
                    top_box = top_box.resize((new_w, int(top_box.height * scale)), Image.LANCZOS)
                if bot_box:
                    bot_box = bot_box.resize((new_w, int(bot_box.height * scale)), Image.LANCZOS)

            n = len(src_frames)
            out_frames = []
            for i, sf in enumerate(src_frames):
                self.progress.emit(int(i / n * 90))
                parts = []
                if top_box: parts.append(top_box)
                parts.append(sf)
                if bot_box: parts.append(bot_box)
                # Pass bg_color so transparent pixels composite correctly
                out_frames.append(composite_parts(parts, bg_color=bg_color))

            self.progress.emit(95)

            if out_fmt == "WEBP":
                out_frames[0].save(
                    p["output_path"], format="WEBP", save_all=True,
                    append_images=out_frames[1:], loop=0,
                    duration=durations[:n],
                )
            else:
                out_frames[0].save(
                    p["output_path"], format="GIF", save_all=True,
                    append_images=out_frames[1:], loop=0,
                    duration=durations[:n], optimize=False,
                )

            self.progress.emit(100)
            self.finished.emit(p["output_path"])
        except Exception:
            import traceback
            self.error.emit(traceback.format_exc())


# ── Estimate output size ──────────────────────────────────────────────────────

class SizeEstimator(QObject):
    done = Signal(int)  # estimated bytes

    def __init__(self, params):
        super().__init__()
        self.params = params

    def run(self):
        try:
            p = self.params
            src = Image.open(p["input_path"])
            frames = []
            try:
                for frame in ImageSequence.Iterator(src):
                    frames.append(frame.convert("RGB"))
            except EOFError:
                pass
            if not frames:
                frames = [src.convert("RGB")]

            n_frames = len(frames)
            w, h = frames[0].size

            compress = p.get("compress_pct", 100)
            if compress < 100:
                scale = compress / 100.0
                w = max(16, int(w * scale))
                h = max(16, int(h * scale))

            # Rough estimation: each frame ~ 256 color palette
            # GIF colors per pixel ~ 8 bits with LZW ~50% compression
            frame_bytes = w * h * 0.5  # rough LZW compressed
            overhead = 800 + n_frames * 20
            estimated = int(frame_bytes * n_frames + overhead)
            self.done.emit(estimated)
        except Exception:
            self.done.emit(-1)


# ── Styled widget factories ───────────────────────────────────────────────────

def lbl(text, size=13, bold=False, color=None, align=None):
    w = QLabel(text)
    c = color or C["text"]
    wt = "600" if bold else "400"
    w.setStyleSheet(f"color:{c}; font-size:{size}px; font-weight:{wt}; background:transparent;")
    if align:
        w.setAlignment(align)
    return w


def inp(placeholder="", min_h=32):
    w = QLineEdit()
    w.setPlaceholderText(placeholder)
    w.setMinimumHeight(min_h)
    w.setStyleSheet(f"""
        QLineEdit {{
            background:{C['input_bg']}; color:{C['text']};
            border:1px solid {C['border']}; border-radius:7px;
            padding:6px 12px; font-size:12px;
        }}
        QLineEdit:focus {{ border-color:{C['accent']}; }}
        QLineEdit:hover {{ border-color:{C['border_hi']}; }}
    """)
    return w


def btn(text, accent=False, danger=False, small=False):
    b = QPushButton(text)
    if accent:
        bg, hov = C["accent"], C["accent2"]
        tc = "#fff"
    elif danger:
        bg, hov = "#2a1015", C["error"]
        tc = C["error"]
    else:
        bg, hov = C["card"], C["border_hi"]
        tc = C["text"]
    pad = "5px 12px" if small else "8px 18px"
    fs = "11px" if small else "12px"
    b.setStyleSheet(f"""
        QPushButton {{
            background:{bg}; color:{tc};
            border:1px solid {C['border']}; border-radius:7px;
            padding:{pad}; font-size:{fs}; font-weight:600;
            letter-spacing:0.3px;
        }}
        QPushButton:hover {{ background:{hov}; border-color:{C['border_hi']}; }}
        QPushButton:pressed {{ background:{C['accent2']}; }}
        QPushButton:disabled {{ background:{C['panel']}; color:{C['subtext']}; border-color:{C['border']}; }}
    """)
    return b


def chk(text):
    c = QCheckBox(text)
    c.setStyleSheet(f"""
        QCheckBox {{ color:{C['text']}; font-size:12px; background:transparent; spacing:6px; }}
        QCheckBox::indicator {{ width:15px; height:15px; border-radius:4px;
            border:1px solid {C['border']}; background:{C['input_bg']}; }}
        QCheckBox::indicator:checked {{
            background:{C['accent']}; border-color:{C['accent']};
            image: none;
        }}
        QCheckBox::indicator:hover {{ border-color:{C['border_hi']}; }}
    """)
    return c


def spn(lo, hi, val, suffix=""):
    s = QSpinBox()
    s.setRange(lo, hi)
    s.setValue(val)
    if suffix:
        s.setSuffix(suffix)
    s.setMinimumHeight(32)
    s.setStyleSheet(f"""
        QSpinBox {{
            background:{C['input_bg']}; color:{C['text']};
            border:1px solid {C['border']}; border-radius:7px;
            padding:4px 8px; font-size:12px;
        }}
        QSpinBox:focus {{ border-color:{C['accent']}; }}
        QSpinBox::up-button, QSpinBox::down-button {{
            width:20px; background:{C['card']}; border:none;
            border-radius:4px;
        }}
        QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
            background:{C['border_hi']};
        }}
    """)
    return s


def cmb(items, current=None):
    """Themed QComboBox."""
    c = QComboBox()
    c.addItems(items)
    if current and current in items:
        c.setCurrentText(current)
    c.setMinimumHeight(32)
    c.setStyleSheet(f"""
        QComboBox {{
            background:{C['input_bg']}; color:{C['text']};
            border:1px solid {C['border']}; border-radius:7px;
            padding:5px 10px; font-size:12px;
        }}
        QComboBox::drop-down {{ border:none; width:24px; }}
        QComboBox QAbstractItemView {{
            background:{C['card']}; color:{C['text']};
            selection-background-color:{C['accent']};
            border:1px solid {C['border']};
        }}
        QComboBox:hover {{ border-color:{C['border_hi']}; }}
        QComboBox:focus {{ border-color:{C['accent']}; }}
    """)
    return c


def section(title):
    g = QGroupBox(title)
    g.setStyleSheet(f"""
        QGroupBox {{
            background:{C['card']}; border:1px solid {C['border']};
            border-radius:9px; margin-top:16px; padding:10px 10px 8px 10px;
        }}
        QGroupBox::title {{
            color:{C['subtext']}; font-size:9px; font-weight:700;
            subcontrol-origin:margin; left:12px; letter-spacing:2px;
            text-transform:uppercase;
        }}
    """)
    return g


def divider():
    f = QFrame()
    f.setFrameShape(QFrame.HLine)
    f.setStyleSheet(f"background:{C['border']}; border:none; max-height:1px;")
    return f


def color_swatch(hex_val="#ffffff"):
    """Small coloured square button that opens a QColorDialog when clicked."""
    b = QPushButton()
    b.setFixedSize(32, 32)
    b.setToolTip("Pick colour")
    b.setStyleSheet(f"""
        QPushButton {{
            background:{hex_val}; border:1px solid {C['border']};
            border-radius:6px;
        }}
        QPushButton:hover {{ border-color:{C['border_hi']}; }}
    """)
    return b


# ── Settings Dialog ───────────────────────────────────────────────────────────

class SettingsDialog(QDialog):
    theme_changed = Signal(str)

    def __init__(self, parent, current_theme):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setFixedSize(320, 200)
        self.setModal(True)
        self.setStyleSheet(f"""
            QDialog {{ background:{C['bg']}; }}
            QLabel {{ background:transparent; color:{C['text']}; }}
        """)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(16)

        title = QLabel("⚙  Settings")
        title.setStyleSheet(f"font-size:15px; font-weight:700; color:{C['text']}; background:transparent;")
        lay.addWidget(title)

        lay.addWidget(divider())

        theme_row = QHBoxLayout()
        theme_lbl = QLabel("Theme")
        theme_lbl.setStyleSheet(f"font-size:12px; color:{C['text']}; background:transparent;")
        theme_row.addWidget(theme_lbl)
        theme_row.addStretch()

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(list(THEMES.keys()))
        self.theme_combo.setCurrentText(current_theme)
        self.theme_combo.setFixedWidth(140)
        self.theme_combo.setStyleSheet(f"""
            QComboBox {{
                background:{C['input_bg']}; color:{C['text']};
                border:1px solid {C['border']}; border-radius:7px;
                padding:5px 10px; font-size:12px;
            }}
            QComboBox::drop-down {{ border:none; width:24px; }}
            QComboBox QAbstractItemView {{
                background:{C['card']}; color:{C['text']};
                selection-background-color:{C['accent']};
                border:1px solid {C['border']};
            }}
        """)
        theme_row.addWidget(self.theme_combo)
        lay.addLayout(theme_row)

        lay.addStretch()

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        apply_btn = QPushButton("Apply")
        apply_btn.setFixedWidth(80)
        apply_btn.setStyleSheet(f"""
            QPushButton {{
                background:{C['accent']}; color:#fff;
                border:none; border-radius:7px;
                padding:7px 14px; font-size:12px; font-weight:600;
            }}
            QPushButton:hover {{ background:{C['accent2']}; }}
        """)
        apply_btn.clicked.connect(self._apply)
        btn_row.addWidget(apply_btn)
        lay.addLayout(btn_row)

    def _apply(self):
        self.theme_changed.emit(self.theme_combo.currentText())
        self.accept()


# ── Drop / Paste zone ─────────────────────────────────────────────────────────

class DropZone(QLabel):
    file_dropped = Signal(str)
    paste_data   = Signal(object)

    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumHeight(120)
        self._set_empty()

    def _set_empty(self):
        self.setPixmap(QPixmap())
        self.setText("Drop image/video  ·  Click to browse  ·  Ctrl+V")
        self.setStyleSheet(f"""
            QLabel {{
                background:{C['input_bg']}; color:{C['subtext']};
                border:1px dashed {C['border']}; border-radius:9px;
                font-size:11px; padding:8px;
            }}
        """)

    def set_preview(self, path=None, pil_img=None):
        if path:
            pix = QPixmap(path)
        elif pil_img:
            buf = io.BytesIO()
            pil_img.save(buf, format="PNG")
            buf.seek(0)
            pix = QPixmap()
            pix.loadFromData(buf.read())
        else:
            return
        if not pix.isNull():
            pix = pix.scaled(360, 120, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.setPixmap(pix)
            self.setStyleSheet(f"""
                QLabel {{
                    background:{C['input_bg']};
                    border:1px solid {C['accent']}; border-radius:9px;
                }}
            """)

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()
            self.setStyleSheet(f"""
                QLabel {{
                    background:{C['card']}; color:{C['text']};
                    border:1px dashed {C['accent']}; border-radius:9px;
                    font-size:11px;
                }}
            """)

    def dragLeaveEvent(self, e):
        if not self.pixmap() or self.pixmap().isNull():
            self._set_empty()

    def dropEvent(self, e):
        urls = e.mimeData().urls()
        if urls:
            self.file_dropped.emit(urls[0].toLocalFile())

    def mousePressEvent(self, e):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Image or Video", "",
            "Images & Videos (*.png *.jpg *.jpeg *.webp *.gif *.bmp *.tiff *.mp4 *.mov *.avi *.mkv *.webm)"
        )
        if path:
            self.file_dropped.emit(path)


# ── Live preview panel ────────────────────────────────────────────────────────

class PreviewPanel(QLabel):
    def __init__(self):
        super().__init__()
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumSize(380, 380)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._movie = None  # keep reference alive to prevent GC mid-animation
        self._set_empty()

    def _panel_style(self):
        return f"""
            QLabel {{
                background:{C['panel']}; color:{C['subtext']};
                border:1px solid {C['border']}; border-radius:11px;
                padding:6px;
            }}
        """

    def _set_empty(self):
        if self._movie:
            self._movie.stop()
            self._movie = None
        self.setPixmap(QPixmap())
        self.setText("Preview will appear here")
        self.setStyleSheet(f"""
            QLabel {{
                background:{C['panel']}; color:{C['subtext']};
                border:1px solid {C['border']}; border-radius:11px;
                font-size:12px;
            }}
        """)

    def show_image(self, pil_img):
        """Display a static PIL image (used for live preview)."""
        if self._movie:
            self._movie.stop()
            self._movie = None
        buf = io.BytesIO()
        pil_img.save(buf, format="PNG")
        buf.seek(0)
        pix = QPixmap()
        pix.loadFromData(buf.read())
        if not pix.isNull():
            scaled = pix.scaled(
                self.width() - 16, self.height() - 16,
                Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            self.setPixmap(scaled)
            self.setText("")
            self.setStyleSheet(self._panel_style())

    def show_gif(self, path):
        """Display an animated GIF using QMovie so all frames play back."""
        try:
            movie = QMovie(path)
            if not movie.isValid():
                raise ValueError("QMovie could not load the GIF")

            # Use QImageReader for reliable native-size lookup without needing
            # to start the movie first (jumpToFrame can fail on some systems)
            reader = QImageReader(path)
            native = reader.size()
            if native.isValid() and not native.isEmpty():
                scaled_size = native.scaled(
                    self.width() - 16, self.height() - 16,
                    Qt.KeepAspectRatio
                )
                movie.setScaledSize(scaled_size)

            self._movie = movie
            self.setMovie(self._movie)
            self._movie.start()
            self.setText("")
            self.setStyleSheet(self._panel_style())
        except Exception:
            # Fall back to showing only the first frame as a static image
            try:
                img = Image.open(path).convert("RGB")
                self.show_image(img)
            except Exception:
                pass

    def show_webp(self, path):
        """Display the first frame of a WebP file as a static image."""
        try:
            img = Image.open(path).convert("RGB")
            self.show_image(img)
        except Exception:
            pass


# ── Main window ───────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gomorron Caption Maker")
        self.setMinimumSize(1000, 660)
        self.showMaximized()

        self._input_path = ""
        self._pasted_img = None
        self._thread = None
        self._worker = None
        self._last_output = ""
        self._is_video = False
        self._current_theme = "Dark"
        self._size_thread = None
        self._size_worker = None

        for icon_name in ("icon.ico", "icon.jpg"):
            icon_path = Path(__file__).parent / icon_name
            if icon_path.exists():
                self.setWindowIcon(QIcon(str(icon_path)))
                break

        self._build_ui()
        self._apply_global_style()

        sc = QShortcut(QKeySequence("Ctrl+V"), self)
        sc.activated.connect(self._paste_from_clipboard)

    def _apply_global_style(self):
        self.setStyleSheet(f"""
            QMainWindow, QWidget {{ background:{C['bg']}; font-family: 'Segoe UI', 'Inter', sans-serif; }}
            QScrollArea {{ background:transparent; border:none; }}
            QScrollBar:vertical {{
                background:{C['panel']}; width:5px; border-radius:3px; margin:0;
            }}
            QScrollBar::handle:vertical {{
                background:{C['border_hi']}; border-radius:3px; min-height:20px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height:0; }}
            QToolTip {{ background:{C['card']}; color:{C['text']}; border:1px solid {C['border']}; padding:4px 8px; border-radius:6px; font-size:11px; }}
        """)

    # ── Theme change ──────────────────────────────────────────────────────────

    def _change_theme(self, theme_name):
        global C
        self._current_theme = theme_name
        C.update(THEMES[theme_name])

        # Snapshot all current UI values so they survive the widget rebuild
        state = self._snapshot_ui_state()

        self._build_ui()
        self._apply_global_style()

        # Restore everything without triggering cascading updates
        self._restore_ui_state(state)

        # Re-trigger file load if one was already open
        if state["input_path"]:
            self._on_file_dropped(state["input_path"], skip_preview=False)

    def _snapshot_ui_state(self):
        """Capture all user-configurable widget values into a plain dict."""
        def _get(attr, default):
            w = getattr(self, attr, None)
            if w is None:               return default
            if isinstance(w, QLineEdit): return w.text()
            if isinstance(w, QCheckBox): return w.isChecked()
            if isinstance(w, QSpinBox):  return w.value()
            if isinstance(w, QSlider):   return w.value()
            if isinstance(w, QComboBox): return w.currentText()
            return default

        return {
            "input_path":    self._input_path,
            "top_text":      _get("top_input",          ""),
            "bot_text":      _get("bot_input",          ""),
            "no_caption":    _get("no_caption_check",   False),
            "font_size":     _get("font_size_spin",     52),
            "padding":       _get("padding_spin",       18),
            "outline_thick": _get("outline_thick_spin", 2),
            "uppercase":     _get("uppercase_check",    True),
            "outline":       _get("outline_check",      True),
            "auto_size":     _get("auto_size_check",    False),
            "align":         _get("align_combo",        "Center"),
            "bg_color":      _get("bg_color_inp",       "#ffffff"),
            "text_color":    _get("text_color_inp",     "#000000"),
            "font_path":     _get("font_input",         ""),
            "compress":      _get("compress_slider",    100),
            "max_frames":    _get("max_frames_spin",    60),
            "out_format":    _get("format_combo",       "GIF"),
            "out_name":      _get("out_name_input",     ""),
        }

    def _restore_ui_state(self, s):
        """Restore widget values from a snapshot dict (signals blocked throughout)."""

        # Numeric / text widgets
        for attr, value in [
            ("top_input",          s["top_text"]),
            ("bot_input",          s["bot_text"]),
            ("font_size_spin",     s["font_size"]),
            ("padding_spin",       s["padding"]),
            ("outline_thick_spin", s["outline_thick"]),
            ("compress_slider",    s["compress"]),
            ("max_frames_spin",    s["max_frames"]),
        ]:
            w = getattr(self, attr, None)
            if w:
                w.blockSignals(True)
                (w.setText if isinstance(w, QLineEdit) else w.setValue)(value)
                w.blockSignals(False)

        # Checkboxes
        for attr, value in [
            ("uppercase_check",  s["uppercase"]),
            ("outline_check",    s["outline"]),
            ("auto_size_check",  s["auto_size"]),
            ("no_caption_check", s["no_caption"]),
        ]:
            w = getattr(self, attr, None)
            if w:
                w.blockSignals(True)
                w.setChecked(value)
                w.blockSignals(False)

        # Combo boxes
        for attr, value in [
            ("align_combo",  s["align"]),
            ("format_combo", s["out_format"]),
        ]:
            w = getattr(self, attr, None)
            if w:
                w.blockSignals(True)
                w.setCurrentText(value)
                w.blockSignals(False)

        # Plain text inputs
        for attr, value in [
            ("bg_color_inp",   s["bg_color"]),
            ("text_color_inp", s["text_color"]),
            ("font_input",     s["font_path"]),
            ("out_name_input", s["out_name"]),
        ]:
            w = getattr(self, attr, None)
            if w:
                w.blockSignals(True)
                w.setText(value)
                w.blockSignals(False)

        # Re-sync swatch colours and derived UI states manually
        self._sync_swatch(self.bg_swatch,   s["bg_color"])
        self._sync_swatch(self.text_swatch, s["text_color"])
        self._toggle_auto_size(s["auto_size"])
        self._on_no_caption_toggle(s["no_caption"])
        self._on_format_changed(s["out_format"])  # keeps gen_btn label in sync

        self._input_path = s["input_path"]

    def _open_settings(self):
        dlg = SettingsDialog(self, self._current_theme)
        dlg.theme_changed.connect(self._change_theme)
        dlg.exec()

    # ── UI build ──────────────────────────────────────────────────────────────

    def _build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        root_lay = QVBoxLayout(root)
        root_lay.setContentsMargins(0, 0, 0, 0)
        root_lay.setSpacing(0)

        # ── Header ──────────────────────────────────────────────────────────
        header = QWidget()
        header.setFixedHeight(48)
        header.setStyleSheet(f"background:{C['panel']}; border-bottom:1px solid {C['border']};")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(16, 0, 20, 0)
        hl.setSpacing(10)

        # Settings button (top-left)
        settings_btn = QPushButton("⚙")
        settings_btn.setFixedSize(32, 32)
        settings_btn.setToolTip("Settings")
        settings_btn.setStyleSheet(f"""
            QPushButton {{
                background:{C['card']}; color:{C['subtext']};
                border:1px solid {C['border']}; border-radius:7px;
                font-size:14px; font-weight:600;
            }}
            QPushButton:hover {{ background:{C['border_hi']}; color:{C['text']}; }}
        """)
        settings_btn.clicked.connect(self._open_settings)
        hl.addWidget(settings_btn)

        # Logo / title
        title_row = QHBoxLayout()
        title_row.setSpacing(8)
        icon_path = None
        for n in ("icon.ico", "icon.jpg"):
            p = Path(__file__).parent / n
            if p.exists():
                icon_path = str(p)
                break
        if icon_path:
            icon_lbl = QLabel()
            pix = QPixmap(icon_path).scaled(26, 26, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            icon_lbl.setPixmap(pix)
            icon_lbl.setStyleSheet("background:transparent;")
            title_row.addWidget(icon_lbl)

        app_title = QLabel("Gomorron Caption Maker")
        app_title.setStyleSheet(f"color:{C['text']}; font-size:15px; font-weight:700; background:transparent; letter-spacing:-0.3px;")
        title_row.addWidget(app_title)
        hl.addLayout(title_row)
        hl.addStretch()

        credits = QLabel("by Gomorronmannen 💜")
        credits.setStyleSheet(f"color:{C['subtext']}; font-size:10px; background:transparent;")
        hl.addWidget(credits)
        root_lay.addWidget(header)

        # ── Main body ────────────────────────────────────────────────────────
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(1)
        splitter.setStyleSheet(f"QSplitter::handle {{ background:{C['border']}; }}")
        root_lay.addWidget(splitter)

        # ── Left panel ────────────────────────────────────────────────────────
        left_wrap = QWidget()
        left_wrap.setMinimumWidth(360)
        left_wrap.setMaximumWidth(480)
        left_wrap.setStyleSheet(f"background:{C['bg']};")
        left_wrap_lay = QVBoxLayout(left_wrap)
        left_wrap_lay.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("background:transparent; border:none;")
        inner = QWidget()
        inner.setStyleSheet(f"background:{C['bg']};")
        scroll.setWidget(inner)
        lay = QVBoxLayout(inner)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(10)
        left_wrap_lay.addWidget(scroll)
        splitter.addWidget(left_wrap)

        # ── IMAGE ─────────────────────────────────────────────────────────────
        img_sec = section("IMAGE / VIDEO")
        img_lay = QVBoxLayout(img_sec)
        img_lay.setSpacing(6)

        self.drop_zone = DropZone()
        self.drop_zone.file_dropped.connect(self._on_file_dropped)
        img_lay.addWidget(self.drop_zone)

        img_btn_row = QHBoxLayout()
        browse_btn = btn("📂  Browse", small=True)
        browse_btn.clicked.connect(self._browse_image)
        paste_btn = btn("📋  Paste", small=True)
        paste_btn.clicked.connect(self._paste_from_clipboard)
        img_btn_row.addWidget(browse_btn)
        img_btn_row.addWidget(paste_btn)
        img_btn_row.addStretch()
        img_lay.addLayout(img_btn_row)

        self.img_path_label = lbl("No file selected", 10, color=C["subtext"])
        self.img_path_label.setWordWrap(True)
        img_lay.addWidget(self.img_path_label)
        lay.addWidget(img_sec)

        # ── CAPTIONS ──────────────────────────────────────────────────────────
        cap_sec = section("CAPTIONS")
        cap_lay = QVBoxLayout(cap_sec)
        cap_lay.setSpacing(6)

        # No Caption toggle
        self.no_caption_check = chk("No Caption")
        self.no_caption_check.setChecked(False)
        self.no_caption_check.setToolTip("Output the GIF/video without any text overlay")
        self.no_caption_check.stateChanged.connect(self._on_no_caption_toggle)
        cap_lay.addWidget(self.no_caption_check)

        cap_lay.addWidget(divider())

        cap_lay.addWidget(lbl("Top caption", 10, color=C["subtext"]))
        self.top_input = inp("Top text…")
        self.top_input.textChanged.connect(self._update_preview)
        cap_lay.addWidget(self.top_input)

        cap_lay.addWidget(lbl("Bottom caption", 10, color=C["subtext"]))
        self.bot_input = inp("Bottom text…")
        self.bot_input.textChanged.connect(self._update_preview)
        cap_lay.addWidget(self.bot_input)
        lay.addWidget(cap_sec)

        # ── STYLE ────────────────────────────────────────────────────────────
        style_sec = section("STYLE")
        style_lay = QVBoxLayout(style_sec)
        style_lay.setSpacing(8)

        # Font size + Padding
        row1 = QHBoxLayout()
        fs_col = QVBoxLayout()
        fs_col.setSpacing(3)
        fs_col.addWidget(lbl("Font size", 9, color=C["subtext"]))
        self.font_size_spin = spn(16, 300, 52, " px")
        self.font_size_spin.valueChanged.connect(self._update_preview)
        fs_col.addWidget(self.font_size_spin)
        row1.addLayout(fs_col)
        row1.addSpacing(8)
        pad_col = QVBoxLayout()
        pad_col.setSpacing(3)
        pad_col.addWidget(lbl("Padding", 9, color=C["subtext"]))
        self.padding_spin = spn(4, 120, 18, " px")
        self.padding_spin.valueChanged.connect(self._update_preview)
        pad_col.addWidget(self.padding_spin)
        row1.addLayout(pad_col)
        row1.addStretch()
        style_lay.addLayout(row1)

        self.auto_size_check = chk("Auto-scale to image")
        self.auto_size_check.setChecked(False)
        self.auto_size_check.stateChanged.connect(self._toggle_auto_size)
        self.auto_size_check.stateChanged.connect(self._update_preview)
        style_lay.addWidget(self.auto_size_check)

        style_lay.addWidget(divider())

        # Uppercase + Outline toggles
        row2 = QHBoxLayout()
        self.uppercase_check = chk("UPPERCASE")
        self.uppercase_check.setChecked(True)
        self.uppercase_check.stateChanged.connect(self._update_preview)
        self.outline_check = chk("Text outline")
        self.outline_check.setChecked(True)
        self.outline_check.stateChanged.connect(self._update_preview)
        row2.addWidget(self.uppercase_check)
        row2.addWidget(self.outline_check)
        row2.addStretch()
        style_lay.addLayout(row2)

        # Outline thickness + Text alignment (same row)
        thick_align_row = QHBoxLayout()

        thick_col = QVBoxLayout()
        thick_col.setSpacing(3)
        thick_col.addWidget(lbl("Outline thickness", 9, color=C["subtext"]))
        self.outline_thick_spin = spn(1, 10, 2, " px")
        self.outline_thick_spin.setToolTip("Stroke width around each character")
        self.outline_thick_spin.valueChanged.connect(self._update_preview)
        thick_col.addWidget(self.outline_thick_spin)
        thick_align_row.addLayout(thick_col)

        thick_align_row.addSpacing(8)

        align_col = QVBoxLayout()
        align_col.setSpacing(3)
        align_col.addWidget(lbl("Alignment", 9, color=C["subtext"]))
        self.align_combo = cmb(["Left", "Center", "Right"], current="Center")
        self.align_combo.setToolTip("Horizontal alignment of caption text")
        self.align_combo.currentTextChanged.connect(self._update_preview)
        align_col.addWidget(self.align_combo)
        thick_align_row.addLayout(align_col)

        thick_align_row.addStretch()
        style_lay.addLayout(thick_align_row)

        style_lay.addWidget(divider())

        # Colours — hex input paired with a colour-swatch picker button
        color_row = QHBoxLayout()

        bg_col = QVBoxLayout()
        bg_col.setSpacing(3)
        bg_col.addWidget(lbl("Caption BG", 9, color=C["subtext"]))
        bg_inp_row = QHBoxLayout()
        bg_inp_row.setSpacing(4)
        self.bg_color_inp = inp("#ffffff")
        self.bg_color_inp.setMaximumWidth(84)
        self.bg_swatch = color_swatch("#ffffff")
        bg_inp_row.addWidget(self.bg_color_inp)
        bg_inp_row.addWidget(self.bg_swatch)
        bg_col.addLayout(bg_inp_row)
        color_row.addLayout(bg_col)

        color_row.addSpacing(8)

        tc_col = QVBoxLayout()
        tc_col.setSpacing(3)
        tc_col.addWidget(lbl("Text color", 9, color=C["subtext"]))
        tc_inp_row = QHBoxLayout()
        tc_inp_row.setSpacing(4)
        self.text_color_inp = inp("#000000")
        self.text_color_inp.setMaximumWidth(84)
        self.text_swatch = color_swatch("#000000")
        tc_inp_row.addWidget(self.text_color_inp)
        tc_inp_row.addWidget(self.text_swatch)
        tc_col.addLayout(tc_inp_row)
        color_row.addLayout(tc_col)

        color_row.addStretch()
        style_lay.addLayout(color_row)

        # Wire swatch ↔ text input bidirectionally; then hook preview update
        self._wire_color_swatch(self.bg_swatch,   self.bg_color_inp)
        self._wire_color_swatch(self.text_swatch, self.text_color_inp)
        self.bg_color_inp.textChanged.connect(self._update_preview)
        self.text_color_inp.textChanged.connect(self._update_preview)

        style_lay.addWidget(divider())

        # Custom font
        style_lay.addWidget(lbl("Custom font (.ttf / .otf)", 9, color=C["subtext"]))
        font_row = QHBoxLayout()
        self.font_input = inp("Auto-detect Impact")
        font_row.addWidget(self.font_input)
        browse_font = btn("📂", small=True)
        browse_font.setFixedWidth(36)
        browse_font.clicked.connect(self._browse_font)
        font_row.addWidget(browse_font)
        style_lay.addLayout(font_row)
        lay.addWidget(style_sec)

        # ── COMPRESSION ──────────────────────────────────────────────────────
        compress_sec = section("COMPRESSION")
        compress_lay = QVBoxLayout(compress_sec)
        compress_lay.setSpacing(6)

        compress_header = QHBoxLayout()
        compress_header.addWidget(lbl("Scale", 10, color=C["subtext"]))
        compress_header.addStretch()
        self.compress_val_lbl = lbl("100%", 10, bold=True, color=C["accent"])
        compress_header.addWidget(self.compress_val_lbl)
        compress_lay.addLayout(compress_header)

        self.compress_slider = QSlider(Qt.Horizontal)
        self.compress_slider.setRange(10, 100)
        self.compress_slider.setValue(100)
        self.compress_slider.setTickPosition(QSlider.NoTicks)
        self.compress_slider.setStyleSheet(f"""
            QSlider::groove:horizontal {{
                background:{C['border']}; height:4px; border-radius:2px;
            }}
            QSlider::handle:horizontal {{
                background:{C['accent']}; width:14px; height:14px;
                border-radius:7px; margin:-5px 0;
            }}
            QSlider::sub-page:horizontal {{
                background:{C['accent']}; border-radius:2px;
            }}
        """)
        self.compress_slider.valueChanged.connect(self._on_compress_changed)
        compress_lay.addWidget(self.compress_slider)

        # Max frames — quality vs. file-size knob for video input
        frames_col = QVBoxLayout()
        frames_col.setSpacing(3)
        frames_col.addWidget(lbl("Max frames (video)", 9, color=C["subtext"]))
        self.max_frames_spin = spn(5, 300, 60, " fr")
        self.max_frames_spin.setToolTip(
            "Maximum frames extracted from a video.\n"
            "Lower → smaller file  ·  Higher → smoother motion."
        )
        frames_col.addWidget(self.max_frames_spin)
        compress_lay.addLayout(frames_col)

        # Estimated size display
        size_row = QHBoxLayout()
        size_row.addWidget(lbl("Est. output size:", 10, color=C["subtext"]))
        self.est_size_lbl = lbl("—", 10, bold=True, color=C["text"])
        size_row.addWidget(self.est_size_lbl)
        size_row.addStretch()
        compress_lay.addLayout(size_row)
        lay.addWidget(compress_sec)

        # ── OUTPUT ───────────────────────────────────────────────────────────
        out_sec = section("OUTPUT")
        out_lay = QVBoxLayout(out_sec)
        out_lay.setSpacing(6)

        # Format selector — GIF for compatibility, WebP for smaller files
        fmt_col = QVBoxLayout()
        fmt_col.setSpacing(3)
        fmt_col.addWidget(lbl("Format", 9, color=C["subtext"]))
        self.format_combo = cmb(["GIF", "WebP"], current="GIF")
        self.format_combo.setToolTip("GIF  — universal  ·  WebP  — smaller file, better quality")
        self.format_combo.currentTextChanged.connect(self._on_format_changed)
        fmt_col.addWidget(self.format_combo)
        out_lay.addLayout(fmt_col)

        out_lay.addWidget(lbl("Filename (blank = auto)", 9, color=C["subtext"]))
        self.out_name_input = inp("my_caption.gif")
        out_lay.addWidget(self.out_name_input)
        lay.addWidget(out_sec)

        # ── Generate button ──────────────────────────────────────────────────
        self.gen_btn = QPushButton("▶  Generate GIF")
        self.gen_btn.setFixedHeight(42)
        self.gen_btn.setStyleSheet(f"""
            QPushButton {{
                background:{C['accent']}; color:#fff;
                border:none; border-radius:8px;
                font-size:13px; font-weight:700; letter-spacing:0.5px;
            }}
            QPushButton:hover {{ background:{C['accent2']}; }}
            QPushButton:pressed {{ background:{C['accent2']}; }}
            QPushButton:disabled {{ background:{C['panel']}; color:{C['subtext']}; }}
        """)
        self.gen_btn.clicked.connect(self._generate)
        lay.addWidget(self.gen_btn)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setVisible(False)
        self.progress.setFixedHeight(3)
        self.progress.setTextVisible(False)
        self.progress.setStyleSheet(f"""
            QProgressBar {{ background:{C['border']}; border:none; border-radius:2px; }}
            QProgressBar::chunk {{
                background:qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 {C['accent2']}, stop:1 {C['accent']});
                border-radius:2px;
            }}
        """)
        lay.addWidget(self.progress)

        self.status_lbl = lbl("", 10, color=C["subtext"])
        self.status_lbl.setAlignment(Qt.AlignCenter)
        self.status_lbl.setWordWrap(True)
        lay.addWidget(self.status_lbl)

        self.copy_btn = btn("📋  Copy to Clipboard")
        self.copy_btn.setVisible(False)
        self.copy_btn.clicked.connect(self._copy_to_clipboard)
        lay.addWidget(self.copy_btn)

        lay.addStretch()

        # ── Right panel (preview) ──────────────────────────────────────────
        right_wrap = QWidget()
        right_wrap.setStyleSheet(f"background:{C['panel']}; border-left:1px solid {C['border']};")
        right_lay = QVBoxLayout(right_wrap)
        right_lay.setContentsMargins(16, 16, 16, 16)
        right_lay.setSpacing(10)

        prev_header = QHBoxLayout()
        prev_header.addWidget(lbl("Preview", 11, bold=True))
        prev_header.addStretch()
        self.prev_info_lbl = lbl("", 9, color=C["subtext"])
        prev_header.addWidget(self.prev_info_lbl)
        right_lay.addLayout(prev_header)

        self.preview = PreviewPanel()
        right_lay.addWidget(self.preview)

        splitter.addWidget(right_wrap)
        splitter.setSizes([400, 700])

    # ── Colour swatch helpers ─────────────────────────────────────────────────

    def _sync_swatch(self, swatch, hex_val):
        """Update a swatch button's background colour to match hex_val."""
        try:
            v = hex_val.strip()
            if len(v) in (4, 7) and v.startswith("#"):
                QColor(v)  # validate
                swatch.setStyleSheet(f"""
                    QPushButton {{
                        background:{v}; border:1px solid {C['border']};
                        border-radius:6px;
                    }}
                    QPushButton:hover {{ border-color:{C['border_hi']}; }}
                """)
        except Exception:
            pass

    def _wire_color_swatch(self, swatch, line_edit):
        """Connect a colour swatch and its paired QLineEdit bidirectionally.

        Clicking the swatch opens QColorDialog and pushes the result into
        line_edit; typing in line_edit immediately repaints the swatch.
        """
        def _on_swatch_click():
            current = line_edit.text().strip() or "#ffffff"
            color = QColorDialog.getColor(QColor(current), self, "Pick colour")
            if color.isValid():
                line_edit.setText(color.name())   # triggers textChanged → _sync_swatch

        def _on_text_changed(text):
            self._sync_swatch(swatch, text)

        swatch.clicked.connect(_on_swatch_click)
        line_edit.textChanged.connect(_on_text_changed)

    # ── No Caption toggle ─────────────────────────────────────────────────────

    def _on_no_caption_toggle(self, state):
        enabled = not bool(state)
        self.top_input.setEnabled(enabled)
        self.bot_input.setEnabled(enabled)
        self._update_preview()

    # ── Format changed ────────────────────────────────────────────────────────

    def _on_format_changed(self, fmt):
        """Sync the generate button label and filename placeholder to the chosen format."""
        ext = "webp" if fmt == "WebP" else "gif"
        self.gen_btn.setText(f"▶  Generate {fmt}")
        self.out_name_input.setPlaceholderText(f"my_caption.{ext}")

    # ── Compression slider ────────────────────────────────────────────────────

    def _on_compress_changed(self, val):
        self.compress_val_lbl.setText(f"{val}%")
        self._schedule_size_estimate()

    def _schedule_size_estimate(self):
        if not self._input_path or self._is_video:
            self.est_size_lbl.setText("N/A for video")
            return
        self.est_size_lbl.setText("calculating…")
        QTimer.singleShot(300, self._run_size_estimate)

    def _run_size_estimate(self):
        if not self._input_path or self._is_video:
            return
        try:
            if self._size_thread and self._size_thread.isRunning():
                return
            params = {"input_path": self._input_path, "compress_pct": self.compress_slider.value()}
            self._size_thread = QThread()
            self._size_worker = SizeEstimator(params)
            self._size_worker.moveToThread(self._size_thread)
            self._size_thread.started.connect(self._size_worker.run)
            self._size_worker.done.connect(self._on_size_estimated)
            self._size_worker.done.connect(self._size_thread.quit)
            self._size_thread.start()
        except Exception:
            pass

    def _on_size_estimated(self, size_bytes):
        if size_bytes < 0:
            self.est_size_lbl.setText("—")
        else:
            self.est_size_lbl.setText(format_size(size_bytes))

    # ── Image selection / paste ───────────────────────────────────────────────

    def _browse_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Image or Video", "",
            "Images & Videos (*.png *.jpg *.jpeg *.webp *.gif *.bmp *.tiff *.mp4 *.mov *.avi *.mkv *.webm)"
        )
        if path:
            self._on_file_dropped(path)

    VIDEO_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}

    def _on_file_dropped(self, path, skip_preview=False):
        self._input_path = path
        self._pasted_img = None
        ext = Path(path).suffix.lower()
        self._is_video = ext in self.VIDEO_EXTS

        if self._is_video:
            # Check ffmpeg is available before accepting the file
            try:
                get_ffmpeg()
            except RuntimeError:
                QMessageBox.warning(
                    self, "ffmpeg not found",
                    "ffmpeg was not found.\n\n"
                    "Option 1 (easiest): pip install imageio-ffmpeg\n"
                    "Option 2: download from https://www.gyan.dev/ffmpeg/builds/\n"
                    "  and place ffmpeg next to GomorronCaptionMaker."
                )
                self._input_path = ""
                self._is_video = False
                return
            # For video, show a placeholder in the drop zone
            self.drop_zone.setText(f"🎬  {Path(path).name}")
            self.drop_zone.setStyleSheet(f"""
                QLabel {{
                    background:{C['input_bg']}; color:{C['accent']};
                    border:1px solid {C['accent']}; border-radius:9px;
                    font-size:11px; padding:8px;
                }}
            """)
            self.img_path_label.setText(f"Video: {Path(path).name}")
            self.img_path_label.setStyleSheet(f"color:{C['accent']}; font-size:10px; background:transparent;")
            self.prev_info_lbl.setText("Video — frames extracted on generate")
            self.est_size_lbl.setText("N/A for video")
        else:
            self.drop_zone.set_preview(path=path)
            name = Path(path).name
            self.img_path_label.setText(name)
            self.img_path_label.setStyleSheet(f"color:{C['success']}; font-size:10px; background:transparent;")
            try:
                img = Image.open(path)
                w, h = img.size
                frames = getattr(img, "n_frames", 1)
                self.prev_info_lbl.setText(f"{w}×{h}  ·  {frames} frame{'s' if frames > 1 else ''}")
            except Exception:
                pass
            self._schedule_size_estimate()
            if not skip_preview:
                self._update_preview()

    def _paste_from_clipboard(self):
        cb = QApplication.clipboard()
        mime = cb.mimeData()
        if mime.hasImage():
            qimg = cb.image()
            qimg = qimg.convertToFormat(QImage.Format_RGBA8888)
            width, height = qimg.width(), qimg.height()
            arr = bytes(qimg.bits())
            pil = Image.frombytes("RGBA", (width, height), arr)
            self._pasted_img = pil.convert("RGB")
            self._is_video = False
            tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
            self._pasted_img.save(tmp.name)
            self._input_path = tmp.name
            self.drop_zone.set_preview(pil_img=self._pasted_img)
            self.img_path_label.setText("Pasted from clipboard")
            self.img_path_label.setStyleSheet(f"color:{C['success']}; font-size:10px; background:transparent;")
            w, h = self._pasted_img.size
            self.prev_info_lbl.setText(f"{w}×{h}  ·  1 frame")
            self._schedule_size_estimate()
            self._update_preview()
        elif mime.hasUrls():
            path = mime.urls()[0].toLocalFile()
            if path:
                self._on_file_dropped(path)

    # ── Live preview ──────────────────────────────────────────────────────────

    def _update_preview(self):
        if not self._input_path or self._is_video:
            return
        no_caption = self.no_caption_check.isChecked()
        top = self.top_input.text().strip()
        bot = self.bot_input.text().strip()
        if not no_caption and not top and not bot:
            return
        try:
            font_path, is_impact = find_font(self.font_input.text().strip() or None)
            src = Image.open(self._input_path).convert("RGB")
            img_w = src.width
            if self.auto_size_check.isChecked():
                fs  = max(28, int(img_w * 0.085))
                pad = max(10, int(img_w * 0.03))
            else:
                fs  = self.font_size_spin.value()
                pad = self.padding_spin.value()

            def safe_hex(v, fallback):
                try:
                    c = v.strip()
                    if not c.startswith("#") or len(c) not in (4, 7):
                        return hex_to_rgb(fallback)
                    return hex_to_rgb(c)
                except Exception:
                    return hex_to_rgb(fallback)

            bg_c  = safe_hex(self.bg_color_inp.text(),   "#ffffff")
            txt_c = safe_hex(self.text_color_inp.text(), "#000000")

            kw = dict(
                font_size=fs, padding=pad,
                font_path=font_path, is_impact=is_impact,
                outline=self.outline_check.isChecked(),
                outline_thickness=self.outline_thick_spin.value(),
                uppercase=self.uppercase_check.isChecked(),
                align=self.align_combo.currentText().lower(),
                bg_color=bg_c, text_color=txt_c,
            )

            if no_caption:
                preview_img = src
            else:
                top_box = render_caption_box(img_w, top, **kw) if top else None
                bot_box = render_caption_box(img_w, bot, **kw) if bot else None
                parts = []
                if top_box: parts.append(top_box)
                parts.append(src)
                if bot_box: parts.append(bot_box)
                preview_img = composite_parts(parts, bg_color=bg_c)
            self.preview.show_image(preview_img)
        except Exception:
            import traceback
            traceback.print_exc()  # surface errors to console — never silently dropped

    # ── Style toggles ─────────────────────────────────────────────────────────

    def _toggle_auto_size(self, state):
        self.font_size_spin.setEnabled(not state)
        self.padding_spin.setEnabled(not state)

    def _browse_font(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Font", "", "Fonts (*.ttf *.otf)")
        if path:
            self.font_input.setText(path)

    # ── Generate ──────────────────────────────────────────────────────────────

    def _generate(self):
        if not self._input_path:
            self._flash_status("Select or paste an image/video first.", error=True)
            return
        no_caption = self.no_caption_check.isChecked()
        top = self.top_input.text().strip()
        bot = self.bot_input.text().strip()
        if not no_caption and not top and not bot:
            self._flash_status("Enter at least one caption (or enable No Caption).", error=True)
            return

        out_fmt = self.format_combo.currentText()          # "GIF" or "WebP"
        ext     = ".webp" if out_fmt == "WebP" else ".gif"

        out_name = self.out_name_input.text().strip()
        if out_name:
            # Strip any existing extension, then reapply the correct one
            out_name = Path(out_name).stem + ext
        else:
            stem     = Path(self._input_path).stem
            out_name = f"{stem}_caption{ext}"
        out_path = str(OUTPUT_DIR / out_name)

        def safe_hex(v, fallback):
            try:
                c = v.strip()
                if not c.startswith("#") or len(c) not in (4, 7):
                    return fallback
                return c
            except Exception:
                return fallback

        params = dict(
            input_path        = self._input_path,
            top_text          = top,
            bot_text          = bot,
            output_path       = out_path,
            auto_size         = self.auto_size_check.isChecked(),
            font_size         = self.font_size_spin.value(),
            padding           = self.padding_spin.value(),
            font_custom       = self.font_input.text().strip() or None,
            outline           = self.outline_check.isChecked(),
            outline_thickness = self.outline_thick_spin.value(),
            uppercase         = self.uppercase_check.isChecked(),
            align             = self.align_combo.currentText().lower(),
            bg_color          = safe_hex(self.bg_color_inp.text(),   "#ffffff"),
            text_color        = safe_hex(self.text_color_inp.text(), "#000000"),
            no_caption        = no_caption,
            is_video          = self._is_video,
            compress_pct      = self.compress_slider.value(),
            max_frames        = self.max_frames_spin.value(),
            out_format        = out_fmt,
        )

        self.gen_btn.setEnabled(False)
        self.copy_btn.setVisible(False)
        self.progress.setVisible(True)
        self.progress.setValue(0)
        self._set_status("Generating…", color=C["subtext"])

        self._thread = QThread()
        self._worker = Worker(params)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self.progress.setValue)
        self._worker.finished.connect(self._on_done)
        self._worker.error.connect(self._on_error)
        self._worker.finished.connect(self._thread.quit)
        self._worker.error.connect(self._thread.quit)
        self._thread.start()

    def _on_done(self, path):
        self._last_output = path
        self.gen_btn.setEnabled(True)
        self.progress.setValue(100)
        stem = Path(path).name
        size = os.path.getsize(path)
        self._set_status(f"Saved → outputs/{stem}  ({format_size(size)})", color=C["success"])
        self.copy_btn.setVisible(True)

        # Show animated playback for GIF; static first-frame for WebP
        if path.endswith(".webp"):
            self.preview.show_webp(path)
        else:
            self.preview.show_gif(path)

        # Update actual file size
        self.est_size_lbl.setText(format_size(size) + " (actual)")
        QTimer.singleShot(3000, lambda: self.progress.setVisible(False))

    def _on_error(self, msg):
        self.gen_btn.setEnabled(True)
        self.progress.setVisible(False)
        self._set_status("Error — check console for details.", error=True)
        QMessageBox.critical(self, "Error", msg)

    # ── Copy to clipboard ─────────────────────────────────────────────────────

    def _copy_to_clipboard(self):
        if not self._last_output or not os.path.isfile(self._last_output):
            return
        try:
            with open(self._last_output, "rb") as f:
                data_bytes = f.read()
            from PySide6.QtCore import QMimeData, QUrl
            # Use the correct MIME type for the output format
            mime_type = "image/webp" if self._last_output.endswith(".webp") else "image/gif"
            mdata = QMimeData()
            mdata.setData(mime_type, QByteArray(data_bytes))
            url = QUrl.fromLocalFile(self._last_output)
            mdata.setUrls([url])
            QApplication.clipboard().setMimeData(mdata)
            self._set_status("Copied to clipboard.", color=C["success"])
        except Exception as e:
            self._set_status(f"Copy failed: {e}", error=True)

    # ── Status helpers ────────────────────────────────────────────────────────

    def _set_status(self, msg, color=None, error=False):
        c = C["error"] if error else (color or C["subtext"])
        self.status_lbl.setText(msg)
        self.status_lbl.setStyleSheet(f"color:{c}; font-size:10px; background:transparent;")

    def _flash_status(self, msg, error=False):
        self._set_status(msg, error=error)
        QTimer.singleShot(3500, lambda: self.status_lbl.setText(""))

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if getattr(self, "_input_path", None):
            QTimer.singleShot(100, self._update_preview)


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    win = MainWindow()
    sys.exit(app.exec())
