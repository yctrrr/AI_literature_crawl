from __future__ import annotations

import json
import os

from src.config import LLMConfig
from src.models import Candidate, Classification


class LLMClient:
    def __init__(self, config: LLMConfig):
        self.config = config
        self.max_pdf_chars = config.max_pdf_chars
        self._client = None

    @property
    def client(self):
        if self._client is None:
            api_key = os.environ.get(self.config.api_key_env)
            if not api_key:
                raise RuntimeError(f"Missing LLM API key environment variable: {self.config.api_key_env}")
            from openai import OpenAI

            kwargs = {"api_key": api_key}
            if self.config.base_url:
                kwargs["base_url"] = self.config.base_url
            self._client = OpenAI(**kwargs)
        return self._client

    def classify(self, candidate: Candidate, metadata: dict, text_excerpt: str, categories: list[str]) -> Classification:
        if not os.environ.get(self.config.api_key_env):
            return Classification("others", 0.0, f"{self.config.api_key_env} is missing.", "fallback")

        prompt = {
            "task": "Choose exactly one category for this academic paper.",
            "allowed_categories": categories,
            "paper": {
                "title": metadata.get("title") or candidate.title,
                "abstract": metadata.get("abstract", ""),
                "keyword": candidate.keyword,
                "url": candidate.url,
                "text_excerpt": text_excerpt[:12000],
            },
            "output": {
                "category": "one item from allowed_categories",
                "confidence": "number from 0 to 1",
                "rationale": "one short sentence",
            },
        }
        try:
            content = self._chat_json(
                "You classify papers into a fixed local taxonomy. Return strict JSON only.",
                json.dumps(prompt, ensure_ascii=False),
            )
            category = str(content.get("category", "")).strip()
            if category not in categories:
                category = "others" if "others" in categories else categories[0]
            return Classification(
                category=category,
                confidence=float(content.get("confidence", 0.0)),
                rationale=str(content.get("rationale", ""))[:500],
            )
        except Exception as exc:
            fallback = "others" if "others" in categories else categories[0]
            return Classification(fallback, 0.0, f"Classification failed: {exc}", "fallback")

    def summarize(self, candidate: Candidate, metadata: dict, text_excerpt: str, classification: Classification) -> str:
        if not text_excerpt.strip():
            raise RuntimeError("PDF text extraction returned empty text.")
        prompt = f"""
Summarize this Nature article in Chinese for an environmental and energy research literature archive.

Title: {metadata.get("title") or candidate.title}
URL: {candidate.url}
Category: {classification.category}
Publication date: {metadata.get("published") or candidate.published}

Write these sections:
1. Citation metadata
2. Research question
3. Data and methods
4. Main findings
5. Relevance to air quality, climate change, or energy transition
6. Limitations and caveats
7. Keywords

Use concise bullet points. Base the answer only on the supplied PDF text excerpt.

PDF text excerpt:
{text_excerpt[: self.max_pdf_chars]}
""".strip()
        response = self.client.chat.completions.create(
            model=self.config.model,
            messages=[
                {"role": "system", "content": "You are a careful academic literature summarizer."},
                {"role": "user", "content": prompt},
            ],
        )
        return response.choices[0].message.content or ""

    def _chat_json(self, system: str, user: str) -> dict:
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        try:
            response = self.client.chat.completions.create(
                model=self.config.model,
                response_format={"type": "json_object"},
                messages=messages,
            )
        except Exception:
            response = self.client.chat.completions.create(
                model=self.config.model,
                messages=messages,
            )
        raw = response.choices[0].message.content or "{}"
        raw = _strip_json_fence(raw)
        return json.loads(raw)


def _strip_json_fence(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.lower().startswith("json"):
            raw = raw[4:]
    return raw.strip()
