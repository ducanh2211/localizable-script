"""AI Translation Service supporting Google Gemini, OpenAI, Claude, DeepSeek."""

import enum
import json
import time
from typing import Any, Callable, Dict, List, Optional, Sequence, Union
import urllib.request
import urllib.error


class AIProvider(str, enum.Enum):
    GEMINI = "gemini"
    OPENAI = "openai"
    DEEPSEEK = "deepseek"
    CLAUDE = "claude"


class AITranslator:
    """Service to automatically translate localization strings via LLM REST APIs."""

    def __init__(
        self,
        provider: Union[str, AIProvider] = AIProvider.GEMINI,
        api_key: str = "",
        model: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        self.provider = AIProvider(provider)
        self.api_key = api_key.strip()
        self.base_url = base_url

        if not model:
            if self.provider == AIProvider.GEMINI:
                self.model = "gemini-2.0-flash"
            elif self.provider == AIProvider.OPENAI:
                self.model = "gpt-4o-mini"
            elif self.provider == AIProvider.DEEPSEEK:
                self.model = "deepseek-chat"
            elif self.provider == AIProvider.CLAUDE:
                self.model = "claude-3-5-haiku-latest"
        else:
            self.model = model

    def _build_system_prompt(self, target_langs: Sequence[str]) -> str:
        langs_str = ", ".join(target_langs)
        return (
            f"You are a professional software localization specialist for iOS apps. "
            f"You will receive a JSON list of items containing 'id', 'key', 'variant', and 'source'. "
            f"Translate 'source' into the target languages: [{langs_str}].\n\n"
            f"MANDATORY RULES:\n"
            f"1. Preserve ALL format specifiers/placeholders EXACTLY: %@, %d, %lld, %f, %1$@, %2$lld, etc. "
            f"Never translate or drop them. %% is a literal percent sign, keep it unchanged.\n"
            f"2. If 'variant' starts with 'plural.', adapt the translation naturally for plural forms in the target language.\n"
            f"3. If 'variant' starts with 'device.', maintain consistent device terminology.\n"
            f"4. If 'source' is empty, return empty string for translations.\n"
            f"5. Return ONLY a valid JSON object with the key 'translations' which is a list of objects in the format:\n"
            f'{{"translations": [{{"id": ..., "translations": {{"lang_code": "translated text"}}}}}}\n'
            f"Do not include markdown code block formatting or any explanation text outside the JSON."
        )

    def _call_gemini(self, system_prompt: str, user_content: str) -> str:
        url = (
            self.base_url
            or f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        )
        payload = {
            "system_instruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"parts": [{"text": user_content}]}],
            "generationConfig": {
                "response_mime_type": "application/json",
                "temperature": 0.2,
            },
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            candidates = data.get("candidates", [])
            if not candidates:
                raise ValueError(f"Gemini API returned no candidates: {data}")
            return candidates[0]["content"]["parts"][0]["text"]

    def _call_openai_compatible(self, url: str, system_prompt: str, user_content: str) -> str:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        payload = {
            "model": self.model,
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"]

    def _call_claude(self, system_prompt: str, user_content: str) -> str:
        url = self.base_url or "https://api.anthropic.com/v1/messages"
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
        }
        payload = {
            "model": self.model,
            "max_tokens": 4096,
            "temperature": 0.2,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_content}],
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["content"][0]["text"]

    def translate_batch(
        self, items: List[Dict[str, Any]], target_langs: Sequence[str]
    ) -> List[Dict[str, Any]]:
        """Dịch 1 batch items qua AI API."""
        if not items:
            return []

        system_prompt = self._build_system_prompt(target_langs)
        user_content = json.dumps({"items": items}, ensure_ascii=False)

        for attempt in range(3):
            try:
                if self.provider == AIProvider.GEMINI:
                    raw_res = self._call_gemini(system_prompt, user_content)
                elif self.provider == AIProvider.OPENAI:
                    url = self.base_url or "https://api.openai.com/v1/chat/completions"
                    raw_res = self._call_openai_compatible(url, system_prompt, user_content)
                elif self.provider == AIProvider.DEEPSEEK:
                    url = self.base_url or "https://api.deepseek.com/chat/completions"
                    raw_res = self._call_openai_compatible(url, system_prompt, user_content)
                elif self.provider == AIProvider.CLAUDE:
                    raw_res = self._call_claude(system_prompt, user_content)
                else:
                    raise ValueError(f"Unsupported provider: {self.provider}")

                # Parse kết quả
                parsed = json.loads(raw_res)
                if isinstance(parsed, dict) and "translations" in parsed:
                    return parsed["translations"]
                elif isinstance(parsed, list):
                    return parsed
                return []
            except Exception as e:
                if attempt == 2:
                    raise RuntimeError(f"Lỗi khi gọi AI API ({self.provider}): {e}") from e
                time.sleep(1.5 * (attempt + 1))
        return []

    def translate_rows(
        self,
        rows: List[Dict[str, Any]],
        target_langs: Sequence[str],
        batch_size: int = 25,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> List[Dict[str, Any]]:
        """Dịch danh sách các row (in-place cập nhật các cột {lang}_target)."""
        # Chuẩn bị danh sách cần dịch
        items_to_translate = []
        for idx, row in enumerate(rows):
            items_to_translate.append({
                "id": idx,
                "key": row["key"],
                "variant": row.get("variant", ""),
                "source": row.get("source_value", ""),
            })

        total = len(items_to_translate)
        completed = 0

        for i in range(0, total, batch_size):
            batch = items_to_translate[i : i + batch_size]
            results = self.translate_batch(batch, target_langs)

            # Map kết quả lại vào rows
            for res in results:
                row_id = res.get("id")
                if row_id is not None and 0 <= row_id < len(rows):
                    trans_map = res.get("translations", {})
                    for lang, val in trans_map.items():
                        rows[row_id][f"{lang}_target"] = str(val)

            completed = min(total, i + batch_size)
            if progress_callback:
                progress_callback(completed, total)

        return rows
