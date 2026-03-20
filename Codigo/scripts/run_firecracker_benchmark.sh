#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CODIGO_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

BIN_DIR="${CODIGO_DIR}/firecracker-bin"
ASSETS_DIR="${CODIGO_DIR}/firecracker-assets"
ARTIFACT_DIR="${CODIGO_DIR}/firecracker-run"
RUN_DIR="${RUN_TMP_DIR:-/tmp/snapvm-firecracker-run}"
SOCK_PATH="${RUN_DIR}/firecracker.sock"
LOG_PATH="${RUN_DIR}/firecracker.log"
METRICS_PATH="${RUN_DIR}/firecracker-metrics.log"
CONSOLE_LOG="${RUN_DIR}/firecracker-console.log"
SUMMARY_PATH="${RUN_DIR}/run_summary.txt"
ARTIFACT_SUMMARY="${ARTIFACT_DIR}/run_summary.txt"

KERNEL_IMAGE="${ASSETS_DIR}/vmlinux.bin"
ROOTFS_IMAGE="${ASSETS_DIR}/rootfs.ext4"

mkdir -p "${RUN_DIR}" "${ARTIFACT_DIR}"

for dep in curl; do
  command -v "${dep}" >/dev/null 2>&1 || { echo "Missing dependency: ${dep}"; exit 1; }
done

[[ -x "${BIN_DIR}/firecracker" ]] || { echo "Missing firecracker binary in ${BIN_DIR}"; exit 1; }
[[ -f "${KERNEL_IMAGE}" ]] || { echo "Missing kernel image at ${KERNEL_IMAGE}"; exit 1; }
[[ -f "${ROOTFS_IMAGE}" ]] || { echo "Missing rootfs image at ${ROOTFS_IMAGE}"; exit 1; }

cleanup_previous() {
  rm -f "${SOCK_PATH}" "${LOG_PATH}" "${METRICS_PATH}" "${CONSOLE_LOG}"
  touch "${LOG_PATH}" "${METRICS_PATH}"
}

configure_microvm() {
  local sock="$1"
  local cpu_count="${CPU_COUNT:-2}"
  local mem_mib="${MEM_SIZE_MIB:-1024}"

  curl --unix-socket "${sock}" -s -S -X PUT 'http://localhost/machine-config' \
    -H 'Accept: application/json' \
    -H 'Content-Type: application/json' \
    -d "{\"vcpu_count\":${cpu_count},\"mem_size_mib\":${mem_mib},\"smt\":false}" >/dev/null

  curl --unix-socket "${sock}" -s -S -X PUT 'http://localhost/boot-source' \
    -H 'Accept: application/json' \
    -H 'Content-Type: application/json' \
    -d "{\"kernel_image_path\":\"${KERNEL_IMAGE}\",\"boot_args\":\"console=ttyS0 reboot=k panic=1 pci=off init=/init root=/dev/vda\"}" >/dev/null

  curl --unix-socket "${sock}" -s -S -X PUT 'http://localhost/drives/rootfs' \
    -H 'Accept: application/json' \
    -H 'Content-Type: application/json' \
    -d "{\"drive_id\":\"rootfs\",\"path_on_host\":\"${ROOTFS_IMAGE}\",\"is_root_device\":false,\"is_read_only\":false}" >/dev/null
}

start_microvm() {
  local sock="$1"
  curl --unix-socket "${sock}" -s -S -X PUT 'http://localhost/actions' \
    -H 'Accept: application/json' \
    -H 'Content-Type: application/json' \
    -d '{"action_type":"InstanceStart"}' >/dev/null
}

start_firecracker() {
  "${BIN_DIR}/firecracker" \
    --api-sock "${SOCK_PATH}" \
    --log-path "${LOG_PATH}" \
    --level "Info" \
    --metrics-path "${METRICS_PATH}" \
    > "${CONSOLE_LOG}" 2>&1 &
  FC_PID=$!
}

wait_for_socket() {
  local sock="$1"
  for _ in $(seq 1 50); do
    [[ -S "${sock}" ]] && return 0
    sleep 0.1
  done
  echo "Firecracker API socket not available: ${sock}" >&2
  return 1
}

extract_metrics() {
  local console_file="$1"
  local java_ms=$(grep -Eo 'JAVA_INTERNAL_MS=[0-9]+' "${console_file}" | tail -n 1 | cut -d'=' -f2)
  local wall_ms=$(grep -Eo 'FIRECRACKER_WALL_MS=[0-9]+' "${console_file}" | tail -n 1 | cut -d'=' -f2)
  echo "${java_ms:-NA}" "${wall_ms:-NA}"
}

main() {
  cleanup_previous

  START_MS=$(date +%s%3N)
  start_firecracker

  trap "kill ${FC_PID} >/dev/null 2>&1 || true" EXIT

  wait_for_socket "${SOCK_PATH}"
  configure_microvm "${SOCK_PATH}"
  start_microvm "${SOCK_PATH}"

  wait "${FC_PID}"
  END_MS=$(date +%s%3N)
  trap - EXIT

  HOST_DURATION=$((END_MS - START_MS))

  read JAVA_MS FIRECRACKER_WALL <<<"$(extract_metrics "${CONSOLE_LOG}")"

  {
    echo "Host_wall_ms=${HOST_DURATION}"
    echo "Guest_java_internal_ms=${JAVA_MS}"
    echo "Guest_firecracker_wall_ms=${FIRECRACKER_WALL}"
    echo "Console_log=${ARTIFACT_DIR}/firecracker-console.log"
    echo "Firecracker_log=${ARTIFACT_DIR}/firecracker.log"
    echo "Metrics_log=${ARTIFACT_DIR}/firecracker-metrics.log"
  } > "${SUMMARY_PATH}"

  cp "${CONSOLE_LOG}" "${ARTIFACT_DIR}/firecracker-console.log"
  cp "${LOG_PATH}" "${ARTIFACT_DIR}/firecracker.log"
  cp "${METRICS_PATH}" "${ARTIFACT_DIR}/firecracker-metrics.log"
  cp "${SUMMARY_PATH}" "${ARTIFACT_SUMMARY}"

  cat "${ARTIFACT_SUMMARY}"
}

main "$@"
