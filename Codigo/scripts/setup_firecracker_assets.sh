#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CODIGO_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
REPO_ROOT="$(cd "${CODIGO_DIR}/.." && pwd)"

BIN_DIR="${CODIGO_DIR}/firecracker-bin"
ASSETS_DIR="${CODIGO_DIR}/firecracker-assets"
BUILD_DIR="${CODIGO_DIR}/.firecracker-build"

FC_VERSION="${FC_VERSION:-v1.7.0}"
FC_ARCH="${FC_ARCH:-x86_64}"
ROOTFS_SIZE_MB="${ROOTFS_SIZE_MB:-2048}"
IMAGE_TAG="snapvm-firecracker-rootfs:${FC_VERSION}"
KERNEL_URL="${KERNEL_URL:-https://s3.amazonaws.com/spec.ccfc.min/firecracker-ci/20260304-1e1378a65f61-0/x86_64/vmlinux-5.10.245}"
KERNEL_BASENAME="${KERNEL_BASENAME:-vmlinux-5.10.245}"

BENCHMARK_JAR="${CODIGO_DIR}/benchmark/target/csv-analytics-benchmark.jar"
DATASET_FILE="${CODIGO_DIR}/benchmark/input/sales.csv"

command -v curl >/dev/null 2>&1 || { echo "curl is required"; exit 1; }
command -v docker >/dev/null 2>&1 || { echo "docker is required"; exit 1; }
command -v mke2fs >/dev/null 2>&1 || { echo "mke2fs (e2fsprogs) is required"; exit 1; }

mkdir -p "${BIN_DIR}" "${ASSETS_DIR}"

ensure_benchmark_jar() {
  if [[ -f "${BENCHMARK_JAR}" ]]; then
    return
  fi

  echo "Benchmark JAR not found. Building with Maven..."
  if command -v mvn >/dev/null 2>&1; then
    MVN_BIN="mvn"
  elif [[ -x "${HOME}/.local/apache-maven-3.9.9/bin/mvn" ]]; then
    MVN_BIN="${HOME}/.local/apache-maven-3.9.9/bin/mvn"
  else
    echo "Maven is required to build the benchmark (install it or add to PATH)." >&2
    exit 1
  fi

  (cd "${CODIGO_DIR}/benchmark" && "${MVN_BIN}" -q clean package)
}

