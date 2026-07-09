trade_stats.py

```python
"""
trade_stats.py

Provides parse_trade_log() to compute basic win/loss statistics from
various trade record formats (list of dicts, list of objects, or a
pandas DataFrame).
"""

try:
    import pandas as pd
    _PANDAS_AVAILABLE = True
except ImportError:
    _PANDAS_AVAILABLE = False


# ---------------------------------------------------------------------------
# Small helper
# ---------------------------------------------------------------------------

def _get_profit_loss(trade):
    """
    Extract the profit_loss value from a trade record.

    Tries, in order:
      1. getattr(trade, 'profit_loss', None)  – covers objects with an attribute
      2. trade.get('profit_loss')              – covers plain dicts
      3. Raises ValueError if neither yields a value.

    Parameters
    ----------
    trade : object or dict
        A single trade record.

    Returns
    -------
    numeric
        The profit_loss value.

    Raises
    ------
    ValueError
        If profit_loss cannot be found on the trade record.
    """
    # Attempt 1: attribute access (works for objects and, harmlessly, for dicts too
    # since dict has no 'profit_loss' attribute unless explicitly set)
    value = getattr(trade, 'profit_loss', None)
    if value is not None:
        return value

    # Attempt 2: dict-style access
    if isinstance(trade, dict):
        value = trade.get('profit_loss')
        if value is not None:
            return value

    # Nothing worked
    raise ValueError(
        f"Cannot extract 'profit_loss' from trade record: {