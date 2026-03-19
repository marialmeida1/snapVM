# Using This Benchmark in Docker

> Last documented update: 2026-03-19  
> Author: Mariana Almeida

This guide explains how to run `csv-analytics-benchmark` inside Docker and how to use it for simple, repeatable performance measurements.

## What the container does

The Docker image:

1. builds the Java project with Maven
2. copies the runnable JAR into a smaller Java runtime image
3. copies the `input/` directory
4. runs the benchmark application
5. prints an outer wall-clock time as `APP_TIME_MS`

The Java application itself also prints `JAVA_INTERNAL_MS`.

That means each container run gives you:

- the analytics results
- internal Java execution time
- total process time measured by the container command

## Prerequisites

You need:

- Docker installed
- the benchmark project available in the `benchmark/` directory

Optional but recommended:

- generate the larger benchmark dataset before running repeated tests

## 1. Move into the benchmark directory

```bash
cd /benchmark
```

## 2. Build the Docker image

```bash
docker build -t csv-analytics-benchmark .
```

This creates an image named `csv-analytics-benchmark`.

## 3. Run the benchmark container

```bash
docker run --rm csv-analytics-benchmark
```

Example output shape:

```text
DATASET_FILE=sales.csv
TOTAL_TRANSACTIONS=100000
VALID_TRANSACTIONS=100000
GROSS_REVENUE=...
NET_REVENUE=...
TOP_5_CATEGORIES_BY_REVENUE=...
TRANSACTIONS_BY_COUNTRY={...}
TRANSACTIONS_BY_CATEGORY={...}
JAVA_INTERNAL_MS=...
APP_TIME_MS=...
```

## What the timing values mean

See [EXPLICATION-VALUES-BENCHMARK.md](/Users/mariana/Documents/graduation/snapVM/benchmark/EXPLICATION-VALUES-BENCHMARK.md).

## 4. Generate a larger dataset for real benchmarking

If you want the intended benchmark scale, generate `100000` rows:

```bash
./scripts/generate_sales_csv.sh input/sales.csv 100000
```

Then rebuild the image so Docker includes the updated file:

```bash
docker build -t csv-analytics-benchmark .
```

Run again:

```bash
docker run --rm csv-analytics-benchmark
```

## 5. Run multiple times

A single run is usually not enough for benchmarking. Run several times and record the timings:

```bash
for i in {1..5}; do
  docker run --rm csv-analytics-benchmark
done
```

You can collect:

- `JAVA_INTERNAL_MS`
- `APP_TIME_MS`

Then compare:

- first run vs later runs
- average time
- fastest and slowest runs
- consistency between runs

## 6. What to keep constant for fair comparisons

If you want to compare Docker with Firecracker or another environment, keep these constant:

- same input file
- same Java version
- same benchmark code
- same host machine
- same CPU and memory limits if you apply them
- same number of repetitions

This helps ensure the environment is the main variable being compared.

## 7. Useful Docker options

Run with explicit CPU and memory limits:

```bash
docker run --rm --cpus="1" --memory="512m" csv-analytics-benchmark
```

This can make comparisons more controlled if you want the container to resemble a fixed VM shape.

## 8. Suggested benchmark workflow

1. Generate the target dataset.
2. Build the image once.
3. Run the container multiple times.
4. Save `JAVA_INTERNAL_MS` and `APP_TIME_MS` from each run.
5. Compute averages and variance.
6. Repeat the same idea in Firecracker.

## 9. Important note about rebuilds

The Docker image copies `input/` at build time. If you change `input/sales.csv`, rebuild the image before running again:

```bash
docker build -t csv-analytics-benchmark .
```

Otherwise the container may still use the old dataset from the previous image build.

## 10. Simple interpretation

If `JAVA_INTERNAL_MS` stays similar across environments but total runtime changes a lot, the difference is probably in environment/process startup overhead.

If both `JAVA_INTERNAL_MS` and total runtime change a lot, the environment may also be affecting application execution performance.