prepare_build_context() {
  rm -rf "${BUILD_DIR}"
  mkdir -p "${BUILD_DIR}/context"

  cat > "${BUILD_DIR}/context/Dockerfile" <<'EOF'
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      openjdk-21-jre-headless \
      ca-certificates \
      busybox \
      rsync \
      e2fsprogs && \
    rm -rf /var/lib/apt/lists/*

COPY csv-analytics-benchmark.jar /tmp/build/app/csv-analytics-benchmark.jar
COPY sales.csv /tmp/build/app/input/sales.csv
COPY init.sh /tmp/build/init.sh
COPY build-rootfs.sh /usr/local/bin/build-rootfs.sh

RUN chmod +x /usr/local/bin/build-rootfs.sh /tmp/build/init.sh

ENTRYPOINT ["/usr/local/bin/build-rootfs.sh"]
EOF

  cat > "${BUILD_DIR}/context/init.sh" <<'EOF'
#!/bin/sh
set -eu

echo "[SNAPVM] Boot script starting at $(date -Iseconds)"
if ! mountpoint -q /proc; then
  mount -t proc proc /proc
fi
if ! mountpoint -q /sys; then
  mount -t sysfs sysfs /sys
fi
if ! mountpoint -q /dev; then
  mount -t devtmpfs devtmpfs /dev 2>/dev/null || true
fi

cd /app
echo "[SNAPVM] Running csv-analytics-benchmark.jar"
START_MS=$(date +%s%3N)
java -Xms256m -Xmx768m -jar csv-analytics-benchmark.jar input/sales.csv
APP_RC=$?
END_MS=$(date +%s%3N)
echo "APP_EXIT_CODE=${APP_RC}"
echo "FIRECRACKER_WALL_MS=$((END_MS - START_MS))"
echo "[SNAPVM] Benchmark finished"
sync
/bin/busybox poweroff
EOF

  cat > "${BUILD_DIR}/context/build-rootfs.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

ROOTFS_DIR="/tmp/rootfs"
APP_SRC="/tmp/build/app"
INIT_SRC="/tmp/build/init.sh"
OUTPUT_DIR="/output"

mkdir -p "${ROOTFS_DIR}"

rsync -aHx \
  --exclude=/proc \
  --exclude=/sys \
  --exclude=/dev \
  --exclude=/run \
  --exclude=/tmp \
  --exclude=/var/run \
  --exclude=/var/tmp \
  --exclude=/output \
  --exclude=/tmp/rootfs \
  --exclude=/tmp/build \
  / "${ROOTFS_DIR}"

mkdir -p "${ROOTFS_DIR}/dev" "${ROOTFS_DIR}/proc" "${ROOTFS_DIR}/sys" "${ROOTFS_DIR}/run" "${ROOTFS_DIR}/tmp"
chmod 755 "${ROOTFS_DIR}/dev" "${ROOTFS_DIR}/proc" "${ROOTFS_DIR}/sys" "${ROOTFS_DIR}/run" "${ROOTFS_DIR}/tmp"

create_node() {
  local path="$1"
  local type="$2"
  local major="$3"
  local minor="$4"
  if [[ ! -e "${path}" ]]; then
    mknod -m 666 "${path}" "${type}" "${major}" "${minor}"
  fi
}

create_node "${ROOTFS_DIR}/dev/null" c 1 3
create_node "${ROOTFS_DIR}/dev/zero" c 1 5
create_node "${ROOTFS_DIR}/dev/random" c 1 8
create_node "${ROOTFS_DIR}/dev/urandom" c 1 9
create_node "${ROOTFS_DIR}/dev/tty" c 5 0
create_node "${ROOTFS_DIR}/dev/console" c 5 1
create_node "${ROOTFS_DIR}/dev/ttyS0" c 4 64

mkdir -p "${ROOTFS_DIR}/app/input"
cp "${APP_SRC}/csv-analytics-benchmark.jar" "${ROOTFS_DIR}/app/"
cp "${APP_SRC}/input/sales.csv" "${ROOTFS_DIR}/app/input/"
cp "${INIT_SRC}" "${ROOTFS_DIR}/init"
chmod +x "${ROOTFS_DIR}/init"

cat > "${ROOTFS_DIR}/etc/motd" <<'EOM'
SnapVM Firecracker benchmark rootfs
EOM

mkdir -p "${OUTPUT_DIR}"
TARGET="${OUTPUT_DIR}/rootfs.ext4"
ROOTFS_SIZE_MB="${ROOTFS_SIZE_MB:-2048}"
truncate -s "${ROOTFS_SIZE_MB}M" "${TARGET}"
BLOCKS=$((ROOTFS_SIZE_MB * 1024 * 1024 / 4096))

mke2fs -d "${ROOTFS_DIR}" -t ext4 -b 4096 -m 0 -F "${TARGET}" "${BLOCKS}"
EOF

  cp "${BENCHMARK_JAR}" "${BUILD_DIR}/context/csv-analytics-benchmark.jar"
  cp "${DATASET_FILE}" "${BUILD_DIR}/context/sales.csv"
}

build_rootfs_image() {
  docker build -t "${IMAGE_TAG}" "${BUILD_DIR}/context"
  docker run --rm \
    -e ROOTFS_SIZE_MB="${ROOTFS_SIZE_MB}" \
    -v "${ASSETS_DIR}":/output \
    "${IMAGE_TAG}"
}

download_if_missing() {
  local url="$1"
  local dest="$2"
  if [[ -f "${dest}" ]]; then
    echo "Already present: ${dest}"
    return
  fi
  echo "Downloading ${url}"
  curl -L "${url}" -o "${dest}"
}

download_firecracker_bits() {
  local base_url="https://github.com/firecracker-microvm/firecracker/releases/download/${FC_VERSION}"
  local tarball="${BUILD_DIR}/firecracker-${FC_VERSION}-${FC_ARCH}.tgz"
  download_if_missing "${base_url}/firecracker-${FC_VERSION}-${FC_ARCH}.tgz" "${tarball}"

  if [[ ! -f "${BIN_DIR}/firecracker" || ! -f "${BIN_DIR}/jailer" ]]; then
    tar -xzf "${tarball}" -C "${BUILD_DIR}"
    cp "${BUILD_DIR}/firecracker-${FC_VERSION}-${FC_ARCH}/firecracker" "${BIN_DIR}/firecracker"
    cp "${BUILD_DIR}/firecracker-${FC_VERSION}-${FC_ARCH}/jailer" "${BIN_DIR}/jailer"
    chmod +x "${BIN_DIR}/firecracker" "${BIN_DIR}/jailer"
  else
    echo "Firecracker binaries already exist in ${BIN_DIR}"
  fi

  download_if_missing "${KERNEL_URL}" "${ASSETS_DIR}/vmlinux.bin"
  ln -sfn "vmlinux.bin" "${ASSETS_DIR}/${KERNEL_BASENAME}.bin" >/dev/null 2>&1 || true
}

main() {
  ensure_benchmark_jar
  prepare_build_context
  build_rootfs_image
  download_firecracker_bits
  echo "Firecracker assets ready under ${ASSETS_DIR} and binaries under ${BIN_DIR}"
}

main "$@"
