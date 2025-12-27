-- ============================================================================
-- Database Schema Migration: Expand grail_files table
-- ============================================================================
-- Purpose: Extract frequently-used fields from json_content to dedicated columns
-- Safety: Creates backup table before any modifications
-- Rollback: Instructions provided at end of file
--
-- Run this script with: psql -h hostname -U username -d grail_files -f migrate_expand_schema.sql
-- ============================================================================

-- ============================================================================
-- PHASE 1: BACKUP CREATION
-- ============================================================================

DO $$
DECLARE
    backup_table_name TEXT := 'grail_files_backup_' || to_char(CURRENT_DATE, 'YYYYMMDD');
    original_count INTEGER;
    backup_count INTEGER;
BEGIN
    RAISE NOTICE 'Starting migration process...';
    RAISE NOTICE 'Backup table will be: %', backup_table_name;

    -- Create backup table
    EXECUTE format('CREATE TABLE IF NOT EXISTS %I AS SELECT * FROM grail_files', backup_table_name);

    -- Verify backup integrity
    SELECT COUNT(*) INTO original_count FROM grail_files;
    EXECUTE format('SELECT COUNT(*) FROM %I', backup_table_name) INTO backup_count;

    IF original_count = backup_count THEN
        RAISE NOTICE 'Backup successful: % rows backed up to %', backup_count, backup_table_name;
    ELSE
        RAISE EXCEPTION 'Backup verification FAILED! Original: %, Backup: %', original_count, backup_count;
    END IF;
END $$;

-- ============================================================================
-- PHASE 2: ADD NEW COLUMNS
-- ============================================================================

ALTER TABLE grail_files
    -- Core fields
    ADD COLUMN IF NOT EXISTS status VARCHAR(20),
    ADD COLUMN IF NOT EXISTS error_message TEXT,
    ADD COLUMN IF NOT EXISTS trade_style VARCHAR(20),
    ADD COLUMN IF NOT EXISTS account_size NUMERIC(12,2),
    ADD COLUMN IF NOT EXISTS risk_percent NUMERIC(4,2),

    -- Trading decision fields
    ADD COLUMN IF NOT EXISTS should_trade BOOLEAN,
    ADD COLUMN IF NOT EXISTS trade_action VARCHAR(50),
    ADD COLUMN IF NOT EXISTS trade_confidence_text TEXT,
    ADD COLUMN IF NOT EXISTS trade_confidence_pct NUMERIC(5,2),
    ADD COLUMN IF NOT EXISTS no_trade_reason TEXT,

    -- Entry fields
    ADD COLUMN IF NOT EXISTS entry_direction VARCHAR(10),
    ADD COLUMN IF NOT EXISTS entry_price NUMERIC(12,4),
    ADD COLUMN IF NOT EXISTS entry_recommendation VARCHAR(50),

    -- Position sizing
    ADD COLUMN IF NOT EXISTS position_quantity INTEGER,
    ADD COLUMN IF NOT EXISTS position_unit_type VARCHAR(20),
    ADD COLUMN IF NOT EXISTS position_size_recommendation VARCHAR(20),
    ADD COLUMN IF NOT EXISTS position_total_cost_text TEXT,
    ADD COLUMN IF NOT EXISTS position_max_risk_text TEXT,

    -- Market context
    ADD COLUMN IF NOT EXISTS market_status VARCHAR(20),
    ADD COLUMN IF NOT EXISTS is_tradeable_now BOOLEAN,
    ADD COLUMN IF NOT EXISTS in_trial BOOLEAN,

    -- API usage tracking
    ADD COLUMN IF NOT EXISTS runs_remaining INTEGER,
    ADD COLUMN IF NOT EXISTS daily_runs_remaining INTEGER,

    -- Ticker resolution
    ADD COLUMN IF NOT EXISTS resolved_ticker VARCHAR(20),
    ADD COLUMN IF NOT EXISTS resolved_ticker_method VARCHAR(50),

    -- Agent confidence scores
    ADD COLUMN IF NOT EXISTS technical_confidence NUMERIC(5,2),
    ADD COLUMN IF NOT EXISTS macro_confidence NUMERIC(5,2),
    ADD COLUMN IF NOT EXISTS wild_card_risk VARCHAR(20),
    ADD COLUMN IF NOT EXISTS agent_agreement VARCHAR(20),

    -- Options-specific fields
    ADD COLUMN IF NOT EXISTS option_contract_symbol VARCHAR(50),
    ADD COLUMN IF NOT EXISTS option_type VARCHAR(10),
    ADD COLUMN IF NOT EXISTS option_strike NUMERIC(12,2),
    ADD COLUMN IF NOT EXISTS option_expiration DATE,
    ADD COLUMN IF NOT EXISTS option_days_to_expiry INTEGER,
    ADD COLUMN IF NOT EXISTS option_delta NUMERIC(6,4),
    ADD COLUMN IF NOT EXISTS option_mid_price NUMERIC(8,4),
    ADD COLUMN IF NOT EXISTS option_volume INTEGER,
    ADD COLUMN IF NOT EXISTS option_open_interest INTEGER;

