"""Model wrappers: a free local LLM (llama.cpp GGUF) and the paid Fireworks proxy.

Local tokens are free and count toward accuracy; Fireworks tokens count toward the score,
so the router prefers local and escalates only when necessary.
"""

import inspect
import os


class LocalModel:
    """Optional local GGUF model via llama-cpp-python. Free at evaluation time.

    Bundle a small (2-3B, 4-bit) GGUF in the image and set LOCAL_MODEL_PATH. If the model
    or the library is unavailable, `available` is False and the router falls back to
    Fireworks for everything.
    """

    def __init__(self, model_path: str | None = None, n_threads: int | None = None):
        self.available = False
        self.llm = None
        self.supports_thinking_control = False
        model_path = model_path or os.getenv("LOCAL_MODEL_PATH")
        if not model_path or not os.path.exists(model_path):
            return
        try:
            from llama_cpp import Llama

            self.llm = Llama(
                model_path=model_path,
                n_ctx=int(os.getenv("LOCAL_N_CTX", "4096")),
                n_threads=n_threads or int(os.getenv("LOCAL_N_THREADS", "2")),  # 2 vCPU VM
                verbose=False,
            )
            self.supports_thinking_control = (
                "chat_template_kwargs" in inspect.signature(
                    self.llm.create_chat_completion
                ).parameters
            )
            self.available = True
        except Exception as exc:  # pragma: no cover - depends on runtime env
            print(f"[local] disabled: {exc}", flush=True)
            self.available = False

    def generate(self, system: str, user: str, max_tokens: int = 1024,
                 temperature: float = 0.3) -> str | None:
        if not self.available:
            return None
        try:
            completion_kwargs = {
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "max_tokens": max_tokens,
                "temperature": temperature,
            }
            if self.supports_thinking_control:
                completion_kwargs["chat_template_kwargs"] = {
                    "enable_thinking": False
                }

            out = self.llm.create_chat_completion(
                **completion_kwargs,
            )
            return out["choices"][0]["message"]["content"].strip()
        except Exception as exc:  # pragma: no cover
            print(f"[local] generation error: {exc}", flush=True)
            return None


class FireworksModel:
    """Paid Fireworks proxy via the OpenAI-compatible SDK. Every token counts to the score."""

    def __init__(self):
        self.available = False
        self.client = None
        self.models = []
        api_key = os.getenv("FIREWORKS_API_KEY")
        base_url = os.getenv("FIREWORKS_BASE_URL")
        allowed = os.getenv("ALLOWED_MODELS", "")
        self.models = [m.strip() for m in allowed.split(",") if m.strip()]
        if not (api_key and base_url and self.models):
            return
        try:
            from openai import OpenAI

            self.client = OpenAI(api_key=api_key, base_url=base_url)
            self.available = True
        except Exception as exc:  # pragma: no cover
            print(f"[fireworks] disabled: {exc}", flush=True)
            self.available = False

    def pick_model(self, prefer_strong: bool) -> str | None:
        """Select an allowed model. ALLOWED_MODELS order is unknown, so callers should treat
        the last entry as a candidate 'strong' model and the first as a candidate 'cheap'
        one; both are valid. Adjust after inspecting the launch-day list."""
        if not self.models:
            return None
        return self.models[-1] if prefer_strong else self.models[0]

    def generate(self, system: str, user: str, prefer_strong: bool = False,
                 max_tokens: int = 1024, temperature: float = 0.3) -> str | None:
        if not self.available:
            return None
        model = self.pick_model(prefer_strong)
        try:
            resp = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                max_tokens=max_tokens,
                temperature=temperature,
                extra_body={"thinking": {"type": "disabled"}},
            )
            return resp.choices[0].message.content.strip()
        except Exception as exc:  # pragma: no cover
            print(f"[fireworks] generation error ({model}): {exc}", flush=True)
            return None
