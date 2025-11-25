# src/services/nlu/intent_classifier.py
"""
Zero-shot intent classifier using CamemBERT embeddings + cosine similarity.

NOTE:
- This version uses ENGLISH intent definitions (as requested).
- If your users speak French, accuracy may drop. In practice, best is to keep
  intent definitions in the same language as user input.
"""
from __future__ import annotations

import asyncio
from typing import Dict, Tuple, Optional

import torch
import torch.nn.functional as F
from transformers import CamembertModel, CamembertTokenizer

from src.core.logging import logger


class ZeroShotIntentClassifier:
    def __init__(self) -> None:
        # English intent definitions (as requested)
        self.intent_definitions: Dict[str, str] = {
            "check_balance": "check my bank account balance, show my balance, what is my balance",
            "make_transfer": "make a bank transfer, send money to a beneficiary, transfer money to someone",
            "add_beneficiary": "add a beneficiary, add a new recipient, save a new beneficiary",
            "pay_bill": "pay a bill (orange, eneo, camwater, edf, etc.), pay my utility bill",
            "show_bank_details": "show my bank details, show my IBAN and BIC, display my bank coordinates",
        }

        self.tokenizer: Optional[CamembertTokenizer] = None
        self.model: Optional[CamembertModel] = None
        self._intent_embeddings: Dict[str, torch.Tensor] = {}
        self._is_ready = False

        self.device = "cuda" if torch.cuda.is_available() else "cpu"

    async def initialize(self) -> None:
        if self._is_ready:
            return

        logger.info("Loading CamemBERT for intent classification...")

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._load_sync)

        logger.info("Computing intent embeddings...")
        await loop.run_in_executor(None, self._build_intent_embeddings_sync)

        logger.info("✅ Intent classifier ready with %d intents", len(self.intent_definitions))
        self._is_ready = True

    def _load_sync(self) -> None:
        self.tokenizer = CamembertTokenizer.from_pretrained("camembert-base")
        self.model = CamembertModel.from_pretrained("camembert-base")
        self.model.to(self.device)
        self.model.eval()

    def _encode_sync(self, text: str) -> torch.Tensor:
        """Encode text into one normalized vector using mean pooling."""
        assert self.tokenizer is not None and self.model is not None

        inputs = self.tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            max_length=128,
            padding=True,
        )
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = self.model(**inputs)
            hidden = outputs.last_hidden_state
            mask = inputs["attention_mask"].unsqueeze(-1).expand(hidden.size()).float()
            summed = torch.sum(hidden * mask, dim=1)
            counts = torch.clamp(mask.sum(dim=1), min=1e-9)
            mean_pooled = summed / counts

        emb = mean_pooled[0]
        emb = F.normalize(emb, p=2, dim=0)
        return emb.detach().cpu()

    def _build_intent_embeddings_sync(self) -> None:
        self._intent_embeddings = {}
        for intent, desc in self.intent_definitions.items():
            self._intent_embeddings[intent] = self._encode_sync(desc)

    async def classify(self, text: str) -> Tuple[Optional[str], float]:
        """Return (best_intent, confidence)."""
        if not self._is_ready:
            raise RuntimeError("Intent classifier not initialized")

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._classify_sync, text)

    def _classify_sync(self, text: str) -> Tuple[Optional[str], float]:
        query_emb = self._encode_sync(text)

        best_intent = None
        best_score = -1.0

        for intent, emb in self._intent_embeddings.items():
            score = float(torch.dot(query_emb, emb))
            if score > best_score:
                best_score = score
                best_intent = intent

        # cosine [-1..1] -> map to [0..1]
        confidence = max(0.0, min(1.0, (best_score + 1.0) / 2.0))

        logger.info("Intent: %s (confidence: %.2f)", best_intent, confidence)
        return best_intent, confidence
