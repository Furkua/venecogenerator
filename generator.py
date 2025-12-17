from __future__ import annotations

import random
import re
import unicodedata
from dataclasses import dataclass
from typing import List, Tuple


VOWELS = set("aeiou")
ALPHABET = set("abcdefghijklmnopqrstuvwxyz")


# Morfemas típicos “venecos” (no académicos; estética cultural popular)
VENCO_PREFIXES_M = [
    "yus", "yub", "jhon", "jho", "jh", "jhair", "jha",
    "maik", "mayk", "deiv", "yei", "yon", "yoh", "jei",
    "dai", "day", "key", "kei"
]

VENCO_PREFIXES_H = [
    "jhon", "jho", "jh", "yus", "maik", "mayk", "deiv",
    "jhair", "wil", "and", "bra", "kev", "yon", "yei",
    "dai", "day", "kei", "key"
]

VENCO_SUFFIXES_M = [
    "mar", "mary", "mari", "elis", "elys", "liss", "lis",
    "any", "aney", "eth", "eith", "y", "is", "nys", "dys",
    "a", "ia"
]

VENCO_SUFFIXES_H = [
    "son", "sone", "sen", "el", "iel", "en", "an", "is",
    "air", "er", "eth", "y", "n", "d", "o"
]

VENCO_LINKERS = ["a", "e", "i", "o", "u", "y", "h"]


def _normalize_letters(s: str) -> str:
    s = s.strip()
    s = re.sub(r"\s+", " ", s)
    s = s.replace("-", " ")
    # Solo letras y espacios; preserva ñ si viene escrita
    s = re.sub(r"[^A-Za-zñÑ\s]", "", s)
    return s


def _lower_ascii(s: str) -> str:
    return s.lower()


def _titlecase_name(s: str) -> str:
    if not s:
        return s
    return s[0].upper() + s[1:].lower()


def _strip_accents_keep_enye(s: str) -> str:
    # quita acentos pero mantiene ñ
    out = []
    for ch in s:
        if ch in ("ñ", "Ñ"):
            out.append(ch)
            continue
        decomp = unicodedata.normalize("NFD", ch)
        decomp = "".join(c for c in decomp if unicodedata.category(c) != "Mn")
        out.append(decomp)
    return "".join(out)


def _syllableish_chunks(name: str) -> List[str]:
    """
    Segmentación práctica: ventanas 2-4 + prefijos/sufijos típicos.
    No es silabificación estricta: es ingeniería fonética.
    """
    n = _lower_ascii(_strip_accents_keep_enye(name))
    n = re.sub(r"\s+", "", n)
    if len(n) < 2:
        return [n] if n else []

    chunks = set()

    # prefijos/sufijos 2-4
    for L in (2, 3, 4):
        if len(n) >= L:
            chunks.add(n[:L])
            chunks.add(n[-L:])

    # ventanas internas 2-4
    for L in (2, 3, 4):
        for i in range(1, max(1, len(n) - L)):
            chunks.add(n[i:i + L])

    chunks = {c for c in chunks if c}
    # orden estable: preferir 3-4
    return sorted(chunks, key=lambda x: (abs(len(x) - 3), -len(x), x))


