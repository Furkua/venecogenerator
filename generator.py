from __future__ import annotations

import random
import re
import unicodedata
from dataclasses import dataclass
from typing import List, Tuple


VOWELS = set("aeiou")
ALPHABET = set("abcdefghijklmnopqrstuvwxyz")


def _normalize_letters(s: str) -> str:
    s = s.strip()
    s = re.sub(r"\s+", " ", s)
    s = s.replace("-", " ")
    # Solo letras y espacios; preserva ñ si viene escrita
    s = re.sub(r"[^A-Za-zñÑ\s]", "", s)
    return s


def _lower_ascii(s: str) -> str:
    # conserva ñ como ñ si viene; luego lo dejamos en unicode normal
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
    Segmentación simple: ventanas 2-4 + prefijos/sufijos típicos.
    No es silabificación lingüística estricta; es ingeniería fonética práctica.
    """
    n = _lower_ascii(_strip_accents_keep_enye(name))
    n = re.sub(r"\s+", "", n)
    if len(n) < 3:
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

    # recortes que suelen funcionar bien
    if len(n) >= 5:
        chunks.add(n[:3])
        chunks.add(n[:4])
        chunks.add(n[-3:])
        chunks.add(n[-4:])

    # limpia vacíos
    chunks = {c for c in chunks if c}
    # orden estable por "calidad": preferir 3-4 letras
    return sorted(chunks, key=lambda x: (abs(len(x) - 3), -len(x), x))


def _join_with_smoothing(parts: List[str], rng: random.Random, mode: str) -> str:
    """
    Une piezas evitando triples consonantes, y aplica 'estética' por modo.
    """
    s = "".join(parts)

    # limpieza básica
    s = re.sub(r"\s+", "", s)
    s = re.sub(r"[^a-zñ]", "", s)

    # suavizado: evitar 3 consonantes seguidas
    def is_vowel(ch: str) -> bool:
        return ch in VOWELS

    out = []
    for ch in s:
        out.append(ch)
        if len(out) >= 3:
            a, b, c = out[-3], out[-2], out[-1]
            if (not is_vowel(a)) and (not is_vowel(b)) and (not is_vowel(c)):
                # inserta vocal puente
                out.insert(-1, rng.choice(list(VOWELS)))

    s = "".join(out)

    # reduce repeticiones extremas
    s = re.sub(r"(.)\1\1+", r"\1\1", s)

    if mode == "Normal":
        # Normal: nombres más "legibles"
        s = s.replace("hh", "h")
        s = s.replace("yy", "y")
        s = re.sub(r"j+h", "j", s)  # evita jh redundante
        return s

    if mode == "Veneco":
        # Veneco: marca cultural (jhon/maik/yus/jhair), pero sin diacríticos raros
        # Inserta 'h' estratégica para complicar un poco, no tanto
        if rng.random() < 0.25:
            pos = rng.randrange(1, len(s))
            s = s[:pos] + "h" + s[pos:]
        # Aumenta probabilidad de y
        if "y" not in s and rng.random() < 0.40:
            pos = rng.randrange(0, len(s))
            s = s[:pos] + "y" + s[pos:]
        # Estilo "jho" ocasional
        if rng.random() < 0.20:
            s = "jho" + s[1:]
        return s

    if mode == "Worst-case":
        # Worst-case: maximiza fricción fuera de Venezuela:
        # - prefijos raros yh/jh/nh
        # - mezcla y+h
        # - terminaciones confusas
        prefixes = ["yh", "jh", "nhy", "yhajh", "jha", "yha", "nh"]
        suffixes = ["leth", "air", "eith", "x", "h", "th", "lynth"]
        s = rng.choice(prefixes) + s

        # Inserta combinaciones disruptivas
        for _ in range(rng.randint(1, 3)):
            pos = rng.randrange(1, len(s))
            s = s[:pos] + rng.choice(["h", "y", "jh"]) + s[pos:]

        # termina raro
        s = s + rng.choice(suffixes)

        # fuerza ambigüedad en pronunciación
        s = s.replace("qu", "k")
        s = s.replace("c", rng.choice(["k", "s"]))

        # aún sin acentos para que pase sistemas, pero igual sea “infierno” ortográfico
        return s

    return s


def _gender_endings(gender: str, mode: str) -> List[str]:
    # terminaciones típicas; en worst-case se ignora o se usa para confundir
    if mode == "Worst-case":
        return ["", "h", "th", "x", "leth"]

    if gender == "M":
        return ["a", "y", "is", "any", "elis", "mar", "lis", "eth"]
    return ["o", "el", "en", "son", "iel", "is", "any", "mar"]


@dataclass(frozen=True)
class Candidate:
    name: str
    score: float


def _score_name(name: str, gender: str, mode: str) -> float:
    """
    Score heurístico: no 'verdad lingüística', sino probabilidad de 'se siente del estilo'.
    En worst-case, el score premia fricción.
    """
    n = name.lower()
    base = 0.0

    length = len(n)
    if mode != "Worst-case":
        # rango sano
        if 5 <= length <= 9:
            base += 3.0
        elif 4 <= length <= 11:
            base += 1.5
        else:
            base -= 2.0
    else:
        # worst-case: que sea largo y difícil
        if length >= 10:
            base += 3.0
        if length >= 14:
            base += 2.0

    # alternancia consonante-vocal (más pronunciable)
    if mode != "Worst-case":
        penalties = 0
        for i in range(length - 2):
            tri = n[i:i+3]
            if all(ch not in VOWELS for ch in tri if ch != "ñ"):
                penalties += 1
        base -= 1.0 * penalties

    # patrones culturales
    cultural = ["yus", "yub", "jhon", "maik", "deiv", "jhair", "nath", "mar", "lis", "any", "eth"]
    hits = sum(1 for p in cultural if p in n)
    if mode == "Veneco":
        base += 1.0 * hits
        if n.startswith(("yh", "jh", "nh")):
            base += 0.5
    elif mode == "Normal":
        base += 0.5 * hits
        if n.startswith(("yh", "jh", "nh")):
            base -= 1.0
    else:
        # worst-case: premia lo "malo"
        base += 1.5 * hits
        if n.startswith(("yh", "jh", "nh")):
            base += 2.0
        if "h" in n:
            base += 1.0
        if n.count("y") >= 1:
            base += 1.0
        if any(x in n for x in ["jh", "yhajh", "nhy"]):
            base += 2.0

    # penaliza caracteres fuera de set esperado (por si algo se cuela)
    if any(ch not in ALPHABET and ch not in {"ñ"} for ch in n):
        base -= 10.0

    # ligero sesgo por género solo en modos no destructivos
    if mode != "Worst-case":
        fem_bias = n.endswith(("a", "y", "is", "any", "eth", "lis", "mar", "elis"))
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
    k: int = 20,
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

    # patrones de combinación
    patterns: List[Tuple[int, int, int]] = [
        (1, 1, 0),  # pref padre + suf madre
        (1, 0, 1),  # pref padre + ending
        (0, 1, 1),  # madre + ending
        (1, 1, 1),  # padre + madre + ending
    ]

    # helpers para elegir pref/suf “probables”
    def pick_prefix(chunks: List[str]) -> str:
        # favorece 3-4 letras iniciales
        c = chunks[: min(len(chunks), 10)]
        return rng.choice(c)

    def pick_suffix_from_name(name: str) -> str:
        n = _lower_ascii(_strip_accents_keep_enye(name))
        n = re.sub(r"\s+", "", n)
        if len(n) <= 3:
            return n
        L = rng.choice([2, 3, 4])
        return n[-L:]

    candidates = {}
    attempts = max(1500, k * 200)

    for _ in range(attempts):
        use_f, use_m, use_e = rng.choice(patterns)

        parts = []

        if use_f:
            parts.append(pick_prefix(f_chunks))
        if use_m:
            # usar sufijo real de la madre para simular casos tipo Gerardo+Maria -> Gerimar
            parts.append(pick_suffix_from_name(mother) if rng.random() < 0.6 else pick_prefix(m_chunks))
        if use_e:
            parts.append(rng.choice(endings))

        name_raw = _join_with_smoothing(parts, rng, mode)

        # filtros de legibilidad
        if not name_raw:
            continue
        if len(name_raw) < 4:
            continue

        # evita que sea igual al padre/madre normalizados (en modos no destructivos)
        f_norm = re.sub(r"\s+", "", _lower_ascii(_strip_accents_keep_enye(father)))
        m_norm = re.sub(r"\s+", "", _lower_ascii(_strip_accents_keep_enye(mother)))
        if mode != "Worst-case" and (name_raw == f_norm or name_raw == m_norm):
            continue

        # evitar cadenas demasiado “basura” en Normal/Veneco
        if mode != "Worst-case":
            if re.search(r"[qxz]{2,}", name_raw):
                continue

        score = _score_name(name_raw, gender, mode)
        key = name_raw
        if key not in candidates or score > candidates[key].score:
            candidates[key] = Candidate(name=key, score=score)

    ranked = sorted(candidates.values(), key=lambda c: c.score, reverse=True)
    out = [_titlecase_name(c.name) for c in ranked[:k]]
    return out
