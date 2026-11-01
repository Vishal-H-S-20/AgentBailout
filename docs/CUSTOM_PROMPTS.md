# Custom tasks and instructions

# Custom real multi-LLM pipelines

Build Pipeline defaults to Custom AI pipeline. Guided offline templates remain optional and clearly separate. There is one sequential execution engine, extended with the generic custom operation.

1. Set Number of stages (1–10). Exactly that many stage panels are saved. Add by increasing the count; remove/duplicate/reorder with each card's controls. Stable IDs keep instructions attached to the stage.
2. Set name, objective and custom system instructions. The name is descriptive and never switches hardcoded behavior.
3. Choose OpenAI, Gemini, Groq, Claude or Ollama. Refresh models or enter an exact explicit ID. Switching provider clears the incompatible model choice. A listed model is not automatically generation-verified; Test connection checks the selected model.
4. Choose Markdown, plain text, code (with language), or JSON. Optional JSON Schema is validated locally against the actual response. Structured JSON failure can invoke recovery. General text is not treated as a verified code artifact.
5. Select context: original task, previous output, both, all prior outputs plus original, or selected prior stable stage IDs. Stage 1 always receives the original task. Prior responses are passed completely, not reduced to keywords.
6. Configure timeout, output tokens, explicit context-character limit, recovery eligibility, optional same-model retry and an authorized backup provider/model.
7. Save Custom Pipeline. Drafts may be saved before credentials are configured; task creation requires configured primary providers. Open a saved custom pipeline reloads the correct agent versions and stage settings.
8. Run & Recover → select pipeline → enter a multiline task → No failure → Start Task.

Each stage makes its own real/local API call. Full results, input and submitted system instructions are persisted. The final response is rendered directly in its selected format with actual final provider/model attribution. Code remains untrusted text and is never executed.

The configured character safety limit refuses excessive context without silently truncating it. It is not an exact per-model tokenizer/context-window database; providers can still reject context limits. Reduce selected context or explicitly raise the configured limit. Original persisted outputs remain intact.

Incomplete provider output is retained with usage and error metadata. It is not accepted as successful final output. Inspect the partial result and explicitly create a new continuation task using it. No automatic continuation or summarization is silently performed.

## Working example configuration

Task: Design a Python application that manages a small library. Include adding books, searching, borrowing, returning, validation, error handling and example usage.

- Stage 1 — Plan: OpenAI / an accessible discovered model. Objective: create a detailed architecture and implementation plan. Context: original task + previous output.
- Stage 2 — Implement: Gemini / an accessible discovered model. Objective: implement the original request using the actual plan. Context: original + previous. Authorize Groq and an accessible model as backup.
- Stage 3 — Review: Groq / an accessible discovered model. Objective: review the implementation and produce the final complete answer with improvements. Context: original + all prior outputs.

This is a configuration example, not a claim of a successful live three-provider run. Valid credentials were absent. Mock-network integration tests verify the same propagation/recovery behavior. Never substitute fabricated model IDs or offline outputs.

See [provider setup](PROVIDER_SETUP.md) and [recovery guide](RECOVERY_GUIDE.md).
