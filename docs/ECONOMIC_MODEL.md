# Simulated accounting

All balances are demo allocations, not money, escrow custody or blockchain assets. New API tasks receive a fixed $5.00 simulated budget. Funding debits client and credits escrow. Each transfer has equal debit and credit entries, stored as integer cents; all calculations use Decimal. Account balances here use credit minus debit, so the source client account is negative.

On completion each completed primary stage earns $1.00. A formatter replaced by a backup receives no primary payout. An attempted backup costs $0.25 and recovery overhead $0.05, including when the backup fails. Successful tasks allocate $0.50 to reserve. Everything left is credited to client_refund. Failed tasks pay only completed primary stages and attempted recovery costs; no reserve is allocated. No worker stakes or penalties are implemented.

Examples: normal task refunds $1.50; rescued task refunds $2.20; rejected bailout after research refunds $4.00; failed backup refunds $3.70. Rescue expenses are separate accounts. Zero escrow after settlement means the same funds cannot be allocated again. A unique settlement task key prevents duplicates; journal, terminal result and settlement marker commit in one transaction. Concurrent duplicate insertions fail the unique constraint and roll back.

Task execution status remains COMPLETED or FAILED. The ledger endpoint separately exposes settled and outcome; a successful computation is distinguishable from its accounting status. Historical tasks created before Phase 3 have no funding or settlement and are not retroactively assigned invented balances. Start new tasks for demonstrations.

Recovery policy uses fixed demo values and a simulated 95% backup success estimate, not calibrated forecasts: expected net benefit = 0.95 × $5 − $0.30 = $4.45. The $0.30 recovery spend passes the 40% cap. Available simulated budget covers all configured payouts and recovery costs. Configurable budgets and policies remain future work.
