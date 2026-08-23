"""Pending Analysis Service — trend, cycle, volatility, and process health from archived pending records.

Reads from the dated_outside/ archive (JSONL.gz files) and computes:
  - Demand trends by product class
  - Seasonal cycles (peak/valley months)
  - Volatility (CV) for adaptive inventory window
  - Cash flow seasonality by category
  - Pending→applied conversion rates (process health)
  - Processing latency trends (infrastructure health)
  - Pattern change detection (coaching signals for Alice)

All functions return plain dicts — no Django model dependencies.
Analysis results feed ItemUsage metrics and Alice's coaching signals.
"""
from __future__ import annotations

import gzip
import json
import logging
import math
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from django.conf import settings

logger = logging.getLogger(__name__)

ARCHIVE_ROOT = Path(getattr(settings, 'BASE_DIR', '.')) / '.local' / 'dated_outside'


# ── Archive loader ────────────────────────────────────────────────────

def load_archive_collection(
    archive_type: str,
    category: str,
    start_month: str,
    end_month: str,
) -> List[Dict[str, Any]]:
    """Load archived JSONL.gz files into memory for analysis.

    Args:
        archive_type: 'inventory', 'cash_flow', or 'queue'
        category: product class (inventory), cash category (cash_flow), or model_name (queue)
        start_month: 'YYYY-MM' inclusive
        end_month: 'YYYY-MM' inclusive

    Returns:
        List of archive record dicts.
    """
    base_dir = ARCHIVE_ROOT / archive_type / category

    if not base_dir.exists():
        logger.debug("Archive directory not found: %s", base_dir)
        return []

    records = []
    # Generate month range
    months = _month_range(start_month, end_month)

    for month in months:
        filepath = base_dir / f"{month}.jsonl.gz"
        if not filepath.exists():
            continue
        try:
            with gzip.open(filepath, 'rt', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        records.append(json.loads(line))
        except Exception as e:
            logger.warning("Failed to read archive file %s: %s", filepath, e)

    logger.debug("Loaded %d records from %s/%s [%s to %s]",
                 len(records), archive_type, category, start_month, end_month)
    return records


def _month_range(start: str, end: str) -> List[str]:
    """Generate list of YYYY-MM strings from start to end inclusive."""
    months = []
    try:
        sy, sm = int(start[:4]), int(start[5:7])
        ey, em = int(end[:4]), int(end[5:7])
    except (ValueError, IndexError):
        return [start]

    y, m = sy, sm
    while (y, m) <= (ey, em):
        months.append(f"{y:04d}-{m:02d}")
        m += 1
        if m > 12:
            m = 1
            y += 1
    return months


def _safe_float(val, default=0.0) -> float:
    if val is None:
        return default
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


# ── Analysis functions ────────────────────────────────────────────────

def compute_demand_trend(
    product_class: str,
    months: int = 12,
) -> Dict[str, Any]:
    """Compute demand trend slope and direction from inventory archives.

    Aggregates qty by month and computes linear regression slope.

    Returns:
        {product_class, months_analyzed, monthly_totals, slope, direction,
         avg_monthly, total_records}
    """
    end_month = _current_month()
    start_month = _months_ago(end_month, months)
    records = load_archive_collection('inventory', product_class, start_month, end_month)

    if not records:
        return {
            'product_class': product_class,
            'months_analyzed': 0,
            'monthly_totals': {},
            'slope': 0,
            'direction': 'no_data',
            'avg_monthly': 0,
            'total_records': 0,
        }

    # Aggregate qty by month (only applied records = real demand)
    monthly = defaultdict(float)
    for rec in records:
        if rec.get('state') != 'applied':
            continue
        dt = rec.get('dt_created', 0)
        month_key = _epoch_to_month(dt)
        monthly[month_key] += abs(_safe_float(rec.get('qty')))

    # Build ordered series
    all_months = _month_range(start_month, end_month)
    series = [monthly.get(m, 0) for m in all_months]

    slope = _linear_slope(series)
    avg = sum(series) / len(series) if series else 0

    if slope > avg * 0.05:
        direction = 'growing'
    elif slope < -avg * 0.05:
        direction = 'declining'
    else:
        direction = 'flat'

    return {
        'product_class': product_class,
        'months_analyzed': len(all_months),
        'monthly_totals': dict(zip(all_months, series)),
        'slope': round(slope, 4),
        'direction': direction,
        'avg_monthly': round(avg, 2),
        'total_records': len(records),
    }


def detect_seasonal_cycle(
    product_class: str,
    min_months: int = 12,
) -> Dict[str, Any]:
    """Detect seasonal patterns — peak and valley months.

    Needs at least min_months of data. Computes average demand by calendar
    month (Jan-Dec) and identifies peaks (>120% of mean) and valleys (<80%).

    Returns:
        {product_class, data_months, month_averages, peak_months, valley_months,
         seasonality_index, has_pattern}
    """
    end_month = _current_month()
    start_month = _months_ago(end_month, max(min_months, 24))  # try for 24 months
    records = load_archive_collection('inventory', product_class, start_month, end_month)

    # Aggregate by calendar month (1-12) across years
    cal_month_totals = defaultdict(list)
    monthly = defaultdict(float)
    for rec in records:
        if rec.get('state') != 'applied':
            continue
        dt = rec.get('dt_created', 0)
        month_key = _epoch_to_month(dt)
        monthly[month_key] += abs(_safe_float(rec.get('qty')))

    for month_key, total in monthly.items():
        try:
            cal_month = int(month_key[5:7])
            cal_month_totals[cal_month].append(total)
        except (ValueError, IndexError):
            continue

    if len(cal_month_totals) < 6:
        return {
            'product_class': product_class,
            'data_months': len(monthly),
            'month_averages': {},
            'peak_months': [],
            'valley_months': [],
            'seasonality_index': 0,
            'has_pattern': False,
        }

    # Average per calendar month
    month_avgs = {}
    for cal_month in range(1, 13):
        vals = cal_month_totals.get(cal_month, [])
        month_avgs[cal_month] = sum(vals) / len(vals) if vals else 0

    overall_avg = sum(month_avgs.values()) / len([v for v in month_avgs.values() if v > 0]) if any(month_avgs.values()) else 1

    # Peaks > 120% of mean, valleys < 80%
    peak_months = [m for m, v in month_avgs.items() if v > overall_avg * 1.2]
    valley_months = [m for m, v in month_avgs.items() if 0 < v < overall_avg * 0.8]

    # Seasonality index: max/min ratio (higher = more seasonal)
    non_zero = [v for v in month_avgs.values() if v > 0]
    if non_zero and min(non_zero) > 0:
        seasonality_index = round(max(non_zero) / min(non_zero), 2)
    else:
        seasonality_index = 0

    month_names = {1: 'Jan', 2: 'Feb', 3: 'Mar', 4: 'Apr', 5: 'May', 6: 'Jun',
                   7: 'Jul', 8: 'Aug', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dec'}

    return {
        'product_class': product_class,
        'data_months': len(monthly),
        'month_averages': {month_names.get(k, k): round(v, 2) for k, v in sorted(month_avgs.items())},
        'peak_months': [month_names.get(m, m) for m in sorted(peak_months)],
        'valley_months': [month_names.get(m, m) for m in sorted(valley_months)],
        'seasonality_index': seasonality_index,
        'has_pattern': seasonality_index > 1.5,
    }


def compute_volatility(
    product_class: str,
    months: int = 12,
) -> Dict[str, Any]:
    """Compute coefficient of variation for a product class from archive data.

    Feeds the adaptive window calculation in inventory_bounds.py.

    Returns:
        {product_class, cv, std_dev, mean, band, recommended_window, monthly_totals}
    """
    end_month = _current_month()
    start_month = _months_ago(end_month, months)
    records = load_archive_collection('inventory', product_class, start_month, end_month)

    monthly = defaultdict(float)
    for rec in records:
        if rec.get('state') != 'applied':
            continue
        dt = rec.get('dt_created', 0)
        month_key = _epoch_to_month(dt)
        monthly[month_key] += abs(_safe_float(rec.get('qty')))

    all_months = _month_range(start_month, end_month)
    series = [monthly.get(m, 0) for m in all_months]

    if len(series) < 3:
        return {
            'product_class': product_class,
            'cv': None, 'std_dev': 0, 'mean': 0,
            'band': 'insufficient_data', 'recommended_window': 6,
            'monthly_totals': dict(zip(all_months, series)),
        }

    mean = sum(series) / len(series)
    if mean <= 0:
        return {
            'product_class': product_class,
            'cv': 0, 'std_dev': 0, 'mean': 0,
            'band': 'no_demand', 'recommended_window': 6,
            'monthly_totals': dict(zip(all_months, series)),
        }

    variance = sum((x - mean) ** 2 for x in series) / (len(series) - 1)
    std_dev = math.sqrt(variance)
    cv = std_dev / mean

    # Map to adaptive window band
    if cv < 0.25:
        band, window = 'very_stable', 12
    elif cv < 0.50:
        band, window = 'stable', 9
    elif cv < 0.75:
        band, window = 'moderate', 6
    elif cv < 1.00:
        band, window = 'volatile', 4
    else:
        band, window = 'very_volatile', 3

    return {
        'product_class': product_class,
        'cv': round(cv, 4),
        'std_dev': round(std_dev, 2),
        'mean': round(mean, 2),
        'band': band,
        'recommended_window': window,
        'monthly_totals': dict(zip(all_months, series)),
    }


def compute_cash_flow_seasonality(
    category: str,
    months: int = 24,
) -> Dict[str, Any]:
    """Compute monthly cash flow pattern from payment archive.

    Reveals revenue concentration (e.g., 60% in Q4) and cash crunches.

    Returns:
        {category, data_months, month_averages, peak_months, valley_months,
         concentration_pct, quarter_distribution}
    """
    end_month = _current_month()
    start_month = _months_ago(end_month, months)
    records = load_archive_collection('cash_flow', category, start_month, end_month)

    cal_month_totals = defaultdict(list)
    monthly = defaultdict(float)
    for rec in records:
        if rec.get('state') != 'applied':
            continue
        dt = rec.get('dt_created') or rec.get('dt_applied', 0)
        month_key = _epoch_to_month(dt)
        monthly[month_key] += abs(_safe_float(rec.get('amount')))

    for month_key, total in monthly.items():
        try:
            cal_month = int(month_key[5:7])
            cal_month_totals[cal_month].append(total)
        except (ValueError, IndexError):
            continue

    month_avgs = {}
    for cal_month in range(1, 13):
        vals = cal_month_totals.get(cal_month, [])
        month_avgs[cal_month] = sum(vals) / len(vals) if vals else 0

    total_avg = sum(month_avgs.values())
    overall_avg = total_avg / 12 if total_avg > 0 else 1

    peak_months = [m for m, v in month_avgs.items() if v > overall_avg * 1.2]
    valley_months = [m for m, v in month_avgs.items() if 0 < v < overall_avg * 0.8]

    # Quarter distribution
    quarters = {'Q1': 0, 'Q2': 0, 'Q3': 0, 'Q4': 0}
    for m, v in month_avgs.items():
        if m <= 3:
            quarters['Q1'] += v
        elif m <= 6:
            quarters['Q2'] += v
        elif m <= 9:
            quarters['Q3'] += v
        else:
            quarters['Q4'] += v

    if total_avg > 0:
        quarter_pcts = {q: round(v / total_avg * 100, 1) for q, v in quarters.items()}
        max_quarter_pct = max(quarter_pcts.values())
    else:
        quarter_pcts = {q: 0 for q in quarters}
        max_quarter_pct = 0

    month_names = {1: 'Jan', 2: 'Feb', 3: 'Mar', 4: 'Apr', 5: 'May', 6: 'Jun',
                   7: 'Jul', 8: 'Aug', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dec'}

    return {
        'category': category,
        'data_months': len(monthly),
        'month_averages': {month_names.get(k, k): round(v, 2) for k, v in sorted(month_avgs.items())},
        'peak_months': [month_names.get(m, m) for m in sorted(peak_months)],
        'valley_months': [month_names.get(m, m) for m in sorted(valley_months)],
        'concentration_pct': max_quarter_pct,
        'quarter_distribution': quarter_pcts,
    }


def compute_conversion_rates(
    archive_type: str,
    category: str,
    months: int = 6,
) -> Dict[str, Any]:
    """Compute pending→applied conversion rate — process health signal.

    Low conversion rate means bottleneck or validation failures.

    Returns:
        {type, category, total, applied, canceled, conversion_rate,
         monthly_rates, avg_processing_ms}
    """
    end_month = _current_month()
    start_month = _months_ago(end_month, months)
    records = load_archive_collection(archive_type, category, start_month, end_month)

    total = len(records)
    applied = sum(1 for r in records if r.get('state') == 'applied')
    canceled = sum(1 for r in records if r.get('state') == 'canceled')

    # Monthly breakdown
    monthly_applied = defaultdict(int)
    monthly_total = defaultdict(int)
    processing_times = []

    for rec in records:
        dt = rec.get('dt_created', 0)
        month_key = _epoch_to_month(dt)
        monthly_total[month_key] += 1
        if rec.get('state') == 'applied':
            monthly_applied[month_key] += 1
        pt = _safe_float(rec.get('processing_ms'))
        if pt > 0:
            processing_times.append(pt)

    all_months = _month_range(start_month, end_month)
    monthly_rates = {}
    for m in all_months:
        t = monthly_total.get(m, 0)
        a = monthly_applied.get(m, 0)
        monthly_rates[m] = round(a / t, 4) if t > 0 else None

    avg_processing_ms = round(sum(processing_times) / len(processing_times), 1) if processing_times else None

    return {
        'type': archive_type,
        'category': category,
        'total': total,
        'applied': applied,
        'canceled': canceled,
        'conversion_rate': round(applied / total, 4) if total > 0 else None,
        'monthly_rates': monthly_rates,
        'avg_processing_ms': avg_processing_ms,
    }


def compute_processing_latency(
    archive_type: str,
    category: str,
    months: int = 6,
) -> Dict[str, Any]:
    """Compute processing latency trends — infrastructure health signal.

    Growing latency means system under stress or workers falling behind.

    Returns:
        {type, category, avg_ms, median_ms, p95_ms, trend_direction,
         monthly_avg_ms}
    """
    end_month = _current_month()
    start_month = _months_ago(end_month, months)
    records = load_archive_collection(archive_type, category, start_month, end_month)

    monthly_latencies = defaultdict(list)
    all_latencies = []

    for rec in records:
        pt = _safe_float(rec.get('processing_ms'))
        if pt > 0:
            dt = rec.get('dt_created', 0)
            month_key = _epoch_to_month(dt)
            monthly_latencies[month_key].append(pt)
            all_latencies.append(pt)

    if not all_latencies:
        return {
            'type': archive_type, 'category': category,
            'avg_ms': None, 'median_ms': None, 'p95_ms': None,
            'trend_direction': 'no_data', 'monthly_avg_ms': {},
        }

    all_latencies.sort()
    avg_ms = sum(all_latencies) / len(all_latencies)
    median_ms = all_latencies[len(all_latencies) // 2]
    p95_idx = int(len(all_latencies) * 0.95)
    p95_ms = all_latencies[min(p95_idx, len(all_latencies) - 1)]

    # Monthly averages for trend
    all_months = _month_range(start_month, end_month)
    monthly_avg = {}
    series = []
    for m in all_months:
        lats = monthly_latencies.get(m, [])
        if lats:
            avg = sum(lats) / len(lats)
            monthly_avg[m] = round(avg, 1)
            series.append(avg)
        else:
            monthly_avg[m] = None

    slope = _linear_slope(series) if len(series) >= 3 else 0
    if slope > avg_ms * 0.1:
        trend = 'increasing'
    elif slope < -avg_ms * 0.1:
        trend = 'decreasing'
    else:
        trend = 'stable'

    return {
        'type': archive_type,
        'category': category,
        'avg_ms': round(avg_ms, 1),
        'median_ms': round(median_ms, 1),
        'p95_ms': round(p95_ms, 1),
        'trend_direction': trend,
        'monthly_avg_ms': monthly_avg,
    }


def flag_pattern_changes(
    product_class: str,
    lookback_months: int = 12,
    recent_months: int = 3,
) -> Dict[str, Any]:
    """Detect when an item's demand pattern shifts band.

    Compares recent volatility to historical volatility. A band shift
    (e.g., stable→volatile) is a coaching signal — Alice should flag
    the product class for manual review.

    Returns:
        {product_class, historical_band, recent_band, band_shifted,
         historical_cv, recent_cv, coaching_signal}
    """
    historical = compute_volatility(product_class, lookback_months)
    recent = compute_volatility(product_class, recent_months)

    historical_band = historical.get('band', 'insufficient_data')
    recent_band = recent.get('band', 'insufficient_data')
    band_shifted = (
        historical_band != recent_band
        and historical_band != 'insufficient_data'
        and recent_band != 'insufficient_data'
    )

    return {
        'product_class': product_class,
        'historical_band': historical_band,
        'recent_band': recent_band,
        'band_shifted': band_shifted,
        'historical_cv': historical.get('cv'),
        'recent_cv': recent.get('cv'),
        'coaching_signal': band_shifted,
    }


# ── Helpers ───────────────────────────────────────────────────────────

def _current_month() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime('%Y-%m')


def _months_ago(end_month: str, n: int) -> str:
    try:
        y, m = int(end_month[:4]), int(end_month[5:7])
    except (ValueError, IndexError):
        return end_month
    for _ in range(n):
        m -= 1
        if m < 1:
            m = 12
            y -= 1
    return f"{y:04d}-{m:02d}"


def _epoch_to_month(epoch_ms: int) -> str:
    if not epoch_ms or epoch_ms <= 0:
        return _current_month()
    try:
        from datetime import datetime, timezone
        dt = datetime.fromtimestamp(epoch_ms / 1000, tz=timezone.utc)
        return dt.strftime('%Y-%m')
    except (OSError, ValueError):
        return _current_month()


def _linear_slope(series: List[float]) -> float:
    """Simple linear regression slope over an evenly-spaced series."""
    n = len(series)
    if n < 2:
        return 0
    x_mean = (n - 1) / 2.0
    y_mean = sum(series) / n
    numerator = sum((i - x_mean) * (y - y_mean) for i, y in enumerate(series))
    denominator = sum((i - x_mean) ** 2 for i in range(n))
    if denominator == 0:
        return 0
    return numerator / denominator


def list_archived_categories(archive_type: str) -> List[str]:
    """List all product classes or cash flow categories that have archived data."""
    base_dir = ARCHIVE_ROOT / archive_type
    if not base_dir.exists():
        return []
    return sorted([
        d.name for d in base_dir.iterdir()
        if d.is_dir() and not d.name.startswith('.')
    ])
