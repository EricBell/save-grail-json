"""
JSON file ingestion and field extraction.
"""

import json
import hashlib
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any


class IngestionError(Exception):
    """Custom exception for ingestion errors."""
    pass


def _extract_confidence_pct(confidence_text: Optional[str]) -> Optional[float]:
    """
    Extract numeric percentage from confidence text.

    Handles formats like:
    - "85% confidence - reason..."
    - "60% confidence"
    - "0% confidence - Data Unavailable"

    Args:
        confidence_text: Text containing confidence percentage

    Returns:
        Numeric percentage (e.g., 85.0) or None
    """
    if not confidence_text:
        return None

    # Extract number before '%' or before ' '
    match = re.search(r'(\d+(?:\.\d+)?)%?', confidence_text)
    if match:
        try:
            return float(match.group(1))
        except (ValueError, AttributeError):
            return None
    return None


def _safe_float(value: Any) -> Optional[float]:
    """Safely convert value to float, returning None on failure."""
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def _safe_int(value: Any) -> Optional[int]:
    """Safely convert value to int, returning None on failure."""
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def _safe_bool(value: Any) -> Optional[bool]:
    """Safely convert value to bool, returning None on failure."""
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    return None


class GrailFileData:
    """Container for extracted grail file data."""

    def __init__(
        self,
        file_path: str,
        json_content: str,
        content_hash: str,
        ticker: Optional[str] = None,
        asset_type: Optional[str] = None,
        file_created_at: Optional[datetime] = None,
        file_modified_at: Optional[datetime] = None,
        # Core fields
        status: Optional[str] = None,
        error_message: Optional[str] = None,
        trade_style: Optional[str] = None,
        account_size: Optional[float] = None,
        risk_percent: Optional[float] = None,
        # Trading decision
        should_trade: Optional[bool] = None,
        trade_action: Optional[str] = None,
        trade_confidence_text: Optional[str] = None,
        trade_confidence_pct: Optional[float] = None,
        no_trade_reason: Optional[str] = None,
        # Entry fields
        entry_direction: Optional[str] = None,
        entry_price: Optional[float] = None,
        entry_recommendation: Optional[str] = None,
        # Position sizing
        position_quantity: Optional[int] = None,
        position_unit_type: Optional[str] = None,
        position_size_recommendation: Optional[str] = None,
        position_total_cost_text: Optional[str] = None,
        position_max_risk_text: Optional[str] = None,
        # Market context
        market_status: Optional[str] = None,
        is_tradeable_now: Optional[bool] = None,
        in_trial: Optional[bool] = None,
        # API tracking
        runs_remaining: Optional[int] = None,
        daily_runs_remaining: Optional[int] = None,
        # Ticker resolution
        resolved_ticker: Optional[str] = None,
        resolved_ticker_method: Optional[str] = None,
        # Agent confidence
        technical_confidence: Optional[float] = None,
        macro_confidence: Optional[float] = None,
        wild_card_risk: Optional[str] = None,
        agent_agreement: Optional[str] = None,
        # Options-specific (all optional)
        option_contract_symbol: Optional[str] = None,
        option_type: Optional[str] = None,
        option_strike: Optional[float] = None,
        option_expiration: Optional[str] = None,
        option_days_to_expiry: Optional[int] = None,
        option_delta: Optional[float] = None,
        option_mid_price: Optional[float] = None,
        option_volume: Optional[int] = None,
        option_open_interest: Optional[int] = None
    ):
        self.file_path = file_path
        self.json_content = json_content
        self.content_hash = content_hash
        self.ticker = ticker
        self.asset_type = asset_type
        self.file_created_at = file_created_at
        self.file_modified_at = file_modified_at
        # Core fields
        self.status = status
        self.error_message = error_message
        self.trade_style = trade_style
        self.account_size = account_size
        self.risk_percent = risk_percent
        # Trading decision
        self.should_trade = should_trade
        self.trade_action = trade_action
        self.trade_confidence_text = trade_confidence_text
        self.trade_confidence_pct = trade_confidence_pct
        self.no_trade_reason = no_trade_reason
        # Entry fields
        self.entry_direction = entry_direction
        self.entry_price = entry_price
        self.entry_recommendation = entry_recommendation
        # Position sizing
        self.position_quantity = position_quantity
        self.position_unit_type = position_unit_type
        self.position_size_recommendation = position_size_recommendation
        self.position_total_cost_text = position_total_cost_text
        self.position_max_risk_text = position_max_risk_text
        # Market context
        self.market_status = market_status
        self.is_tradeable_now = is_tradeable_now
        self.in_trial = in_trial
        # API tracking
        self.runs_remaining = runs_remaining
        self.daily_runs_remaining = daily_runs_remaining
        # Ticker resolution
        self.resolved_ticker = resolved_ticker
        self.resolved_ticker_method = resolved_ticker_method
        # Agent confidence
        self.technical_confidence = technical_confidence
        self.macro_confidence = macro_confidence
        self.wild_card_risk = wild_card_risk
        self.agent_agreement = agent_agreement
        # Options-specific
        self.option_contract_symbol = option_contract_symbol
        self.option_type = option_type
        self.option_strike = option_strike
        self.option_expiration = option_expiration
        self.option_days_to_expiry = option_days_to_expiry
        self.option_delta = option_delta
        self.option_mid_price = option_mid_price
        self.option_volume = option_volume
        self.option_open_interest = option_open_interest


