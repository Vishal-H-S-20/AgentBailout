# AgentBailout 4.1 demo

1. Start both services using [Windows CMD setup](PROVIDER_SETUP.md).
2. Settings & History → AI Providers: confirm key configured, refresh/discover models and test a selected model. No frontend credential entry is needed or allowed.
3. Build Pipeline → Custom AI pipeline. Configure the three-provider [library example](REAL_LLM_PIPELINES.md), or any task and 1–10 custom stages. Set an explicitly authorized backup for stage 2.
4. Save → Run & Recover. Enter the original library task in the large multiline box, choose No failure, Start Task. Inspect every input, actual output, model, usage and submitted instructions; read the complete final answer.
5. Reset Demo to prepare a fresh task with the selected workflow, choose controlled crash and stage 2, and use Compare Results for equivalent protection OFF/ON runs. Inspect the actual failure, selected backup, preserved input and resumed final stage.
6. No keys available: Home → Run Quick Demo remains a clearly labeled offline simulation. It is not evidence of real cloud execution.

Verification scripts: `scripts/verify_custom_builder.py`, `scripts/verify_navigation.py`, `scripts/verify_judge_views.py` require backend 8003. `scripts/smoke_real_providers.py` runs small actual cloud calls only when keys plus explicit model IDs exist; otherwise it prints SKIPPED.
