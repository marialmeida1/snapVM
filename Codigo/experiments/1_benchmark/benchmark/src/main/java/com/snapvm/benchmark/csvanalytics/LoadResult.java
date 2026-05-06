package com.snapvm.benchmark.csvanalytics;

import java.util.List;

public record LoadResult(int totalTransactions, List<SaleRecord> validRecords) {
}
