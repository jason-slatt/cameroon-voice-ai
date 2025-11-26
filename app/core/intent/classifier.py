"""Intent classification for customer support queries"""

from enum import Enum
from typing import Tuple
import re

from app.config import settings


class Intent(Enum):
    ACCOUNT_CREATION = "account_creation"
    VIEW_ACCOUNT = "view_account"  # NEW
    WITHDRAWAL = "withdrawal"
    TOPUP = "topup"
    BALANCE_INQUIRY = "balance_inquiry"
    TRANSACTION_HISTORY = "transaction_history"
    GREETING = "greeting"
    GOODBYE = "goodbye"
    GENERAL_SUPPORT = "general_support"
    CONFIRMATION = "confirmation"
    DENIAL = "denial"
    OFF_TOPIC = "off_topic"
    TRANSFER = "transfer"


class IntentClassifier:
    """Classifies user intent for customer support interactions."""
    
    def __init__(self):
        self.intent_patterns = {
            Intent.ACCOUNT_CREATION: {
                'keywords': [
                    'create', 'open', 'new', 'register', 'sign up', 'signup',
                    'setup', 'set up', 'make', 'start', 'begin'
                ],
                'context': ['account', 'profile', 'registration', 'member'],
                'phrases': [
                    'create account', 'open account', 'new account',
                    'sign up', 'register', 'want account', 'need account',
                    'get account', 'make account', 'start account',
                    'create an account', 'open an account', 'i want to register','i would like to create an account' 
                ]
            },
            Intent.VIEW_ACCOUNT: {  # NEW
                'keywords': [
                    'view', 'show', 'see', 'check', 'display', 'look',
                    'my account', 'account info', 'account details', 'profile'
                ],
                'context': ['account', 'profile', 'info', 'information', 'details', 'my'],
                'phrases': [
                    'view account', 'show account', 'my account', 'account details',
                    'account info', 'account information', 'see my account',
                    'check my account', 'view my profile', 'show my profile',
                    'what is my account', 'display account', 'account status', 'View my details'
                ]
            },
            Intent.WITHDRAWAL: {
                'keywords': [
                    'withdraw', 'withdrawal', 'take out', 'cash out',
                    'pull out', 'get money', 'remove', 'transfer out', 'retrait'
                ],
                'context': ['money', 'cash', 'funds', 'amount', 'xaf', 'fcfa'],
                'phrases': [
                    'withdraw money', 'make withdrawal', 'cash out',
                    'take out money', 'get my money', 'withdraw funds',
                    'make a withdrawal', 'want to withdraw', 'i want to withdraw'
                ]
            },
            Intent.TOPUP: {
                'keywords': [
                    'top up', 'topup', 'top-up', 'deposit', 'add', 'load',
                    'fund', 'put in', 'transfer in', 'recharge', 'credit', 'depot'
                ],
                'context': ['money', 'funds', 'balance', 'account', 'cash', 'amount', 'xaf', 'fcfa'],
                'phrases': [
                    'add money', 'deposit money', 'top up', 'top-up', 'topup',
                    'add funds', 'load money', 'put money', 'fund account',
                    'add to balance', 'make a deposit', 'want to deposit',
                    'i want to deposit', 'i want to top up', 'recharge account'
                ]
            },
            Intent.BALANCE_INQUIRY: {
                'keywords': [
                    'balance', 'how much', 'check', 'available',
                    'status', 'amount', 'total', 'solde'
                ],
                'context': ['account', 'money', 'have', 'funds', 'my'],
                'phrases': [
                    'check balance', 'my balance', 'account balance',
                    'how much money', 'how much do i have', 'available balance',
                    'what is my balance', 'show balance', 'check my balance',
                    'what do i have', 'my account balance'
                ]
            },
            Intent.TRANSACTION_HISTORY: {
                'keywords': [
                    'history', 'transactions', 'statement', 'activity',
                    'records', 'past', 'previous', 'recent', 'historique'
                ],
                'context': ['transaction', 'payment', 'transfer', 'account'],
                'phrases': [
                    'transaction history', 'my transactions', 'past transactions',
                    'recent activity', 'account history', 'show transactions',
                    'view history', 'statement', 'my history', 'show history',
                    'get transactions', 'voir mes transactions', 'historique de transactions'
                ]
            },
            Intent.GREETING: {
                'keywords': [
                    'hello', 'hi', 'hey', 'good morning', 'good afternoon',
                    'good evening', 'greetings', 'howdy', 'bonjour', 'salut'
                ],
                'context': [],
                'phrases': ['hello there', 'hi there', 'hey there']
            },
            Intent.GOODBYE: {
                'keywords': [
                    'bye', 'goodbye', 'see you', 'thanks', 'thank you',
                    'done', 'exit', 'quit', 'finished', 'merci', 'au revoir'
                ],
                'context': [],
                'phrases': [
                    'thank you', 'thanks bye', 'goodbye', 'that is all',
                    'i\'m done', 'no more', 'nothing else', 'that\'s all'
                ]
            },
            Intent.CONFIRMATION: {
                'keywords': [
                    'yes', 'yeah', 'yep', 'correct', 'confirm', 'sure',
                    'ok', 'okay', 'right', 'exactly', 'affirmative',
                    'proceed', 'oui', 'ouais'
                ],
                'context': [],
                'phrases': ['that\'s right', 'that is correct', 'go ahead', 'sounds good']
            },
            Intent.DENIAL: {
                'keywords': [
                    'no', 'nope', 'cancel', 'stop', 'wrong', 'incorrect',
                    'nevermind', 'never mind', 'forget it', 'non'
                ],
                'context': [],
                'phrases': ['no thanks', 'cancel that', 'forget it', 'not right']
            },
            Intent.TRANSFER: {
                "keywords": [
                    "send", "send money", "transfer", "send cash", "pay",
                    "payer", "envoyer", "envoyer de l'argent", "transfert",
                    "remit", "remittance", "p2p"
                ],
                "context": [
                    "money", "cash", "funds", "amount", "xaf", "fcfa",
                    "to", "someone", "phone", "number", "wallet", "account",
                    "a", "à", "au", "vers", "numero", "numéro", "telephone", "téléphone"
                ],
                "phrases": [
                    "transfer money", "send money", "send funds",
                    "make a transfer", "do a transfer", "i want to transfer",
                    "i want to send money", "send money to", "transfer to",
                    "envoyer de l'argent", "faire un transfert",
                    "je veux envoyer", "je veux faire un transfert",
                    "transférer de l'argent", "envoi d'argent"
                ]
            },

        }
        
        self.blocked_phrases = [
            'weather', 'forecast', 'temperature', 'joke', 'funny',
            'story', 'recipe', 'movie', 'music', 'song', 'game',
            'president', 'politics', 'write code', 'programming',
            'homework', 'essay', 'translate'
        ]
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for matching"""
        text = text.lower().strip()
        text = text.replace('-', ' ')
        text = re.sub(r'\s+', ' ', text)
        return text
    
    def classify(self, text: str) -> Tuple[Intent, float]:
        """
        Classify user intent from text.
        
        Args:
            text: User input text
            
        Returns:
            Tuple of (Intent, confidence_score)
        """
        if not text or not text.strip():
            return Intent.GENERAL_SUPPORT, 0.0
        
        text_normalized = self._normalize_text(text)
        
        # Check blocked phrases
        for phrase in self.blocked_phrases:
            if phrase in text_normalized:
                return Intent.OFF_TOPIC, 0.9
        
        # Score each intent
        scores = {}
        
        for intent, patterns in self.intent_patterns.items():
            score = 0.0
            
            # Check phrases (highest weight)
            for phrase in patterns.get('phrases', []):
                phrase_normalized = self._normalize_text(phrase)
                if phrase_normalized in text_normalized:
                    score += 0.8
                    break
            
            # Check keywords
            keyword_found = False
            for keyword in patterns.get('keywords', []):
                keyword_normalized = self._normalize_text(keyword)
                if keyword_normalized in text_normalized:
                    score += 0.5
                    keyword_found = True
                    break
            
            # Check context
            context_words = patterns.get('context', [])
            if context_words:
                for ctx in context_words:
                    if ctx in text_normalized:
                        score += 0.2
                        break
            
            # Boost for short inputs with keyword match
            if keyword_found and len(text_normalized.split()) <= 2:
                score += 0.3
            
            scores[intent] = min(score, 1.0)
        
        # Find best match
        if scores:
            best_intent = max(scores, key=scores.get)
            best_score = scores[best_intent]
            
            if best_score >= 0.4:
                return best_intent, best_score
        
        return Intent.GENERAL_SUPPORT, 0.5