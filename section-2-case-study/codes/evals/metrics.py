from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Any


EMPTY_VALUES = (None, "", [], {}, ())


def normalize_text(value: Any) -> str:
    """Normalize extracted values before exact and similarity checks."""
    if value is None:
        return ""
    if isinstance(value, (list, tuple, set)):
        return " ".join(normalize_text(item) for item in value)
    if isinstance(value, dict):
        return " ".join(f"{key} {normalize_text(val)}" for key, val in sorted(value.items()))
    return re.sub(r"\s+", " ", str(value).casefold()).strip()


def exact_match(predicted: Any, expected: Any) -> bool:
    return normalize_text(predicted) == normalize_text(expected)


def textual_similarity(predicted: Any, expected: Any) -> float:
    predicted_text = normalize_text(predicted)
    expected_text = normalize_text(expected)
    if not predicted_text and not expected_text:
        return 1.0
    if not predicted_text or not expected_text:
        return 0.0
    return SequenceMatcher(None, predicted_text, expected_text).ratio()


def is_complete(value: Any) -> bool:
    if value in EMPTY_VALUES:
        return False
    if isinstance(value, str) and not value.strip():
        return False
    return True


def value_supported_by_paper(value: Any, paper_text: str, *, similarity_threshold: float = 0.86) -> bool:
    """Return True when a predicted value appears to be grounded in paper text.

    Exact containment catches identifiers, marks, and short phrases. For longer
    strings, a sliding-window similarity check allows minor whitespace/OCR
    differences without requiring an embedding service.
    """
    value_text = normalize_text(value)
    haystack = normalize_text(paper_text)
    if not value_text:
        return True
    if value_text in haystack:
        return True
    if len(value_text) < 8:
        return False

    words = value_text.split()
    haystack_words = haystack.split()
    if not haystack_words:
        return False

    window_size = max(3, min(len(words), 28))
    candidate = " ".join(words[:window_size])
    for index in range(0, max(1, len(haystack_words) - window_size + 1)):
        window = " ".join(haystack_words[index : index + window_size])
        if SequenceMatcher(None, candidate, window).ratio() >= similarity_threshold:
            return True
    return False


def evaluate_key(
    key: str,
    predicted: Any,
    expected: Any | None,
    paper_text: str,
    *,
    required: bool = True,
) -> dict[str, Any]:
    complete = is_complete(predicted)
    exact = exact_match(predicted, expected) if expected is not None else None
    similarity = textual_similarity(predicted, expected) if expected is not None else None
    supported = (exact is True) or value_supported_by_paper(predicted, paper_text) if complete else True
    return {
        "key": key,
        "predicted": predicted,
        "expected": expected,
        "accuracy": {
            "exact_match": exact,
            "textual_similarity": similarity,
        },
        "completeness": {
            "required": required,
            "present": complete,
            "failed_to_obtain": required and not complete,
        },
        "hallucination": {
            "supported_by_paper": supported,
            "hallucinated": complete and not supported,
        },
    }
