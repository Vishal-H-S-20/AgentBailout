# Groq integration

Groq uses official `groq` Python SDK 1.7.0, AsyncGroq Chat Completions and model listing. It is distinct from xAI Grok. GROQ_API_KEY stays in the backend. No single model ID is hardcoded.

The adapter sends selected model, system/user messages and max_completion_tokens, records provider usage and latency, classifies errors, disables hidden SDK retries and leaves API monetary cost unknown without grounded pricing. JSON is prompted and locally validated rather than assuming every Groq model supports native strict schema mode.

Groq can be primary, same-provider alternative or explicitly authorized per-stage backup. The original stage objective, system instructions and saved input are used for fallback. Cost/Time/Balanced selection uses declared estimates and reliability; it does not assume Groq is faster or cheaper. Actual latency is measured.

Mock HTTP tests verify paths, messages, model selection, usage, discovery, timeout, missing/invalid credentials, unavailable models and rate limits. Engine tests verify cross-provider recovery and continuation. Live Groq generation was SKIPPED because credentials were absent.

[Official generation documentation](https://console.groq.com/docs/text-chat) · [API reference](https://console.groq.com/docs/api-reference) · [Setup](PROVIDER_SETUP.md).
