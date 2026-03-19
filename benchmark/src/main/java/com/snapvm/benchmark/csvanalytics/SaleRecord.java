package com.snapvm.benchmark.csvanalytics;

import java.math.BigDecimal;
import java.time.LocalDateTime;

public record SaleRecord(
        String transactionId,
        LocalDateTime timestamp,
        String customerId,
        String productId,
        String category,
        int quantity,
        BigDecimal unitPrice,
        int discountPercent,
        String country,
        String paymentMethod
) {
    public BigDecimal grossAmount() {
        return unitPrice.multiply(BigDecimal.valueOf(quantity));
    }

    public BigDecimal netAmount() {
        BigDecimal discountMultiplier = BigDecimal.valueOf(100L - discountPercent)
                .movePointLeft(2);
        return grossAmount().multiply(discountMultiplier);
    }
}
