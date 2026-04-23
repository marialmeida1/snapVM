#!/bin/bash
set -u

log_kmsg() {
  echo "init: $1" >/dev/kmsg 2>/dev/null || true
}

mount -t proc proc /proc 2>/dev/null || true
mount -t sysfs sys /sys 2>/dev/null || true
mount -t devtmpfs dev /dev 2>/dev/null || true
mkdir -p /dev/shm
mount -t tmpfs -o mode=1777,nosuid,nodev tmpfs /dev/shm 2>/dev/null || true
chmod 1777 /tmp 2>/dev/null || true

ip link set dev lo up 2>/dev/null || true

# Configure guest network interface. Fall back to first non-loopback iface.
guest_iface="${GUEST_IFACE:-eth0}"
if ! ip link show "$guest_iface" >/dev/null 2>&1; then
  guest_iface="$(ip -o link show | awk -F': ' '$2 != "lo" {print $2; exit}')"
fi
if [ -z "${guest_iface}" ]; then
  log_kmsg "no guest iface found"
  exec sleep infinity
fi

ip link set dev "$guest_iface" up 2>/dev/null || true
ip addr add 172.16.0.2/24 dev "$guest_iface" 2>/dev/null || true
ip route replace default via 172.16.0.1 dev "$guest_iface" 2>/dev/null || true

# In rootless docker export, postgres-owned files may be uid 1000.
if id postgres >/dev/null 2>&1 && [ "$(id -u postgres)" != "1000" ]; then
  sed -i -E 's/^postgres:x:[0-9]+:[0-9]+:/postgres:x:1000:1000:/' /etc/passwd || true
  sed -i -E 's/^postgres:x:[0-9]+:/postgres:x:1000:/' /etc/group || true
fi

mkdir -p /var/log /run/postgresql
touch /var/log/postgres-start.log /var/log/node.log /var/log/haveged.log
chown 1000:1000 /run/postgresql 2>/dev/null || true
chmod 2775 /run/postgresql 2>/dev/null || true

entropy_before="$(cat /proc/sys/kernel/random/entropy_avail 2>/dev/null || echo unknown)"
if command -v haveged >/dev/null 2>&1; then
  haveged -F >/var/log/haveged.log 2>&1 &
  for _ in $(seq 1 40); do
    entropy_now="$(cat /proc/sys/kernel/random/entropy_avail 2>/dev/null || echo 0)"
    case "$entropy_now" in
      ''|*[!0-9]*) break ;;
    esac
    if [ "$entropy_now" -ge 256 ]; then
      break
    fi
    sleep 0.25
  done
fi
entropy_after="$(cat /proc/sys/kernel/random/entropy_avail 2>/dev/null || echo unknown)"
log_kmsg "entropy before=${entropy_before} after=${entropy_after}"

postgres_start_output="$(pg_ctlcluster 15 main start 2>&1)"
postgres_start_rc=$?
printf '%s\n' "$postgres_start_output" > /var/log/postgres-start.log
if [ "$postgres_start_rc" -ne 0 ]; then
  postgres_start_compact="$(printf '%s' "$postgres_start_output" | tr '\n' '|')"
  log_kmsg "pg_ctlcluster failed: ${postgres_start_compact:-unknown}"
fi

cd /opt/app || {
  log_kmsg "missing /opt/app"
  exec sleep infinity
}
/usr/bin/node server.js >/var/log/node.log 2>&1 &

sleep 3
pg_ready_status="$(pg_isready -h 127.0.0.1 -p 5432 -U admin 2>&1 || true)"
log_kmsg "pg_isready: ${pg_ready_status}"
if ss -ltn 2>/dev/null | grep -q ':5432' && ss -ltn 2>/dev/null | grep -q ':3000'; then
  log_kmsg "services ready"
else
  log_kmsg "services not ready"
fi

exec sleep infinity