def _join_with_smoothing(parts: List[str], rng: random.Random, mode: str) -> str:
    s = "".join(parts)

    # limpieza
    s = re.sub(r"\s+", "", s)
    s = re.sub(r"[^a-zñ]", "", s)

    def is_vowel(ch: str) -> bool:
        return ch in VOWELS

    # suavizado: evita 3 consonantes seguidas insertando vocal
    out = []
    for ch in s:
        out.append(ch)
        if len(out) >= 3:
            a, b, c = out[-3], out[-2], out[-1]
            if (not is_vowel(a)) and (not is_vowel(b)) and (not is_vowel(c)) and (a != "ñ") and (b != "ñ") and (c != "ñ"):
                out.insert(-1, rng.choice(list(VOWELS)))

    s = "".join(out)

    # reduce repeticiones extremas
    s = re.sub(r"(.)\1\1+", r"\1\1", s)

    if mode == "Normal":
        s = s.replace("hh", "h").replace("yy", "y")
        s = re.sub(r"j+h", "j", s)  # evita jh redundante
        return s

    if mode == "Veneco":
        # agrega “ruido cultural” pero con variedad controlada
        if rng.random() < 0.18:
            pos = rng.randrange(1, len(s))
            s = s[:pos] + "h" + s[pos:]
        if "y" not in s and rng.random() < 0.25:
            pos = rng.randrange(0, len(s))
            s = s[:pos] + "y" + s[pos:]
        # prefijo cultural ocasional, variando (evita monotonear con solo jho)
        if rng.random() < 0.18:
            pref = rng.choice(["jho", "jhon", "jhair", "maik", "yus", "deiv", "mayk"])
            s = pref + s[1:]
        return s

    if mode == "Worst-case":
        prefixes = ["yh", "jh", "nhy", "yhajh", "jha", "yha", "nh"]
        suffixes = ["leth", "air", "eith", "x", "h", "th", "lynth"]
        s = rng.choice(prefixes) + s

        for _ in range(rng.randint(1, 3)):
            pos = rng.randrange(1, len(s))
            s = s[:pos] + rng.choice(["h", "y", "jh"]) + s[pos:]

        s = s + rng.choice(suffixes)

        s = s.replace("qu", "k")
        s = s.replace("c", rng.choice(["k", "s"]))
        return s

    return s


def _gender_endings(gender: str, mode: str) -> List[str]:
    if mode == "Worst-case":
        return ["", "h", "th", "x", "leth"]

    if gender == "M":
        return ["a", "y", "is", "any", "elis", "mar", "lis", "eth", "ia"]
    return ["o", "el", "en", "son", "iel", "is", "any", "mar"]


@dataclass(frozen=True)
class Candidate:
    name: str
    score: float


def _score_name(name: str, gender: str, mode: str) -> float:
    n = name.lower()
    base = 0.0
    length = len(n)

    if mode != "Worst-case":
        if 5 <= length <= 10:
            base += 3.0
        elif 4 <= length <= 12:
            base += 1.5
        else:
            base -= 2.0
    else:
        if length >= 10:
            base += 3.0
        if length >= 14:
            base += 2.0

    if mode != "Worst-case":
        penalties = 0
        for i in range(length - 2):
            tri = n[i:i + 3]
            if all(ch not in VOWELS for ch in tri if ch != "ñ"):
                penalties += 1
        base -= 0.9 * penalties

    cultural = ["yus", "yub", "jhon", "maik", "mayk", "deiv", "jhair", "nath", "mar", "lis", "any", "eth", "yei", "yon"]
    hits = sum(1 for p in cultural if p in n)

    if mode == "Veneco":
        base += 1.2 * hits
        if n.startswith(("yh", "jh", "nh")):
            base += 0.6
    elif mode == "Normal":
        base += 0.4 * hits
        if n.startswith(("yh", "jh", "nh")):
            base -= 1.0
    else:
        base += 1.6 * hits
        if n.startswith(("yh", "jh", "nh")):
            base += 2.0
        if "h" in n:
            base += 1.0
        if n.count("y") >= 1:
            base += 1.0
        if any(x in n for x in ["jh", "yhajh", "nhy"]):
            base += 2.0

    if any(ch not in ALPHABET and ch not in {"ñ"} for ch in n):
        base -= 10.0

    if mode != "Worst-case":
        fem_bias = n.endswith(("a", "y", "is", "any", "eth", "lis", "mar", "elis", "ia"))
        masc_bias = n.endswith(("o", "el", "en", "son", "iel", "is", "any", "mar"))
        if gender == "M" and fem_bias:
            base += 0.5
        if gender == "H" and masc_bias:
            base += 0.5

    return base


