"""Read a one-line check-in and answer as Slumbrock (R5). Code decides; the model only labels and talks.

The reply has three parts:

- **line**: Gemma's reaction, in Slumbrock's voice (sleepy, warm, a little self-aware about being a rock).
  Rejected if it is too short, too long, or has a digit or a URL (R5.4); a template stands in.
- **tip**: one recovery or encouragement tip, chosen by code from a curated list by what the person
  mentioned (legs, back, low energy, ill...). The model never gives advice, so nothing medical is made up.
- **aside**: now and then, a rock joke. Never on an excused (ill or injured) day.

`excused` is set here from a word list with a negation check, never by the model (R5.2). The model
proposes `energy` and `body`; a body part is kept only if it is a known area and really appears in the text.
If the model is down or off, keyword readers and templates stand in (R5.3).
"""

from __future__ import annotations

import logging
import re
import zlib
from typing import Literal

from slowstart.checkin.ollama import ChatJSON, LLMError
from slowstart.models import Checkin

log = logging.getLogger("slowstart.checkin")

Energy = Literal["low", "ok", "high"]

BODY_AREAS = (
    "knee", "knees", "back", "ankle", "ankles", "shoulder", "shoulders", "hip", "hips", "neck",
    "wrist", "wrists", "elbow", "elbows", "foot", "feet", "calf", "calves", "hamstring", "hamstrings",
    "quad", "quads", "glutes", "head", "legs", "leg", "arms", "arm", "chest", "core", "abs",
    "upper body", "lower body", "biceps", "triceps", "lats", "traps",
)  # fmt: skip
# Gym words say which part of the body did the work: "weighted pull ups" means a sore upper body.
EXERCISE_HINTS: tuple[tuple[str, str], ...] = (
    (r"\bpull[- ]?ups?\b|\bchin[- ]?ups?\b|\bpush[- ]?ups?\b|\bbench\b|\boverhead press\b|\bdips?\b"
     r"|\brows?\b|\bcurls?\b|\bpress[- ]?ups?\b", "upper body"),
    (r"\bsquats?\b|\blunges?\b|\bleg press\b|\bleg day\b|\bstep[- ]?ups?\b", "legs"),
    (r"\bdeadlifts?\b", "lower body"),
)  # fmt: skip
LOW_WORDS = (
    "tired", "exhausted", "drained", "sleepy", "wiped", "no energy", "knackered", "burnt out", "brutal",
    "sore", "wrecked", "dead", "destroyed", "killed me", "heavy", "aching", "achy", "stiff", "rough",
)  # fmt: skip
HIGH_WORDS = (
    "energetic", "great", "pumped", "strong", "fresh", "fantastic", "amazing", "good", "awesome",
    "personal best", "pr", "crushed it", "smashed it",
)  # fmt: skip
EXCUSE_WORDS = (
    "sick", "ill", "unwell", "fever", "flu", "covid", "migraine", "injured", "injury", "sprain",
    "sprained", "strained", "torn", "broken", "surgery", "hospital", "doctor", "vomiting",
    "food poisoning", "stomach bug",
)  # fmt: skip
NEGATIONS = ("not", "no", "never", "n't", "isn't", "wasn't", "don't", "without", "recovered")

# Openers used when the model is down or its line is rejected, by (excused, energy).
TEMPLATES: dict[tuple[bool, str], list[str]] = {
    (True, "low"): [
        "Rest. I am not going anywhere. I have been sitting here for centuries, one more day is nothing.",
        "Oh no. Bed, blanket, water. I will guard the path while you heal.",
    ],
    (True, "ok"): ["Rest first. The goal will wait for you, and so will I."],
    (True, "high"): ["Rest first, even if you feel fine. The goal will wait, and so will I."],
    (False, "low"): [
        "Mmm. A heavy day. Slow is fine. Slow is my whole personality.",
        "That sounds rough. Even a short walk is a win for a sleepy giant like me.",
        "I felt that from here, and I am made of stone.",
    ],
    (False, "ok"): [
        "Steady steps. I can feel myself waking up a little.",
        "Good to hear from you. The moss on my head is listening.",
    ],
    (False, "high"): [
        "Look at you! I nearly opened both eyes.",
        "That energy shook a pebble loose. Let us stomp.",
    ],
}

