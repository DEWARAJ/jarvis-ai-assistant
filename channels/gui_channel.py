"""GUI channel stub. Full command-center dashboard arrives in Phase 6."""
from __future__ import annotations

class GuiChannel:
    available = False
    def __init__(self, orchestrator=None, logger=None):
        self.orchestrator = orchestrator
        self.logger = logger
    def launch(self) -> str:
        return "GUI dashboard is planned for Phase 6. Use terminal mode for now."
