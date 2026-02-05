# External API Integration Bug Analysis

## Problem
Price updates are not reaching the external WordPress API (sarafipardis.co.uk) during the finalization flow, while a standalone script (`t.py`) works.

---

## 1. Five Possible Reasons for Django vs Script Discrepancy

### 1.1 Filter Logic in `_build_rates_from_items` (GBP "Account" Matching)
**Likelihood: HIGH**

The service checks `"حسابی"` or `"account"` for GBP account prices. Other parts of the codebase (e.g. `change_price/views.py`, `change_price/templatetags/change_price_tags.py`) also check for **`"از حساب"`** (from account). If PriceType names use "خرید از حساب" or "فروش از حساب" without the word "حسابی", they will be **incorrectly skipped** as cash.

- **sort_gbp_price_types**: checks `'حسابی'`, `'از حساب'`, `'account'`
- **_build_rates_from_items**: checks only `'حسابی'`, `'account'` → **missing "از حساب"**

### 1.2 Empty `rates` Dict (All Items Skipped)
**Likelihood: HIGH**

If every price type is filtered out (e.g. all GBP are "نقدی", or currency codes don't match), `rates` will be empty. The code returns early with "No GBP/USDT prices found" and **no API call is made**. The script always sends a hardcoded rate.

### 1.3 Request Timeout / Connection in Django Context
**Likelihood: MEDIUM**

- Django may run behind a reverse proxy (nginx, gunicorn) with different timeouts.
- The server may have restricted outbound connections (firewall, security group).
- DNS resolution or SSL verification could behave differently in the WSGI context.
- The script runs in a different environment (local machine, different network).

### 1.4 Logger Configuration (Logs Not Visible)
**Likelihood: MEDIUM**

- Production may have `logging` level set to WARNING or ERROR; INFO logs would be suppressed.
- Logs may go to a file or external service not checked by the operator.
- The panel's Log model uses `log_finalize_event` which writes to DB; the standard `logger` may use a different sink.

### 1.5 Uncommitted Database Transactions
**Likelihood: LOW**

- The API call is **outside** `transaction.atomic()` (Step 1 runs before Step 3).
- `price_items` are built from `PriceType` and `PriceHistory` which are already committed (updated in a prior request).
- **Conclusion**: Transaction rollback is not affecting the API call. The API call is never rolled back.

---

## 2. `_build_rates_from_items` Analysis: GBP "Account/حسابی" Handling

### Current Logic (line 251–268)

```python
is_account = "حسابی" in getattr(price_type, "name", "") or "account" in price_type_name
```

- `price_type_name` = `(getattr(price_type, "name", "") or "").lower()`

### Issues Identified

| Issue | Description |
|-------|-------------|
| **Missing "از حساب"** | Names like "خرید از حساب" or "فروش از حساب" do NOT contain "حسابی" and would be skipped. |
| **Case sensitivity** | `"account" in price_type_name` is correct (name is lowercased). |
| **Currency pair** | Only `{"GBP","IRR"}` and `{"GBP","IRT"}` are accepted. If target is "Toman" or other, pair won't match. |
| **Duplicate overwrite** | "Latest value wins" – if multiple items map to same key, the last one overwrites. Order of iteration matters. |

### Recommendation
Add `"از حساب"` to the `is_account` check to align with `sort_gbp_price_types` and `change_price`:

```python
is_account = (
    "حسابی" in getattr(price_type, "name", "")
    or "از حساب" in getattr(price_type, "name", "")
    or "account" in price_type_name
)
```

---

## 3. Transaction and Rollback Analysis

### Execution Order in `finalize_category`

1. **Step 1** (lines 250–332): API call – **outside** any `transaction.atomic()`
2. **Step 2** (lines 334–369): Telegram publish – **outside** `transaction.atomic()`
3. **Step 3** (lines 371–392): `with transaction.atomic():` – only wraps `Finalization` + `FinalizedPriceHistory` creation

### Conclusion

- The API call is **not** inside a transaction block.
- If the Telegram step or the transaction fails, the API call **has already executed** and is **not rolled back**.
- The design is intentional: API first, then Telegram, then DB.

---

## 4. Instrumentation Added

The following logging has been added to `finalize/services.py`:

### In `send_request`
- Full request payload (with optional api_key redaction for production)
- Full response status code and body (or truncated text on non-JSON)
- Explicit error logs with response details on HTTP/connection errors

### In `send_finalized_prices`
- Entry log with item count
- Per-item input dump (source/target, trade_type, price, name)
- Result of `_build_rates_from_items`: `rates` and `skipped`
- Explicit log when `rates` is empty (no API call)
- Summary of `sent` / `failed` with payload

### In `_build_rates_from_items`
- For each GBP item: `is_account` result and the exact `price_type.name` used
- When GBP is skipped: reason (cash vs no key)
- When a rate is extracted: key, value, price_type name

### Log Prefix
All new logs use `[ExternalAPI]` prefix for easy filtering in log aggregation.

### Ensuring Logs Are Visible
Django's default logging may only show WARNING and above. To see INFO logs from `finalize.services`:

1. **Temporarily** add to `SarafiPardis/settings.py`:
```python
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {"class": "logging.StreamHandler"},
    },
    "loggers": {
        "finalize.services": {"level": "INFO", "handlers": ["console"]},
    },
}
```

2. Or run with: `python manage.py runserver` and ensure no custom LOGGING overrides the root logger level.

3. In production, ensure your log collector (e.g. gunicorn logs, systemd journal) captures INFO level for the `finalize.services` logger.
