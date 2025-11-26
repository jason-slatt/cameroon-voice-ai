
"""LLM prompts and templates"""

from .settings import settings

SYSTEM_PROMPT = f"""You are a friendly and professional customer support AI assistant for {settings.COMPANY_NAME} (Bafoka).

ABOUT BAFOKA:
Bafoka is a digital barter trade system developed by GFA Consulting, ActivSpace, German Cooperation (Coopération Allemande), and partner NGOs. It empowers rural communities to exchange goods virtually using blockchain technology (CELO).

CURRENT SERVICE AREAS (Cameroon):
- Bemeka
- Batoufam
- Fondjomekwet

HOW BAFOKA WORKS:
- Community members agree on fair exchange rates (e.g., 1 bag of cassava = 1 bag of corn)
- Exchanges are recorded securely on the CELO blockchain
- No cash required — trade is based on mutual agreement and trust

SUPPORTED LANGUAGES:
- English
- French

LANGUAGE RULE:
- Always respond in the SAME language the user is using.
  → French input = French response
  → English input = English response

YOUR RESPONSIBILITIES:
1. Account Creation — Help users register on Bafoka
2. View Account — Assist with account details and settings
3. Withdrawals — Guide users through withdrawal processes
4. Top-ups/Deposits — Explain how to add value to accounts
5. Balance Inquiries — Check CELO wallet balances
6. Transaction History — Review past barter exchanges
7. Barter Guidance — Explain how to propose and accept trades

OTHER RULES:
- Keep responses under {settings.MAX_RESPONSE_WORDS} words
- Be warm, culturally respectful, and helpful
- Ask ONE question at a time
- Use {settings.CURRENCY} or CELO where appropriate
- For off-topic requests, politely redirect to supported services in the user's language
- Use simple, clear language suitable for users with varying tech literacy

EXAMPLE BARTER CONTEXT:
When users ask about trading, explain that Bafoka allows them to:
- List goods they want to trade (e.g., cassava, corn, plantains)
- Find community members with matching needs
- Agree on fair exchange terms
- Complete the trade securely via blockchain

Remember: Guide users step by step through natural, patient conversation. Many users may be new to digital systems — be encouraging and supportive."""


# Available groupements
GROUPEMENTS = [
    {"id": 1, "name": "Batoufam", "token": "MBIP TSWEFAP"},
    {"id": 2, "name": "Fondjomekwet", "token": "MBAM"},
    {"id": 3, "name": "Bameka", "token": "MUNKAP"},
]

