"""Screen capture for JARVIS. Uses Pillow (ImageGrab) if available, else mss, else honest fail."""
from __future__ import annotations
import os
from datetime import datetime
from tools.base_tool import BaseTool


class ScreenControlTool(BaseTool):
    name = "screen"; scope = "screenshots"

    def __init__(self, context=None, logger=None):
        super().__init__(context, logger)
        self.dir = "screenshots"
        os.makedirs(self.dir, exist_ok=True)

    def screenshot(self) -> dict:
        path = os.path.join(self.dir, datetime.now().strftime("shot_%Y%m%d_%H%M%S.png"))
        # try Pillow first
        try:
            from PIL import ImageGrab
            img = ImageGrab.grab()
            img.save(path)
            return {"action": "screenshot", "started": True, "path": os.path.abspath(path),
                    "spoken": "Screenshot saved.", "debug": f"PIL.ImageGrab -> {path}"}
        except Exception as e1:
            pass
        # try mss
        try:
            import mss
            with mss.mss() as sct:
                sct.shot(output=path)
            return {"action": "screenshot", "started": True, "path": os.path.abspath(path),
                    "spoken": "Screenshot saved.", "debug": f"mss -> {path}"}
        except Exception as e2:
            return {"action": "screenshot", "started": False, "path": "",
                    "spoken": "I couldn't take a screenshot — the capture library isn't installed. "
                              "Install it with: pip install pillow",
                    "debug": f"no PIL/mss available"}

    # Anthropic's vision API rejects very large images (long edge > 8000px) with HTTP 400, and
    # bills/slows on anything over ~1568px. A full-res or multi-monitor screenshot routinely
    # trips this — the cause of "the vision request didn't come back". We downscale the long
    # edge to <=1568px before encoding: well within limits, faster, cheaper, still legible.
    _VISION_MAX_EDGE = 1568

    def _downscale(self, img, max_edge: int = None):
        max_edge = max_edge or self._VISION_MAX_EDGE
        try:
            from PIL import Image
            w, h = img.size
            longest = max(w, h)
            if longest > max_edge:
                scale = max_edge / float(longest)
                img = img.resize((max(1, int(w * scale)), max(1, int(h * scale))), Image.LANCZOS)
        except Exception:
            pass
        return img

    def capture_b64(self):
        """Return (ok, base64_png, error) for the vision model. Uses Pillow then mss, and
        DOWNSCALES the long edge to <=1568px so Anthropic never 400s on an oversized image."""
        import io, base64
        try:
            from PIL import ImageGrab
            img = ImageGrab.grab()
            img = self._downscale(img)
            if img.mode not in ("RGB", "L"):
                img = img.convert("RGB")          # drop alpha so PNG encodes cleanly
            buf = io.BytesIO(); img.save(buf, format="PNG")
            return True, base64.b64encode(buf.getvalue()).decode("ascii"), ""
        except Exception as e1:
            pass
        try:
            import mss, mss.tools
            from PIL import Image
            with mss.mss() as sct:
                # monitors[1] = primary screen (monitors[0] is the whole virtual desktop, which
                # on multi-monitor rigs can exceed 8000px wide and be rejected). Fall back to [0].
                mon = sct.monitors[1] if len(sct.monitors) > 1 else sct.monitors[0]
                raw = sct.grab(mon)
                img = Image.frombytes("RGB", raw.size, raw.rgb)
                img = self._downscale(img)
                buf = io.BytesIO(); img.save(buf, format="PNG")
                return True, base64.b64encode(buf.getvalue()).decode("ascii"), ""
        except Exception as e2:
            return False, "", "no PIL/mss (pip install pillow)"
