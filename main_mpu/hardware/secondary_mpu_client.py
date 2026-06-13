"""HTTP client for querying and commanding secondary MPUs (Rock Zeros).

Each Rock Zero is reachable at a fixed IP on its USB-OTG network interface.
The Main R3B assigns 192.168.N.1 to itself and 192.168.N.2 to the Rock Zero
for each USB interface N (1–4).
"""

import json
import urllib.request
from declarations import NODE_ID

# Fixed IP map: Rock Zero index → IP on USB-OTG network
_SECONDARY_IPS = {
    1: "192.168.1.2",
    2: "192.168.2.2",
    3: "192.168.3.2",
    4: "192.168.4.2",
}

_PORT = 9001
_TIMEOUT = 2  # seconds — must not block the telemetry loop


class SecondaryMPUClient:
    def get_status(self, index: int) -> dict:
        """Return status dict from Rock Zero. Returns {"alive": False} on any failure."""
        try:
            url = f"http://{_SECONDARY_IPS[index]}:{_PORT}/status"
            with urllib.request.urlopen(url, timeout=_TIMEOUT) as resp:
                return json.loads(resp.read())
        except Exception:
            return {"alive": False, "recording": False, "disk_free_gb": 0}

    def send_command(self, index: int, cmd: str) -> bool:
        """Send a command to a Rock Zero. Returns True on success."""
        try:
            url = f"http://{_SECONDARY_IPS[index]}:{_PORT}/cmd"
            body = json.dumps({"cmd": cmd}).encode()
            req = urllib.request.Request(url, data=body, method="POST")
            req.add_header("Content-Type", "application/json")
            urllib.request.urlopen(req, timeout=_TIMEOUT)
            return True
        except Exception as e:
            print(f"[{NODE_ID}] Secondary MPU {index} cmd '{cmd}' failed: {e}")
            return False
