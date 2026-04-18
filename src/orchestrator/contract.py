"""State-diff contract: verify guest health via HTTP probe."""

import requests

from .network import GUEST_IP

HEALTH_URL = f"http://{GUEST_IP}:3000/health"
PROBE_TIMEOUT = 5


def verify_state(url=HEALTH_URL, timeout=PROBE_TIMEOUT):
    """Probe the guest /health endpoint. Returns (passed: bool, detail: str)."""
    try:
        r = requests.get(url, timeout=timeout)
        body = r.json()
        if r.status_code == 200 and body.get("status") == "healthy":
            return True, "state-diff contract passed"
        return False, f"unhealthy: {body}"
    except requests.ConnectionError:
        return False, "connection refused — server down"
    except requests.Timeout:
        return False, "probe timed out"
    except Exception as e:
        return False, f"probe error: {e}"
