"""Vision Core — JARVIS's eyes: capture the screen, look (describe/answer), and verify.

This gives JARVIS a real act -> look -> verify loop. After doing something, JARVIS can
look at the screen and confirm it actually happened, instead of assuming. Vision uses the
Anthropic (Claude) vision model via LLMClient.vision(); everything degrades honestly when
there's no screen-capture library or no vision key.
"""
from __future__ import annotations
import os, sys
import os, sys


class VisionCore:
    def __init__(self, orch):
        self.orch = orch

    def _screen(self):
        return self.orch.tools.get("screen")

    def _has_eyes(self) -> bool:
        # Vision is Claude-only and REQUIRES a real Anthropic key — the screenshot is sent to the
        # Anthropic vision API. Being on the 'claude' brain without a key is NOT enough (that just
        # made vision fail silently). Accept either the env key, or a keyed 'claude' profile.
        if os.environ.get("ANTHROPIC_API_KEY"):
            return True
        try:
            prof = (self.orch.settings.get("llm", {}).get("profiles", {}) or {}).get("claude", {}) or {}
            return bool(os.environ.get(prof.get("api_key_env", "ANTHROPIC_API_KEY")))
        except Exception:
            return False

    def capture(self):
        screen = self._screen()
        if not screen:
            return (False, "", "no screen tool")
        return screen.capture_b64()

    def look(self, question: str = "") -> str:
        ok, b64, err = self.capture()
        if not ok:
            return f"I couldn't capture the screen, sir — {err}."
        if not self._has_eyes():
            return ("To actually see your screen I need Claude's eyes, sir — add your ANTHROPIC_API_KEY "
                    "to .env and I'll describe whatever is on screen.")
        q = question.strip() or ("Describe what is currently on this Windows screen — the active app, "
                                 "the windows open, and anything notable.")
        desc = self.orch.llm.vision(self.orch.system_prompt, q, b64)
        if desc:
            return desc
        err = (getattr(self.orch.llm, "_last_error", "") or "").strip()
        return ("I captured the screen, sir, but the vision request failed"
                + (f" — {err}." if err else
                   ". Check that ANTHROPIC_API_KEY is valid and has vision access."))

    def verify(self, expectation: str) -> dict:
        """Look at the screen and judge whether `expectation` is true right now.
        Returns {ok, verdict: yes|no|unclear, detail}."""
        expectation = (expectation or "").strip()
        if not expectation:
            return {"ok": False, "verdict": "unclear", "detail": "nothing specified to verify"}
        ok, b64, err = self.capture()
        if not ok:
            return {"ok": False, "verdict": "unclear", "detail": f"couldn't capture the screen ({err})"}
        if not self._has_eyes():
            return {"ok": False, "verdict": "unclear",
                    "detail": "I have no vision key (ANTHROPIC_API_KEY) to look with"}
        q = ("Look at this screen. Is the following true right now? \"" + expectation + "\". "
             "Answer with YES or NO on the first line, then one short sentence explaining what you see.")
        ans = (self.orch.llm.vision(self.orch.system_prompt, q, b64) or "").strip()
        head = ans.splitlines()[0].lower() if ans else ""
        verdict = "yes" if head.startswith("yes") else ("no" if head.startswith("no") else "unclear")
        return {"ok": verdict == "yes", "verdict": verdict, "detail": ans or "no response from vision"}

    # ---- masterpiece grounding: accessibility tree -> two-pass vision -------------
    @staticmethod
    def _clamp(v, lo, hi):
        return max(lo, min(hi, v))

    @staticmethod
    def refine_point(left, top, right, bottom, xc_pct, yc_pct):
        """Map a percentage point inside a crop box back to absolute screen pixels (pure/testable)."""
        x = left + (float(xc_pct) / 100.0) * (right - left)
        y = top + (float(yc_pct) / 100.0) * (bottom - top)
        return int(x), int(y)

    def _grab_image(self):
        """Return a full-screen PIL image, or None (no pillow / capture failure)."""
        try:
            from PIL import ImageGrab
            return ImageGrab.grab()
        except Exception:
            return None

    def _image_b64(self, img) -> str:
        import io, base64
        buf = io.BytesIO(); img.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode("ascii")

    def _crop_region(self, img, left, top, right, bottom):
        """Crop + 2x upscale a region so small targets become large and easy to pinpoint."""
        crop = img.crop((left, top, right, bottom))
        try:
            from PIL import Image
            crop = crop.resize((crop.size[0] * 2, crop.size[1] * 2), Image.LANCZOS)
        except Exception:
            pass
        return crop

    def _vision_point(self, b64: str, target: str, context: str = "") -> dict:
        """Ask the vision model for the centre of `target` as a percentage of THIS image."""
        ctx = (" " + context) if context else ""
        q = ("Find this element: \"" + target + "\"." + ctx + " Reply with ONLY JSON: "
             "{\"found\": true/false, \"x_pct\": <0-100>, \"y_pct\": <0-100>, \"label\": \"what is there\"}. "
             "x_pct/y_pct are the CENTRE of the element as a percentage of THIS image's width/height.")
        ans = (self.orch.llm.vision(self.orch.system_prompt, q, b64) or "").strip()
        import json, re
        data = None
        try:
            data = json.loads(ans)
        except Exception:
            m = re.search(r"\{.*\}", ans, re.DOTALL)
            if m:
                try:
                    data = json.loads(m.group(0))
                except Exception:
                    data = None
        if not isinstance(data, dict):
            return {"found": False}
        return data

    def _locate_uia(self, target: str):
        """Pixel-exact targeting via the Windows accessibility tree (UI Automation), if available."""
        if not sys.platform.startswith("win"):
            return None
        try:
            import uiautomation as auto
        except Exception:
            return None
        try:
            t = target.lower()
            root = auto.GetForegroundControl() or auto.GetRootControl()
            best = None
            for ctrl, _depth in auto.WalkControl(root, maxDepth=12):
                name = (getattr(ctrl, "Name", "") or "")
                if name and t in name.lower():
                    r = ctrl.BoundingRectangle
                    if r and (r.right - r.left) > 0 and (r.bottom - r.top) > 0:
                        best = {"x": int((r.left + r.right) / 2), "y": int((r.top + r.bottom) / 2),
                                "label": name}
                        # prefer an exact name match; otherwise take the first contains-match
                        if name.lower() == t:
                            break
            return best
        except Exception:
            return None

    def locate(self, target: str) -> dict:
        """Find a UI element and return the click point. Strategy, best-first:
          1) Windows accessibility tree (UIA) -> pixel-exact.
          2) Two-pass vision ("zoom and confirm") -> coarse locate, crop+upscale, precise locate.
          3) Single-pass vision fallback.
        Returns {ok, x, y, label, method, detail}. Degrades honestly at every step."""
        target = (target or "").strip()
        if not target:
            return {"ok": False, "detail": "nothing specified to find"}

        # 1) Accessibility tree — exact and fast
        u = self._locate_uia(target)
        if u:
            return {"ok": True, "x": u["x"], "y": u["y"], "label": u.get("label", ""),
                    "method": "accessibility tree", "detail": "exact"}

        # 2/3) Vision
        if not self._has_eyes():
            return {"ok": False, "detail": "I have no vision key (ANTHROPIC_API_KEY) and couldn't read the UI tree"}
        img = self._grab_image()
        if img is None:
            return {"ok": False, "detail": "I need pillow to see the screen for grounding (pip install pillow)"}
        W, H = img.size
        coarse = self._vision_point(self._image_b64(img), target)
        if not coarse.get("found"):
            return {"ok": False, "detail": "I couldn't find '" + target + "' on screen",
                    "label": coarse.get("label", "")}
        cx, cy = self.refine_point(0, 0, W, H, coarse.get("x_pct", 50), coarse.get("y_pct", 50))

        two_pass = bool((self.orch.settings.get("vision", {}) or {}).get("two_pass", True))
        if not two_pass:
            return {"ok": True, "x": self._clamp(cx, 0, W - 1), "y": self._clamp(cy, 0, H - 1),
                    "label": coarse.get("label", ""), "method": "vision (1-pass)", "detail": "single pass"}

        # zoom-and-confirm: crop a window around the coarse point, upscale, re-locate
        half_w = max(120, int(W * 0.16)); half_h = max(90, int(H * 0.16))
        left = self._clamp(cx - half_w, 0, W); right = self._clamp(cx + half_w, 0, W)
        top = self._clamp(cy - half_h, 0, H); bottom = self._clamp(cy + half_h, 0, H)
        try:
            crop = self._crop_region(img, left, top, right, bottom)
            fine = self._vision_point(self._image_b64(crop), target, context="this is a zoomed-in region of the screen")
        except Exception:
            fine = {"found": False}
        if not fine.get("found"):
            return {"ok": True, "x": self._clamp(cx, 0, W - 1), "y": self._clamp(cy, 0, H - 1),
                    "label": coarse.get("label", ""), "method": "vision (1-pass; refine missed)",
                    "detail": "coarse only"}
        fx, fy = self.refine_point(left, top, right, bottom, fine.get("x_pct", 50), fine.get("y_pct", 50))
        return {"ok": True, "x": self._clamp(fx, 0, W - 1), "y": self._clamp(fy, 0, H - 1),
                "label": fine.get("label", coarse.get("label", "")), "method": "vision (2-pass)",
                "detail": "zoom-and-confirm"}
