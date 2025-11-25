# src/services/text_processing/cleaner.py
"""
BankingTextCleaner

Lightweight text cleaner for banking NLU:
- Normalizes spaces
- Lowercases text
- Removes common fillers and hesitations
- Keeps numbers, euros, account-related words
"""

from __future__ import annotations

import re
from typing import List

from src.core.logging import logger


class BankingTextCleaner:
    """
    Clean raw ASR (Whisper) text for banking use cases.

    Keep it simple and deterministic:
    - DO NOT try to be too smart or semantic
    - Just remove obvious noise that hurts NLU
    """

    # Common French filler words / hesitations that bring no meaning
    FILLER_WORDS: List[str] = [
        "euh",
        "bah",
        "ben",
        "heu",
        "genre",
        "tu vois",
        "vous voyez",
        "en fait",
        "du coup",
        "voilà",
    ]

    # Extra stuff we want to trim out (like some discourse markers)
    REDUNDANT_PHRASES: List[str] = [
        "s'il te plaît",
        "s'il vous plaît",
        "stp",
        "svp",
        "merci",
        "merci beaucoup",
    ]

    def __init__(self) -> None:
        # Pre-build regex for fillers to make cleaning fast
        if self.FILLER_WORDS:
            filler_pattern = r"\b(" + "|".join(
                re.escape(w) for w in self.FILLER_WORDS
            ) + r")\b"
            self._filler_regex = re.compile(filler_pattern, flags=re.IGNORECASE)
        else:
            self._filler_regex = None

        if self.REDUNDANT_PHRASES:
            phrases_pattern = r"\b(" + "|".join(
                re.escape(w) for w in self.REDUNDANT_PHRASES
            ) + r")\b"
            self._phrases_regex = re.compile(phrases_pattern, flags=re.IGNORECASE)
        else:
            self._phrases_regex = None

    def clean(self, text: str) -> str:
        """
        Main cleaning entrypoint.

        Steps:
        1. Strip/normalize whitespace
        2. Lowercase
        3. Remove fillers & redundant polite phrases
        4. Normalize spaces again
        """
        if not text:
            return ""

        original = text
        logger.info(f"🔤 Raw text before cleaning: {original}")

        # Normalize whitespace & strip
        cleaned = text.strip()
        cleaned = re.sub(r"\s+", " ", cleaned)

        # Lowercase for NLU
        cleaned = cleaned.lower()

        # Remove fillers
        if self._filler_regex is not None:
            cleaned = self._filler_regex.sub(" ", cleaned)

        # Remove redundant polite phrases
        if self._phrases_regex is not None:
            cleaned = self._phrases_regex.sub(" ", cleaned)

        # Normalize special characters (keep € and digits, allow accents & letters)
        # Here we mostly remove weird punctuation duplicates
        cleaned = cleaned.replace("€", " euros ")
        cleaned = re.sub(r"[!?]+", " ", cleaned)

        # Collapse spaces again
        cleaned = re.sub(r"\s+", " ", cleaned).strip()

        logger.info(f"🧹 Text after cleaning: {cleaned}")
        return cleaned
