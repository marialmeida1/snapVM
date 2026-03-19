# SnapVM Overview

> Last documented update: 2026-03-19  
> Author: Mariana Almeida

## What is SnapVM

SnapVM is an experimental tool that explores the use of **Firecracker microVM snapshots** to create fast, recoverable execution environments.

The main idea behind SnapVM is to allow environments to be **saved, restored, and cloned instantly**, enabling workflows where systems can safely experiment, fail, and recover without rebuilding the entire environment.

---

## The Problem

Modern systems that execute code automatically — such as AI coding agents, automated testing systems, or CI pipelines — require **isolated environments** where code can run safely.

The most common solution today is:

- Docker containers
- Git-based recovery
- Full environment rebuilds

However, these approaches have limitations:

- Recovering from environment corruption can take seconds or minutes
- Rebuilding dependencies repeatedly is inefficient
- Running multiple parallel environments consumes significant memory
- Restoring a previous system state is not instantaneous

These limitations make rapid experimentation difficult.

---

## The Core Idea

SnapVM explores a different approach: **using VM snapshots as the primary mechanism for environment management.**

With snapshots, the entire state of a virtual machine can be saved and restored, including:

- memory
- running processes
- file system state
- system configuration

This makes it possible to:

- restore environments almost instantly
- safely experiment without permanent damage
- clone environments for parallel execution
- revert systems to previous states in milliseconds

Instead of rebuilding environments, SnapVM focuses on **rewinding them.**

---

## How SnapVM Works

SnapVM acts as a lightweight orchestration layer on top of **Firecracker microVMs**.

Its responsibilities include:

- starting and stopping microVMs
- creating snapshots
- restoring snapshots
- managing VM execution states
