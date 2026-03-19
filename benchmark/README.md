# csv-analytics-benchmark

> Last documented update: 2026-03-19  
> Author: Mariana Almeida

`csv-analytics-benchmark` is a small Java 21 CLI application designed for reproducible performance comparisons between Docker containers and Firecracker microVMs.

It loads a sales CSV file, validates each record, computes summary analytics, prints machine-readable `KEY=VALUE` output, prints internal Java execution time in milliseconds, and exits.

## Why this project is useful for Docker vs Firecracker benchmarking

This benchmark is intentionally simple and deterministic:

- fixed input file path by default: `input/sales.csv`
- no network calls
- no database
- no framework startup overhead
- single-process CLI execution
- stable output ordering for easy parsing

That makes it useful when comparing isolated runtime environments because the work being measured is mostly:

- JVM startup
- file I/O
- CSV parsing
- validation
- in-memory analytics

## Project layout

```text
benchmark/
  input/sales.csv
  pom.xml
  README.md
  Dockerfile
  scripts/generate_sales_csv.sh
  src/main/java/com/snapvm/benchmark/csvanalytics/...
```

## Build

From the `benchmark` directory:

```bash
mvn clean package
```

This produces a runnable fat JAR:

```bash
target/csv-analytics-benchmark.jar
```

## Run

Use the default dataset:

```bash
java -jar target/csv-analytics-benchmark.jar
```

Use a custom dataset path:

```bash
java -jar target/csv-analytics-benchmark.jar input/sales.csv
```

## Expected output

The program prints one `KEY=VALUE` pair per line.

Example:

```text
DATASET_FILE=sales.csv
TOTAL_TRANSACTIONS=120
VALID_TRANSACTIONS=120
GROSS_REVENUE=126023.70
NET_REVENUE=109249.20
TOP_5_CATEGORIES_BY_REVENUE=Electronics,Home,Beauty,Grocery,Sports
TRANSACTIONS_BY_COUNTRY={Brazil=24,USA=24,Germany=24,Japan=24,Canada=24}
TRANSACTIONS_BY_CATEGORY={Electronics=15,Books=15,Clothing=15,Home=15,Sports=15,Beauty=15,Grocery=15,Toys=15}
JAVA_INTERNAL_MS=18
```

`JAVA_INTERNAL_MS` is measured inside the Java process using `System.nanoTime()`. If you run the container image, the Docker entrypoint also prints `APP_TIME_MS`, which captures wall-clock process duration from the shell.

## Docker usage

Build the image from the `benchmark` directory:

```bash
docker build -t csv-analytics-benchmark .
```

Run it:

```bash
docker run --rm csv-analytics-benchmark
```

## Generating a larger 100,000-row dataset

A deterministic generator script is included:

```bash
./scripts/generate_sales_csv.sh input/sales.csv 100000
```

The script:

- keeps the required schema
- uses only the allowed categories, countries, and payment methods
- generates stable values from the row index
- avoids randomness so repeated benchmark runs are reproducible

## Notes for benchmarking

- Warmup matters for JVM benchmarks, so run multiple iterations.
- Keep the dataset identical across Docker and Firecracker runs.
- If you compare cold starts, rebuild the environment consistently before each run.
- Prefer collecting both outer wall-clock time and `JAVA_INTERNAL_MS`.
