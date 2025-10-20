# llm.py
"""
Module cấu hình LLM linh hoạt cho chatbot Kinh Dịch.
Hỗ trợ Gemini, OpenAI và mô hình cục bộ (Transformers).
"""

import logging
import time
from typing import Any, Dict, List, Optional

from config import (
    LLM_PROVIDER,
    LLM_TEMPERATURE,
    LLM_TOP_P,
    LLM_TOP_K,
    LLM_MAX_OUTPUT_TOKENS,
    GEMINI_API_KEY,
    GEMINI_MODEL,
    OPENAI_API_KEY,
    OPENAI_MODEL,
    OPENAI_API_BASE,
    LOCAL_MODEL_PATH,
    LOCAL_MODEL_TYPE,
    LOCAL_DEVICE,
    LOCAL_MAX_NEW_TOKENS,
)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Optional imports per provider -------------------------------------------------
try:
    import google.generativeai as genai
    from google.generativeai.types import HarmCategory, HarmBlockThreshold

    GEMINI_AVAILABLE = True
except ImportError:  # pragma: no cover - optional dependency
    genai = None
    HarmCategory = HarmBlockThreshold = None
    GEMINI_AVAILABLE = False

try:
    import openai  # type: ignore

    OPENAI_AVAILABLE = True
except ImportError:  # pragma: no cover - optional dependency
    openai = None  # type: ignore
    OPENAI_AVAILABLE = False

try:
    from transformers import pipeline  # type: ignore
    import torch  # type: ignore

    HF_AVAILABLE = True
except ImportError:  # pragma: no cover - optional dependency
    pipeline = None  # type: ignore
    torch = None  # type: ignore
    HF_AVAILABLE = False


# Backends ----------------------------------------------------------------------

class BaseBackend:
    """Abstract backend interface."""

    provider_name = "base"

    def generate(self, prompt: str) -> str:  # pragma: no cover - interface
        raise NotImplementedError

    def test_connection(self) -> None:
        """Default connectivity test."""
        self.generate("Test connection")


class GeminiBackend(BaseBackend):
    provider_name = "gemini"

    def __init__(self) -> None:
        if not GEMINI_AVAILABLE:
            raise ImportError("google-generativeai chưa được cài đặt.")
        if not GEMINI_API_KEY:
            raise RuntimeError("GEMINI_API_KEY chưa được cấu hình.")

        genai.configure(api_key=GEMINI_API_KEY)
        generation_config = {
            "temperature": LLM_TEMPERATURE,
            "top_p": LLM_TOP_P,
            "top_k": LLM_TOP_K,
            "max_output_tokens": LLM_MAX_OUTPUT_TOKENS,
            "response_mime_type": "text/plain",
        }

        safety_settings = {}
        if HarmCategory and HarmBlockThreshold:
            safety_settings = {
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            }

        self.model = genai.GenerativeModel(
            model_name=GEMINI_MODEL,
            generation_config=generation_config,
            safety_settings=safety_settings or None,
        )

    def generate(self, prompt: str) -> str:
        response = self.model.generate_content(prompt)
        if getattr(response, "text", None):
            return response.text.strip()
        raise RuntimeError("Gemini trả về phản hồi rỗng.")


class OpenAIBackend(BaseBackend):
    provider_name = "openai"

    def __init__(self) -> None:
        if not OPENAI_AVAILABLE:
            raise ImportError("openai chưa được cài đặt.")
        if not OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY chưa được cấu hình.")

        self.model = OPENAI_MODEL

        if hasattr(openai, "OpenAI"):
            kwargs: Dict[str, Any] = {"api_key": OPENAI_API_KEY}
            if OPENAI_API_BASE:
                kwargs["base_url"] = OPENAI_API_BASE
            self.client = openai.OpenAI(**kwargs)
            self._client_mode = "client"
        else:
            openai.api_key = OPENAI_API_KEY  # type: ignore[attr-defined]
            if OPENAI_API_BASE:
                openai.api_base = OPENAI_API_BASE  # type: ignore[attr-defined]
            self.client = openai
            self._client_mode = "legacy"

    def generate(self, prompt: str) -> str:
        messages = [{"role": "user", "content": prompt}]
        if self._client_mode == "client":
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=LLM_TEMPERATURE,
                max_tokens=LLM_MAX_OUTPUT_TOKENS,
                top_p=LLM_TOP_P,
            )
            content = response.choices[0].message.content
        else:
            response = self.client.ChatCompletion.create(  # type: ignore[attr-defined]
                model=self.model,
                messages=messages,
                temperature=LLM_TEMPERATURE,
                max_tokens=LLM_MAX_OUTPUT_TOKENS,
                top_p=LLM_TOP_P,
            )
            content = response["choices"][0]["message"]["content"]

        if not content:
            raise RuntimeError("OpenAI trả về phản hồi rỗng.")
        return content.strip()


