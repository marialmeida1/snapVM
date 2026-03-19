package com.snapvm.benchmark.csvanalytics;

import java.math.BigDecimal;
import java.nio.file.Path;
import java.util.Map;
import java.util.StringJoiner;

public final class OutputPrinter {
    public void print(Path csvPath, AnalyticsResult result, long javaInternalMs) {
        System.out.println("DATASET_FILE=" + csvPath.getFileName());
        System.out.println("TOTAL_TRANSACTIONS=" + result.totalTransactions());
        System.out.println("VALID_TRANSACTIONS=" + result.validTransactions());
        System.out.println("GROSS_REVENUE=" + formatMoney(result.grossRevenue()));
        System.out.println("NET_REVENUE=" + formatMoney(result.netRevenue()));
        System.out.println("TOP_5_CATEGORIES_BY_REVENUE=" + String.join(",", result.top5CategoriesByRevenue()));
        System.out.println("TRANSACTIONS_BY_COUNTRY=" + formatMap(result.transactionsByCountry()));
        System.out.println("TRANSACTIONS_BY_CATEGORY=" + formatMap(result.transactionsByCategory()));
        System.out.println("JAVA_INTERNAL_MS=" + javaInternalMs);
    }

    private String formatMoney(BigDecimal value) {
        return value.toPlainString();
    }

    private String formatMap(Map<String, Integer> values) {
        StringJoiner joiner = new StringJoiner(",", "{", "}");
        for (Map.Entry<String, Integer> entry : values.entrySet()) {
            joiner.add(entry.getKey() + "=" + entry.getValue());
        }
        return joiner.toString();
    }
}
