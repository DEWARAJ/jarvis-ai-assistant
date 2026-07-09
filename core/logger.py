"""Lightweight, dependency-free logger. Writes to logs/ and console."""
from __future__ import annotations
import os
from datetime import datetime

class Logger:
    def __init__(self, logs_dir: str = "logs", echo: bool = False):
        self.logs_dir = logs_dir
        self.echo = echo
        try:
            os.makedirs(logs_dir, exist_ok=True)
            self.logfile = os.path.join(logs_dir, "jarvis.log")
        except OSError:
            self.logfile = None  # never crash on logging

    def _write(self, level: str, msg: str) -> None:
        line = f"{datetime.now().isoformat(timespec='seconds')} [{level}] {msg}"
        if self.logfile:
            try:
                with open(self.logfile, "a", encoding="utf-8") as f:
                    f.write(line + "\n")
            except OSError:
                pass
        if self.echo:
            print(line)

    def info(self, msg: str) -> None: self._write("INFO", msg)
    def warn(self, msg: str) -> None: self._write("WARN", msg)
    def error(self, msg: str) -> None: self._write("ERROR", msg)
    def action(self, msg: str) -> None: self._write("ACTION", msg)
