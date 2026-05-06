package com.snapvm.benchmark.csvanalytics;

import java.io.IOException;
import java.nio.file.Path;

public final class CsvAnalyticsApplication {
    private CsvAnalyticsApplication() {
    }

    public static void main(String[] args) {
        long startNanos = System.nanoTime();
        Path csvPath = args.length > 0 ? Path.of(args[0]) : Path.of("input", "sales.csv");

        try {
            CsvSalesLoader loader = new CsvSalesLoader();
            AnalyticsService analyticsService = new AnalyticsService();
            OutputPrinter outputPrinter = new OutputPrinter();

            LoadResult loadResult = loader.load(csvPath);
            AnalyticsResult analyticsResult = analyticsService.analyze(loadResult);
            long javaInternalMs = (System.nanoTime() - startNanos) / 1_000_000;

            outputPrinter.print(csvPath, analyticsResult, javaInternalMs);
        } catch (IOException ex) {
            System.err.println("ERROR=" + ex.getMessage());
            System.exit(1);
        }
    }
}
