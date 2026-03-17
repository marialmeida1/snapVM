#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXAMPLE_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
GUEST_DIR="${EXAMPLE_DIR}/guest"
RUN_DIR="${EXAMPLE_DIR}/run"
mkdir -p "${RUN_DIR}"

: "${FIRECRACKER_BIN:?Set FIRECRACKER_BIN to the firecracker binary path}"
: "${KERNEL_IMAGE:?Set KERNEL_IMAGE to a guest kernel image path}"
: "${ROOTFS_IMAGE:?Set ROOTFS_IMAGE to a rootfs image with python3 + ssh server}"
: "${SSH_KEY:?Set SSH_KEY to the private key for guest root login}"

TAP_DEV="${TAP_DEV:-fctap0}"
HOST_TAP_IP="${HOST_TAP_IP:-172.16.0.1}"
GUEST_IP="${GUEST_IP:-172.16.0.2}"
GUEST_MAC="${GUEST_MAC:-06:00:AC:10:00:02}"
SSH_USER="${SSH_USER:-root}"
SSH_PORT="${SSH_PORT:-22}"
SSH_TIMEOUT_SEC="${SSH_TIMEOUT_SEC:-90}"

SOCK1="${RUN_DIR}/fc-1.socket"
SOCK2="${RUN_DIR}/fc-2.socket"
LOG1="${RUN_DIR}/fc-1.log"
LOG2="${RUN_DIR}/fc-2.log"
PID1_FILE="${RUN_DIR}/fc-1.pid"
PID2_FILE="${RUN_DIR}/fc-2.pid"

SNAPSHOT_STATE="${RUN_DIR}/snapshot_vmstate.fc"
SNAPSHOT_MEM="${RUN_DIR}/snapshot_mem.fc"

SSH_OPTS=(
    -i "${SSH_KEY}"
    -o StrictHostKeyChecking=no
    -o UserKnownHostsFile=/dev/null
    -o LogLevel=ERROR
    -p "${SSH_PORT}"
)

api_call() {
    local sock="$1" method="$2" path="$3"
    local body="${4:-}"
    if [[ -n "${body}" ]]; then
        curl --silent --show-error --fail \
            --unix-socket "${sock}" \
            -H "Content-Type: application/json" \
            -X "${method}" \
            -d "${body}" \
            "http://localhost${path}" >/dev/null
    else
        curl --silent --show-error --fail \
            --unix-socket "${sock}" \
            -X "${method}" \
            "http://localhost${path}" >/dev/null
    fi
}

start_firecracker() {
    local sock="$1" log="$2" pid_file="$3"
    rm -f "${sock}"
    "${FIRECRACKER_BIN}" --api-sock "${sock}" >"${log}" 2>&1 &
    echo "$!" >"${pid_file}"

    for _ in $(seq 1 100); do
        [[ -S "${sock}" ]] && return 0
        sleep 0.05
    done
    echo "Firecracker socket did not appear: ${sock}" >&2
    return 1
}

stop_firecracker() {
    local pid_file="$1"
    if [[ -f "${pid_file}" ]]; then
        local pid
        pid="$(cat "${pid_file}")"
        if kill -0 "${pid}" >/dev/null 2>&1; then
            kill "${pid}"
            wait "${pid}" 2>/dev/null || true
        fi
    fi
}

configure_and_boot_vm() {
    local sock="$1"
    local boot_args
    boot_args="console=ttyS0 reboot=k panic=1 pci=off ip=${GUEST_IP}::${HOST_TAP_IP}:255.255.255.0::eth0:off"

    api_call "${sock}" PUT /machine-config \
        '{"vcpu_count":1,"mem_size_mib":512,"smt":false}'

    api_call "${sock}" PUT /boot-source \
        "{\"kernel_image_path\":\"${KERNEL_IMAGE}\",\"boot_args\":\"${boot_args}\"}"

    api_call "${sock}" PUT /drives/rootfs \
        "{\"drive_id\":\"rootfs\",\"path_on_host\":\"${ROOTFS_IMAGE}\",\"is_root_device\":true,\"is_read_only\":false}"

    api_call "${sock}" PUT /network-interfaces/eth0 \
        "{\"iface_id\":\"eth0\",\"host_dev_name\":\"${TAP_DEV}\",\"guest_mac\":\"${GUEST_MAC}\"}"

    api_call "${sock}" PUT /actions '{"action_type":"InstanceStart"}'
}

