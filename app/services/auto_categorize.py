# filename: app/services/auto_categorize.py
"""
AI-based auto-categorization (v0).

Design goals:
- Safe: never raises exceptions to callers
- Optional: controlled by env var AUTO_CATEGORIZE_AI=1
- Strict: validates category against allowed_categories
- Simple v0: one AI call per transaction (not optimized)

Public API:
    categorize(description, account_name, amount_eur, allowed_categories)
        -> (category: str|None, confidence: float, reason: str)
"""

from __future__ import annotations

import json
import os
import re
from dotenv import load_dotenv
from typing import Iterable, Optional, Tuple, Dict, Any


_JSON_FENCE_RE = re.compile(r"^\s*```(?:json)?\s*|\s*```\s*$", re.IGNORECASE)
load_dotenv()


def _env_truthy(name: str, default: str = "0") -> bool:
    v = os.getenv(name, default)
    return str(v).strip().lower() in ("1", "true", "yes", "y", "on")


def _clamp01(x: Any) -> float:
    try:
        f = float(x)
    except Exception:
        return 0.0
    if f < 0.0:
        return 0.0
    if f > 1.0:
        return 1.0
    return f


def _clean_text(s: Any, max_len: int = 400) -> str:
    t = str(s or "").strip()
    if len(t) > max_len:
        t = t[:max_len].rstrip() + "…"
    return t


def _strip_json_fences(s: str) -> str:
    # Removes leading/trailing ```json fences if the model includes them.
    return _JSON_FENCE_RE.sub("", s).strip()


def _safe_json_loads(s: str) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(s)
    except Exception:
        return None


def _normalize_allowed(allowed_categories: Iterable[str]) -> Tuple[set[str], Dict[str, str]]:
    """
    Returns:
      - allowed_set: original strings set
      - allowed_ci: case-insensitive mapping to original
    """
    allowed_list = [str(c) for c in allowed_categories if str(c).strip() != ""]
    allowed_set = set(allowed_list)
    allowed_ci = {c.strip().lower(): c for c in allowed_list}
    return allowed_set, allowed_ci


def _openai_client():
    """
    Lazily import and create an OpenAI client.

    Returns:
        client or None
    """
    try:
        from openai import OpenAI  # type: ignore
    except Exception:
        return None

    try:
        # The OpenAI SDK reads OPENAI_API_KEY from env by default.
        return OpenAI()
    except Exception:
        return None


def _build_prompt(
    description: str,
    account_name: str,
    amount_eur: Optional[float],
    allowed_categories: list[str],
) -> list[dict]:
    amt = None if amount_eur is None else float(amount_eur)

    # Keep the prompt short (v0, not optimized yet), but strict about output.
    developer = (
        "You categorize personal finance transactions.\n"
        "Return ONLY valid JSON (no markdown, no extra text).\n"
        "Choose category ONLY from the provided allowed list or null.\n"
        "Output schema:\n"
        '{ "category": string|null, "confidence": number, "reason": string }\n'
        "confidence is 0..1.\n"
        "reason should be short (merchant/keyword cue).\n"
    )

    user = {
        "allowed_categories": allowed_categories,
        "transaction": {
            "description": description,
            "account_name": account_name,
            "amount_eur": amt,
        },
    }

    return [
        {"role": "developer", "content": developer},
        {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
    ]


def _call_openai_once(
    description: str,
    account_name: str,
    amount_eur: Optional[float],
    allowed_categories: list[str],
) -> Optional[Dict[str, Any]]:
    """
    Returns parsed JSON dict on success, or None on any failure.
    """
    client = _openai_client()
    if client is None:
        return None

    model = os.getenv("AUTO_CATEGORIZE_MODEL", "gpt-4.1-mini")
    prompt = _build_prompt(description, account_name, amount_eur, allowed_categories)

    try:
        # Responses API: https://platform.openai.com/docs/api-reference/responses  [oai_citation:0‡OpenAI Platform](https://platform.openai.com/docs/api-reference/responses?utm_source=chatgpt.com)
        resp = client.responses.create(
            model=model,
            input=prompt,
        )
    except Exception:
        return None

    # SDK exposes output_text helper in examples; keep robust fallback.
    text = ""
    try:
        text = (getattr(resp, "output_text", "") or "").strip()
    except Exception:
        text = ""

    if not text:
        # Try common alternative serialization
        try:
            dumped = resp.model_dump()  # type: ignore[attr-defined]
            text = str(dumped)
        except Exception:
            return None

    cleaned = _strip_json_fences(text)
    data = _safe_json_loads(cleaned)
    return data


def categorize(
    description: str,
    account_name: str = "",
    amount_eur: Optional[float] = None,
    allowed_categories: Iterable[str] = (),
) -> Tuple[Optional[str], float, str]:
    """
    AI categorize one transaction.

    Returns:
        (category, confidence, reason)
    Where:
        - category is a string from allowed_categories, or None
        - confidence is float in [0, 1]
        - reason is short and safe to display as a tooltip

    Silent failure:
        On any error or misconfiguration, returns (None, 0.0, <reason>).
    """
    allowed_set, allowed_ci = _normalize_allowed(allowed_categories)
    allowed_list = sorted(list(allowed_set))

    # Feature flag
    if not _env_truthy("AUTO_CATEGORIZE_AI", "0"):
        return None, 0.0, "ai_disabled"

    # If no categories available, never guess.
    if not allowed_list:
        return None, 0.0, "no_allowed_categories"

    # Basic input cleanup (avoid sending huge/empty payloads)
    desc = _clean_text(description, max_len=300)
    acc = _clean_text(account_name, max_len=80)

    if not desc:
        return None, 0.0, "empty_description"

    # Ensure API key exists; OpenAI SDK expects it in env.  [oai_citation:1‡OpenAI Platform](https://platform.openai.com/docs/api-reference/introduction?utm_source=chatgpt.com)
    if not (os.getenv("OPENAI_API_KEY") or "").strip():
        return None, 0.0, "missing_openai_api_key"

    data = _call_openai_once(desc, acc, amount_eur, allowed_list)
    if not isinstance(data, dict):
        return None, 0.0, "ai_error"

    raw_cat = data.get("category", None)
    raw_conf = data.get("confidence", 0.0)
    raw_reason = data.get("reason", "")

    # Normalize category
    category: Optional[str]
    if raw_cat is None:
        category = None
    else:
        cat_str = str(raw_cat).strip()
        if cat_str in allowed_set:
            category = cat_str
        else:
            # try case-insensitive match
            mapped = allowed_ci.get(cat_str.lower())
            category = mapped if mapped in allowed_set else None

    confidence = _clamp01(raw_conf)
    reason = _clean_text(raw_reason, max_len=120) if raw_reason is not None else ""

    if category is None:
        return None, confidence if confidence > 0 else 0.0, reason or "no_valid_category"

    if not reason:
        reason = "ai_suggested"

    return category, confidence, reason