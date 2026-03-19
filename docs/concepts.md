# Concepts

> Last documented update: 2026-03-19  
> Author: Mariana Almeida

This document introduces the core concepts required to understand the ideas explored in SnapVM.  
The goal is **not to provide deep theoretical explanations**, but to give enough context to understand the project and the experiments documented in this repository.

---

# AI Coding Agents

AI coding agents are systems that can write, modify, and execute code autonomously.

They typically operate in a loop where the agent:

1. analyzes a task
2. generates code or terminal commands
3. executes them
4. observes the results
5. adjusts its strategy

Examples of systems using this approach include automated debugging tools, autonomous programming agents, and AI-driven development assistants.

Because these systems execute arbitrary commands, they require **safe and isolated environments** where code can run without affecting the host system.

---

# ReAct Loop

Many AI agents use a workflow called **ReAct (Reason + Act)**.

In this model the agent repeatedly performs two steps:

**Reason**

The agent analyzes the current state and decides what to do next.

**Act** 

The agent executes a command such as running code, modifying files, or calling an API.

This cycle continues until the task is completed.

Because the agent continuously interacts with its environment, it is common for the environment to become **corrupted or unstable** during experimentation.

---

# Virtual Machines

A virtual machine (VM) is a software-based computer that runs inside another computer.

A VM includes its own:

- operating system
- memory
- processes
- file system

Virtual machines are commonly used to create **isolated environments** for running untrusted or experimental code.

This isolation ensures that failures inside the VM do not affect the host system.

---

# MicroVMs

A microVM is a lightweight virtual machine designed to start quickly and use minimal resources.

Unlike traditional virtual machines, microVMs remove unnecessary hardware emulation and focus only on the components required to run modern operating systems.

This allows microVMs to:

- start much faster
- consume less memory
- scale more efficiently

SnapVM uses **Firecracker microVMs** as the execution environment.

---

# Firecracker

Firecracker is an open-source Virtual Machine Monitor (VMM) developed by Amazon.

It is designed for serverless computing and powers services such as AWS Lambda.

Firecracker provides:

- fast microVM startup
- strong hardware-level isolation
- minimal resource overhead

Because of its lightweight design, Firecracker is well suited for systems that need to create and destroy environments frequently.

---

# VM Snapshots

A snapshot is a saved state of a virtual machine.

A snapshot typically contains:

- the VM memory
- CPU state
- device state
- file system state

Restoring a snapshot allows the system to **return to a previous state instantly**, including all running processes.

Snapshots make it possible to:

- recover from failures quickly
- experiment safely
- reproduce previous environments

Snapshots are a core primitive used in SnapVM.

---

# Copy-on-Write Memory

Copy-on-Write (CoW) is a memory optimization technique used when multiple systems share the same data.

When several VMs start from the same snapshot, they can initially share the same memory pages.

A new copy of a memory page is only created when one of the VMs modifies it.

This approach allows multiple environments to share most of their memory while still remaining independent.

CoW makes it possible to run many environments efficiently without duplicating all memory usage.

---

# Time-Travel Debugging

Time-travel debugging is the ability to move backward and forward through the execution state of a system.

Instead of manually reproducing a failure, the system can restore a previously saved state and continue execution from that point.

Snapshots enable this behavior because they capture the complete state of the environment.

This concept is one of the key motivations behind SnapVM.
