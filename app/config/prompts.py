"""LLM prompts and templates"""

from .settings import settings

SYSTEM_PROMPT = f"""You are a friendly and professional customer support AI assistant for {settings.COMPANY_NAME}.

SUPPORTED LANGUAGES:
- English
- French

RULE:
- Always respond in the SAME language the user is using.
  If the user writes or speaks in French, answer in French.
  If the user writes or speaks in English, answer in English.

YOUR RESPONSIBILITIES:
1. Account Creation
2. View Account
3. Withdrawals
4. Top-ups/Deposits
5. Balance Inquiries (CELO wallet)
6. Transaction History

OTHER RULES:
- Keep responses under {settings.MAX_RESPONSE_WORDS} words
- Be warm, professional, and helpful
- Ask ONE question at a time
- Use {settings.CURRENCY} or CELO where appropriate
- For off-topic requests, politely redirect to supported services, in the user's language.

Remember: Guide the user step by step through natural conversation."""

# Available groupements
GROUPEMENTS = [
    {"id": 1, "name": "Batoufam", "token": "MBIP TSWEFAP"},
    {"id": 2, "name": "Fondjomekwet", "token": "MBAM"},
    {"id": 3, "name": "Bameka", "token": "MUNKAP"},
]

FLOW_PROMPTS = {
    "account_creation": {
        "start_en": "Welcome to BAFOKA! I'll help you create an account. What is your full name?",
        "start_fr": "Bienvenue chez BAFOKA ! Je vais vous aider à créer un compte. Quel est votre nom complet ?",

        "ask_age_en": "Thank you, {name}! How old are you?",
        "ask_age_fr": "Merci, {name} ! Quel âge avez-vous ?",

        "ask_sex_en": "Got it! Are you male or female?",
        "ask_sex_fr": "Très bien ! Êtes-vous un homme ou une femme ?",

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

        "success_en": (
            "Congratulations {name}! Your account has been created successfully. "
            "Your account details have been registered. Is there anything else I can help with?"
        ),
        "success_fr": (
            "Félicitations {name} ! Votre compte a été créé avec succès. "
            "Vos informations ont été enregistrées. Puis-je vous aider avec autre chose ?"
        ),

        "error_en": "I'm sorry, there was an issue creating your account. Please try again later.",
        "error_fr": "Je suis désolé, un problème est survenu lors de la création de votre compte. Veuillez réessayer plus tard.",
    },

    "withdrawal": {
        "start_en": (
            f"I'll help you with a withdrawal. How much would you like to withdraw? "
            f"(Min: {settings.WITHDRAWAL_MIN:.0f} {settings.CURRENCY}, Max: {settings.WITHDRAWAL_MAX:.0f} {settings.CURRENCY})"
        ),
        "start_fr": (
            f"Je vais vous aider à faire un retrait. Quel montant souhaitez-vous retirer ? "
            f"(Min : {settings.WITHDRAWAL_MIN:.0f} {settings.CURRENCY}, Max : {settings.WITHDRAWAL_MAX:.0f} {settings.CURRENCY})"
        ),

        "confirm_en": (
            "You want to withdraw {amount:.0f} {currency}. "
            "Is that correct? Say 'yes' to confirm or 'no' to cancel."
        ),
        "confirm_fr": (
            "Vous souhaitez retirer {amount:.0f} {currency}. "
            "Est-ce correct ? Dites 'oui' pour confirmer ou 'non' pour annuler."
        ),

        "success_en": "Your withdrawal of {amount:.0f} {currency} has been processed successfully!",
        "success_fr": "Votre retrait de {amount:.0f} {currency} a été effectué avec succès !",

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
    },

    "topup": {
        "start_en": (
            f"I'll help you top up your account. How much would you like to deposit? "
            f"(Min: {settings.TOPUP_MIN:.0f} {settings.CURRENCY}, Max: {settings.TOPUP_MAX:.0f} {settings.CURRENCY})"
        ),
        "start_fr": (
            f"Je vais vous aider à recharger votre compte. Quel montant souhaitez-vous déposer ? "
            f"(Min : {settings.TOPUP_MIN:.0f} {settings.CURRENCY}, Max : {settings.TOPUP_MAX:.0f} {settings.CURRENCY})"
        ),

        "confirm_en": (
            "You want to deposit {amount:.0f} {currency}. "
            "Is that correct? Say 'yes' to confirm or 'no' to cancel."
        ),
        "confirm_fr": (
            "Vous souhaitez déposer {amount:.0f} {currency}. "
            "Est-ce correct ? Dites 'oui' pour confirmer ou 'non' pour annuler."
        ),

        "success_en": (
            "Your deposit of {amount:.0f} {currency} has been received. "
            "Your new balance is {new_balance:.0f} {currency}."
        ),
        "success_fr": (
            "Votre dépôt de {amount:.0f} {currency} a été reçu. "
            "Votre nouveau solde est de {new_balance:.0f} {currency}."
        ),

        "error_en": "I'm sorry, there was an issue processing your deposit. Please try again later.",
        "error_fr": "Je suis désolé, un problème est survenu lors du traitement de votre dépôt. Veuillez réessayer plus tard.",
    },
    
     "transfer": {
        "start": "Sure — who do you want to send money to? Please share the receiver phone number.",
        "ask_receiver_retry": "I couldn't read the receiver phone number. Please send digits only (example: 690123456).",
        "ask_amount": f"How much do you want to send? (in {settings.CURRENCY})",
        "ask_amount_retry": f"I couldn't understand the amount. Please send a number like '10000' (in {settings.CURRENCY}).",
        "ask_pin": "Please enter your PIN to confirm the transfer.",
        "ask_pin_retry": "Invalid PIN. Please enter a valid PIN (4–6 digits).",
        "confirm": "Confirm transfer: send {amount} {currency} to {receiver}. Reply 'yes' to confirm or 'no' to cancel.",
        "confirm_retry": "Please reply 'yes' to confirm or 'no' to cancel this transfer.",
        "insufficient_funds": "Sorry, you don't have enough balance. Your current balance is {balance:.0f} {currency}.",
        "success": "✅ Transfer completed successfully. Reference: {reference}.",
        "error": "I'm sorry, there was an issue processing your transfer. Please try again later.",
    },
}