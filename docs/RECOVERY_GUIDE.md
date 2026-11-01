# Recovery and comparison

Custom stages may authorize same-model retry and/or a selected backup provider/model. A real-provider stage cannot recover through offline simulation. Global AgentBailout protection and stage-level eligibility are separate. Existing attempt, task deadline and simulated recovery-budget bounds remain in force. Repeated identical failures open the existing circuit breaker.

The engine preserves completed upstream outputs and the failed stage's complete input. For custom fallback it reuses the primary stage's objective and system instructions, converts messages through the replacement provider's adapter, validates the response and resumes downstream stages. Retry and replacement are labeled separately. No permanent repair of the original model/configuration is claimed; arbitrary safe configuration repair is not implemented.

To demonstrate: configure a valid real primary and authorized backup, save the custom pipeline, choose a controlled crash at the desired named stage, enable protection and Start Task. Controlled failures interrupt before unnecessary known-failing paid calls. Inspect failed primary, recovery input/output and resumed next stage. An actual provider error is separately classified and never described as a controlled outage.

Compare Results runs the same frozen pipeline, task, primary versions and fault twice with protection OFF/ON. Read actual statuses, stage traces, outputs and timings. Real LLM outputs can differ. Recovery may increase runtime and cost; savings are not fabricated. Simulated escrow/payout/refund values remain separate from external API costs. Token usage is recorded; unknown pricing is never shown as zero.

[Setup](PROVIDER_SETUP.md) · [Custom pipelines](REAL_LLM_PIPELINES.md). No live provider recovery was verified without credentials; mocked integration tests verify the engine path.
