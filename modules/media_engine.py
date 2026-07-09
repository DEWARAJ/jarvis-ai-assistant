"""JARVIS v6.0 — Image and video editing via Pillow and moviepy."""
from __future__ import annotations
from pathlib import Path

try: from PIL import Image, ImageDraw; _PIL = True
except ImportError: _PIL = False

try: import moviepy.editor as mp; _MOVIE = True
except ImportError: _MOVIE = False


def resize_image(path: str, width: int, height: int, out: str | None = None,
                 confirmed: bool = False) -> str:
    if not _PIL: return "Pillow not installed."
    try:
        img = Image.open(path).resize((width, height), Image.LANCZOS)
        dest = out or path; img.save(dest)
        return f"Resized to {width}x{height}: {dest}"
    except Exception as e: return f"Resize error: {e}"


def crop_image(path: str, left: int, top: int, right: int, bottom: int,
               out: str | None = None, confirmed: bool = False) -> str:
    if not _PIL: return "Pillow not installed."
    try:
        img = Image.open(path).crop((left, top, right, bottom))
        dest = out or path; img.save(dest)
        return f"Cropped: {dest}"
    except Exception as e: return f"Crop error: {e}"


def convert_image(path: str, fmt: str, out: str | None = None,
                  confirmed: bool = False) -> str:
    if not _PIL: return "Pillow not installed."
    try:
        img = Image.open(path)
        dest = out or str(Path(path).with_suffix(f".{fmt.lower()}"))
        img.save(dest, fmt.upper()); return f"Converted: {dest}"
    except Exception as e: return f"Convert error: {e}"


def add_text_overlay(path: str, text: str, x: int = 10, y: int = 10,
                     out: str | None = None, confirmed: bool = False) -> str:
    if not _PIL: return "Pillow not installed."
    try:
        img = Image.open(path).convert("RGBA")
        ImageDraw.Draw(img).text((x, y), text, fill=(255, 255, 255, 200))
        dest = out or path; img.save(dest); return f"Overlay added: {dest}"
    except Exception as e: return f"Overlay error: {e}"


def compress_image(path: str, quality: int = 60, out: str | None = None,
                   confirmed: bool = False) -> str:
    if not _PIL: return "Pillow not installed."
    try:
        img = Image.open(path)
        dest = out or path; img.save(dest, quality=quality, optimize=True)
        return f"Compressed (q={quality}): {dest}"
    except Exception as e: return f"Compress error: {e}"


def image_info(path: str) -> dict:
    if not _PIL: return {"error": "Pillow not installed"}
    try:
        img = Image.open(path)
        return {"size": img.size, "mode": img.mode, "format": img.format,
                "file_size_kb": round(Path(path).stat().st_size / 1024, 1)}
    except Exception as e: return {"error": str(e)}


def video_info(path: str) -> dict:
    if not _MOVIE: return {"error": "moviepy not installed"}
    try:
        clip = mp.VideoFileClip(path)
        info = {"duration_s": round(clip.duration, 2), "fps": clip.fps, "size": clip.size}
        clip.close(); return info
    except Exception as e: return {"error": str(e)}


def trim_video(path: str, start: float, end: float, out: str,
               confirmed: bool = False) -> str:
    if not _MOVIE: return "moviepy not installed."
    try:
        clip = mp.VideoFileClip(path).subclip(start, end)
        clip.write_videofile(out, logger=None); clip.close()
        return f"Trimmed: {out}"
    except Exception as e: return f"Trim error: {e}"


def extract_audio(path: str, out: str, confirmed: bool = False) -> str:
    if not _MOVIE: return "moviepy not installed."
    try:
        clip = mp.VideoFileClip(path)
        clip.audio.write_audiofile(out, logger=None); clip.close()
        return f"Audio extracted: {out}"
    except Exception as e: return f"Extract error: {e}"
