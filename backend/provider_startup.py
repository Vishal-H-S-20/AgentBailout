"""Load SDK resource modules before a task's watchdog starts; no network requests."""

def prepare_sdks():
    from openai.resources.responses import AsyncResponses
    from openai.resources.models import AsyncModels as OpenAIModels
    from anthropic.resources.messages import AsyncMessages
    from anthropic.resources.models import AsyncModels as ClaudeModels
    from groq.resources.chat.completions import AsyncCompletions
    from groq.resources.models import AsyncModels as GroqModels
    from google import genai
