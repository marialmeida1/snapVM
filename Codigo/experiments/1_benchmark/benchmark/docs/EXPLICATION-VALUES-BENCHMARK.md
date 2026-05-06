# Benchmark Timing Values

> Last documented update: 2026-03-19  
> Author: Mariana Almeida

This document explains the timing values printed by the benchmark and how to interpret them during performance comparisons.

## `JAVA_INTERNAL_MS`

`JAVA_INTERNAL_MS` is measured inside the Java application.

It starts near the beginning of the `main` method and covers:

- CSV file loading
- row parsing
- row validation
- analytics computation
- result printing

This value is useful when you want to understand the time spent by the benchmark workload itself inside the JVM.

## `APP_TIME_MS`

`APP_TIME_MS` is measured outside the Java application by the shell command used in the Docker container.

It includes:

- Java process startup
- execution of the benchmark application
- process completion time

This value is useful when you want to measure the total runtime from the environment perspective.

## How to interpret both values

In practice:

- `JAVA_INTERNAL_MS` tells you how long the workload took inside the application
- `APP_TIME_MS` tells you how long the whole process took from outside the application

The difference between them usually reflects environment and startup overhead.

## How this helps in Docker vs Firecracker comparisons

If `JAVA_INTERNAL_MS` is similar in both environments but total runtime differs, the main difference is likely startup or runtime overhead from the environment.

If both `JAVA_INTERNAL_MS` and total runtime differ significantly, the environment may also be affecting execution performance of the application itself.

## Simple mental model

- `JAVA_INTERNAL_MS` = application work time
- `APP_TIME_MS` = full execution time