RAISE NOTICE 'New columns added successfully';

-- ============================================================================
-- PHASE 3: BACKFILL DATA FROM JSON
-- ============================================================================

-- Create helper function to safely extract numeric value from confidence strings
-- Handles formats like: "85% confidence - reason", "0% confidence", etc.
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

RAISE NOTICE 'Starting data backfill from json_content...';

-- Update all records with extracted data
UPDATE grail_files SET
    -- Core fields
    status = json_content->>'status',
    error_message = json_content->>'error',
    trade_style = json_content->>'trade_style',
    account_size = CASE
        WHEN json_content->>'account_size' ~ '^\d+(\.\d+)?$'
        THEN (json_content->>'account_size')::NUMERIC
        ELSE NULL
    END,
    risk_percent = CASE
        WHEN json_content->>'risk_percent' ~ '^\d+(\.\d+)?$'
        THEN (json_content->>'risk_percent')::NUMERIC
        ELSE NULL
    END,

    -- Trading decision fields
    should_trade = CASE
        WHEN json_content->'trade_plan'->>'trade' IS NOT NULL
        THEN (json_content->'trade_plan'->>'trade')::BOOLEAN
        ELSE NULL
    END,
    trade_action = json_content->'trade_plan'->'verdict'->>'action',
    trade_confidence_text = json_content->'trade_plan'->'verdict'->>'confidence',
    trade_confidence_pct = extract_confidence_pct(json_content->'trade_plan'->'verdict'->>'confidence'),
    no_trade_reason = json_content->'trade_plan'->>'no_trade_reason',

    -- Entry fields
    entry_direction = json_content->'trade_plan'->'entry'->>'direction',
    entry_price = CASE
        WHEN json_content->'trade_plan'->'entry'->>'current_price' ~ '^-?\d+(\.\d+)?$'
        THEN (json_content->'trade_plan'->'entry'->>'current_price')::NUMERIC
        ELSE NULL
    END,
    entry_recommendation = json_content->'trade_plan'->'entry'->>'recommendation',

    -- Position sizing
    position_quantity = CASE
        WHEN json_content->'trade_plan'->'position'->>'quantity' ~ '^\d+$'
        THEN (json_content->'trade_plan'->'position'->>'quantity')::INTEGER
        ELSE NULL
    END,
    position_unit_type = json_content->'trade_plan'->'position'->>'unit_type',
    position_size_recommendation = json_content->'trade_plan'->'position'->>'size_recommendation',
    position_total_cost_text = json_content->'trade_plan'->'position'->>'total_cost',
    position_max_risk_text = json_content->'trade_plan'->'position'->>'max_risk',

    -- Market context
    market_status = json_content->'market_session'->>'status',
    is_tradeable_now = CASE
        WHEN json_content->'market_session'->>'is_tradeable_now' IS NOT NULL
        THEN (json_content->'market_session'->>'is_tradeable_now')::BOOLEAN
        ELSE NULL
    END,
    in_trial = CASE
        WHEN json_content->>'in_trial' IS NOT NULL
        THEN (json_content->>'in_trial')::BOOLEAN
        ELSE NULL
    END,

    -- API usage tracking
    runs_remaining = CASE
        WHEN json_content->>'runs_remaining' ~ '^\d+$'
        THEN (json_content->>'runs_remaining')::INTEGER
        ELSE NULL
    END,
    daily_runs_remaining = CASE
        WHEN json_content->>'daily_runs_remaining' ~ '^\d+$'
        THEN (json_content->>'daily_runs_remaining')::INTEGER
        ELSE NULL
    END,

    -- Ticker resolution
    resolved_ticker = json_content->>'resolved_ticker',
    resolved_ticker_method = json_content->>'resolved_ticker_method',

    -- Agent confidence scores
    technical_confidence = CASE
        WHEN json_content->'agent_verdicts'->'technical'->>'confidence' ~ '^\d+(\.\d+)?$'
        THEN (json_content->'agent_verdicts'->'technical'->>'confidence')::NUMERIC
        ELSE NULL
    END,
    macro_confidence = CASE
        WHEN json_content->'agent_verdicts'->'macro'->>'confidence' ~ '^\d+(\.\d+)?$'
        THEN (json_content->'agent_verdicts'->'macro'->>'confidence')::NUMERIC
        ELSE NULL
    END,
    wild_card_risk = json_content->'trade_plan'->'synthesis'->>'wild_card_risk',
    agent_agreement = json_content->'trade_plan'->'synthesis'->>'agent_agreement',

    -- Options-specific fields (only populated for OPTIONS asset_type)
    option_contract_symbol = CASE
        WHEN asset_type = 'OPTIONS'
        THEN json_content->'trade_plan'->'recommended_contract'->>'symbol'
        ELSE NULL
    END,
    option_type = CASE
        WHEN asset_type = 'OPTIONS'
        THEN json_content->'trade_plan'->'recommended_contract'->>'type'
        ELSE NULL
    END,
    option_strike = CASE
        WHEN asset_type = 'OPTIONS' AND json_content->'trade_plan'->'recommended_contract'->>'strike' ~ '^\d+(\.\d+)?$'
        THEN (json_content->'trade_plan'->'recommended_contract'->>'strike')::NUMERIC
        ELSE NULL
    END,
    option_expiration = CASE
        WHEN asset_type = 'OPTIONS' AND json_content->'trade_plan'->'recommended_contract'->>'expiration' IS NOT NULL
        THEN (json_content->'trade_plan'->'recommended_contract'->>'expiration')::DATE
        ELSE NULL
    END,
    option_days_to_expiry = CASE
        WHEN asset_type = 'OPTIONS' AND json_content->'trade_plan'->'recommended_contract'->>'days_to_expiration' ~ '^\d+$'
        THEN (json_content->'trade_plan'->'recommended_contract'->>'days_to_expiration')::INTEGER
        ELSE NULL
    END,
    option_delta = CASE
        WHEN asset_type = 'OPTIONS' AND json_content->'trade_plan'->'recommended_contract'->>'delta' ~ '^-?\d+(\.\d+)?$'
        THEN (json_content->'trade_plan'->'recommended_contract'->>'delta')::NUMERIC
        ELSE NULL
    END,
    option_mid_price = CASE
        WHEN asset_type = 'OPTIONS' AND json_content->'trade_plan'->'recommended_contract'->>'mid_price' ~ '^\d+(\.\d+)?$'
        THEN (json_content->'trade_plan'->'recommended_contract'->>'mid_price')::NUMERIC
        ELSE NULL
    END,
    option_volume = CASE
        WHEN asset_type = 'OPTIONS' AND json_content->'trade_plan'->'recommended_contract'->>'volume' ~ '^\d+$'
        THEN (json_content->'trade_plan'->'recommended_contract'->>'volume')::INTEGER
        ELSE NULL
    END,
    option_open_interest = CASE
        WHEN asset_type = 'OPTIONS' AND json_content->'trade_plan'->'recommended_contract'->>'open_interest' ~ '^\d+$'
        THEN (json_content->'trade_plan'->'recommended_contract'->>'open_interest')::INTEGER
        ELSE NULL
    END;

