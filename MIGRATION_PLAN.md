# Database Schema Migration Plan

## Executive Summary

This plan outlines a safe, reversible migration to expand the `grail_files` table schema by extracting 38 new fields from the existing `json_content` JSONB column. The migration preserves all existing data and supports diverse JSON formats including STOCK, FUTURES, and OPTIONS trade plans.

## Current State

**Database:** PostgreSQL
**Table:** `grail_files`
**Estimated Records:** Unknown (check with `SELECT COUNT(*) FROM grail_files;`)
**Current Schema:** 10 columns (id, ticker, asset_type, file_path, content_hash, file_created_at, file_modified_at, json_content, ingested_at, updated_at)

## Analysis of Existing Data

### Sample Files Analyzed

Four representative JSON files were analyzed to understand data variations:

1. **SIDU (STOCK)** - Standard stock trade with all fields populated
2. **MES (FUTURES)** - Futures contract with resolved ticker ("MESH6")
3. **MNQ (NO TRADE)** - Error case with missing data (all prices = 0, trade = false)
4. **SPY (OPTIONS)** - Options trade with 0DTE contract details

### Key Variations Discovered

| Variation Type | Examples | Impact |
|----------------|----------|--------|
| **Asset Types** | STOCK, FUTURES, OPTIONS | Different fields available per type |
| **Nullable Fields** | in_trial, runs_remaining, resolved_ticker | Must handle NULL values |
| **Confidence Format** | "85% confidence - reasoning text" | Need regex extraction |
| **Currency Strings** | "$1,970.00", "$90.00 (0.9% of account)", "Margin requirement..." | Store as TEXT |
| **Zero Values** | entry_price = 0 when data unavailable | Must distinguish 0 from NULL |
| **Action Variations** | "BUY STOCK", "BUY CALLS", "NO TRADE" | 50-char VARCHAR sufficient |
| **Options-Specific** | recommended_contract object | Only present for OPTIONS |

### Data Quality Findings

✅ **Consistent across all files:**
- `status` field (always "success" in samples)
- `asset_type` field
- `trade_style` field
- `trade_plan.trade` boolean
- `trade_plan.verdict.action`

⚠️ **Varies or can be NULL:**
- `in_trial` (true, null)
- `runs_remaining` (175, null)
- `resolved_ticker` (null, "MESH6")
- `entry_price` (can be 0 when unavailable)
- `recommended_contract` (only for OPTIONS)

## Migration Strategy

### Chosen Approach: Backup Table + In-Place Migration

**Why this approach:**
- ✅ Fastest rollback (just rename tables)
- ✅ Data exists in two places during migration
- ✅ Easy to validate (compare old vs new)
- ✅ No file system dependencies
- ✅ Follows existing migration pattern in codebase

**Alternative approaches considered:**
- ❌ **pg_dump only**: Slower to restore, file system dependency
- ❌ **New table + rename**: More complex, requires more disk space

### Migration Phases

```
Phase 1: BACKUP CREATION
├── Create backup table (grail_files_backup_YYYYMMDD)
├── Copy all data
└── Verify row counts match

Phase 2: SCHEMA MODIFICATION
├── Add 38 new columns (all nullable)
└── Verify column additions

Phase 3: DATA BACKFILL
├── Create helper function (extract_confidence_pct)
├── UPDATE all rows with extracted data
├── Handle NULL/zero/invalid values safely
└── Verify extraction accuracy

Phase 4: INDEX CREATION
├── Create 8 new indexes on frequently-queried columns
└── Verify index creation

Phase 5: VALIDATION
├── Compare row counts
├── Check extraction statistics
├── Sample data inspection
└── Document results
```

## New Fields Definition

### Core Fields (17 fields)

