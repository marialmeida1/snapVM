#!/usr/bin/env bash
set -euo pipefail

TAP_DEV="${TAP_DEV:-fctap0}"

if ip link show "${TAP_DEV}" >/dev/null 2>&1; then
    sudo ip link del "${TAP_DEV}"
    echo "[teardown_tap] Removed ${TAP_DEV}."
else
    echo "[teardown_tap] ${TAP_DEV} not found."
fi
