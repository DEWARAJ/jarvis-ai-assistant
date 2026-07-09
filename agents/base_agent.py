"""Base class for all specialist sub-agents."""
from __future__ import annotations


class BaseAgent:
    role = "Generic specialist agent"
    risk = "low"

    def __init__(self, name: str, context: dict | None = None, logger=None):
        self.name = name
        self.context = context or {}
        self.logger = logger

    # convenience accessors into shared context
    @property
    def memory(self): return self.context.get("memory")
    @property
    def tools(self): return self.context.get("tools")
    @property
    def tasks(self): return self.context.get("tasks")
    @property
    def llm(self): return self.context.get("llm")

    def tool(self, name):
        reg = self.context.get("tools")
        return reg.get(name) if reg else None

    def knowledge(self, *files: str, limit: int = 3500) -> str:
        """Load one or more business_knowledge/*.md files for grounding this agent's
        reasoning. Returns concatenated text (capped). Missing files are skipped quietly.
        Lets specialists reason from curated domain knowledge, not just the base persona."""
        import os
        parts = []
        for fn in files:
            name = fn if fn.endswith(".md") else fn + ".md"
            path = os.path.join("business_knowledge", name)
            try:
                if os.path.exists(path):
                    with open(path, encoding="utf-8") as f:
                        parts.append(f.read().strip())
            except OSError:
                continue
        text = "\n\n".join(p for p in parts if p)
        return text[:limit]

    def think(self, instruction: str, context_note: str = "") -> str | None:
        """Ask the LLM to reason as this specialist. Returns text, or None to fall back.

        The LLM only generates text; it never executes actions. All side-effecting
        operations stay behind the orchestrator's safety + permission gates.
        """
        llm = self.llm
        if not (llm and llm.available):
            return None
        persona = self.context.get("persona") or "You are JARVIS, a helpful AI operating system."
        system = (f"{persona}\n\nYou are acting as the '{self.name}' specialist sub-agent. "
                  f"Role: {self.role}. Be practical, concrete and concise. Use plain text. "
                  f"Never claim to have sent messages, spent money, or placed trades — you only advise/draft.")
        user = instruction if not context_note else f"{instruction}\n\nContext:\n{context_note}"
        return llm.chat(system, user)

    def _header(self, title: str, plan=None) -> str:
        out = [f"[{self.name}] {title}"]
        if plan:
            out.append("Plan: " + " -> ".join(plan))
        return "\n".join(out)

    def run(self, action: str, args: str = "", plan=None) -> str:
        """Default handler. Subclasses override with real capabilities."""
        return self._header(f"received '{action}' (no specialized handler yet).", plan) + \
               f"\nArgs: {args or '(none)'}"