wait_for_ssh() {
    local deadline=$((SECONDS + SSH_TIMEOUT_SEC))
    while ((SECONDS < deadline)); do
        if ssh "${SSH_OPTS[@]}" "${SSH_USER}@${GUEST_IP}" "true" >/dev/null 2>&1; then
            return 0
        fi
        sleep 1
    done
    echo "Timed out waiting for SSH on ${GUEST_IP}:${SSH_PORT}" >&2
    return 1
}

guest_ssh() {
    ssh "${SSH_OPTS[@]}" "${SSH_USER}@${GUEST_IP}" "$@"
}

copy_to_guest() {
    local src="$1" dst="$2"
    scp "${SSH_OPTS[@]}" "${src}" "${SSH_USER}@${GUEST_IP}:${dst}" >/dev/null
}

start_guest_api() {
    guest_ssh "if [ -f /tmp/app.pid ]; then kill \$(cat /tmp/app.pid) 2>/dev/null || true; fi"
    guest_ssh "nohup python3 /dev/shm/app.py >/tmp/app.log 2>&1 & echo \$! >/tmp/app.pid"
}

assert_guest_api_healthy() {
    local body
    body="$(guest_ssh "curl -fsS http://127.0.0.1:8000/")"
    if [[ "${body}" != "Hello, world!"* ]]; then
        echo "Unexpected API response: ${body}" >&2
        return 1
    fi
}

assert_guest_api_broken() {
    if guest_ssh "curl -fsS --max-time 2 http://127.0.0.1:8000/" >/dev/null 2>&1; then
        echo "Expected failure, but API still responded successfully." >&2
        return 1
    fi
}

cleanup() {
    stop_firecracker "${PID1_FILE}"
    stop_firecracker "${PID2_FILE}"
}
trap cleanup EXIT

echo "[1/8] Starting Firecracker VM #1"
start_firecracker "${SOCK1}" "${LOG1}" "${PID1_FILE}"
configure_and_boot_vm "${SOCK1}"
wait_for_ssh

echo "[2/8] Deploying working Hello World API inside guest (/dev/shm/app.py)"
copy_to_guest "${GUEST_DIR}/api_working.py" "/dev/shm/app.py"
start_guest_api
assert_guest_api_healthy
echo "      API healthy."

echo "[3/8] Pausing VM and creating snapshot"
api_call "${SOCK1}" PATCH /vm '{"state":"Paused"}'
api_call "${SOCK1}" PUT /snapshot/create \
    "{\"snapshot_type\":\"Full\",\"snapshot_path\":\"${SNAPSHOT_STATE}\",\"mem_file_path\":\"${SNAPSHOT_MEM}\"}"
api_call "${SOCK1}" PATCH /vm '{"state":"Resumed"}'

echo "[4/8] Introducing broken code and restarting API"
copy_to_guest "${GUEST_DIR}/api_broken.py" "/dev/shm/app.py"
start_guest_api
assert_guest_api_broken
echo "      Failure detected as expected."

echo "[5/8] Stopping Firecracker VM #1"
stop_firecracker "${PID1_FILE}"
rm -f "${PID1_FILE}"

echo "[6/8] Starting fresh Firecracker VM #2"
start_firecracker "${SOCK2}" "${LOG2}" "${PID2_FILE}"

echo "[7/8] Loading previous snapshot and resuming"
api_call "${SOCK2}" PUT /snapshot/load \
    "{\"snapshot_path\":\"${SNAPSHOT_STATE}\",\"mem_backend\":{\"backend_path\":\"${SNAPSHOT_MEM}\",\"backend_type\":\"File\"},\"resume_vm\":true}"
wait_for_ssh

echo "[8/8] Verifying rollback recovered working API"
assert_guest_api_healthy
echo "✅ Rollback successful: API is healthy again (Hello, world!)."

