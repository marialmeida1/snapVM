package com.snapvm.benchmark.csvanalytics;

import java.math.BigDecimal;
import java.util.List;
import java.util.Map;

public record AnalyticsResult(
        int totalTransactions,
        int validTransactions,
        BigDecimal grossRevenue,
        BigDecimal netRevenue,
        Map<String, Integer> transactionsByCategory,
        Map<String, Integer> transactionsByCountry,
        List<String> top5CategoriesByRevenue
) {
}
