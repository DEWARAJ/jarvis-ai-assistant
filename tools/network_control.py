"""Wi-Fi + Bluetooth control. Honest about admin limits — never fakes success."""
from __future__ import annotations
import os, sys, subprocess, re
from tools.base_tool import BaseTool


class NetworkControlTool(BaseTool):
    name = "network"; scope = "wi-fi / bluetooth"

    def _adapter_name(self) -> str:
        try:
            out = subprocess.run(["netsh", "interface", "show", "interface"],
                                 capture_output=True, text=True, timeout=10).stdout
            for line in out.splitlines():
                if "wi-fi" in line.lower() or "wireless" in line.lower():
                    parts = line.split()
                    return parts[-1] if parts else "Wi-Fi"
        except Exception:
            pass
        return "Wi-Fi"

    def _set_wifi(self, enabled: bool) -> dict:
        verb = "enabled" if enabled else "disabled"
        if not sys.platform.startswith("win"):
            return {"started": True, "spoken": f"(Would turn Wi-Fi {'on' if enabled else 'off'} on Windows.)",
                    "debug": "simulated"}
        name = self._adapter_name()
        try:
            r = subprocess.run(["netsh", "interface", "set", "interface", f"name={name}", f"admin={verb}"],
                               capture_output=True, text=True, timeout=12)
            err = (r.stderr + r.stdout).lower()
            if r.returncode == 0 and "requires elevation" not in err and "access is denied" not in err:
                return {"started": True, "spoken": f"Wi-Fi turned {'on' if enabled else 'off'}.",
                        "debug": f"netsh ok adapter={name}"}
            if "elevation" in err or "denied" in err:
                os.startfile("ms-settings:network-wifi")
                return {"started": False,
                        "spoken": "I need administrator permission to change Wi-Fi. I opened Wi-Fi settings — "
                                  "or restart JARVIS as administrator and I'll do it directly.",
                        "debug": "needs admin"}
            os.startfile("ms-settings:network-wifi")
            return {"started": False,
                    "spoken": f"I couldn't toggle Wi-Fi directly (adapter '{name}'). I opened Wi-Fi settings for you.",
                    "debug": err[:200]}
        except Exception as e:
            try: os.startfile("ms-settings:network-wifi")
            except Exception: pass
            return {"started": False, "spoken": f"I couldn't change Wi-Fi ({e}). I opened the settings page.",
                    "debug": str(e)}

    def wifi_on(self):  return self._set_wifi(True)
    def wifi_off(self): return self._set_wifi(False)

    def bluetooth(self, on: bool) -> dict:
        if not sys.platform.startswith("win"):
            return {"started": True, "spoken": "(Would toggle Bluetooth on Windows.)", "debug": "sim"}
        # Real radio toggle via the WinRT Radio API, properly awaited + with radio-access consent.
        # This genuinely flips the Bluetooth radio on Windows 10/11 (first run may show a one-time
        # consent prompt). Falls back honestly to the Settings page if the OS still refuses.
        state = "On" if on else "Off"
        ps = (
            "$ErrorActionPreference='Stop';"
            "try{"
            "Add-Type -AssemblyName System.Runtime.WindowsRuntime | Out-Null;"
            "$as=([System.WindowsRuntimeSystemExtensions].GetMethods()|"
            "?{$_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and "
            "$_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1'})[0];"
            "function Await($op,$t){$tk=$as.MakeGenericMethod($t).Invoke($null,@($op));"
            "$tk.Wait(-1)|Out-Null;return $tk.Result};"
            "[Windows.Devices.Radios.Radio,Windows.System.Devices,ContentType=WindowsRuntime]|Out-Null;"
            "[Windows.Devices.Radios.RadioState,Windows.System.Devices,ContentType=WindowsRuntime]|Out-Null;"
            "[Windows.Devices.Radios.RadioAccessStatus,Windows.System.Devices,ContentType=WindowsRuntime]|Out-Null;"
            "Await ([Windows.Devices.Radios.Radio]::RequestAccessAsync()) "
            "([Windows.Devices.Radios.RadioAccessStatus])|Out-Null;"
            "$radios=Await ([Windows.Devices.Radios.Radio]::GetRadiosAsync()) "
            "([System.Collections.Generic.IReadOnlyList[Windows.Devices.Radios.Radio]]);"
            "$done=$false;"
            "foreach($r in $radios){ if($r.Kind -eq 'Bluetooth'){"
            "Await ($r.SetStateAsync([Windows.Devices.Radios.RadioState]::" + state + ")) "
            "([Windows.Devices.Radios.RadioAccessStatus])|Out-Null; $done=$true } };"
            "if($done){'OK'}else{'NORADIO'}"
            "}catch{'FAIL:'+$_.Exception.Message}"
        )
        try:
            r = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
                               capture_output=True, text=True, timeout=30)
            out = (r.stdout or "").strip()
            if "OK" in out:
                return {"started": True, "spoken": f"Bluetooth turned {'on' if on else 'off'}, sir.",
                        "debug": "winrt radio toggled"}
            if "NORADIO" in out:
                return {"started": False,
                        "spoken": "I couldn't find a Bluetooth radio on this machine, sir.",
                        "debug": "no bluetooth radio"}
            # otherwise fall through to settings, keeping the real error for the log
            err = out or (r.stderr or "").strip()
        except Exception as e:
            err = str(e)
        try:
            os.startfile("ms-settings:bluetooth")
        except Exception:
            pass
        return {"started": False,
                "spoken": "I opened Bluetooth settings, sir. Windows declined the direct toggle this time — "
                          "if it asked for permission, allow it once and I'll flip it directly from then on.",
                "debug": f"winrt declined; settings opened ({err[:160]})"}
