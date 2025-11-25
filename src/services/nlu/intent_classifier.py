# src/services/nlu/intent_classifier.py
"""
Zero-shot intent classifier using CamemBERT embeddings.

- Uses French Camembert to embed both:
  • user utterance
  • short natural-language descriptions of each intent
- Chooses closest intent via cosine similarity
- Applies:
  • global confidence threshold
  • keyword guard per intent (to avoid nonsense mappings)
"""

import asyncio
from typing import Dict, List, Optional, Tuple

import torch
import torch.nn.functional as F
from transformers import CamembertTokenizer, CamembertModel

from src.core.logging import logger


class ZeroShotIntentClassifier:
    """
    Zero-shot intent classifier using CamemBERT embeddings.
    """

    # Minimum similarity to accept an intent at all
    MIN_INTENT_CONFIDENCE: float = 0.75

    # Intent triggers: each intent must match at least one keyword in the text
    INTENT_KEYWORDS: Dict[str, List[str]] = {
        "consulter_solde": [
            "solde",
            "reste",
            "combien il me reste",
            "argent sur mon compte",
            "combien d'argent",
        ],
        "faire_virement": [
            "virement",
            "envoyer",
            "envoyé",
            "envoie",
            "transférer",
            "transfert",
            "faire un virement",
        ],
        "ajouter_beneficiaire": [
            "bénéficiaire",
            "bénéficiaires",
            "ajoute",
            "ajouter",
            "nouveau bénéficiaire",
            "ajoute un bénéficiaire",
        ],
        "payer_facture": [
            "paye",
            "payer",
            "régler",
            "regler",
            "facture",
            "factures",
        ],
        "consulter_rib": [
            "rib",
            "coordonnées bancaires",
            "relevé d'identité bancaire",
            "releve d'identite bancaire",
            "iban",
        ],
    }

    def __init__(self) -> None:
        self.device: str = "cuda" if torch.cuda.is_available() else "cpu"

        self.tokenizer: Optional[CamembertTokenizer] = None
        self.model: Optional[CamembertModel] = None

        # Natural language definitions that describe each intent
        self.intent_definitions: Dict[str, str] = {
            "consulter_solde": "consulter mon solde bancaire",
            "faire_virement": "faire un virement vers un bénéficiaire",
            "ajouter_beneficiaire": "ajouter un nouveau bénéficiaire à mon compte",
            "payer_facture": "payer une facture (orange, eneo, camwater, edf, etc.)",
            "consulter_rib": "consulter ou afficher mon RIB / coordonnées bancaires",
        }

        # List of intent ids (keys)
        self.intents: List[str] = list(self.intent_definitions.keys())

        # Will hold embeddings of each intent description
        self.intent_embeddings: Optional[torch.Tensor] = None

        self._is_ready: bool = False

    async def initialize(self) -> None:
        """
        Load Camembert model and pre-compute intent embeddings.
        Called once on app startup.
        """
        if self._is_ready:
            return

        logger.info("Loading CamemBERT for zero-shot intent classification...")

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._load_model_and_intents)

        logger.info("✅ Zero-shot classifier ready with %s intents", len(self.intents))
        self._is_ready = True

    def _load_model_and_intents(self) -> None:
        """Runs in background thread: load model + embed intent descriptions."""
        # 1) Load tokenizer + model
        self.tokenizer = CamembertTokenizer.from_pretrained("camembert-base")
        self.model = CamembertModel.from_pretrained("camembert-base")
        self.model.to(self.device)
        self.model.eval()

        # 2) Compute embeddings for each intent description
        logger.info("Computing intent embeddings...")

        all_embeddings: List[torch.Tensor] = []
        for intent_id in self.intents:
            definition = self.intent_definitions[intent_id]
            emb = self._encode(definition)
            all_embeddings.append(emb)

        # Shape: (num_intents, hidden_dim)
        self.intent_embeddings = torch.cat(all_embeddings, dim=0)

    def _encode(self, text: str) -> torch.Tensor:
        """
        Encode text into a single embedding vector using Camembert.

        Returns:
            tensor of shape (1, hidden_dim)
        """
        if self.tokenizer is None or self.model is None:
            raise RuntimeError("ZeroShotIntentClassifier not initialized")

        with torch.no_grad():
            encoded = self.tokenizer(
                text,
                return_tensors="pt",
                truncation=True,
                max_length=128,
            )
            encoded = {k: v.to(self.device) for k, v in encoded.items()}
            outputs = self.model(**encoded)
            # Mean pooling over tokens
            token_embeddings = outputs.last_hidden_state  # (1, seq_len, hidden_dim)
            embedding = token_embeddings.mean(dim=1)      # (1, hidden_dim)
        return embedding

    def _similarity(self, text_embedding: torch.Tensor, intent_embeddings: torch.Tensor) -> torch.Tensor:
        """
        Cosine similarity between text embedding and each intent embedding.

        Args:
            text_embedding: (1, hidden_dim)
            intent_embeddings: (num_intents, hidden_dim)

        Returns:
            scores: (num_intents,)
        """
        text_norm = F.normalize(text_embedding, p=2, dim=-1)
        intents_norm = F.normalize(intent_embeddings, p=2, dim=-1)
        scores = torch.matmul(text_norm, intents_norm.T)  # (1, num_intents)
        return scores.squeeze(0)

    def classify(self, text: str) -> Tuple[Optional[str], float]:
        """
        Classify text into one of the known intents.

        Returns:
            (intent_id or None, confidence float in [0,1])

        - If score < MIN_INTENT_CONFIDENCE → returns (None, score)
        - If no trigger keyword for the best intent is found in the text → (None, score)
        """
        if not self._is_ready:
            raise RuntimeError("ZeroShotIntentClassifier not initialized")

        if not text or not text.strip():
            return None, 0.0

        normalized_text = text.lower()

        if self.intent_embeddings is None:
            raise RuntimeError("Intent embeddings not computed")

        # 1) Embed the user text
        text_embedding = self._encode(normalized_text)

        # 2) Compare to each intent embedding
        scores = self._similarity(text_embedding, self.intent_embeddings)
        best_index = int(scores.argmax())
        best_intent = self.intents[best_index]
        best_score = float(scores[best_index])

        # 3) Global confidence gate
        if best_score < self.MIN_INTENT_CONFIDENCE:
            logger.info(
                "Intent score below threshold: %.2f for text: %s",
                best_score,
                text,
            )
            return None, best_score

        # 4) Keyword guard: ensure text contains some typical words for that intent
        keywords = self.INTENT_KEYWORDS.get(best_intent, [])
        if keywords and not any(keyword in normalized_text for keyword in keywords):
            logger.info(
                "Intent %s rejected by keyword check. Text: %s",
                best_intent,
                text,
            )
            return None, best_score

        logger.info(
            "Intent selected: %s (confidence: %.2f) for text: %s",
            best_intent,
            best_score,
            text,
        )
        return best_intent, best_score

    def is_ready(self) -> bool:
        return self._is_ready
