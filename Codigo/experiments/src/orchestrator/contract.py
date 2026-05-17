"""State-diff contract: verify guest health via HTTP probe."""

import requests

from .config import HEALTH_URL

PROBE_TIMEOUT = 5


def verify_state(url=HEALTH_URL, timeout=PROBE_TIMEOUT):
    """Probe the guest /health endpoint. Returns (passed: bool, detail: str)."""
    try:
        r = requests.get(url, timeout=timeout)
        try:
            body = r.json()
        except ValueError:
            return False, f"non-json response (status={r.status_code})"
        if r.status_code == 200 and body.get("status") == "healthy":
            return True, "state-diff contract passed"
        return False, f"unhealthy: {body}"
    except requests.ConnectionError:
        return False, "connection refused — server down"
    except requests.Timeout:
        return False, "probe timed out"
    except requests.RequestException as e:
        return False, f"probe error: {e}"
