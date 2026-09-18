from decimal import Decimal, InvalidOperation


def _numeric_or_none(value):
    # Bybit reports an unset numeric field (e.g. no take profit) as "0" from one
    # source and "" from another; both mean the same absence of a value.
    try:
        return Decimal(str(value)) if value not in (None, "") else Decimal(0)
    except InvalidOperation:
        return None


def semantic_position_change(previous, current):
    if previous is None:
        return True
    # Price/PnL drift alone is market movement, not a trader action.
    for key in ("side", "size", "entryPrice", "leverage", "takeProfit", "stopLoss", "trailingStop"):
        left, right = previous.get(key), current.get(key)
        if left == right:
            continue
        left_num, right_num = _numeric_or_none(left), _numeric_or_none(right)
        if left_num is not None and right_num is not None and left_num == right_num:
            continue
        return True
    return False
