"""JARVIS v6.0 — USB devices, printers, peripheral management (Windows)."""
from __future__ import annotations

try: import wmi; _WMI = True
except ImportError: _WMI = False

try: import win32print; _WIN32 = True
except ImportError: _WIN32 = False


def list_usb_devices() -> list[dict]:
    if not _WMI: return [{"error": "wmi not installed (Windows only)"}]
    try:
        c = wmi.WMI()
        return [{"name": d.Description, "device_id": d.DeviceID,
                 "status": d.Status}
                for d in c.Win32_USBControllerDevice()]
    except Exception as e: return [{"error": str(e)}]


def list_printers() -> list[str]:
    if not _WIN32: return ["win32print not installed (Windows only)"]
    try:
        return [p[2] for p in win32print.EnumPrinters(
            win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS)]
    except Exception as e: return [f"Error: {e}"]


def print_file(filepath: str, printer: str | None = None,
               confirmed: bool = False) -> str:
    if not _WIN32: return "win32print not installed."
    try:
        p = printer or win32print.GetDefaultPrinter()
        win32print.ShellExecute(0, "print", filepath, None, ".", 0)
        return f"Print job sent to {p}"
    except Exception as e: return f"Print error: {e}"


def get_default_printer() -> str:
    if not _WIN32: return "win32print not installed."
    try: return win32print.GetDefaultPrinter()
    except Exception as e: return f"Error: {e}"
