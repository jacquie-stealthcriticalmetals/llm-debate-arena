from abc import ABC, abstractmethod
from backend.keys import get_key


class LLMClient(ABC):
    @abstractmethod
    async def complete(self, messages: list[dict], model: str) -> str:
        ...


class OpenAIClient(LLMClient):
    async def complete(self, messages: list[dict], model: str) -> str:
        import openai

        key = get_key("openai")
        if not key:
            raise ValueError("OpenAI API key not configured")

        client = openai.AsyncOpenAI(api_key=key)
        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=4096,
        )
        return response.choices[0].message.content


class ClaudeClient(LLMClient):
    async def complete(self, messages: list[dict], model: str) -> str:
        import anthropic

        key = get_key("anthropic")
        if not key:
            raise ValueError("Anthropic API key not configured")

        client = anthropic.AsyncAnthropic(api_key=key)

        system_text = ""
        chat_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_text = msg["content"]
            else:
                chat_messages.append(msg)

        kwargs = dict(
            model=model,
            max_tokens=4096,
            messages=chat_messages,
        )
        if system_text:
            kwargs["system"] = system_text

        response = await client.messages.create(**kwargs)
        return response.content[0].text


class GeminiClient(LLMClient):
    async def complete(self, messages: list[dict], model: str) -> str:
        from google import genai

        key = get_key("google")
        if not key:
            raise ValueError("Google API key not configured")

        client = genai.Client(api_key=key)

        system_text = None
        contents = []
        for msg in messages:
            if msg["role"] == "system":
                system_text = msg["content"]
            elif msg["role"] == "assistant":
                contents.append({"role": "model", "parts": [{"text": msg["content"]}]})
            else:
                contents.append({"role": "user", "parts": [{"text": msg["content"]}]})

        config = {"max_output_tokens": 4096}
        if system_text:
            config["system_instruction"] = system_text

        response = await client.aio.models.generate_content(
            model=model,
            contents=contents,
            config=config,
        )
        return response.text


def get_client(provider: str) -> LLMClient:
    clients = {
        "openai": OpenAIClient,
        "anthropic": ClaudeClient,
        "google": GeminiClient,
    }
    cls = clients.get(provider)
    if not cls:
        raise ValueError(f"Unknown provider: {provider}")
    return cls()
