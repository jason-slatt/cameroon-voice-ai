# app/utils/lang.py

import re

def detect_language(text: str) -> str:
    """
    Very simple EN/FR heuristic.
    Returns 'fr' if it sees obvious French words or accents, else 'en'.
    """
    if not text:
        return "en"

    text_lower = text.lower()

    french_markers = [
        "bonjour", "salut", "merci",
        "compte", "solde", "retrait", "dépôt", "depot", "déposer",
        "historique", "transactions", "voir mes", "introuvable",
    ]

    for word in french_markers:
        if word in text_lower:
            return "fr"

    if re.search(r"[àâçéèêëîïôûùüÿñæœ]", text_lower):
        return "fr"

    return "en"