| Column | Type | Source Path | Notes |
|--------|------|-------------|-------|
| status | VARCHAR(20) | status | "success", "error" |
| error_message | TEXT | error | NULL when success |
| trade_style | VARCHAR(20) | trade_style | "DAY", "SWING" |
| account_size | NUMERIC(12,2) | account_size | 10000, 2000 |
| risk_percent | NUMERIC(4,2) | risk_percent | 1.00, 0.5 |
| should_trade | BOOLEAN | trade_plan.trade | true/false decision |
| trade_action | VARCHAR(50) | trade_plan.verdict.action | "BUY STOCK", "BUY CALLS", "NO TRADE" |
| trade_confidence_text | TEXT | trade_plan.verdict.confidence | Full string with reasoning |
| trade_confidence_pct | NUMERIC(5,2) | Extracted from above | 85, 60, 0 (numeric only) |
| no_trade_reason | TEXT | trade_plan.no_trade_reason | NULL when trade=true |
| market_status | VARCHAR(20) | market_session.status | "open", "closed" |
| is_tradeable_now | BOOLEAN | market_session.is_tradeable_now | Current tradeability |
| in_trial | BOOLEAN | in_trial | NULL or true/false |
| runs_remaining | INTEGER | runs_remaining | NULL or count |
| daily_runs_remaining | INTEGER | daily_runs_remaining | NULL or count |
| resolved_ticker | VARCHAR(20) | resolved_ticker | "MESH6" for futures |
| resolved_ticker_method | VARCHAR(50) | resolved_ticker_method | "most_active_volume" |

### Entry Fields (3 fields)

| Column | Type | Source Path | Notes |
|--------|------|-------------|-------|
| entry_direction | VARCHAR(10) | trade_plan.entry.direction | "LONG", "SHORT", "neutral" |
| entry_price | NUMERIC(12,4) | trade_plan.entry.current_price | Can be 0 if unavailable |
| entry_recommendation | VARCHAR(50) | trade_plan.entry.recommendation | "buy_support_bounce", etc. |

### Position Fields (5 fields)

| Column | Type | Source Path | Notes |
|--------|------|-------------|-------|
| position_quantity | INTEGER | trade_plan.position.quantity | Shares or contracts |
| position_unit_type | VARCHAR(20) | trade_plan.position.unit_type | "shares", "contracts" |
| position_size_recommendation | VARCHAR(20) | trade_plan.position.size_recommendation | "full", "quarter", "half" |
| position_total_cost_text | TEXT | trade_plan.position.total_cost | Stored as text (varied formats) |
| position_max_risk_text | TEXT | trade_plan.position.max_risk | Stored as text (includes % info) |

### Agent Confidence Fields (4 fields)

| Column | Type | Source Path | Notes |
|--------|------|-------------|-------|
| technical_confidence | NUMERIC(5,2) | agent_verdicts.technical.confidence | 90, 45, 0 |
| macro_confidence | NUMERIC(5,2) | agent_verdicts.macro.confidence | 65, 50 |
| wild_card_risk | VARCHAR(20) | trade_plan.synthesis.wild_card_risk | "high", "moderate", "low" |
| agent_agreement | VARCHAR(20) | trade_plan.synthesis.agent_agreement | "full", "partial", "conflict" |

### Options-Specific Fields (9 fields - only for OPTIONS asset_type)

| Column | Type | Source Path | Notes |
|--------|------|-------------|-------|
| option_contract_symbol | VARCHAR(50) | trade_plan.recommended_contract.symbol | "O:SPY251223C00688000" |
| option_type | VARCHAR(10) | trade_plan.recommended_contract.type | "CALL", "PUT" |
| option_strike | NUMERIC(12,2) | trade_plan.recommended_contract.strike | 688 |
| option_expiration | DATE | trade_plan.recommended_contract.expiration | "2025-12-23" |
| option_days_to_expiry | INTEGER | trade_plan.recommended_contract.days_to_expiration | 0 (0DTE) |
| option_delta | NUMERIC(6,4) | trade_plan.recommended_contract.delta | 0.461 |
| option_mid_price | NUMERIC(8,4) | trade_plan.recommended_contract.mid_price | 0.205 |
| option_volume | INTEGER | trade_plan.recommended_contract.volume | 366965 |
| option_open_interest | INTEGER | trade_plan.recommended_contract.open_interest | 18851 |

**Total New Fields: 38**

## Extraction Logic

### Confidence Percentage Extraction