class LocalHFBackend(BaseBackend):
    provider_name = "local"

    def __init__(self) -> None:
        if not HF_AVAILABLE:
            raise ImportError("transformers/torch chưa được cài đặt cho chế độ local.")
        if not LOCAL_MODEL_PATH:
            raise RuntimeError("LOCAL_MODEL_PATH chưa được cấu hình.")

        device = self._resolve_device()
        generation_kwargs = {"device": device}
        if LOCAL_MODEL_TYPE != "auto":
            generation_kwargs["task"] = LOCAL_MODEL_TYPE

        self.generator = pipeline(
            "text-generation",
            model=LOCAL_MODEL_PATH,
            **generation_kwargs,
        )

    def _resolve_device(self) -> int:
        if LOCAL_DEVICE == "auto":
            if torch and torch.cuda.is_available():  # type: ignore[call-arg]
                return 0
            return -1
        if LOCAL_DEVICE == "cpu":
            return -1
        if LOCAL_DEVICE.startswith("cuda"):
            if ":" in LOCAL_DEVICE:
                return int(LOCAL_DEVICE.split(":", maxsplit=1)[1])
            return 0
        # Allow passing integer device id via env
        try:
            return int(LOCAL_DEVICE)
        except ValueError:
            return -1

    def generate(self, prompt: str) -> str:
        outputs = self.generator(
            prompt,
            max_new_tokens=LOCAL_MAX_NEW_TOKENS,
            do_sample=False,
            temperature=LLM_TEMPERATURE,
            top_p=LLM_TOP_P,
        )
        generated_text = outputs[0]["generated_text"]
        if generated_text.startswith(prompt):
            generated_text = generated_text[len(prompt) :]
        return generated_text.strip()


# Factory -----------------------------------------------------------------------

def create_backend() -> BaseBackend:
    if LLM_PROVIDER == "gemini":
        return GeminiBackend()
    if LLM_PROVIDER == "openai":
        return OpenAIBackend()
    if LLM_PROVIDER == "local":
        return LocalHFBackend()
    raise ValueError(f"LLM provider '{LLM_PROVIDER}' không được hỗ trợ.")


# High-level interface ----------------------------------------------------------

class KinhDichLLM:
    """LLM interface chung cho chatbot Kinh Dịch."""

    def __init__(self) -> None:
        self.backend = create_backend()
        self.conversation_history: Dict[str, List[Dict[str, Any]]] = {}
        self._test_connection()

    def _test_connection(self) -> None:
        try:
            self.backend.test_connection()
            logger.info("Kết nối LLM (%s) thành công.", self.backend.provider_name)
        except Exception as exc:  # pragma: no cover - runtime connectivity check
            logger.error("Kết nối LLM (%s) thất bại: %s", self.backend.provider_name, exc)
            raise

    def generate(self, prompt: str, session_id: str = "default", use_history: bool = False) -> str:
        try:
            full_prompt = self._inject_history(prompt, session_id) if use_history else prompt
            response = self.backend.generate(full_prompt)
            self._store_history(session_id, prompt, response)
            return response
        except Exception as exc:
            logger.error("LLM generation failed: %s", exc)
            return self._get_fallback_response(prompt)

    def _inject_history(self, prompt: str, session_id: str) -> str:
        if session_id not in self.conversation_history:
            return prompt

        recent_history = self.conversation_history[session_id][-3:]
        parts = ["NGỮ CẢNH CUỘC TRÒ CHUYỆN TRƯỚC:"]
        for item in recent_history:
            prompt_preview = item["prompt"][:100] + "..." if len(item["prompt"]) > 100 else item["prompt"]
            response_preview = item["response"][:150] + "..." if len(item["response"]) > 150 else item["response"]
            parts.append(f"Hỏi: {prompt_preview}")
            parts.append(f"Đáp: {response_preview}")

        parts.append("---")
        parts.append(prompt)
        return "\n".join(parts)

    def _store_history(self, session_id: str, prompt: str, response: str) -> None:
        history = self.conversation_history.setdefault(session_id, [])
        history.append({"prompt": prompt, "response": response, "timestamp": time.time()})
        if len(history) > 10:
            self.conversation_history[session_id] = history[-10:]

    def _get_fallback_response(self, prompt: str) -> str:
        if "quẻ" in prompt.lower() or "hexagram" in prompt.lower():
            return (
                "Xin lỗi, tôi đang gặp khó khăn kỹ thuật.\n\n"
                "Tuy nhiên, tôi khuyên bạn nên:\n"
                "1. Suy ngẫm về tình huống hiện tại\n"
                "2. Tìm hiểu ý nghĩa quẻ trong bối cảnh cụ thể\n"
                "3. Áp dụng triết lý cân bằng âm dương\n\n"
                "Vui lòng thử lại sau."
            )
        return "Xin lỗi, tôi đang gặp sự cố kỹ thuật. Vui lòng thử lại sau."