# Tips are chosen by code, never written by the model. General wellness, nothing medical, no digits.
TIPS: dict[str, list[str]] = {
    "excused": [
        "Tip: rest and fluids today. The goal stays where it is and nothing is cut.",
        "Tip: sleep is the best workout today. I will keep your spot warm. Well, cool. I am a rock.",
    ],
    "legs": [
        "Tip: an easy walk tomorrow helps sore legs more than the sofa does. Slow counts.",
        "Tip: drink water, get some protein in, and let your legs rebuild while you sleep.",
        "Tip: gentle calf and hamstring stretches before bed, nothing fancy.",
    ],
    "back": [
        "Tip: keep moving gently. A short walk is kinder to a sore back than sitting all day.",
        "Tip: stand up and walk around for a few minutes every hour today.",
    ],
    "upper": [
        "Tip: your legs are fine, so a walk still counts. Let your arms rest.",
        "Tip: protein and sleep are where the strength actually comes from.",
    ],
    "feet": [
        "Tip: comfy shoes and a short, flat walk. Skip the hills today.",
    ],
    "head": [
        "Tip: water first, then a little fresh air if you feel up to it.",
    ],
    "low": [
        "Tip: aim for a short walk after a meal. Small steps still wake me.",
        "Tip: put your shoes by the door tonight. Tomorrow-you will thank you.",
    ],
    "high": [
        "Tip: bank it. Take the long way home today.",
        "Tip: good days are for exploring. Walk somewhere new and see what follows you.",
    ],
    "ok": [
        "Tip: little and often. That is the whole trick.",
        "Tip: a walk after dinner is the laziest way to hit your goal.",
    ],
}

ASIDES = (
    "(You are, to be clear, talking to a rock.)",
    "(I have been asleep for three hundred years. Take your time.)",
    "(Rocks do not get leg day. We just get moss.)",
    "(I would give you a high five, but I am mostly granite.)",
    "(My cardio is erosion.)",
    "(Moss is my entire skincare routine.)",
    "(Fun fact: I am the strongest one here. I have never moved.)",
)

SYSTEM = """You are Slumbrock, a sleepy stone giant who wakes up a little each time the person you look \
after walks. You are kind, slow, a bit dramatic, and you know you are a rock.
Reply to their message in ONE or TWO short sentences, between twelve and thirty words.
Rules:
- React to what they actually said. Be warm and a little funny.
- Never use digits. Never give medical advice or exercise instructions. Never scold or pressure.
- If they are ill or hurt, be gentle and tell them you will wait.
- energy is how the person feels: low, ok or high.
- body lists body parts they mention, copied from their words (empty if none).
Examples of good lines:
- "Leg day? I felt the ground shake from here. Your legs did the work, so let them be dramatic tonight."
- "A whole walk before breakfast? You woke up a mountain. Well, a medium-sized rock."
- "Oh, a slow day. I have had about four hundred of those. They count too."
Reply with JSON only."""

SCHEMA = {
    "type": "object",
    "properties": {
        "energy": {"type": "string", "enum": ["low", "ok", "high"]},
        "body": {"type": "array", "items": {"type": "string", "maxLength": 20}, "maxItems": 3},
        "line": {"type": "string", "maxLength": 220},
    },
    "required": ["energy", "body", "line"],
}

UPPER = {"shoulder", "shoulders", "arm", "arms", "chest", "elbow", "elbows", "wrist", "wrists", "upper body", "biceps", "triceps", "lats", "traps"}  # fmt: skip
LEGS = {"leg", "legs", "knee", "knees", "calf", "calves", "hamstring", "hamstrings", "quad", "quads", "glutes", "hip", "hips", "lower body"}  # fmt: skip
FEET = {"foot", "feet", "ankle", "ankles"}


