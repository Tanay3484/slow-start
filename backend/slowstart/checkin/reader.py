"""Read a one-line check-in (R5). Code decides; the model only labels and talks.

- `excused` is set here from a word list with a negation check, never by the model (R5.2).
- The model proposes `energy`, `body` and a line. `body` is kept only if each area really appears in
  the text, and the line is rejected if it has a digit, a URL, or runs long (R5.4).
- If the model is down or off, a keyword reader and a template line stand in (R5.3).
"""

from __future__ import annotations

import logging
import re
from typing import Literal

from slowstart.checkin.ollama import ChatJSON, LLMError
from slowstart.models import Checkin

log = logging.getLogger("slowstart.checkin")

Energy = Literal["low", "ok", "high"]

BODY_AREAS = (
    "knee", "knees", "back", "ankle", "ankles", "shoulder", "shoulders", "hip", "hips", "neck",
    "wrist", "elbow", "foot", "feet", "calf", "calves", "hamstring", "quad", "quads", "head",
    "legs", "leg", "arms", "chest",
)  # fmt: skip
LOW_WORDS = (
    "tired",
    "exhausted",
    "drained",
    "sleepy",
    "wiped",
    "no energy",
    "knackered",
    "burnt out",
)
HIGH_WORDS = ("energetic", "great", "pumped", "strong", "fresh", "fantastic", "amazing", "good")
EXCUSE_WORDS = (
    "sick", "ill", "unwell", "fever", "flu", "covid", "migraine", "injured", "injury", "sprain",
    "sprained", "strained", "torn", "broken", "surgery", "hospital", "doctor", "vomiting",
    "food poisoning", "stomach bug",
)  # fmt: skip
NEGATIONS = ("not", "no", "never", "n't", "isn't", "wasn't", "don't", "without", "recovered")

TEMPLATES: dict[tuple[bool, str], str] = {
    (True, "low"): "Rest. I am not going anywhere. We will start again when you are ready.",
    (True, "ok"): "Rest first. The goal will wait for you, and so will I.",
    (True, "high"): "Rest first. The goal will wait for you, and so will I.",
    (False, "low"): "Slow is fine. A short walk is a win for a sleepy giant.",
    (False, "ok"): "Steady steps. I will wake up as you go.",
    (False, "high"): "Good. Let us stomp. I am waking up.",
}

SYSTEM = """You are Slumbrock, a sleepy stone giant looked after by the person writing to you.
You speak slowly, kindly, in ONE short sentence of at most 14 words.
Rules:
- Never use digits or numbers. Never give medical advice. Never pressure or scold.
- If the person is ill or hurt, tell them to rest and that you will wait.
- energy is how the person feels: low, ok or high.
- body lists body parts the person mentions, copied from their words (empty if none).
Reply with JSON only."""

SCHEMA = {
    "type": "object",
    "properties": {
        "energy": {"type": "string", "enum": ["low", "ok", "high"]},
        "body": {"type": "array", "items": {"type": "string", "maxLength": 20}, "maxItems": 3},
        "line": {"type": "string", "maxLength": 120},
    },
    "required": ["energy", "body", "line"],
}


def _words(text: str) -> list[str]:
    return re.findall(r"[a-z']+", text.lower())


def _has(text: str, vocab: tuple[str, ...]) -> bool:
    low = text.lower()
    return any(re.search(rf"\b{re.escape(w)}\b", low) for w in vocab)


def is_excused(text: str) -> bool:
    """Illness or injury words, unless negated within the three words before ("not sick")."""
    words = _words(text)
    joined = " ".join(words)
    for term in EXCUSE_WORDS:
        for m in re.finditer(rf"\b{re.escape(term)}\b", joined):
            before = joined[: m.start()].split()[-3:]
            if not any(n in before or any(b.endswith("n't") for b in before) for n in NEGATIONS):
                return True
    return False


def keyword_energy(text: str) -> Energy:
    if _has(text, LOW_WORDS):
        return "low"
    if _has(text, HIGH_WORDS) and not any(n in _words(text) for n in ("not", "no")):
        return "high"
    return "ok"


def keyword_body(text: str) -> list[str]:
    low = text.lower()
    return [a for a in BODY_AREAS if re.search(rf"\b{a}\b", low)][:3]


def line_ok(line: str) -> bool:
    return (
        0 < len(line) <= 140
        and len(line.split()) <= 20
        and not re.search(r"\d|https?:|www\.", line)
    )


def read_checkin(text: str, llm: ChatJSON | None) -> Checkin:
    text = text.strip()
    excused = is_excused(text)
    energy: Energy = keyword_energy(text)
    body = keyword_body(text)
    line = ""
    source: Literal["gemma", "template"] = "template"

    if llm is not None:
        try:
            data = llm.chat_json(
                [{"role": "system", "content": SYSTEM}, {"role": "user", "content": text}], SCHEMA
            )
            m_energy = data.get("energy")
            if m_energy in ("low", "ok", "high"):
                energy = m_energy
            m_body = [
                b.strip().lower() for b in data.get("body", []) if isinstance(b, str) and b.strip()
            ]
            body = [b for b in m_body if re.search(rf"\b{re.escape(b)}\b", text.lower())][
                :3
            ] or body
            candidate = str(data.get("line", "")).strip()
            if line_ok(candidate):
                line, source = candidate, "gemma"
        except LLMError as exc:
            log.warning("check-in model failed: %s", exc)

    if not line:
        line = TEMPLATES[(excused, energy)]
    return Checkin(energy=energy, body=body, excused=excused, line=line, source=source)
