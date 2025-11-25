# src/services/banking/orchestrator.py
"""
Banking Orchestrator - Routes intents to handlers and manages workflow
"""
from typing import Dict, Any
from datetime import datetime

from src.core.logging import logger
from src.services.banking.mock_api import MockBankingAPI
from src.services.banking.validators import BankingValidator
from src.services.banking.security import OTPService
from src.services.banking.fraud_detector import FraudDetector
from src.services.banking.audit import AuditLogger


class BankingOrchestrator:
    """
    Main banking orchestration engine
    Routes commands to appropriate handlers
    """

    # Thresholds (explicit, no magic numbers)
    OTP_AMOUNT_THRESHOLD = 500.0
    OTP_RISK_THRESHOLD = FraudDetector.RISK_HIGH

    def __init__(
        self,
        banking_api: MockBankingAPI | None = None,
        validator: BankingValidator | None = None,
        otp_service: OTPService | None = None,
        fraud_detector: FraudDetector | None = None,
        audit_logger: AuditLogger | None = None,
    ) -> None:
        self.banking_api = banking_api or MockBankingAPI()
        self.validator = validator or BankingValidator()
        self.otp_service = otp_service or OTPService()
        self.fraud_detector = fraud_detector or FraudDetector()
        self.audit_logger = audit_logger or AuditLogger()

    async def process_command(
        self,
        intent: str,
        entities: Dict[str, Any],
        conversation_id: str,
        user_id: str,
    ) -> Dict[str, Any]:
        """
        Process a banking command

        Args:
            intent: Classified intent
            entities: Extracted entities
            conversation_id: Conversation ID
            user_id: User ID

        Returns:
            {
                "response": "Human-readable response",
                "status": "success|pending|failed",
                "requires_otp": bool,
                "transaction_id": str (optional)
            }
        """

        logger.info("🏦 Processing intent: %s", intent)

        await self.audit_logger.log_command(
            user_id=user_id,
            intent=intent,
            entities=entities,
            timestamp=datetime.utcnow(),
        )

        handler_map = {
            "faire_virement": self._handle_virement,
            "consulter_solde": self._handle_solde,
            "bloquer_carte": self._handle_bloquer_carte,
            "ajouter_beneficiaire": self._handle_ajouter_beneficiaire,
            "historique_transactions": self._handle_historique,
            "consulter_rib": self._handle_rib,
            "payer_facture": self._handle_payer_facture,
            "changer_plafond": self._handle_changer_plafond,
        }

        handler = handler_map.get(intent)

        if handler is None:
            failure_result = {
                "response": f"Désolé, je ne peux pas traiter cette demande ({intent}).",
                "status": "failed",
            }
            await self.audit_logger.log_result(
                user_id=user_id,
                intent=intent,
                result=failure_result,
                timestamp=datetime.utcnow(),
            )
            return failure_result

        try:
            result = await handler(entities, user_id, conversation_id)

            await self.audit_logger.log_result(
                user_id=user_id,
                intent=intent,
                result=result,
                timestamp=datetime.utcnow(),
            )

            return result

        except Exception as exc:  # noqa: BLE001
            logger.error("Error in banking handler: %s", exc, exc_info=True)

            await self.audit_logger.log_error(
                user_id=user_id,
                intent=intent,
                error=str(exc),
                timestamp=datetime.utcnow(),
            )

            return {
                "response": "Une erreur s'est produite. Veuillez réessayer.",
                "status": "failed",
                "error": str(exc),
            }

    # ==================== INTENT HANDLERS ====================

    async def _handle_virement(
        self,
        entities: Dict[str, Any],
        user_id: str,
        conversation_id: str,
    ) -> Dict[str, Any]:
        """Handle money transfer"""

        montant = entities.get("montant")
        destinataire = entities.get("destinataire")
        devise = entities.get("devise", "EUR")

        logger.info("💸 Transfer: %s %s to %s", montant, devise, destinataire)

        if not self.validator.validate_amount(montant):
            return {
                "response": f"Le montant {montant} EUR n'est pas valide.",
                "status": "failed",
            }

        # Daily limit check (today_total mocked as 0 for now)
        if not self.validator.check_daily_limit(user_id=user_id, new_amount=montant):
            return {
                "response": "Vous avez dépassé votre plafond journalier.",
                "status": "failed",
            }

        balance = await self.banking_api.get_account_balance(user_id)

        if montant > balance:
            return {
                "response": f"Solde insuffisant. Vous avez {balance} EUR disponible.",
                "status": "failed",
            }

        beneficiary_exists = await self.banking_api.check_beneficiary(
            user_id=user_id,
            name=destinataire,
        )

        if not beneficiary_exists:
            return {
                "response": f"Le bénéficiaire '{destinataire}' n'existe pas. Voulez-vous l'ajouter?",
                "status": "pending",
                "action_required": "add_beneficiary",
            }

        risk_score = await self.fraud_detector.assess_risk(
            user_id=user_id,
            amount=montant,
            beneficiary=destinataire,
            conversation_id=conversation_id,
        )

        logger.info("🔍 Risk score: %s/100", risk_score)

        requires_otp = (
            montant > self.OTP_AMOUNT_THRESHOLD
            or risk_score > self.OTP_RISK_THRESHOLD
            or not beneficiary_exists
        )

        if requires_otp:
            otp_code = await self.otp_service.generate_otp(
                user_id=user_id,
                conversation_id=conversation_id,
                action="virement",
                amount=montant,
                beneficiary=destinataire,
            )

            logger.info("🔐 OTP generated for virement.")

            return {
                "response": (
                    f"Pour confirmer le virement de {montant} EUR à {destinataire}, "
                    f"veuillez entrer le code OTP envoyé par SMS."
                ),
                "status": "pending",
                "requires_otp": True,
                "otp_code": otp_code,  # TODO: Remove in production
            }

        transaction_result = await self.banking_api.execute_transfer(
            user_id=user_id,
            amount=montant,
            currency=devise,
            beneficiary=destinataire,
        )

        if transaction_result.get("success"):
            transaction_id = transaction_result["transaction_id"]
            return {
                "response": (
                    f"✅ Virement de {montant} EUR vers {destinataire} effectué avec succès. "
                    f"Référence: {transaction_id}"
                ),
                "status": "success",
                "transaction_id": transaction_id,
            }

        return {
            "response": f"❌ Le virement a échoué: {transaction_result.get('error')}",
            "status": "failed",
        }

    async def _handle_solde(
        self,
        entities: Dict[str, Any],  # noqa: ARG002
        user_id: str,
        conversation_id: str,  # noqa: ARG002
    ) -> Dict[str, Any]:
        """Handle balance inquiry"""

        logger.info("💰 Checking balance")

        balance = await self.banking_api.get_account_balance(user_id)
        available = await self.banking_api.get_available_balance(user_id)

        return {
            "response": (
                f"💰 Votre solde actuel est de {balance:.2f} EUR.\n"
                f"Disponible: {available:.2f} EUR"
            ),
            "status": "success",
            "balance": balance,
            "available": available,
        }

    async def _handle_bloquer_carte(
        self,
        entities: Dict[str, Any],  # noqa: ARG002
        user_id: str,
        conversation_id: str,
    ) -> Dict[str, Any]:
        """Handle card blocking"""

        logger.info("🔒 Blocking card")

        cards = await self.banking_api.get_user_cards(user_id)

        if not cards:
            return {
                "response": "Aucune carte trouvée sur votre compte.",
                "status": "failed",
            }

        card = cards[0]

        result = await self.banking_api.block_card(
            user_id=user_id,
            card_id=card["card_id"],
        )

        if result.get("success"):
            otp_code = await self.otp_service.generate_otp(
                user_id=user_id,
                conversation_id=conversation_id,
                action="bloquer_carte",
            )

            return {
                "response": (
                    f"🔒 Votre carte {card['card_number'][-4:]} a été bloquée avec succès. "
                    f"Code de confirmation: {otp_code}"
                ),
                "status": "success",
            }

        return {
            "response": f"Impossible de bloquer la carte: {result.get('error')}",
            "status": "failed",
        }

    async def _handle_ajouter_beneficiaire(
        self,
        entities: Dict[str, Any],
        user_id: str,
        conversation_id: str,  # noqa: ARG002
    ) -> Dict[str, Any]:
        """Handle adding beneficiary"""

        destinataire = entities.get("destinataire")
        iban = entities.get("iban")

        logger.info("👤 Adding beneficiary: %s", destinataire)

        if iban and not self.validator.validate_iban(iban):
            return {
                "response": f"L'IBAN {iban} n'est pas valide.",
                "status": "failed",
            }

        result = await self.banking_api.add_beneficiary(
            user_id=user_id,
            name=destinataire,
            iban=iban,
        )

        if result.get("success"):
            return {
                "response": (
                    f"✅ {destinataire} a été ajouté à vos bénéficiaires. "
                    f"ID: {result['beneficiary_id']}"
                ),
                "status": "success",
                "beneficiary_id": result["beneficiary_id"],
            }

        return {
            "response": f"Impossible d'ajouter le bénéficiaire: {result.get('error')}",
            "status": "failed",
        }

    async def _handle_historique(
        self,
        entities: Dict[str, Any],  # noqa: ARG002
        user_id: str,
        conversation_id: str,  # noqa: ARG002
    ) -> Dict[str, Any]:
        """Handle transaction history"""

        logger.info("📜 Getting transaction history")

        transactions = await self.banking_api.get_transaction_history(
            user_id=user_id,
            limit=5,
        )

        if not transactions:
            return {
                "response": "Aucune transaction récente.",
                "status": "success",
            }

        response_lines = ["📜 Vos dernières transactions:"]
        for index, transaction in enumerate(transactions, start=1):
            date_str = transaction["date"].strftime("%d/%m/%Y")
            amount = transaction["amount"]
            description = transaction["description"]
            response_lines.append(f"{index}. {date_str}: {amount} EUR - {description}")

        return {
            "response": "\n".join(response_lines),
            "status": "success",
            "transactions": transactions,
        }

    async def _handle_rib(
        self,
        entities: Dict[str, Any],  # noqa: ARG002
        user_id: str,
        conversation_id: str,  # noqa: ARG002
    ) -> Dict[str, Any]:
        """Handle RIB/IBAN request"""

        logger.info("📄 Getting RIB/IBAN")

        account_info = await self.banking_api.get_account_info(user_id)

        return {
            "response": (
                "📄 Vos coordonnées bancaires:\n"
                f"IBAN: {account_info['iban']}\n"
                f"BIC: {account_info['bic']}\n"
                f"Titulaire: {account_info['account_holder']}"
            ),
            "status": "success",
            "iban": account_info["iban"],
            "bic": account_info["bic"],
        }

    async def _handle_payer_facture(
        self,
        entities: Dict[str, Any],
        user_id: str,
        conversation_id: str,  # noqa: ARG002
    ) -> Dict[str, Any]:
        """Handle bill payment"""

        montant = entities.get("montant")
        facture = entities.get("facture")

        logger.info("🧾 Paying bill: %s - %s EUR", facture, montant)

        if not self.validator.validate_amount(montant):
            return {
                "response": f"Le montant {montant} EUR n'est pas valide.",
                "status": "failed",
            }

        balance = await self.banking_api.get_account_balance(user_id)
        if montant > balance:
            return {
                "response": f"Solde insuffisant. Disponible: {balance} EUR",
                "status": "failed",
            }

        result = await self.banking_api.pay_bill(
            user_id=user_id,
            amount=montant,
            biller=facture,
        )

        if result.get("success"):
            return {
                "response": (
                    f"✅ Paiement de {montant} EUR à {facture} effectué. "
                    f"Référence: {result['reference']}"
                ),
                "status": "success",
            }

        return {
            "response": f"Le paiement a échoué: {result.get('error')}",
            "status": "failed",
        }

    async def _handle_changer_plafond(
        self,
        entities: Dict[str, Any],
        user_id: str,
        conversation_id: str,
    ) -> Dict[str, Any]:
        """Handle card limit change"""

        montant = entities.get("montant")

        logger.info("💳 Changing card limit to: %s EUR", montant)

        otp_code = await self.otp_service.generate_otp(
            user_id=user_id,
            conversation_id=conversation_id,
            action="changer_plafond",
            amount=montant,
        )

        return {
            "response": (
                f"Pour modifier votre plafond à {montant} EUR, "
                f"veuillez entrer le code OTP: {otp_code}"
            ),
            "status": "pending",
            "requires_otp": True,
            "otp_code": otp_code,
        }