The `trade_confidence_text` field contains strings like:
- "85% confidence - means strong technical alignment..."
- "60% confidence - means favorable technical setup..."
- "0% confidence - Data Unavailable"

The migration creates a helper function to extract just the numeric percentage:

```sql
CREATE OR REPLACE FUNCTION extract_confidence_pct(confidence_text TEXT)
RETURNS NUMERIC AS $$
DECLARE
    match TEXT;
BEGIN
    IF confidence_text IS NULL THEN
        RETURN NULL;
    END IF;

    -- Extract number before '%' or before ' '
    match := (regexp_match(confidence_text, '(\d+(?:\.\d+)?)%?'))[1];

    IF match IS NOT NULL THEN
        RETURN match::NUMERIC;
    ELSE
        RETURN NULL;
    END IF;
END;
$$ LANGUAGE plpgsql IMMUTABLE;
```

### Safe Numeric Conversion

All numeric conversions use CASE statements to handle:
- NULL values
- Non-numeric strings
- Zero values (which are valid)
- Regex validation before casting

Example:
```sql
account_size = CASE
    WHEN json_content->>'account_size' ~ '^\d+(\.\d+)?$'
    THEN (json_content->>'account_size')::NUMERIC
    ELSE NULL
END
```

### Options Field Conditional Extraction

Options-specific fields only extract when `asset_type = 'OPTIONS'`:

```sql
option_strike = CASE
    WHEN asset_type = 'OPTIONS' AND json_content->'trade_plan'->'recommended_contract'->>'strike' ~ '^\d+(\.\d+)?$'
    THEN (json_content->'trade_plan'->'recommended_contract'->>'strike')::NUMERIC
    ELSE NULL
END
```

## Index Strategy

### New Indexes to Create

```sql
CREATE INDEX idx_should_trade ON grail_files(should_trade);
CREATE INDEX idx_trade_action ON grail_files(trade_action);
CREATE INDEX idx_trade_style ON grail_files(trade_style);
CREATE INDEX idx_status ON grail_files(status);
CREATE INDEX idx_market_status ON grail_files(market_status);
CREATE INDEX idx_entry_direction ON grail_files(entry_direction);
CREATE INDEX idx_resolved_ticker ON grail_files(resolved_ticker);
CREATE INDEX idx_option_expiration ON grail_files(option_expiration) WHERE asset_type = 'OPTIONS';
```

**Rationale:**
- Indexes on frequently-filtered columns (should_trade, trade_action, trade_style)
- Partial index on option_expiration (only for OPTIONS records)
- No index on TEXT fields (position_total_cost_text, etc.)

## Code Changes Required

After successful migration, the following Python files need updates:

### 1. src/ingestion.py

**Update `GrailFileData` dataclass** to include new fields:

```python
@dataclass
class GrailFileData:
    # Existing fields
    file_path: str
    json_content: str
    content_hash: str
    ticker: Optional[str] = None
    asset_type: Optional[str] = None
    file_created_at: Optional[datetime] = None
    file_modified_at: Optional[datetime] = None

    # NEW: Core fields
    status: Optional[str] = None
    error_message: Optional[str] = None
    trade_style: Optional[str] = None
    account_size: Optional[float] = None
    risk_percent: Optional[float] = None

    # NEW: Trading decision
    should_trade: Optional[bool] = None
    trade_action: Optional[str] = None
    trade_confidence_text: Optional[str] = None
    trade_confidence_pct: Optional[float] = None
    no_trade_reason: Optional[str] = None

    # NEW: Entry fields
    entry_direction: Optional[str] = None
    entry_price: Optional[float] = None
    entry_recommendation: Optional[str] = None

    # NEW: Position sizing
    position_quantity: Optional[int] = None
    position_unit_type: Optional[str] = None
    position_size_recommendation: Optional[str] = None
    position_total_cost_text: Optional[str] = None
    position_max_risk_text: Optional[str] = None

    # NEW: Market context
    market_status: Optional[str] = None
    is_tradeable_now: Optional[bool] = None
    in_trial: Optional[bool] = None

    # NEW: API tracking
    runs_remaining: Optional[int] = None
    daily_runs_remaining: Optional[int] = None

    # NEW: Ticker resolution
    resolved_ticker: Optional[str] = None
    resolved_ticker_method: Optional[str] = None

    # NEW: Agent confidence
    technical_confidence: Optional[float] = None
    macro_confidence: Optional[float] = None
    wild_card_risk: Optional[str] = None
    agent_agreement: Optional[str] = None

    # NEW: Options-specific (all optional)
    option_contract_symbol: Optional[str] = None
    option_type: Optional[str] = None
    option_strike: Optional[float] = None
    option_expiration: Optional[str] = None
    option_days_to_expiry: Optional[int] = None
    option_delta: Optional[float] = None
    option_mid_price: Optional[float] = None
    option_volume: Optional[int] = None
    option_open_interest: Optional[int] = None
```

