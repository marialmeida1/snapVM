#!/usr/bin/env bash
set -euo pipefail

TAP_DEV="${TAP_DEV:-fctap0}"
HOST_TAP_IP="${HOST_TAP_IP:-172.16.0.1}"
CIDR="${CIDR:-24}"
OWNER_UID="${OWNER_UID:-$(id -u)}"

if ip link show "${TAP_DEV}" >/dev/null 2>&1; then
    echo "[setup_tap] ${TAP_DEV} already exists."
else
    sudo ip tuntap add dev "${TAP_DEV}" mode tap user "${OWNER_UID}"
fi

if ! ip addr show "${TAP_DEV}" | grep -q "${HOST_TAP_IP}/${CIDR}"; then
    sudo ip addr add "${HOST_TAP_IP}/${CIDR}" dev "${TAP_DEV}"
fi

sudo ip link set "${TAP_DEV}" up
echo "[setup_tap] ${TAP_DEV} is ready at ${HOST_TAP_IP}/${CIDR}."