def ingest_json_file(file_path: str) -> GrailFileData:
    """
    Read and process a JSON file for ingestion.

    Args:
        file_path: Path to the JSON file

    Returns:
        GrailFileData object with extracted information

    Raises:
        IngestionError: If file cannot be read or parsed
    """
    path = Path(file_path)

    # Verify file exists
    if not path.exists():
        raise IngestionError(f"File not found: {file_path}")

    if not path.is_file():
        raise IngestionError(f"Not a file: {file_path}")

    # Read file content
    try:
        with open(path, 'r', encoding='utf-8') as f:
            json_content = f.read()
    except Exception as e:
        raise IngestionError(f"Failed to read file {file_path}: {e}")

    # Parse JSON to extract fields
    try:
        data = json.loads(json_content)
    except json.JSONDecodeError as e:
        raise IngestionError(f"Invalid JSON in {file_path}: {e}")

    # Extract ticker and asset_type (if present)
    ticker = data.get('ticker')
    asset_type = data.get('asset_type')

    # Get file timestamps
    try:
        stat = path.stat()
        # Use birth time if available (creation time), otherwise use ctime
        file_created_at = datetime.fromtimestamp(
            getattr(stat, 'st_birthtime', stat.st_ctime)
        )
        file_modified_at = datetime.fromtimestamp(stat.st_mtime)
    except Exception as e:
        # If we can't get timestamps, continue without them
        file_created_at = None
        file_modified_at = None

    # Compute content hash for duplicate detection
    content_hash = hashlib.sha256(json_content.encode('utf-8')).hexdigest()

    # Extract core fields
    status = data.get('status')
    error_message = data.get('error')
    trade_style = data.get('trade_style')
    account_size = _safe_float(data.get('account_size'))
    risk_percent = _safe_float(data.get('risk_percent'))

    # Extract trading decision fields
    trade_plan = data.get('trade_plan') or {}
    should_trade = _safe_bool(trade_plan.get('trade'))

    verdict = trade_plan.get('verdict') or {}
    trade_action = verdict.get('action')
    trade_confidence_text = verdict.get('confidence')
    trade_confidence_pct = _extract_confidence_pct(trade_confidence_text)
    no_trade_reason = trade_plan.get('no_trade_reason')

    # Extract entry fields
    entry = trade_plan.get('entry') or {}
    entry_direction = entry.get('direction')
    entry_price = _safe_float(entry.get('current_price'))
    entry_recommendation = entry.get('recommendation')

    # Extract position sizing fields
    position = trade_plan.get('position') or {}
    position_quantity = _safe_int(position.get('quantity'))
    position_unit_type = position.get('unit_type')
    position_size_recommendation = position.get('size_recommendation')
    position_total_cost_text = position.get('total_cost')
    position_max_risk_text = position.get('max_risk')

    # Extract market context fields
    market_session = data.get('market_session') or {}
    market_status = market_session.get('status')
    is_tradeable_now = _safe_bool(market_session.get('is_tradeable_now'))
    in_trial = _safe_bool(data.get('in_trial'))

    # Extract API tracking fields
    runs_remaining = _safe_int(data.get('runs_remaining'))
    daily_runs_remaining = _safe_int(data.get('daily_runs_remaining'))

    # Extract ticker resolution fields
    resolved_ticker = data.get('resolved_ticker')
    resolved_ticker_method = data.get('resolved_ticker_method')

    # Extract agent confidence fields
    agent_verdicts = data.get('agent_verdicts') or {}
    technical = agent_verdicts.get('technical') or {}
    macro = agent_verdicts.get('macro') or {}
    technical_confidence = _safe_float(technical.get('confidence'))
    macro_confidence = _safe_float(macro.get('confidence'))

    synthesis = trade_plan.get('synthesis') or {}
    wild_card_risk = synthesis.get('wild_card_risk')
    agent_agreement = synthesis.get('agent_agreement')

    # Extract options-specific fields (only for OPTIONS asset_type)
    option_contract_symbol = None
    option_type = None
    option_strike = None
    option_expiration = None
    option_days_to_expiry = None
    option_delta = None
    option_mid_price = None
    option_volume = None
    option_open_interest = None

    if asset_type == 'OPTIONS':
        recommended_contract = trade_plan.get('recommended_contract') or {}
        option_contract_symbol = recommended_contract.get('symbol')
        option_type = recommended_contract.get('type')
        option_strike = _safe_float(recommended_contract.get('strike'))
        option_expiration = recommended_contract.get('expiration')
        option_days_to_expiry = _safe_int(recommended_contract.get('days_to_expiration'))
        option_delta = _safe_float(recommended_contract.get('delta'))
        option_mid_price = _safe_float(recommended_contract.get('mid_price'))
        option_volume = _safe_int(recommended_contract.get('volume'))
        option_open_interest = _safe_int(recommended_contract.get('open_interest'))

    return GrailFileData(
        file_path=str(path.absolute()),
        json_content=json_content,
        content_hash=content_hash,
        ticker=ticker,
        asset_type=asset_type,
        file_created_at=file_created_at,
        file_modified_at=file_modified_at,
        # Core fields
        status=status,
        error_message=error_message,
        trade_style=trade_style,
        account_size=account_size,
        risk_percent=risk_percent,
        # Trading decision
        should_trade=should_trade,
        trade_action=trade_action,
        trade_confidence_text=trade_confidence_text,
        trade_confidence_pct=trade_confidence_pct,
        no_trade_reason=no_trade_reason,
        # Entry fields
        entry_direction=entry_direction,
        entry_price=entry_price,
        entry_recommendation=entry_recommendation,
        # Position sizing
        position_quantity=position_quantity,
        position_unit_type=position_unit_type,
        position_size_recommendation=position_size_recommendation,
        position_total_cost_text=position_total_cost_text,
        position_max_risk_text=position_max_risk_text,
        # Market context
        market_status=market_status,
        is_tradeable_now=is_tradeable_now,
        in_trial=in_trial,
        # API tracking
        runs_remaining=runs_remaining,
        daily_runs_remaining=daily_runs_remaining,
        # Ticker resolution
        resolved_ticker=resolved_ticker,
        resolved_ticker_method=resolved_ticker_method,
        # Agent confidence
        technical_confidence=technical_confidence,
        macro_confidence=macro_confidence,
        wild_card_risk=wild_card_risk,
        agent_agreement=agent_agreement,
        # Options-specific
        option_contract_symbol=option_contract_symbol,
        option_type=option_type,
        option_strike=option_strike,
        option_expiration=option_expiration,
        option_days_to_expiry=option_days_to_expiry,
        option_delta=option_delta,
        option_mid_price=option_mid_price,
        option_volume=option_volume,
        option_open_interest=option_open_interest
    )


def validate_json_file(file_path: str) -> bool:
    """
    Check if a file is a valid JSON file without full ingestion.

    Args:
        file_path: Path to check

    Returns:
        True if file exists and contains valid JSON
    """
    path = Path(file_path)

    if not path.exists() or not path.is_file():
        return False

    try:
        with open(path, 'r', encoding='utf-8') as f:
            json.load(f)
        return True
    except (json.JSONDecodeError, Exception):
        return False
