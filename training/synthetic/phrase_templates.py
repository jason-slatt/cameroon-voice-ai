# training/synthetic/phrase_templates.py
"""
Generate synthetic French banking phrases for training
"""
from typing import List, Dict
import random


class BankingPhraseGenerator:
    """Generate realistic French banking voice commands"""
    
    # Intent templates with variations
    TEMPLATES = {
        "faire_virement": [
            "transfère {montant} {devise} à {destinataire}",
            "envoie {montant} {devise} vers {destinataire}",
            "fais un virement de {montant} {devise} pour {destinataire}",
            "je veux transférer {montant} {devise} à {destinataire}",
            "peux-tu envoyer {montant} {devise} à {destinataire}",
            "virement de {montant} {devise} vers le compte de {destinataire}",
            "je souhaite faire un virement de {montant} {devise} à {destinataire}",
            "transfert {montant} {devise} à {destinataire}",
        ],
        
        "consulter_solde": [
            "quel est mon solde",
            "combien j'ai sur mon compte",
            "montre-moi mon solde",
            "solde de mon compte",
            "je veux connaître mon solde",
            "affiche mon solde",
            "combien d'argent j'ai",
            "balance de mon compte",
        ],
        
        "bloquer_carte": [
            "bloque ma carte",
            "je veux bloquer ma carte bleue",
            "désactive ma carte bancaire",
            "opposition sur ma carte",
            "j'ai perdu ma carte, bloque-la",
            "ma carte a été volée, bloque-la",
            "bloque ma carte de crédit",
            "désactive ma carte s'il te plaît",
        ],
        
        "ajouter_beneficiaire": [
            "ajoute {destinataire} comme bénéficiaire",
            "enregistre {destinataire} dans mes bénéficiaires",
            "nouveau bénéficiaire {destinataire}",
            "je veux ajouter {destinataire} à mes contacts",
            "crée un bénéficiaire pour {destinataire}",
        ],
        
        "historique_transactions": [
            "montre mes dernières transactions",
            "historique de mon compte",
            "quelles sont mes dernières opérations",
            "affiche mes transactions",
            "liste mes virements",
            "mes opérations récentes",
        ],
        
        "consulter_rib": [
            "donne-moi mon RIB",
            "quel est mon IBAN",
            "je veux mon RIB",
            "affiche mon IBAN",
            "mes coordonnées bancaires",
            "envoie-moi mon RIB",
        ],
    }
    
    # Entity values
    AMOUNTS = [10, 20, 50, 100, 150, 200, 250, 500, 1000, 1500, 2000, 5000]
    CURRENCIES = ["euros", "EUR"]
    BENEFICIARIES = [
        "Paul", "Marie", "Jean", "Sophie", "Pierre", "Julie",
        "Marc", "Emma", "Lucas", "Chloé", "Thomas", "Léa",
        "Nicolas", "Sarah", "Antoine", "Camille"
    ]
    
    # Filler words (to add realism)
    FILLERS = ["euh", "alors", "donc", "ben", "voilà", ""]
    
    # Politeness markers
    POLITENESS = ["s'il te plaît", "s'il vous plaît", "merci", ""]
    
    def generate_samples(self, n_per_intent: int = 100) -> List[Dict]:
        """
        Generate synthetic banking phrases
        
        Args:
            n_per_intent: Number of samples per intent
            
        Returns:
            List of {text, intent, entities}
        """
        samples = []
        
        for intent, templates in self.TEMPLATES.items():
            for _ in range(n_per_intent):
                template = random.choice(templates)
                
                # Fill placeholders
                text = template
                entities = {}
                
                if "{montant}" in template:
                    amount = random.choice(self.AMOUNTS)
                    entities["montant"] = amount
                    text = text.replace("{montant}", str(amount))
                
                if "{devise}" in template:
                    currency = random.choice(self.CURRENCIES)
                    entities["devise"] = currency
                    text = text.replace("{devise}", currency)
                
                if "{destinataire}" in template:
                    beneficiary = random.choice(self.BENEFICIARIES)
                    entities["destinataire"] = beneficiary
                    text = text.replace("{destinataire}", beneficiary)
                
                # Add realism
                if random.random() < 0.3:  # 30% chance
                    filler = random.choice(self.FILLERS)
                    if filler:
                        text = f"{filler} {text}"
                
                if random.random() < 0.2:  # 20% chance
                    politeness = random.choice(self.POLITENESS)
                    if politeness:
                        text = f"{text} {politeness}"
                
                samples.append({
                    "text": text,
                    "intent": intent,
                    "entities": entities,
                })
        
        return samples
    
    def generate_ner_bio_tags(self, text: str, entities: Dict) -> List[tuple]:
        """
        Generate BIO tags for NER training
        
        Returns:
            [(word, tag), (word, tag), ...]
        """
        words = text.split()
        tags = []
        
        for word in words:
            tag = "O"  # Outside (default)
            
            # Check if word is part of an entity
            for entity_type, entity_value in entities.items():
                entity_str = str(entity_value).lower()
                word_lower = word.lower()
                
                if entity_str in word_lower or word_lower in entity_str:
                    # Determine if B (begin) or I (inside)
                    entity_words = entity_str.split()
                    if len(entity_words) > 1 and word_lower == entity_words[0]:
                        tag = f"B-{entity_type.upper()}"
                    elif len(entity_words) > 1:
                        tag = f"I-{entity_type.upper()}"
                    else:
                        tag = f"B-{entity_type.upper()}"
                    break
            
            tags.append((word, tag))
        
        return tags


# Usage
if __name__ == "__main__":
    generator = BankingPhraseGenerator()
    
    # Generate 600 samples (100 per intent)
    samples = generator.generate_samples(n_per_intent=100)
    
    print(f"Generated {len(samples)} samples")
    print("\nExample samples:")
    for sample in samples[:5]:
        print(f"\nIntent: {sample['intent']}")
        print(f"Text: {sample['text']}")
        print(f"Entities: {sample['entities']}")
        
        # Show BIO tags
        bio_tags = generator.generate_ner_bio_tags(
            sample['text'],
            sample['entities']
        )
        print(f"BIO: {bio_tags[:10]}...")