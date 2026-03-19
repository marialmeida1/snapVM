package com.snapvm.benchmark.csvanalytics;

import java.io.BufferedReader;
import java.io.IOException;
import java.math.BigDecimal;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.LocalDateTime;
import java.time.format.DateTimeParseException;
import java.util.ArrayList;
import java.util.List;
import java.util.Set;

public final class CsvSalesLoader {
    private static final String EXPECTED_HEADER =
            "transaction_id,timestamp,customer_id,product_id,category,quantity,unit_price,discount_percent,country,payment_method";

    static final List<String> CATEGORY_ORDER = List.of(
            "Electronics", "Books", "Clothing", "Home", "Sports", "Beauty", "Grocery", "Toys"
    );
    static final List<String> COUNTRY_ORDER = List.of(
            "Brazil", "USA", "Germany", "Japan", "Canada"
    );
    static final List<String> PAYMENT_METHOD_ORDER = List.of(
            "CreditCard", "DebitCard", "Pix", "PayPal", "BankTransfer"
    );

    private static final Set<String> VALID_CATEGORIES = Set.copyOf(CATEGORY_ORDER);
    private static final Set<String> VALID_COUNTRIES = Set.copyOf(COUNTRY_ORDER);
    private static final Set<String> VALID_PAYMENT_METHODS = Set.copyOf(PAYMENT_METHOD_ORDER);

    public LoadResult load(Path csvPath) throws IOException {
        List<SaleRecord> validRecords = new ArrayList<>();
        int totalTransactions = 0;

        try (BufferedReader reader = Files.newBufferedReader(csvPath)) {
            String header = reader.readLine();
            if (header == null) {
                throw new IOException("CSV file is empty: " + csvPath);
            }
            if (!EXPECTED_HEADER.equals(header.trim())) {
                throw new IOException("Unexpected CSV header in " + csvPath);
            }

            String line;
            while ((line = reader.readLine()) != null) {
                if (line.isBlank()) {
                    continue;
                }

                totalTransactions++;
                parseLine(line).ifPresent(validRecords::add);
            }
        }

        return new LoadResult(totalTransactions, List.copyOf(validRecords));
    }

    private java.util.Optional<SaleRecord> parseLine(String line) {
        String[] parts = line.split(",", -1);
        if (parts.length != 10) {
            return java.util.Optional.empty();
        }

        try {
            String transactionId = parts[0].trim();
            LocalDateTime timestamp = LocalDateTime.parse(parts[1].trim());
            String customerId = parts[2].trim();
            String productId = parts[3].trim();
            String category = parts[4].trim();
            int quantity = Integer.parseInt(parts[5].trim());
            BigDecimal unitPrice = new BigDecimal(parts[6].trim());
            int discountPercent = Integer.parseInt(parts[7].trim());
            String country = parts[8].trim();
            String paymentMethod = parts[9].trim();

            if (!isValid(transactionId, customerId, productId, category, quantity, unitPrice,
                    discountPercent, country, paymentMethod)) {
                return java.util.Optional.empty();
            }

            return java.util.Optional.of(new SaleRecord(
                    transactionId,
                    timestamp,
                    customerId,
                    productId,
                    category,
                    quantity,
                    unitPrice,
                    discountPercent,
                    country,
                    paymentMethod
            ));
        } catch (NumberFormatException | DateTimeParseException ex) {
            return java.util.Optional.empty();
        }
    }

    private boolean isValid(
            String transactionId,
            String customerId,
            String productId,
            String category,
            int quantity,
            BigDecimal unitPrice,
            int discountPercent,
            String country,
            String paymentMethod
    ) {
        return !transactionId.isEmpty()
                && !customerId.isEmpty()
                && !productId.isEmpty()
                && VALID_CATEGORIES.contains(category)
                && VALID_COUNTRIES.contains(country)
                && VALID_PAYMENT_METHODS.contains(paymentMethod)
                && quantity >= 1
                && quantity <= 10
                && unitPrice.compareTo(BigDecimal.valueOf(5.00)) >= 0
                && unitPrice.compareTo(BigDecimal.valueOf(2000.00)) <= 0
                && discountPercent >= 0
                && discountPercent <= 30;
    }
}