def _words(text: str) -> list[str]:
    return re.findall(r"[a-z']+", text.lower())


def _has(text: str, vocab: tuple[str, ...]) -> bool:
    low = text.lower()
    return any(re.search(rf"\b{re.escape(w)}\b", low) for w in vocab)


def _pick(options: list[str] | tuple[str, ...], text: str, salt: str = "") -> str:
    """A stable choice: the same message always gets the same reply, which keeps tests honest."""
    return options[zlib.crc32((salt + text.lower()).encode()) % len(options)]


def is_excused(text: str) -> bool:
    """Illness or injury words, unless negated within the three words before ("not sick")."""
    joined = " ".join(_words(text))
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


# "back" and "head" are everyday words ("walked there and back", "head out"): only count them as body
# parts when the sentence is clearly about the body.
AMBIGUOUS = {
    "back": r"\b(my|lower|upper|sore|stiff|bad|aching)\s+back\b|\bback\s+(is|was|hurts|pain|aches?|feels|stiff|sore|killing)",
    "head": r"\b(my|sore)\s+head\b|\bhead\s*ache|\bheadache",
}


def _mentions(low: str, area: str) -> bool:
    if area in AMBIGUOUS:
        return bool(re.search(AMBIGUOUS[area], low))
    return bool(re.search(rf"\b{re.escape(area)}\b", low))


def keyword_body(text: str) -> list[str]:
    low = text.lower()
    found = [a for a in BODY_AREAS if _mentions(low, a)]
    for pattern, area in EXERCISE_HINTS:
        covered = area in found or (area == "legs" and "leg" in found)
        if re.search(pattern, low) and not covered:
            found.insert(0, area)
    return found[:3]


def clean_line(line: str) -> str:
    """Small models under a schema sometimes run on: cut at a stray closing quote, brace or tag."""
    line = line.strip().strip('"').strip()
    cut = re.search(r"[”“]\s*[}\]]|[{}<>\[\]]", line)
    if cut:
        line = line[: cut.start()]
    return line.strip().strip('“”"').strip()


def line_ok(line: str) -> bool:
    words = line.split()
    return 4 <= len(words) <= 40 and len(line) <= 240 and not re.search(r"\d|https?:|www\.", line)


def tip_for(text: str, energy: Energy, body: list[str], excused: bool) -> str:
    parts = set(body)
    if excused:
        key = "excused"
    elif parts & LEGS:
        key = "legs"
    elif "back" in parts or "neck" in parts:
        key = "back"
    elif parts & FEET:
        key = "feet"
    elif parts & UPPER or parts & {"core", "abs"}:
        key = "upper"
    elif "head" in parts:
        key = "head"
    else:
        key = energy
    return _pick(TIPS[key], text, "tip")


def aside_for(text: str, excused: bool) -> str:
    if excused or zlib.crc32(("aside" + text.lower()).encode()) % 3:
        return ""
    return _pick(ASIDES, text, "which")


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
                [{"role": "system", "content": SYSTEM}, {"role": "user", "content": text}],
                SCHEMA,
                temperature=0.8,
            )
            m_energy = data.get("energy")
            if m_energy in ("low", "ok", "high"):
                energy = m_energy
            m_body = [
                b.strip().lower() for b in data.get("body", []) if isinstance(b, str) and b.strip()
            ]
            kept = [
                b
                for b in m_body
                if b in BODY_AREAS and re.search(rf"\b{re.escape(b)}\b", text.lower())
            ]
            body = list(dict.fromkeys(kept + body))[:3]
            candidate = clean_line(str(data.get("line", "")))
            if line_ok(candidate):
                line, source = candidate, "gemma"
        except LLMError as exc:
            log.warning("check-in model failed: %s", exc)

    if not line:
        line = _pick(TEMPLATES[(excused, energy)], text)
    return Checkin(
        energy=energy,
        body=body,
        excused=excused,
        line=line,
        tip=tip_for(text, energy, body, excused),
        aside=aside_for(text, excused),
        source=source,
    )