**Update `ingest_json_file()` function** to extract new fields from parsed JSON.

### 2. src/database.py

**Update `insert_grail_file()` method signature** to accept new parameters:

```python
def insert_grail_file(
    self,
    file_path: str,
    json_content: str,
    content_hash: str,
    ticker: Optional[str] = None,
    asset_type: Optional[str] = None,
    file_created_at: Optional[datetime] = None,
    file_modified_at: Optional[datetime] = None,
    # NEW parameters below
    status: Optional[str] = None,
    error_message: Optional[str] = None,
    trade_style: Optional[str] = None,
    account_size: Optional[float] = None,
    risk_percent: Optional[float] = None,
    should_trade: Optional[bool] = None,
    trade_action: Optional[str] = None,
    trade_confidence_text: Optional[str] = None,
    trade_confidence_pct: Optional[float] = None,
    no_trade_reason: Optional[str] = None,
    entry_direction: Optional[str] = None,
    entry_price: Optional[float] = None,
    entry_recommendation: Optional[str] = None,
    position_quantity: Optional[int] = None,
    position_unit_type: Optional[str] = None,
    position_size_recommendation: Optional[str] = None,
    position_total_cost_text: Optional[str] = None,
    position_max_risk_text: Optional[str] = None,
    market_status: Optional[str] = None,
    is_tradeable_now: Optional[bool] = None,
    in_trial: Optional[bool] = None,
    runs_remaining: Optional[int] = None,
    daily_runs_remaining: Optional[int] = None,
    resolved_ticker: Optional[str] = None,
    resolved_ticker_method: Optional[str] = None,
    technical_confidence: Optional[float] = None,
    macro_confidence: Optional[float] = None,
    wild_card_risk: Optional[str] = None,
    agent_agreement: Optional[str] = None,
    option_contract_symbol: Optional[str] = None,
    option_type: Optional[str] = None,
    option_strike: Optional[float] = None,
    option_expiration: Optional[str] = None,
    option_days_to_expiry: Optional[int] = None,
    option_delta: Optional[float] = None,
    option_mid_price: Optional[float] = None,
    option_volume: Optional[int] = None,
    option_open_interest: Optional[int] = None
) -> str:
```

**Update INSERT and UPDATE SQL statements** to include new columns.

## Execution Plan

### Pre-Migration Checklist

- [ ] Review this plan with stakeholders
- [ ] Verify PostgreSQL version compatibility (requires 9.5+ for JSONB operators)
- [ ] Check available disk space (needs ~2x current table size)
- [ ] Identify maintenance window (estimated 2-5 minutes for 1000 rows)
- [ ] Create full database backup using pg_dump
- [ ] Test migration on development database first
- [ ] Verify database user has necessary permissions

### Execution Steps

1. **Create full database backup (belt and suspenders)**
   ```bash
   pg_dump -h hostname -U username -d grail_files > grail_files_backup_$(date +%Y%m%d_%H%M%S).sql
   ```

2. **Run migration script**
   ```bash
   psql -h hostname -U username -d grail_files -f migrate_expand_schema.sql
   ```

3. **Verify migration success**
   - Check console output for "MIGRATION COMPLETED SUCCESSFULLY"
   - Review validation query results
   - Manually inspect sample records

