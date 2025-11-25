# src/services/nlu/entity_extractor.py
"""
Rule-based entity extraction using regex and patterns
Optimized for French + EUR / FCFA banking expressions
"""

import re
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta

from src.core.logging import logger


class BankingEntityExtractor:
    """Extract banking entities using rules and patterns"""

    # Common facture names you care about (can extend)
    FACTURE_PROVIDERS = [
        "orange",
        "eneo",
        "camwater",
        "edf",
        "canal",
        "canal+",
        "canal plus",
    ]

    PATTERNS: Dict[str, List[str]] = {
        "montant": [
            # 10, 10.5, 10 000, 10 000,50 euros
            r"(\d[\d\s]*(?:[,\.]\d+)?)\s*(?:euros?|eur|€)",
            # 10 000 francs, 10 000 fcfa, 10 000 f cfa, 10 000 F
            r"(\d[\d\s]*(?:[,\.]\d+)?)\s*(?:francs?|fcfa|f\s*cfa|xaf|xof|f\b)",
            # bare number followed by 'pour', 'à', 'vers', 'chez' (e.g. paie 1000 pour orange)
            r"(\d[\d\s]*(?:[,\.]\d+)?)\s+(?=pour|à|vers|chez)",
        ],
        "devise": [
            r"\b(eur|euros?|€)\b",
            r"\b(fcfa|f\s*cfa|francs?|xaf|xof)\b",
            r"\b(usd|dollars?|\$)\b",
        ],
        "destinataire": [
            # à Paul, à Marie Dupont, pour David
            r"(?:à|pour|vers)\s+([A-ZÀ-Ÿ][a-zà-ÿ]+(?:\s+[A-ZÀ-Ÿ][a-zà-ÿ]+)?)",
            r"bénéficiaire\s+([A-ZÀ-Ÿ][a-zà-ÿ]+(?:\s+[A-ZÀ-Ÿ][a-zà-ÿ]+)?)",
        ],
        "iban": [
            r"\b(FR\d{2}\s?\d{4}\s?\d{4}\s?\d{4}\s?\d{4}\s?\d{4}\s?\d{3})\b",
            r"\b(FR\d{25})\b",
        ],
        "date": [
            r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b",
            r"\b(aujourd'hui|demain|hier)\b",
        ],
        "compte": [
            r"compte\s+(courant|épargne|joint)",
            r"(compte\s+courant|compte\s+épargne)",
        ],
        "facture": [
            # facture orange, facture edf, etc.
            r"facture\s+([a-zA-ZÀ-ÿ\+ ]+)",
        ],
        "numero_carte": [
            r"\b(\d{4}\s?\d{4}\s?\d{4}\s?\d{4})\b",
        ],
    }

    def extract(self, text: str) -> Dict[str, object]:
        """
        Extract all entities from text

        Args:
            text: Cleaned input text (lowercased, no weird chars)

        Returns:
            Dict of entities {entity_type: value}
        """
        entities: Dict[str, object] = {}

        # --- Regex-based extraction ---
        for entity_type, patterns in self.PATTERNS.items():
            value = self._extract_entity(text, patterns, entity_type)
            if value:
                entities[entity_type] = value

        # --- Fuzzy facture provider detection (Orange, Eneo...) ---
        facture_from_text = self._detect_facture_provider(text)
        if facture_from_text and "facture" not in entities:
            entities["facture"] = facture_from_text

        normalized_entities = self._normalize_entities(entities)

        logger.info("Extracted entities: %s", normalized_entities)
        return normalized_entities

    def _extract_entity(
        self,
        text: str,
        patterns: List[str],
        entity_type: str,
    ) -> Optional[object]:
        """Extract single entity type using patterns"""
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                if match.lastindex:
                    return match.group(1).strip()
                return match.group(0).strip()
        return None

    def _detect_facture_provider(self, text: str) -> Optional[str]:
        """
        Try to detect facture provider name in raw text, e.g. 'orange', 'eneo', 'camwater'.
        """
        lowered = text.lower()
        for provider in self.FACTURE_PROVIDERS:
            # accept variations like 'canal plus', 'canal+'
            if provider in lowered:
                # Normalize to uppercase key (e.g. ORANGE, ENEO)
                return provider.replace(" ", "").replace("+", "PLUS").upper()
        return None

    def _normalize_entities(self, entities: Dict[str, object]) -> Dict[str, object]:
        """Normalize extracted entities to standard format"""
        normalized: Dict[str, object] = {}

        # ----- montant -----
        if "montant" in entities:
            amount_str = (
                str(entities["montant"])
                .replace(" ", "")
                .replace("\u00a0", "")  # non-breaking spaces
                .replace(",", ".")
            )
            try:
                normalized["montant"] = float(amount_str)
            except ValueError:
                logger.warning("Unable to parse amount: %s", amount_str)

        # ----- devise -----
        if "devise" in entities:
            devise = str(entities["devise"]).lower()
            if "eur" in devise or "euro" in devise or "€" in devise:
                normalized["devise"] = "EUR"
            elif (
                "fcfa" in devise
                or "franc" in devise
                or "xaf" in devise
                or "xof" in devise
                or devise == "f"
            ):
                # You can choose XAF or XOF depending on your bank region
                normalized["devise"] = "XAF"
            elif "usd" in devise or "dollar" in devise or "$" in devise:
                normalized["devise"] = "USD"
        else:
            # If there is a montant but no detected currency,
            # assume FCFA by default for Cameroon
            if "montant" in normalized:
                normalized["devise"] = "XAF"

        # ----- destinataire -----
        if "destinataire" in entities:
            normalized["destinataire"] = str(entities["destinataire"]).title()

        # ----- iban -----
        if "iban" in entities:
            normalized["iban"] = str(entities["iban"]).replace(" ", "").upper()

        # ----- date -----
        if "date" in entities:
            normalized["date"] = self._parse_date(str(entities["date"]))

        # ----- simple passthrough fields -----
        for key in ("compte", "facture", "numero_carte"):
            if key in entities:
                normalized[key] = entities[key]

        return normalized

    def _parse_date(self, date_str: str) -> str:
        """Parse date to ISO format"""
        lowered = date_str.lower()

        if "aujourd'hui" in lowered:
            return datetime.now().strftime("%Y-%m-%d")
        if "demain" in lowered:
            return (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        if "hier" in lowered:
            return (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

        for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y"):
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                continue

        return date_str

    def validate_entities(
        self,
        intent: str,
        entities: Dict[str, object],
    ) -> Tuple[bool, List[str]]:
        """
        Check if all required entities are present for intent

        Returns:
            (is_valid, missing_entities)
        """
        required_entities: Dict[str, List[str]] = {
            "faire_virement": ["montant", "destinataire"],
            "consulter_solde": [],
            "bloquer_carte": [],
            "ajouter_beneficiaire": ["destinataire"],
            "historique_transactions": [],
            "consulter_rib": [],
            "payer_facture": ["montant", "facture"],
            "changer_plafond": ["montant"],
        }

        required = required_entities.get(intent, [])
        missing = [name for name in required if name not in entities]

        return len(missing) == 0, missing
