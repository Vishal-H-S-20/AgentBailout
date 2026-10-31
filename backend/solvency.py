from decimal import Decimal


def evaluate(cost: str = '0.25', value: str = '5.00') -> dict:
    backup, value, overhead = Decimal(cost), Decimal(value), Decimal('0.05')
    total = backup + overhead
    benefit = Decimal('0.95') * value - total
    approved = value > 0 and backup >= 0 and total <= value * Decimal('0.40') and benefit > 0
    return dict(approved=approved, task_value=str(value), recoverable_value=str(value),
                backup_cost=str(backup), overhead=str(overhead), total_rescue_cost=str(total),
                cost_ratio=str(total / value) if value > 0 else None,
                expected_net_benefit=str(benefit), reason='Within policy' if approved else 'Recovery exceeds policy')