def generate_names(
    father: str,
    mother: str,
    gender: str = "M",
    mode: str = "Normal",
    k: int = 3,
    seed: int = 42,
) -> List[str]:
    """
    mode: "Normal" | "Veneco" | "Worst-case"
    gender: "M" (mujer) | "H" (hombre)
    """
    rng = random.Random(seed)

    father = _normalize_letters(father)
    mother = _normalize_letters(mother)

    f_chunks = _syllableish_chunks(father)
    m_chunks = _syllableish_chunks(mother)
    if not f_chunks or not m_chunks:
        return []

    endings = _gender_endings(gender, mode)

    # para k=1..5 no necesitas miles de intentos
    attempts = max(320, k * 90)

    patterns: List[Tuple[int, int, int]] = [
        (1, 1, 0),
        (1, 0, 1),
        (0, 1, 1),
        (1, 1, 1),
    ]

    def pick_prefix(chunks: List[str]) -> str:
        c = chunks[: min(len(chunks), 12)]
        return rng.choice(c)

    def pick_suffix_from_name(name: str) -> str:
        n = _lower_ascii(_strip_accents_keep_enye(name))
        n = re.sub(r"\s+", "", n)
        if len(n) <= 3:
            return n
        L = rng.choice([2, 3, 4])
        return n[-L:]

    # pools venecos por género
    if gender == "M":
        v_prefixes = VENCO_PREFIXES_M
        v_suffixes = VENCO_SUFFIXES_M
    else:
        v_prefixes = VENCO_PREFIXES_H
        v_suffixes = VENCO_SUFFIXES_H

    candidates: dict[str, Candidate] = {}

    f_norm = re.sub(r"\s+", "", _lower_ascii(_strip_accents_keep_enye(father)))
    m_norm = re.sub(r"\s+", "", _lower_ascii(_strip_accents_keep_enye(mother)))

    for _ in range(attempts):
        # Modo Veneco: plantillas + morfemas + familia (sube diversidad real)
        if mode == "Veneco":
            template = rng.choices(
                population=["P+M", "F+S", "P+F+S", "P+M+S", "P+L+M", "F+L+S", "P+F", "M+S", "P+L+F+S"],
                weights=[16, 12, 14, 14, 10, 8, 10, 8, 8],
                k=1
            )[0]

            P = rng.choice(v_prefixes)
            S = rng.choice(v_suffixes)
            L = rng.choice(VENCO_LINKERS)

            F = pick_prefix(f_chunks)
            M = pick_suffix_from_name(mother) if rng.random() < 0.70 else pick_prefix(m_chunks)

            if template == "P+M":
                parts = [P, M]
            elif template == "F+S":
                parts = [F, S]
            elif template == "P+F+S":
                parts = [P, F, S]
            elif template == "P+M+S":
                parts = [P, M, S]
            elif template == "P+L+M":
                parts = [P, L, M]
            elif template == "F+L+S":
                parts = [F, L, S]
            elif template == "P+F":
                parts = [P, F]
            elif template == "P+L+F+S":
                parts = [P, L, F, S]
            else:  # "M+S"
                parts = [M, S]

            name_raw = _join_with_smoothing(parts, rng, mode)

        else:
            use_f, use_m, use_e = rng.choice(patterns)
            parts = []

            if use_f:
                parts.append(pick_prefix(f_chunks))
            if use_m:
                parts.append(pick_suffix_from_name(mother) if rng.random() < 0.6 else pick_prefix(m_chunks))
            if use_e:
                parts.append(rng.choice(endings))

            name_raw = _join_with_smoothing(parts, rng, mode)

        if not name_raw or len(name_raw) < 4:
            continue

        if mode != "Worst-case" and (name_raw == f_norm or name_raw == m_norm):
            continue

        if mode != "Worst-case" and re.search(r"[qxz]{2,}", name_raw):
            continue

        score = _score_name(name_raw, gender, mode)
        key = name_raw
        prev = candidates.get(key)
        if prev is None or score > prev.score:
            candidates[key] = Candidate(name=key, score=score)

    ranked = sorted(candidates.values(), key=lambda c: c.score, reverse=True)
    out = [_titlecase_name(c.name) for c in ranked[:k]]
    return out
