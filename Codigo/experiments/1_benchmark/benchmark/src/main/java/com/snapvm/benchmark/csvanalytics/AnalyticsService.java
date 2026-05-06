package com.snapvm.benchmark.csvanalytics;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.Collections;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

public final class AnalyticsService {
    public AnalyticsResult analyze(LoadResult loadResult) {
        Map<String, Integer> transactionsByCategory = zeroCountMap(CsvSalesLoader.CATEGORY_ORDER);
        Map<String, Integer> transactionsByCountry = zeroCountMap(CsvSalesLoader.COUNTRY_ORDER);
        Map<String, BigDecimal> revenueByCategory = zeroAmountMap(CsvSalesLoader.CATEGORY_ORDER);

        BigDecimal grossRevenue = BigDecimal.ZERO;
        BigDecimal netRevenue = BigDecimal.ZERO;

        for (SaleRecord record : loadResult.validRecords()) {
            BigDecimal grossAmount = record.grossAmount();
            BigDecimal netAmount = record.netAmount();

            grossRevenue = grossRevenue.add(grossAmount);
            netRevenue = netRevenue.add(netAmount);

            transactionsByCategory.merge(record.category(), 1, Integer::sum);
            transactionsByCountry.merge(record.country(), 1, Integer::sum);
            revenueByCategory.merge(record.category(), netAmount, BigDecimal::add);
        }

        List<String> top5Categories = revenueByCategory.entrySet().stream()
                .sorted(Map.Entry.<String, BigDecimal>comparingByValue(Comparator.reverseOrder())
                        .thenComparing(Map.Entry.comparingByKey()))
                .limit(5)
                .map(Map.Entry::getKey)
                .toList();

        return new AnalyticsResult(
                loadResult.totalTransactions(),
                loadResult.validRecords().size(),
                grossRevenue.setScale(2, RoundingMode.HALF_UP),
                netRevenue.setScale(2, RoundingMode.HALF_UP),
                Collections.unmodifiableMap(new LinkedHashMap<>(transactionsByCategory)),
                Collections.unmodifiableMap(new LinkedHashMap<>(transactionsByCountry)),
                top5Categories
        );
    }

    private Map<String, Integer> zeroCountMap(List<String> orderedKeys) {
        Map<String, Integer> map = new LinkedHashMap<>();
        for (String key : orderedKeys) {
            map.put(key, 0);
        }
        return map;
    }

    private Map<String, BigDecimal> zeroAmountMap(List<String> orderedKeys) {
        Map<String, BigDecimal> map = new LinkedHashMap<>();
        for (String key : orderedKeys) {
            map.put(key, BigDecimal.ZERO);
        }
        return map;
    }
}