FLOW_PROMPTS = {
    "account_creation": {
        # === Start ===
        "start_en": "Welcome to BAFOKA! I'll help you create an account. What is your full name?",
        "start_fr": "Bienvenue chez BAFOKA ! Je vais vous aider à créer un compte. Quel est votre nom complet ?",

        # === Ask Age ===
        "ask_age_en": "Thank you, {name}! How old are you?",
        "ask_age_fr": "Merci, {name} ! Quel âge avez-vous ?",

        # === Ask Sex ===
        "ask_sex_en": "Got it! Are you male or female?",
        "ask_sex_fr": "Très bien ! Êtes-vous un homme ou une femme ?",

        # === Ask Groupement ===
        "ask_groupement_en": (
            "Almost done! Which groupement are you from?\n"
            "1. Batoufam (MBIP TSWEFAP)\n"
            "2. Fondjomekwet (MBAM)\n"
            "3. Bameka (MUNKAP)\n\n"
            "Please say the number or name."
        ),
        "ask_groupement_fr": (
            "Nous avons presque terminé ! De quel groupement venez-vous ?\n"
            "1. Batoufam (MBIP TSWEFAP)\n"
            "2. Fondjomekwet (MBAM)\n"
            "3. Bameka (MUNKAP)\n\n"
            "Veuillez dire le numéro ou le nom."
        ),

        # === Confirmation ===
        "confirm_en": (
            "Let me confirm your information:\n"
            "• Name: {name}\n"
            "• Age: {age}\n"
            "• Sex: {sex}\n"
            "• Groupement: {groupement_name}\n\n"
            "Is this correct? Say 'yes' to confirm or 'no' to make changes."
        ),
        "confirm_fr": (
            "Laissez-moi confirmer vos informations :\n"
            "• Nom : {name}\n"
            "• Âge : {age}\n"
            "• Sexe : {sex}\n"
            "• Groupement : {groupement_name}\n\n"
            "Est-ce correct ? Dites 'oui' pour confirmer ou 'non' pour modifier."
        ),

        # === Success ===
        "success_en": (
            "Congratulations {name}! Your account has been created successfully. "
            "Your account details have been registered. Is there anything else I can help with?"
        ),
        "success_fr": (
            "Félicitations {name} ! Votre compte a été créé avec succès. "
            "Vos informations ont été enregistrées. Puis-je vous aider avec autre chose ?"
        ),

        # === Error ===
        "error_en": "I'm sorry, there was an issue creating your account. Please try again later.",
        "error_fr": "Je suis désolé, un problème est survenu lors de la création de votre compte. Veuillez réessayer plus tard.",

        # === Validation Errors ===
        "invalid_name_en": "I didn't catch your name. Please tell me your full name.",
        "invalid_name_fr": "Je n'ai pas compris votre nom. Veuillez me dire votre nom complet.",

        "invalid_age_en": "Please tell me your age. For example, '25' or '25 years old'.",
        "invalid_age_fr": "Veuillez me dire votre âge. Par exemple, '25' ou '25 ans'.",

        "underage_en": "You must be at least 18 years old to create an account. How old are you?",
        "underage_fr": "Vous devez avoir au moins 18 ans pour créer un compte. Quel âge avez-vous ?",

        "invalid_sex_en": "Please say 'male' or 'female'.",
        "invalid_sex_fr": "Veuillez dire 'homme' ou 'femme'.",

        "invalid_groupement_en": "Please select a groupement by number (1, 2, or 3) or by name.",
        "invalid_groupement_fr": "Veuillez sélectionner un groupement par numéro (1, 2 ou 3) ou par nom.",

        # === Confirmation Flow ===
        "what_to_change_en": "What would you like to change? Say 'name', 'age', 'sex', or 'groupement'.",
        "what_to_change_fr": "Que souhaitez-vous modifier ? Dites 'nom', 'âge', 'sexe' ou 'groupement'.",

        "confirm_prompt_en": "Please confirm: is all the information correct? Say 'yes' or 'no'.",
        "confirm_prompt_fr": "Veuillez confirmer : toutes les informations sont-elles correctes ? Dites 'oui' ou 'non'.",

        "change_name_en": "Okay, what is your correct full name?",
        "change_name_fr": "D'accord, quel est votre nom complet correct ?",

        "change_age_en": "Okay, how old are you?",
        "change_age_fr": "D'accord, quel âge avez-vous ?",

        "change_sex_en": "Okay, are you male or female?",
        "change_sex_fr": "D'accord, êtes-vous un homme ou une femme ?",

        # === Max Attempts ===
        "max_attempts_en": "I'm having trouble understanding. Let's start over. Say 'create account' when ready.",
        "max_attempts_fr": "J'ai du mal à comprendre. Recommençons. Dites 'créer un compte' quand vous êtes prêt.",

        # === Cancel ===
        "cancelled_en": "Account creation cancelled. How else can I help you?",
        "cancelled_fr": "Création de compte annulée. Comment puis-je vous aider autrement ?",
    },

    "withdrawal": {
        # === Start ===
        "start_en": (
            f"I'll help you with a withdrawal. How much would you like to withdraw? "
            f"(Min: {settings.WITHDRAWAL_MIN:.0f} {settings.CURRENCY}, Max: {settings.WITHDRAWAL_MAX:.0f} {settings.CURRENCY})"
        ),
        "start_fr": (
            f"Je vais vous aider à faire un retrait. Quel montant souhaitez-vous retirer ? "
            f"(Min : {settings.WITHDRAWAL_MIN:.0f} {settings.CURRENCY}, Max : {settings.WITHDRAWAL_MAX:.0f} {settings.CURRENCY})"
        ),

        # === Confirmation ===
        "confirm_en": (
            "You want to withdraw {amount:.0f} {currency}. "
            "Is that correct? Say 'yes' to confirm or 'no' to cancel."
        ),
        "confirm_fr": (
            "Vous souhaitez retirer {amount:.0f} {currency}. "
            "Est-ce correct ? Dites 'oui' pour confirmer ou 'non' pour annuler."
        ),

        # === Success ===
        "success_en": "Your withdrawal of {amount:.0f} {currency} has been processed successfully!",
        "success_fr": "Votre retrait de {amount:.0f} {currency} a été effectué avec succès !",

        # === Errors ===
        "insufficient_funds_en": (
            "Sorry, you don't have enough balance for this withdrawal. "
            "Your current balance is {balance:.0f} {currency}."
        ),
        "insufficient_funds_fr": (
            "Désolé, votre solde est insuffisant pour ce retrait. "
            "Votre solde actuel est de {balance:.0f} {currency}."
        ),

        "error_en": "I'm sorry, there was an issue processing your withdrawal. Please try again later.",
        "error_fr": "Je suis désolé, un problème est survenu lors du traitement de votre retrait. Veuillez réessayer plus tard.",

        # === Validation ===
        "invalid_amount_en": (
            f"Please provide a valid amount between {settings.WITHDRAWAL_MIN:.0f} and {settings.WITHDRAWAL_MAX:.0f} {settings.CURRENCY}."
        ),
        "invalid_amount_fr": (
            f"Veuillez fournir un montant valide entre {settings.WITHDRAWAL_MIN:.0f} et {settings.WITHDRAWAL_MAX:.0f} {settings.CURRENCY}."
        ),

        # === Max Attempts ===
        "max_attempts_en": "I'm having trouble understanding. Let's try again later.",
        "max_attempts_fr": "J'ai du mal à comprendre. Réessayons plus tard.",

        # === Cancel ===
        "cancelled_en": "Withdrawal cancelled. How else can I help you?",
        "cancelled_fr": "Retrait annulé. Comment puis-je vous aider autrement ?",

        # === Confirm Prompt ===
        "confirm_prompt_en": "Please confirm: do you want to proceed with this withdrawal? Say 'yes' or 'no'.",
        "confirm_prompt_fr": "Veuillez confirmer : voulez-vous procéder à ce retrait ? Dites 'oui' ou 'non'.",
    },

    "topup": {
        # === Start ===
        "start_en": (
            f"I'll help you top up your account. How much would you like to deposit? "
            f"(Min: {settings.TOPUP_MIN:.0f} {settings.CURRENCY}, Max: {settings.TOPUP_MAX:.0f} {settings.CURRENCY})"
        ),
        "start_fr": (
            f"Je vais vous aider à recharger votre compte. Quel montant souhaitez-vous déposer ? "
            f"(Min : {settings.TOPUP_MIN:.0f} {settings.CURRENCY}, Max : {settings.TOPUP_MAX:.0f} {settings.CURRENCY})"
        ),

        # === Confirmation ===
        "confirm_en": (
            "You want to deposit {amount:.0f} {currency}. "
            "Is that correct? Say 'yes' to confirm or 'no' to cancel."
        ),
        "confirm_fr": (
            "Vous souhaitez déposer {amount:.0f} {currency}. "
            "Est-ce correct ? Dites 'oui' pour confirmer ou 'non' pour annuler."
        ),

        # === Success ===
        "success_en": (
            "Your deposit of {amount:.0f} {currency} has been received. "
            "Your new balance is {new_balance:.0f} {currency}."
        ),
        "success_fr": (
            "Votre dépôt de {amount:.0f} {currency} a été reçu. "
            "Votre nouveau solde est de {new_balance:.0f} {currency}."
        ),

        # === Errors ===
        "error_en": "I'm sorry, there was an issue processing your deposit. Please try again later.",
        "error_fr": "Je suis désolé, un problème est survenu lors du traitement de votre dépôt. Veuillez réessayer plus tard.",

        # === Validation ===
        "invalid_amount_en": (
            f"Please provide a valid amount between {settings.TOPUP_MIN:.0f} and {settings.TOPUP_MAX:.0f} {settings.CURRENCY}."
        ),
        "invalid_amount_fr": (
            f"Veuillez fournir un montant valide entre {settings.TOPUP_MIN:.0f} et {settings.TOPUP_MAX:.0f} {settings.CURRENCY}."
        ),

        # === Max Attempts ===
        "max_attempts_en": "I'm having trouble understanding. Let's try again later.",
        "max_attempts_fr": "J'ai du mal à comprendre. Réessayons plus tard.",

        # === Cancel ===
        "cancelled_en": "Deposit cancelled. How else can I help you?",
        "cancelled_fr": "Dépôt annulé. Comment puis-je vous aider autrement ?",

        # === Confirm Prompt ===
        "confirm_prompt_en": "Please confirm: do you want to proceed with this deposit? Say 'yes' or 'no'.",
        "confirm_prompt_fr": "Veuillez confirmer : voulez-vous procéder à ce dépôt ? Dites 'oui' ou 'non'.",

    "transfer": {
        "start_en": "Sure — who do you want to send money to? Please share the receiver phone number.",
        "start_fr": "D’accord — à qui voulez-vous envoyer de l’argent ? Donnez le numéro du bénéficiaire.",

        "ask_receiver_retry_en": "I couldn't read the receiver phone number. Please send digits only (example: 690123456).",
        "ask_receiver_retry_fr": "Je n’ai pas compris le numéro. Envoyez uniquement les chiffres (ex: 690123456).",

        "ask_amount_en": f"How much do you want to send? (in {settings.CURRENCY})",
        "ask_amount_fr": f"Quel montant voulez-vous envoyer ? (en {settings.CURRENCY})",

        "ask_amount_retry_en": f"I couldn't understand the amount. Please send a number like '10000' (in {settings.CURRENCY}).",
        "ask_amount_retry_fr": f"Je n’ai pas compris le montant. Envoyez un nombre comme '10000' (en {settings.CURRENCY}).",

        "ask_pin_en": "Please enter your PIN to confirm the transfer.",
        "ask_pin_fr": "Veuillez entrer votre code PIN pour confirmer le transfert.",

        "ask_pin_retry_en": "Invalid PIN. Please enter a valid PIN (4–6 digits).",
        "ask_pin_retry_fr": "PIN invalide. Entrez un PIN valide (4 à 6 chiffres).",

        "confirm_en": "Confirm transfer: send {amount:.0f} {currency} to {receiver}. Reply 'yes' to confirm or 'no' to cancel.",
        "confirm_fr": "Confirmez le transfert : envoyer {amount:.0f} {currency} à {receiver}. Dites 'oui' pour confirmer ou 'non' pour annuler.",

        "confirm_retry_en": "Please reply 'yes' to confirm or 'no' to cancel this transfer.",
        "confirm_retry_fr": "Veuillez répondre 'oui' pour confirmer ou 'non' pour annuler.",

        "insufficient_funds_en": "Sorry, you don't have enough balance. Your current balance is {balance:.0f} {currency}.",
        "insufficient_funds_fr": "Désolé, solde insuffisant. Votre solde actuel est {balance:.0f} {currency}.",

        "success_en": "✅ Transfer completed successfully. Reference: {reference}.",
        "success_fr": "✅ Transfert effectué avec succès. Référence : {reference}.",

        "error_en": "I'm sorry, there was an issue processing your transfer. Please try again later.",
        "error_fr": "Je suis désolé, un problème est survenu lors du transfert. Veuillez réessayer plus tard.",
    },
}
    },

