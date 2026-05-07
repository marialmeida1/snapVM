#!/usr/bin/env bash

set -euo pipefail

OUTPUT_FILE="${1:-input/sales.csv}"
ROW_COUNT="${2:-100000}"

mkdir -p "$(dirname "$OUTPUT_FILE")"

categories=(Electronics Books Clothing Home Sports Beauty Grocery Toys)
countries=(Brazil USA Germany Japan Canada)
payment_methods=(CreditCard DebitCard Pix PayPal BankTransfer)

printf '%s\n' 'transaction_id,timestamp,customer_id,product_id,category,quantity,unit_price,discount_percent,country,payment_method' > "$OUTPUT_FILE"

for ((i=1; i<=ROW_COUNT; i++)); do
  tx_id=$(printf 'TX%06d' "$i")
  day=$(( ((i - 1) % 28) + 1 ))
  hour=$(( (i * 3) % 24 ))
  minute=$(( (i * 7) % 60 ))
  second=$(( (i * 11) % 60 ))
  customer_id=$(printf 'CUST%03d' $(( ((i - 1) % 500) + 1 )))
  product_id=$(printf 'PROD%03d' $(( ((i - 1) % 250) + 1 )))
  category="${categories[$(( (i - 1) % ${#categories[@]} ))]}"
  quantity=$(( ((i - 1) % 10) + 1 ))
  unit_price_cents=$(( 500 + ((i * 173) % 199501) ))
  unit_price=$(printf '%d.%02d' $(( unit_price_cents / 100 )) $(( unit_price_cents % 100 )))
  discount=$(( (i * 5) % 31 ))
  country="${countries[$(( (i - 1) % ${#countries[@]} ))]}"
  payment_method="${payment_methods[$(( (i - 1) % ${#payment_methods[@]} ))]}"

  printf '%s,2026-03-%02dT%02d:%02d:%02d,%s,%s,%s,%d,%s,%d,%s,%s\n' \
    "$tx_id" "$day" "$hour" "$minute" "$second" \
    "$customer_id" "$product_id" "$category" "$quantity" "$unit_price" "$discount" "$country" "$payment_method" \
    >> "$OUTPUT_FILE"
done
