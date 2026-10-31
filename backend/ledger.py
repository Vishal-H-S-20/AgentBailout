"""Simulated funds only. Integer cents preserve Decimal-derived amounts exactly."""
from decimal import Decimal
from sqlalchemy import select
from backend.models import LedgerEntry, Settlement, Event


def transfer(db, task_id: str, reference: str, source: str, destination: str, amount: str, kind: str) -> None:
    cents = int(Decimal(amount) * 100)
    if cents <= 0:
        raise ValueError('Positive transfer required')
    for account, debit, credit in [(source, cents, 0), (destination, 0, cents)]:
        db.add(LedgerEntry(task_id=task_id, reference=reference, event_type=kind,
                           account=account, debit_cents=debit, credit_cents=credit,
                           description=f'{source} → {destination} (simulation)'))


def fund(db, task_id: str) -> None:
    transfer(db, task_id, 'funding', 'client', 'escrow', '5.00', 'ESCROW_LOCKED')
    db.add(Event(task_id=task_id, type='ESCROW_LOCKED', message='Simulated $5.00 budget funded'))


def settle(db, task) -> bool:
    if db.get(Settlement, task.id):
        return False
    # Unique task primary key fences duplicate settlement; all writes share caller transaction.
    db.add(Settlement(task_id=task.id, outcome=task.status))
    db.flush()
    remaining = Decimal('5.00')
    def pay(account: str, amount: str):
        nonlocal remaining
        value = Decimal(amount)
        if value > remaining:
            raise ValueError('Insufficient simulated escrow')
        transfer(db, task.id, 'settlement', 'escrow', account, amount, 'SETTLEMENT')
        remaining -= value
    for stage in task.stages:
        if stage.status == 'COMPLETED' and not stage.recovery_attempts:
            pay(f'worker_{stage.name.lower()}', '1.00')
    if any(s.recovery_attempts for s in task.stages):
        pay('backup_expense', '0.25')
        pay('recovery_overhead', '0.05')
    if task.status == 'COMPLETED':
        pay('reserve', '0.50')
    pay('client_refund', str(remaining))
    db.add(Event(task_id=task.id, type='LEDGER_SETTLED', message='Balanced simulated settlement committed'))
    return True


def snapshot(db, task_id: str) -> dict:
    rows = list(db.scalars(select(LedgerEntry).where(LedgerEntry.task_id == task_id).order_by(LedgerEntry.id)))
    balances = {}
    for row in rows:
        balances[row.account] = balances.get(row.account, 0) + row.credit_cents - row.debit_cents
    settlement = db.get(Settlement, task_id)
    return {'simulation': True, 'settled': bool(settlement),
            'outcome': settlement.outcome if settlement else None,
            'balances': {k: f'{Decimal(v)/100:.2f}' for k,v in balances.items()},
            'balanced': sum(r.debit_cents-r.credit_cents for r in rows) == 0,
            'entries': [{'id':r.id,'timestamp':r.timestamp,'reference':r.reference,
                         'event_type':r.event_type,'account':r.account,
                         'debit':f'{Decimal(r.debit_cents)/100:.2f}',
                         'credit':f'{Decimal(r.credit_cents)/100:.2f}',
                         'description':r.description} for r in rows]}