# General responses (not flow-specific)
GENERAL_RESPONSES = {
    "welcome_en": f"Welcome to {settings.COMPANY_NAME}! How can I help you today?",
    "welcome_fr": f"Bienvenue chez {settings.COMPANY_NAME} ! Comment puis-je vous aider aujourd'hui ?",

    "goodbye_en": "Thank you for using our service. Have a great day!",
    "goodbye_fr": "Merci d'utiliser notre service. Bonne journée !",

    "help_en": (
        "I can help you with:\n"
        "• Create an account\n"
        "• View your account\n"
        "• Make a withdrawal\n"
        "• Make a deposit\n"
        "• Check your balance\n"
        "• View transaction history\n\n"
        "What would you like to do?"
    ),
    "help_fr": (
        "Je peux vous aider à :\n"
        "• Créer un compte\n"
        "• Voir votre compte\n"
        "• Faire un retrait\n"
        "• Faire un dépôt\n"
        "• Vérifier votre solde\n"
        "• Voir l'historique des transactions\n\n"
        "Que souhaitez-vous faire ?"
    ),

    "not_understood_en": "I'm sorry, I didn't understand that. Could you please rephrase?",
    "not_understood_fr": "Je suis désolé, je n'ai pas compris. Pourriez-vous reformuler ?",

    "no_account_en": "You don't have an account yet. Would you like to create one?",
    "no_account_fr": "Vous n'avez pas encore de compte. Souhaitez-vous en créer un ?",

    "already_has_account_en": (
        f"You already have an account with {settings.COMPANY_NAME}. "
        "I can help you view your account, check your balance, make a withdrawal, or top up. What would you like to do?"
    ),
    "already_has_account_fr": (
        f"Vous avez déjà un compte chez {settings.COMPANY_NAME}. "
        "Je peux vous aider à voir votre compte, vérifier votre solde, faire un retrait ou un dépôt. Que souhaitez-vous faire ?"
    ),
}