class KinhDichLLMAdvanced(KinhDichLLM):
    """Advanced LLM với features mở rộng cho Kinh Dịch."""

    def __init__(self) -> None:
        super().__init__()
        self.response_cache: Dict[str, Dict[str, Any]] = {}

    def generate_with_analysis(
        self,
        prompt: str,
        retrieved_docs: List[Dict[str, Any]],
        session_id: str = "default",
    ) -> Dict[str, Any]:
        try:
            response = self.generate(prompt, session_id)
            analysis = self._analyze_response_quality(response, retrieved_docs)
            citations = self._extract_citations(response, retrieved_docs)
            return {
                "answer": response,
                "confidence": analysis["confidence"],
                "reasoning": analysis["reasoning"],
                "citations": citations,
                "session_id": session_id,
            }
        except Exception as exc:
            logger.error("Error in advanced LLM generation: %s", exc)
            return {
                "answer": self._get_fallback_response(prompt),
                "confidence": 0.1,
                "reasoning": "Fallback response due to technical error",
                "citations": [],
                "error": str(exc),
            }

    def _analyze_response_quality(self, response: str, docs: List[Dict[str, Any]]) -> Dict[str, Any]:
        confidence = 0.5
        reasoning_points = []

        if len(response) > 100:
            confidence += 0.1
            reasoning_points.append("Response có độ dài phù hợp")

        if any(doc.get("hexagram") and doc["hexagram"] in response for doc in docs):
            confidence += 0.2
            reasoning_points.append("Reference đến quẻ cụ thể")

        cultural_keywords = ["âm dương", "thiên địa", "ngũ hành", "quẻ", "triết lý"]
        if any(keyword in response.lower() for keyword in cultural_keywords):
            confidence += 0.1
            reasoning_points.append("Có bối cảnh văn hóa phù hợp")

        import re

        if re.search(r"\[\d+\]", response):
            confidence += 0.1
            reasoning_points.append("Có trích dẫn nguồn")

        return {"confidence": min(confidence, 1.0), "reasoning": " | ".join(reasoning_points)}

    def _extract_citations(self, response: str, docs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        import re

        citations = []
        for match in re.findall(r"\[(\d+)\]", response):
            try:
                idx = int(match) - 1
                if 0 <= idx < len(docs):
                    doc = docs[idx]
                    citations.append(
                        {
                            "index": int(match),
                            "chunk_id": doc.get("_id"),
                            "hexagram": doc.get("hexagram"),
                            "content_preview": (doc.get("text", "")[:200] + "..."),
                            "source_type": doc.get("content_type"),
                        }
                    )
            except (ValueError, IndexError):
                continue
        return citations


# Singleton helpers -------------------------------------------------------------

_llm_instance: Optional[KinhDichLLM] = None


def get_llm() -> KinhDichLLM:
    global _llm_instance
    if _llm_instance is None:
        _llm_instance = KinhDichLLMAdvanced()
    return _llm_instance


def generate(prompt: str, session_id: str = "default", use_history: bool = False) -> str:
    llm = get_llm()
    return llm.generate(prompt, session_id, use_history)


def generate_advanced(
    prompt: str,
    retrieved_docs: List[Dict[str, Any]],
    session_id: str = "default",
) -> Dict[str, Any]:
    llm = get_llm()
    if isinstance(llm, KinhDichLLMAdvanced):
        return llm.generate_with_analysis(prompt, retrieved_docs, session_id)
    response = llm.generate(prompt, session_id)
    return {"answer": response, "confidence": 0.7, "reasoning": "Basic generation", "citations": []}


def test_llm() -> None:
    """Quick manual test for CLI usage."""
    print("Testing Kinh Dịch LLM...")
    llm = get_llm()
    prompts = [
        "Quẻ Cách có ý nghĩa gì?",
        "Hãy giải thích triết lý âm dương trong Kinh Dịch",
        "Tôi nên làm gì khi gặp khó khăn?",
    ]
    for idx, prompt in enumerate(prompts, 1):
        print(f"\nTest {idx}: {prompt}")
        response = llm.generate(prompt, f"test_session_{idx}")
        print(f"Response: {response[:120]}...")
    print("\nLLM testing completed!")


if __name__ == "__main__":
    test_llm()
