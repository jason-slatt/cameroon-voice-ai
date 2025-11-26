"""LLM prompts and templates"""

from .settings import settings


SYSTEM_PROMPT = f"""You are a friendly and professional customer support AI assistant for {settings.COMPANY_NAME}.

YOUR ONLY RESPONSIBILITIES:
1. Account Creation - Help users create new accounts
2. View Account - Show account details and information
3. Withdrawals - Assist with withdrawal requests
4. Top-ups/Deposits - Help users add funds
5. Balance Inquiries - Check account balance
6. Transaction History - View past transactions

RULES:
- Keep responses under {settings.MAX_RESPONSE_WORDS} words
- Be warm, professional, and helpful
- Ask ONE question at a time
- Use {settings.CURRENCY} for all amounts
- For off-topic requests, politely redirect to supported services

Remember: Guide the user step by step through natural conversation."""


# Available groupements
GROUPEMENTS = [
    {"id": 1, "name": "Batoufam", "token": "MBIP TSWEFAP"},
    {"id": 2, "name": "Fondjomekwet", "token": "MBAM"},
    {"id": 3, "name": "Bameka", "token": "MUNKAP"},
]


FLOW_PROMPTS = {
    "account_creation": {
        "start": f"Welcome to {settings.COMPANY_NAME}! I'll help you create an account. What is your full name?",
        "ask_age": "Thank you, {name}! How old are you?",
        "ask_sex": "Got it! Are you male or female?",
        "ask_groupement": (
            "Almost done! Which groupement are you from?\n"
            "1. Batoufam (MBIP TSWEFAP)\n"
            "2. Fondjomekwet (MBAM)\n"
            "3. Bameka (MUNKAP)\n\n"
            "Please say the number or name."
        ),
        "confirm": (
            "Let me confirm your information:\n"
            "• Name: {name}\n"
            "• Age: {age}\n"
            "• Sex: {sex}\n"
            "• Groupement: {groupement_name}\n\n"
            "Is this correct? Say 'yes' to confirm or 'no' to make changes."
        ),
        "success": (
            "Congratulations {name}! Your account has been created successfully. "
            "Your account details have been registered. Is there anything else I can help with?"
        ),
        "error": "I'm sorry, there was an issue creating your account. Please try again later.",
    },
    "withdrawal": {
        "start": f"I'll help you with a withdrawal. How much would you like to withdraw? (Min: {settings.WITHDRAWAL_MIN:.0f} {settings.CURRENCY}, Max: {settings.WITHDRAWAL_MAX:.0f} {settings.CURRENCY})",
        "confirm": "You want to withdraw {amount:.0f} {currency}. Is that correct? Say 'yes' to confirm or 'no' to cancel.",
        "success": "Your withdrawal of {amount:.0f} {currency} has been processed successfully!",
        "insufficient_funds": "Sorry, you don't have enough balance for this withdrawal. Your current balance is {balance:.0f} {currency}.",
        "error": "I'm sorry, there was an issue processing your withdrawal. Please try again later.",
    },
    "topup": {
        "start": f"I'll help you top up your account. How much would you like to deposit? (Min: {settings.TOPUP_MIN:.0f} {settings.CURRENCY}, Max: {settings.TOPUP_MAX:.0f} {settings.CURRENCY})",
        "confirm": "You want to deposit {amount:.0f} {currency}. Is that correct? Say 'yes' to confirm or 'no' to cancel.",
        "success": "Your deposit of {amount:.0f} {currency} has been received. Your new balance is {new_balance:.0f} {currency}.",
        "error": "I'm sorry, there was an issue processing your deposit. Please try again later.",
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