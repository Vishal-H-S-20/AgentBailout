# Guided pipeline and execution evidence repair

The builder now permits compatible connections, Run & Recover shows independent primary and replacement evidence, and Compare Results explains the observed difference. Backend stays on 8003; dashboard stays on 8501.

## Root causes

The builder exposed unrestricted roles and relied on backend rejection. Execution reports exposed aggregate stage results without independently retaining each attempt's input, output and error. Generic rendering obscured useful report/code content. Duplicate saved workflow names made different pipelines indistinguishable. Streamlit also retained an older imported presentation component during hot reload; restarting the frontend loaded the corrected cards.

## Files and components

- `backend/contracts.py`, `main.py`: human-readable contract catalog and compatible next operations.
- `backend/workflows.py`: actionable validation and richer execution reports, including explicit unavailable historical evidence.
- `backend/models.py`, `migrations.py`: additive AttemptEvidence table and automatic SQLite backup before migration.
- `backend/execution_engine.py`, `supervisor.py`: independent attempt evidence, recorded failure duration, candidate-specific selection explanation. Recovery execution remains intact.
- `dashboard/presentation.py` (new): readable content/code, stage schematic, failure/recovery explanation, trace, comparison facts/diff and secondary timeline.
- `dashboard/pages.py`, `styles.py`: guided builder, template shortcuts, unique saved pipeline labels, larger status cards and collapsed technical details.
- `tests/test_execution_evidence.py` (new), `scripts/verify_judge_views.py` (new): backend evidence and live UI regression checks.

## Verification

- Full suite: **76 passed in 48.46 seconds**, one upstream Starlette deprecation warning.
- Six new backend tests cover contract guidance, independent crash/invalid-output evidence, comparison stage states and historical trace disclosure.
- `scripts/verify_navigation.py` and `scripts/verify_judge_views.py` passed against the live backend. The latter checks incompatible action disabling, template switching, saved coding pipeline identity, actual recovery, Python formatting, separate validation and side-by-side comparison.
- Compile check, dependency check and whitespace/diff check passed.
- Migration backup: `phase3-demo.pre-trace-20261101010348890071.db`. All 96 pre-existing task rows retained identical IDs, prompts, statuses and results.
- Browser checked after restarting Streamlit: failed Formatter says “Primary result: No response returned”; separate amber replacement feeds the completed next stage.

## Four requested issue areas

No four new screenshot files accompanied this repair prompt. The following maps its described issues to verified changes, rather than claiming inspection of missing images.

1. **Build Pipeline:** actual input/output badges, compatible role choices, three shortcuts, terminal-chain guidance, disabled invalid saves and friendly server validation. [Browser capture](screenshots/judge-builder.png).
2. **Run & Recover:** task and outcome first; red failed primary, separate amber replacement, green downstream; real stage inputs/outputs and expandable per-attempt trace. [Browser capture](screenshots/judge-trace.png).
3. **Compare Results:** baseline/protected status, measured time, simulated allocations/refund, API cost availability, failure evidence, replacement reason, readable outputs and observed diff. [Comparison](screenshots/judge-comparison.png), [routing](screenshots/judge-comparison-routing.png).
4. **Output:** readable findings/reports and Python syntax blocks; validation displayed separately; timeline and raw JSON are expandable. Offline code is labeled illustrative and is not claimed to have been executed.

## Exact demo steps

1. Start backend and frontend using the README Windows commands. Restart both after upgrading this version to load the new model and presentation module.
2. Open http://127.0.0.1:8501. Home → Run Quick Demo → Start Task.
3. Observe Recovered, the failed Formatter and separate Document Recovery branch. Read Final output, What failed?, What did AgentBailout do?, and expand Agent input/output trace.
4. Compare Results → Compare With vs Without AgentBailout. Observe baseline FAILED and protected COMPLETED; compare the skipped versus resumed final stage, failure details, outputs and What changed?.
5. Build Pipeline → Plan → Generate Code → Validate → Save Pipeline. Enter a coding request in Run & Recover, select Agent crashes, keep protection on and Start Task. Inspect Generated code and Validation result separately.
6. In Build Pipeline, try increasing a completed three-stage template to four stages. Guidance explains the terminal contract and Save Pipeline is disabled. Switching templates reloads the compatible sequence.

## Limits

Historical attempts do not acquire invented input/output evidence. This is compatible agent replacement with preserved upstream input, not arbitrary configuration/code repair. Offline code validation is a deterministic review, not actual code execution or proof of correctness. External provider adapters are mock-tested; no live paid provider execution was verified. Simulated ledger allocations/refunds are distinct from actual API spend, and expected policy estimates are distinct from observed outcomes. Run one backend process per SQLite database.

Browser code view: [formatted code and separate validation](screenshots/judge-code-output.png).
