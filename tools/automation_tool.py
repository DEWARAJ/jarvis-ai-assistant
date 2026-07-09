from __future__ import annotations
from tools.base_tool import BaseTool

class AutomationTool(BaseTool):
    """Produces automation PLANS only. Execution is gated and off in Phase 1."""
    name = "automation"; scope = "plan only"
    def plan(self, goal: str) -> str:
        goal = goal or "(unspecified workflow)"
        return ("Automation spec (design only — not executed):\n"
                f"  name: auto_{abs(hash(goal)) % 10000}\n"
                f"  purpose: {goal}\n"
                "  trigger: manual / scheduled (TBD)\n"
                "  steps: 1) gather inputs 2) transform 3) output 4) verify\n"
                "  required_permissions: confirm before any file write / external call\n"
                "  risk_level: medium\n"
                "  rollback_plan: backup before changes; revert on failure\n"
                "  logs: every run appended to logs/\n"
                "Run only after explicit Master approval.")