RAISE NOTICE 'Data backfill completed';

-- ============================================================================
-- PHASE 4: CREATE INDEXES
-- ============================================================================

RAISE NOTICE 'Creating indexes on new columns...';

CREATE INDEX IF NOT EXISTS idx_should_trade ON grail_files(should_trade);
CREATE INDEX IF NOT EXISTS idx_trade_action ON grail_files(trade_action);
CREATE INDEX IF NOT EXISTS idx_trade_style ON grail_files(trade_style);
CREATE INDEX IF NOT EXISTS idx_status ON grail_files(status);
CREATE INDEX IF NOT EXISTS idx_market_status ON grail_files(market_status);
CREATE INDEX IF NOT EXISTS idx_entry_direction ON grail_files(entry_direction);
CREATE INDEX IF NOT EXISTS idx_resolved_ticker ON grail_files(resolved_ticker);
CREATE INDEX IF NOT EXISTS idx_option_expiration ON grail_files(option_expiration) WHERE asset_type = 'OPTIONS';

RAISE NOTICE 'Indexes created successfully';

-- ============================================================================
-- PHASE 5: VALIDATION QUERIES
-- ============================================================================

RAISE NOTICE '============================================================================';
RAISE NOTICE 'VALIDATION RESULTS';
RAISE NOTICE '============================================================================';

