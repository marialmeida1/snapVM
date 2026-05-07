# Environment Setup Guide (MVP)

This document outlines the planned infrastructure setup for running the Firecracker vs. Git baseline experiments.

## 1. Host Infrastructure Requirements

*   **Operating System:** Bare-metal Linux host.
*   **Virtualization:** Hardware virtualization (KVM) must be enabled. Verify with `lsmod | grep kvm`.
*   **Control Plane:** Python 3.x (for the orchestration scripts, failure injection, and telemetry collection).

## 2. Guest MicroVM Architecture (Firecracker)

To accurately benchmark stateful recovery, the guest environment must be highly stateful. We accomplish this by utilizing a full database daemon rather than a file-based alternative like SQLite.

### Kernel (`vmlinux`)
*   An uncompressed Linux kernel optimized for Firecracker (minimal modules, built for rapid boot times). 

### Root Filesystem (`rootfs.ext4`)
We will construct an `ext4` filesystem image containing:
*   **Base OS:** A minimal distribution such as Alpine Linux or Debian minimal.
*   **Database:** **PostgreSQL** installed and configured to start on boot. Postgres provides the ideal stateful scenario: an active supervisor process, background writers, WAL archivers, shared memory buffer pools, and persistent TCP connection pools.
*   **Runtime:** Node.js runtime.
*   **Application:** The target experimental web server, actively connected to the PostgreSQL database.

### Networking
*   **TAP Interface:** A TAP network interface configured on the bare-metal host. The Python orchestrator will use this to communicate with the guest microVM (e.g., running the State-Diff Contract HTTP probes and injecting the LLM code changes).

## 3. Setup Roadmap

1.  **Host Preparation:** Validate KVM, install Firecracker binaries, set up Python virtual environment.
2.  **Kernel Acquisition:** Compile or download a Firecracker-compatible `vmlinux` kernel.
3.  **Rootfs Construction:** Use `docker` or `debootstrap` to assemble the guest OS, install Node.js + PostgreSQL, and extract the filesystem to a raw `ext4` image file.
4.  **Orchestrator Development:** Write the Python control plane to interact with the Firecracker daemon socket.
