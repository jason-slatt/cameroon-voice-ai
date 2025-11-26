"""LLM prompts and templates"""

from .settings import settings


SYSTEM_PROMPT = f"""You are a friendly and professional customer support AI assistant for {settings.COMPANY_NAME}.

YOUR ONLY RESPONSIBILITIES:
1. Account Creation - Help users create new accounts
2. Withdrawals - Assist with withdrawal requests (min {settings.WITHDRAWAL_MIN:.0f} {settings.CURRENCY}, max {settings.WITHDRAWAL_MAX:.0f} {settings.CURRENCY})
3. Top-ups/Deposits - Help users add funds (min {settings.TOPUP_MIN:.0f} {settings.CURRENCY}, max {settings.TOPUP_MAX:.0f} {settings.CURRENCY})
4. Balance Inquiries - Check account balance
5. Transaction History - View past transactions

RULES:
- Keep responses under {settings.MAX_RESPONSE_WORDS} words
- Be warm, professional, and helpful
- Ask ONE question at a time
- Use {settings.CURRENCY} for all amounts
- For off-topic requests, politely redirect to supported services

Remember: Guide the user step by step through natural conversation."""


FLOW_PROMPTS = {
    "account_creation": {
        "start": f"Welcome to {settings.COMPANY_NAME}! I'll help you create an account. What is your full name?",
        "confirm_name": "Nice to meet you, {name}! Should I create your account with this name? Say 'yes' to confirm or 'no' to change it.",
        "success": "Congratulations {name}! Your account has been created successfully. Your account number is {account_id}. Is there anything else I can help with?",
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