-- Check row counts
DO $$
DECLARE
    original_count INTEGER;
    backup_count INTEGER;
    backup_table_name TEXT := 'grail_files_backup_' || to_char(CURRENT_DATE, 'YYYYMMDD');
BEGIN
    SELECT COUNT(*) INTO original_count FROM grail_files;
    EXECUTE format('SELECT COUNT(*) FROM %I', backup_table_name) INTO backup_count;

    RAISE NOTICE 'Row count check:';
    RAISE NOTICE '  Original table: % rows', original_count;
    RAISE NOTICE '  Backup table: % rows', backup_count;

    IF original_count = backup_count THEN
        RAISE NOTICE '  ✓ Row counts match';
    ELSE
        RAISE WARNING '  ✗ Row counts DO NOT match!';
    END IF;
END $$;

-- Check data extraction statistics
SELECT
    COUNT(*) as total_rows,
    COUNT(status) as has_status,
    COUNT(should_trade) as has_should_trade,
    COUNT(trade_action) as has_trade_action,
    COUNT(entry_price) as has_entry_price,
    COUNT(ticker) as has_ticker,
    COUNT(CASE WHEN asset_type = 'OPTIONS' THEN 1 END) as options_count,
    COUNT(option_contract_symbol) as has_option_contract
FROM grail_files;

-- Show sample of extracted data
RAISE NOTICE 'Sample of extracted data (first 5 rows):';
SELECT
    ticker,
    asset_type,
    should_trade,
    trade_action,
    trade_confidence_pct,
    entry_price,
    market_status
FROM grail_files
LIMIT 5;

-- Check for extraction errors (rows with NULL in critical fields)
SELECT
    COUNT(*) as rows_with_null_should_trade
FROM grail_files
WHERE should_trade IS NULL AND json_content->'trade_plan'->>'trade' IS NOT NULL;

RAISE NOTICE '============================================================================';
RAISE NOTICE 'MIGRATION COMPLETED SUCCESSFULLY';
RAISE NOTICE 'Backup table: grail_files_backup_%', to_char(CURRENT_DATE, 'YYYYMMDD');
RAISE NOTICE '============================================================================';

-- ============================================================================
-- ROLLBACK INSTRUCTIONS (DO NOT RUN - FOR REFERENCE ONLY)
-- ============================================================================

/*
-- If you need to rollback this migration:

-- Option 1: Restore from backup table
DROP TABLE grail_files;
ALTER TABLE grail_files_backup_20251227 RENAME TO grail_files;
-- Then recreate indexes manually (see existing index list above)

-- Option 2: Drop new columns only
ALTER TABLE grail_files
    DROP COLUMN status,
    DROP COLUMN error_message,
    DROP COLUMN trade_style,
    DROP COLUMN account_size,
    DROP COLUMN risk_percent,
    DROP COLUMN should_trade,
    DROP COLUMN trade_action,
    DROP COLUMN trade_confidence_text,
    DROP COLUMN trade_confidence_pct,
    DROP COLUMN no_trade_reason,
    DROP COLUMN entry_direction,
    DROP COLUMN entry_price,
    DROP COLUMN entry_recommendation,
    DROP COLUMN position_quantity,
    DROP COLUMN position_unit_type,
    DROP COLUMN position_size_recommendation,
    DROP COLUMN position_total_cost_text,
    DROP COLUMN position_max_risk_text,
    DROP COLUMN market_status,
    DROP COLUMN is_tradeable_now,
    DROP COLUMN in_trial,
    DROP COLUMN runs_remaining,
    DROP COLUMN daily_runs_remaining,
    DROP COLUMN resolved_ticker,
    DROP COLUMN resolved_ticker_method,
    DROP COLUMN technical_confidence,
    DROP COLUMN macro_confidence,
    DROP COLUMN wild_card_risk,
    DROP COLUMN agent_agreement,
    DROP COLUMN option_contract_symbol,
    DROP COLUMN option_type,
    DROP COLUMN option_strike,
    DROP COLUMN option_expiration,
    DROP COLUMN option_days_to_expiry,
    DROP COLUMN option_delta,
    DROP COLUMN option_mid_price,
    DROP COLUMN option_volume,
    DROP COLUMN option_open_interest;

-- Option 3: Restore from pg_dump backup file
-- psql -h hostname -U username -d postgres < grail_files_backup.sql

-- To delete the backup table (after verification):
-- DROP TABLE grail_files_backup_20251227;
*/
