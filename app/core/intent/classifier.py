"""Intent classification for customer support queries"""

from enum import Enum
from typing import Tuple
import re


class Intent(Enum):
    ACCOUNT_CREATION = "account_creation"
    VIEW_ACCOUNT = "view_account"
    WITHDRAWAL = "withdrawal"
    TOPUP = "topup"
    TRANSFER = "transfer"
    BALANCE_INQUIRY = "balance_inquiry"
    TRANSACTION_HISTORY = "transaction_history"
    DASHBOARD = "dashboard"
    PASSWORD_RESET = "password_reset"      # NEW
    PASSWORD_CHANGE = "password_change"    # NEW
    WHATSAPP_LINK = "whatsapp_link"        # NEW
    GREETING = "greeting"
    GOODBYE = "goodbye"
    GENERAL_SUPPORT = "general_support"
    CONFIRMATION = "confirmation"
    DENIAL = "denial"
    OFF_TOPIC = "off_topic"


class IntentClassifier:
    """Classifies user intent for customer support interactions."""

    def __init__(self):
        self.intent_patterns = {
            Intent.ACCOUNT_CREATION: {
                "keywords": [
                    # EN
                    "create", "open", "new", "register", "sign up", "signup",
                    "set up", "setup", "make", "start", "begin", "join",
                    "enroll", "enrol", "create profile", "register me",
                    # FR
                    "créer", "ouvrir", "inscription", "inscrire", "s'inscrire",
                    "enregistrer", "crée", "ouvre", "nouveau", "nouvelle",
                    "creer", "ouvrir un compte", "creer un compte",
                ],
                "context": [
                    "account", "profile", "registration", "member", "compte",
                    "adhésion", "membre", "profil", "inscription",
                ],
                "phrases": [
                    # EN
                    "create account", "open account", "new account",
                    "sign up", "register", "want an account", "need an account",
                    "get an account", "make an account", "start an account",
                    "create an account", "open an account", "i want to register",
                    "i want to create an account", "help me create an account",
                    # FR
                    "créer un compte", "ouvrir un compte", "je veux créer un compte",
                    "je veux ouvrir un compte", "aide moi à créer un compte",
                    "je veux m'inscrire", "inscris moi", "je veux un compte",
                    "creer un compte", "ouvrir un compte",
                ],
            },

            Intent.VIEW_ACCOUNT: {
                "keywords": [
                    # EN
                    "view", "show", "see", "check", "display", "look",
                    "account info", "account details", "profile", "my account",
                    "my profile", "who am i", "account status",
                    # FR
                    "mon compte", "voir", "afficher", "consulter", "profil",
                    "mes infos", "mes informations", "détails", "details",
                    "etat", "statut", "informations du compte",
                ],
                "context": [
                    "account", "profile", "info", "information", "details", "my", "compte",
                    "profil", "statut", "état", "etat", "coordonnées", "coordonnees",
                ],
                "phrases": [
                    # EN
                    "view account", "show account", "my account", "account details",
                    "account info", "account information", "see my account",
                    "check my account", "view my profile", "show my profile",
                    "what is my account", "display account", "account status",
                    "view my details", "show my details", "see my profile",
                    # FR
                    "voir mon compte", "afficher mon compte", "consulter mon compte",
                    "voir mon profil", "afficher mon profil", "mes informations",
                    "informations de mon compte", "détails de mon compte", "details de mon compte",
                ],
            },

            Intent.WITHDRAWAL: {
                "keywords": [
                    # EN
                    "withdraw", "withdrawal", "take out", "cash out",
                    "pull out", "get money", "remove", "transfer out",
                    "payout", "pay out", "encash",
                    # FR
                    "retrait", "retirer", "retire", "sortir", "encaisser",
                    "retrait d'argent", "retirer de l'argent",
                ],
                "context": [
                    "money", "cash", "funds", "amount", "xaf", "fcfa", "argent",
                    "solde", "wallet", "portefeuille", "compte", "celo",
                ],
                "phrases": [
                    # EN
                    "withdraw money", "make withdrawal", "cash out",
                    "take out money", "get my money", "withdraw funds",
                    "make a withdrawal", "want to withdraw", "i want to withdraw",
                    "withdraw from my account", "withdraw from wallet",
                    # FR
                    "faire un retrait", "retirer de l'argent", "je veux retirer",
                    "je veux faire un retrait", "retirer sur mon compte",
                    "faire un retrait d'argent", "retirer du wallet", "retirer du portefeuille",
                ],
            },

            Intent.TOPUP: {
                "keywords": [
                    # EN
                    "top up", "topup", "top-up", "deposit", "add", "load",
                    "fund", "put in", "transfer in", "recharge", "credit",
                    "add funds", "add money", "fund account",
                    # FR
                    "depot", "dépôt", "deposer", "déposer", "recharger",
                    "charger", "crediter", "créditer", "mettre", "ajouter",
                    "alimenter", "faire un depot", "faire un dépôt",
                ],
                "context": [
                    "money", "funds", "balance", "account", "cash", "amount", "xaf", "fcfa",
                    "compte", "solde", "wallet", "portefeuille", "celo",
                ],
                "phrases": [
                    # EN
                    "add money", "deposit money", "top up", "top-up", "topup",
                    "add funds", "load money", "put money", "fund account",
                    "add to balance", "make a deposit", "want to deposit",
                    "i want to deposit", "i want to top up", "recharge account",
                    "put money in my account", "add money to my wallet",
                    # FR
                    "faire un dépôt", "déposer de l'argent", "recharger mon compte",
                    "je veux déposer", "je veux faire un dépôt", "je veux recharger",
                    "ajouter de l'argent", "alimenter mon compte", "charger mon wallet",
                    "crediter mon compte", "créditer mon compte", "faire un depot",
                ],
            },

            Intent.TRANSFER: {
                "keywords": [
                    # EN
                    "transfer", "send", "send money", "send funds",
                    "pay", "payment", "wire", "remit", "remittance",
                    "move money", "share money", "give money", "to someone",
                    "to friend", "to my friend", "to my wife", "to my husband",
                    # FR
                    "transfert", "transferer", "transférer", "envoyer", "envoi",
                    "virement", "payer", "paiement", "remettre", "faire passer",
                    "donner", "à quelqu'un", "a quelqu'un", "à mon ami", "a mon ami",
                    "a ma femme", "à ma femme", "à mon mari", "a mon mari",
                    # Local/common
                    "momo", "mobile money",
                ],
                "context": [
                    # EN
                    "to", "receiver", "recipient", "beneficiary", "phone", "number",
                    "someone", "friend", "family",
                    # FR
                    "vers", "à", "a", "destinataire", "bénéficiaire", "beneficiaire",
                    "numero", "numéro", "téléphone", "telephone", "contact",
                    # Money context
                    "money", "funds", "amount", "xaf", "fcfa", "argent", "solde",
                    "wallet", "portefeuille", "compte", "celo",
                ],
                "phrases": [
                    # EN
                    "send money", "transfer money", "make a transfer",
                    "i want to transfer", "i want to send money",
                    "send to", "transfer to", "pay someone", "pay my friend",
                    "send funds to", "transfer funds to", "move money to",
                    # FR
                    "envoyer de l'argent", "faire un transfert", "faire un virement",
                    "je veux envoyer", "je veux transférer", "je veux transferer",
                    "envoyer à", "transférer à", "transferer a", "payer quelqu'un",
                    "envoyer de l'argent à", "faire passer de l'argent",
                ],
            },

            Intent.BALANCE_INQUIRY: {
                "keywords": [
                    # EN
                    "balance", "how much", "check", "available",
                    "status", "amount", "total", "wallet",
                    # FR
                    "solde", "combien", "disponible", "montant", "total",
                    "portefeuille",
                ],
                "context": [
                    "account", "money", "have", "funds", "my", "wallet", "compte",
                    "solde", "celo", "xaf", "fcfa", "portefeuille",
                ],
                "phrases": [
                    # EN
                    "check balance", "my balance", "account balance",
                    "how much money", "how much do i have", "available balance",
                    "what is my balance", "show balance", "check my balance",
                    "what do i have", "my account balance", "my wallet balance",
                    # FR
                    "quel est mon solde", "mon solde", "solde du compte",
                    "solde du wallet", "solde du portefeuille", "je veux mon solde",
                    "combien j'ai", "combien il me reste", "montre mon solde",
                ],
            },

            Intent.TRANSACTION_HISTORY: {
                "keywords": [
                    # EN
                    "history", "transactions", "statement", "activity",
                    "records", "past", "previous", "recent",
                    # FR
                    "historique", "relevé", "releve", "activité", "activite",
                    "opérations", "operations", "mouvements",
                ],
                "context": [
                    "transaction", "payment", "transfer", "account", "compte",
                    "wallet", "portefeuille", "celo",
                ],
                "phrases": [
                    # EN
                    "transaction history", "my transactions", "past transactions",
                    "recent activity", "account history", "show transactions",
                    "view history", "statement", "my history", "show history",
                    "get transactions", "show my transactions", "list transactions",
                    # FR
                    "voir mes transactions", "historique de transactions",
                    "historique des transactions", "relevé de compte", "releve de compte",
                    "liste des transactions", "voir l'historique", "montre l'historique",
                    "mouvements du compte", "operations du compte",
                ],
            },

            # =========================================================================
            # DASHBOARD INTENT - ADDED
            # =========================================================================
            Intent.DASHBOARD: {
                "keywords": [
                    # EN
                    "dashboard", "statistics", "stats", "analytics", "overview",
                    "summary", "admin", "reports", "report", "metrics",
                    "registrations", "holders", "all accounts", "all users",
                    "total amount", "total transactions",
                    # FR
                    "tableau de bord", "statistiques", "stats", "analytique",
                    "aperçu", "apercu", "résumé", "resume", "rapports", "rapport",
                    "métriques", "metriques", "inscriptions", "titulaires",
                    "détenteurs", "detenteurs", "tous les comptes", "tous les utilisateurs",
                    "montant total", "total des transactions",
                ],
                "context": [
                    # EN
                    "view", "show", "see", "check", "display", "get",
                    "system", "platform", "overall", "global",
                    # FR
                    "voir", "afficher", "consulter", "système", "systeme",
                    "plateforme", "global", "général", "general",
                ],
                "phrases": [
                    # EN
                    "show dashboard", "view dashboard", "open dashboard",
                    "show statistics", "view statistics", "show stats", "view stats",
                    "registration statistics", "registration stats", "signup stats",
                    "show registrations", "view registrations", "how many registrations",
                    "account holders", "show holders", "view holders", "list holders",
                    "all account holders", "list all accounts", "show all users",
                    "total transaction amount", "transaction totals", "show totals",
                    "platform overview", "system overview", "show overview",
                    "show analytics", "view analytics", "get reports",
                    # FR
                    "voir le tableau de bord", "afficher le tableau de bord",
                    "ouvrir le tableau de bord", "montrer le tableau de bord",
                    "voir les statistiques", "afficher les statistiques",
                    "statistiques d'inscription", "stats d'inscription",
                    "voir les inscriptions", "afficher les inscriptions",
                    "combien d'inscriptions", "nombre d'inscriptions",
                    "titulaires de comptes", "voir les titulaires", "liste des titulaires",
                    "détenteurs de comptes", "liste des détenteurs",
                    "tous les comptes", "afficher tous les comptes",
                    "montant total des transactions", "total des transactions",
                    "aperçu de la plateforme", "aperçu général", "vue d'ensemble",
                ],
            },

            Intent.GREETING: {
                "keywords": [
                    "hello", "hi", "hey", "good morning", "good afternoon",
                    "good evening", "greetings", "howdy",
                    "bonjour", "salut", "coucou", "bonsoir",
                ],
                "context": [],
                "phrases": ["hello there", "hi there", "hey there", "bonjour à vous", "salut à toi"],
            },

            # =========================================================================
            # PASSWORD RESET INTENT 
            # =========================================================================
            Intent.PASSWORD_RESET: {
                "keywords": [
                    # EN
                    "reset", "forgot", "forgotten", "lost", "recover",
                    # FR
                    "réinitialiser", "reinitialiser", "oublié", "oublie",
                    "perdu", "récupérer", "recuperer",
                ],
                "context": [
                    "password", "pin", "code", "mot de passe", "mdp",
                ],
                "phrases": [
                    # EN
                    "reset password", "forgot password", "forgot my password",
                    "lost password", "reset my password", "recover password",
                    "i forgot my password", "password reset", "forgot pin",
                    "reset pin", "lost my pin",
                    # FR
                    "réinitialiser mot de passe", "mot de passe oublié",
                    "j'ai oublié mon mot de passe", "récupérer mot de passe",
                    "reinitialiser mot de passe", "oublié mot de passe",
                    "réinitialiser mon mot de passe", "pin oublié",
                ],
            },

            # =========================================================================
            # PASSWORD CHANGE INTENT 
            # =========================================================================
            Intent.PASSWORD_CHANGE: {
                "keywords": [
                    # EN
                    "change", "update", "modify", "new password",
                    # FR
                    "changer", "modifier", "mettre à jour", "nouveau",
                ],
                "context": [
                    "password", "pin", "code", "mot de passe", "mdp",
                ],
                "phrases": [
                    # EN
                    "change password", "change my password", "update password",
                    "new password", "modify password", "change pin",
                    "update my password", "i want to change my password",
                    "set new password", "change my pin",
                    # FR
                    "changer mot de passe", "changer mon mot de passe",
                    "modifier mot de passe", "nouveau mot de passe",
                    "mettre à jour mot de passe", "changer le mot de passe",
                    "je veux changer mon mot de passe", "changer pin",
                    "modifier mon mot de passe",
                ],
            },

            # =========================================================================
            # WHATSAPP LINK INTENT 
            # =========================================================================
            Intent.WHATSAPP_LINK: {
                "keywords": [
                    # EN
                    "whatsapp", "link", "connect", "associate",
                    # FR
                    "lier", "associer", "connecter", "liaison",
                ],
                "context": [
                    "whatsapp", "wa", "account", "phone", "number",
                    "compte", "numéro", "numero", "téléphone", "telephone",
                ],
                "phrases": [
                    # EN
                    "link whatsapp", "connect whatsapp", "whatsapp link",
                    "link my whatsapp", "connect my whatsapp",
                    "associate whatsapp", "add whatsapp", "setup whatsapp",
                    "link whatsapp account", "connect whatsapp number",
                    # FR
                    "lier whatsapp", "connecter whatsapp", "associer whatsapp",
                    "lier mon whatsapp", "connecter mon whatsapp",
                    "liaison whatsapp", "ajouter whatsapp",
                    "lier compte whatsapp", "associer mon whatsapp",
                ],
            },

            Intent.GOODBYE: {
                "keywords": [
                    "bye", "goodbye", "see you", "thanks", "thank you",
                    "done", "exit", "quit", "finished",
                    "merci", "au revoir", "à bientôt", "a bientot", "bonne journée", "bonne journee",
                ],
                "context": [],
                "phrases": [
                    "thank you", "thanks bye", "goodbye", "that is all",
                    "i'm done", "no more", "nothing else", "that's all",
                    "merci beaucoup", "c'est tout", "rien d'autre",
                ],
            },

            Intent.CONFIRMATION: {
                "keywords": [
                    "yes", "yeah", "yep", "correct", "confirm", "sure",
                    "ok", "okay", "right", "exactly", "affirmative",
                    "proceed",
                    "oui", "ouais", "d'accord", "okey", "parfait", "exact",
                ],
                "context": [],
                "phrases": ["that's right", "that is correct", "go ahead", "sounds good", "c'est bon", "c'est correct"],
            },

            Intent.DENIAL: {
                "keywords": [
                    "no", "nope", "cancel", "stop", "wrong", "incorrect",
                    "nevermind", "never mind", "forget it",
                    "non", "pas du tout", "annule", "annuler", "stop", "laisse", "laissez",
                ],
                "context": [],
                "phrases": ["no thanks", "cancel that", "forget it", "not right", "non merci", "annule ça", "annule ca"],
            },
        }

        # Keep OFF_TOPIC simple; avoid blocking words that might appear in your domain.
        self.blocked_phrases = [
            "weather", "forecast", "temperature", "joke", "funny",
            "story", "recipe", "movie", "music", "song", "game",
            "president", "politics", "write code", "programming",
            "homework", "essay", "translate",
        ]

    def _normalize_text(self, text: str) -> str:
        """Normalize text for matching"""
        text = text.lower().strip()
        text = text.replace("-", " ")
        text = re.sub(r"\s+", " ", text)
        return text

    def _has_word(self, text: str, word: str) -> bool:
        """Whole-word match for single tokens to reduce false positives."""
        return re.search(rf"\b{re.escape(word)}\b", text) is not None

    def classify(self, text: str) -> Tuple[Intent, float]:
        """Classify user intent from text."""
        if not text or not text.strip():
            return Intent.GENERAL_SUPPORT, 0.0

        text_normalized = self._normalize_text(text)

        for phrase in self.blocked_phrases:
            if phrase in text_normalized:
                return Intent.OFF_TOPIC, 0.9

        scores = {}

        for intent, patterns in self.intent_patterns.items():
            score = 0.0

            # phrases (highest weight)
            for phrase in patterns.get("phrases", []):
                p = self._normalize_text(phrase)
                if p and p in text_normalized:
                    score += 0.8
                    break

            # keywords
            keyword_found = False
            for keyword in patterns.get("keywords", []):
                k = self._normalize_text(keyword)
                if not k:
                    continue

                # if keyword is multi-word, use substring match; else use whole-word match
                if (" " in k and k in text_normalized) or (" " not in k and self._has_word(text_normalized, k)):
                    score += 0.5
                    keyword_found = True
                    break

            # context
            context_words = patterns.get("context", [])
            if context_words:
                for ctx in context_words:
                    c = self._normalize_text(ctx)
                    if not c:
                        continue
                    if (" " in c and c in text_normalized) or (" " not in c and self._has_word(text_normalized, c)):
                        score += 0.2
                        break

            # Boost for short inputs with keyword match
            if keyword_found and len(text_normalized.split()) <= 2:
                score += 0.3

            scores[intent] = min(score, 1.0)

        if scores:
            best_intent = max(scores, key=scores.get)
            best_score = scores[best_intent]
            if best_score >= 0.4:
                return best_intent, best_score

        return Intent.GENERAL_SUPPORT, 0.5