4. **Update application code**
   - Update `src/ingestion.py` (GrailFileData class)
   - Update `src/database.py` (insert_grail_file method)
   - Test with new JSON files

5. **Deploy updated code**
   - Commit changes to git
   - Deploy to production

6. **Monitor and verify**
   - Ingest a few test files
   - Verify new fields populate correctly
   - Check database performance

### Post-Migration

**Backup table retention:**
- Keep `grail_files_backup_YYYYMMDD` for 30 days
- After verification, optionally drop: `DROP TABLE grail_files_backup_20251227;`

**Documentation updates:**
- Update PRD.md with new schema
- Update README with new query examples
- Document new fields in CLAUDE.md

## Rollback Strategy

### Option 1: Restore from Backup Table (Fastest)

```sql
-- Drop current table
DROP TABLE grail_files;

-- Rename backup to original
ALTER TABLE grail_files_backup_20251227 RENAME TO grail_files;

-- Recreate original indexes
CREATE INDEX idx_ticker ON grail_files(ticker);
CREATE INDEX idx_asset_type ON grail_files(asset_type);
CREATE INDEX idx_ingested_at ON grail_files(ingested_at);
CREATE INDEX idx_content_hash ON grail_files(content_hash);
```

### Option 2: Drop New Columns Only

```sql
-- Drops all new columns, keeps original data intact
ALTER TABLE grail_files
    DROP COLUMN status,
    DROP COLUMN error_message,
    -- ... (drop all 38 new columns)
```

### Option 3: Restore from pg_dump

```bash
# Drop database and restore from dump
dropdb -h hostname -U username grail_files
createdb -h hostname -U username grail_files
psql -h hostname -U username -d grail_files < grail_files_backup_20251227_153045.sql
```

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Data loss during migration | Very Low | Critical | Backup table + pg_dump |
| Extraction errors (wrong data) | Low | Medium | Validation queries, manual spot checks |
| Insufficient disk space | Low | High | Check space before migration |
| Migration takes too long | Very Low | Low | Estimated <5 mins for 1000 rows |
| Invalid JSON causes errors | Very Low | Low | CASE statements with NULL fallback |
| Performance degradation | Very Low | Medium | Indexes on key columns |

## Performance Considerations

**Migration Duration (estimated):**
- 100 rows: <30 seconds
- 1,000 rows: 1-2 minutes
- 10,000 rows: 5-10 minutes
- 100,000 rows: 30-60 minutes

**Query Performance Impact:**
- ✅ SELECT queries on new indexed columns: Faster
- ✅ Filtering by extracted fields: Much faster than JSON queries
- ⚠️ INSERT operations: Slightly slower (more columns to write)
- ⚠️ Table scans: Slightly slower (more data to scan)

**Disk Space:**
- Estimated increase: 20-30% of current table size
- Backup table: 100% of current table size (temporary)

## Success Criteria

- ✅ All rows from original table exist in new table
- ✅ Row count matches between original and backup
- ✅ No errors during migration execution
- ✅ Validation queries show expected extraction rates
- ✅ Sample data inspection confirms accuracy
- ✅ Application code updated and tested
- ✅ New files ingest correctly with new schema
- ✅ Query performance meets expectations

## Questions for Final Approval

Before executing this migration, please confirm:

1. **Field Selection**: Are all 38 proposed fields needed, or should any be excluded?
2. **Index Strategy**: Are the 8 proposed indexes appropriate for your query patterns?
3. **Backup Retention**: Is 30 days appropriate for backup table retention?
4. **Downtime Window**: When is the best time to run this migration?
5. **Development Testing**: Do you have a development database to test on first?
6. **Code Deployment**: Do you want code changes in the same deployment or separate?

## Next Steps

Once approved:
1. ✅ Migration SQL script created (`migrate_expand_schema.sql`)
2. ⏳ Test on development database
3. ⏳ Review test results
4. ⏳ Schedule production migration
5. ⏳ Execute production migration
6. ⏳ Update application code
7. ⏳ Deploy and monitor

---

**Document Version:** 1.0
**Created:** 2025-12-27
**Author:** Eric Bell / Claude
**Status:** READY FOR REVIEW
