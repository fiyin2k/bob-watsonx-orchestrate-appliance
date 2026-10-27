"""Enterprise Employee Onboarding Orchestrator Agent.

Implements multi-system orchestration, Human-in-the-Loop (HITL) approval gates,
automated Entra ID name deduplication, ServiceNow ITIL provisioning, and structured audit trails.
"""

from typing import Any, Dict, List, Optional
import datetime
import logging
import uuid
import re

try:
    from .tools.core_hr import fetch_candidate, update_status
    from .tools.m365 import create_ad_user, apply_licenses, add_user_to_groups
    from .tools.servicenow import book_equipment_ticket, query_ticket
    from .tools.utils import get_crypto_password
    from .tools.notifier import dispatch_welcome_letter
except (ImportError, ValueError):
    from tools.core_hr import fetch_candidate, update_status
    from tools.m365 import create_ad_user, apply_licenses, add_user_to_groups
    from tools.servicenow import book_equipment_ticket, query_ticket
    from tools.utils import get_crypto_password
    from tools.notifier import dispatch_welcome_letter

logger = logging.getLogger("OnboardingOrchestrator")


# Department Entitlements Matrix (Mock IT Entitlement Knowledge Base)
DEPARTMENT_ENTITLEMENTS = {
    "Engineering": {
        "licenses": ["M365-E5", "GITHUB-ENTERPRISE", "AWS-DEV-ACCESS"],
        "hardware_sku": "LAPTOP-DEV-MAC-16",
        "groups": ["grp-engineering-all", "grp-github-developers", "grp-vpn-internal"],
        "cost_per_month": 120.0,
    },
    "Sales": {
        "licenses": ["M365-E3", "SALESFORCE-ENTERPRISE", "ZOOM-PRO"],
        "hardware_sku": "LAPTOP-SALES-WIN-14",
        "groups": ["grp-sales-global", "grp-crm-access"],
        "cost_per_month": 95.0,
    },
    "Product": {
        "licenses": ["M365-E5", "JIRA-ENTERPRISE", "MIRO-PRO"],
        "hardware_sku": "LAPTOP-PROD-MAC-14",
        "groups": ["grp-product-all", "grp-roadmap-viewers"],
        "cost_per_month": 110.0,
    },
    "Finance": {
        "licenses": ["M365-E3", "NETSUITE-PRO"],
        "hardware_sku": "LAPTOP-FIN-WIN-14",
        "groups": ["grp-finance-all", "grp-erp-restricted"],
        "cost_per_month": 85.0,
    },
    "Default": {
        "licenses": ["M365-E3"],
        "hardware_sku": "LAPTOP-STANDARD-WIN-14",
        "groups": ["grp-all-employees"],
        "cost_per_month": 60.0,
    },
}


class OnboardingOrchestratorAgent:
    """Enterprise Employee Onboarding Orchestrator Agent."""

    def __init__(self, tenant_domain: str = "enterprise.com"):
        self.tenant_domain = tenant_domain
        self.agent_name = "onboarding-orchestrator"
        self.version = "1.0.0"
        self.model_id = "ibm/granite-3-1-8b-instruct"
        self.audit_log: List[Dict[str, Any]] = []

    def _log_event(self, correlation_id: str, stage: str, details: Dict[str, Any]) -> None:
        """Record structured JSON audit log entry with correlation ID."""
        scrubbed_details = {}
        for k, v in details.items():
            if "password" in k.lower():
                scrubbed_details[k] = "[REDACTED-CREDENTIAL]"
            else:
                scrubbed_details[k] = v

        entry = {
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "correlation_id": correlation_id,
            "agent": self.agent_name,
            "stage": stage,
            "details": scrubbed_details,
        }
        self.audit_log.append(entry)
        logger.info("Agent Audit Event: %s", entry)

    def generate_candidate_upn(self, first_name: str, last_name: str, index: int = 1) -> str:
        """Derive standard corporate email/UPN with suffix handling for deduplication."""
        clean_first = re.sub(r"[^a-zA-Z]", "", first_name).lower()
        clean_last = re.sub(r"[^a-zA-Z]", "", last_name).lower()
        
        # Primary pattern: first initial + last name (e.g., sconnor@enterprise.com)
        # Collision pattern: first initial + last name + index (e.g., jdoe2@enterprise.com)
        base = f"{clean_first[0]}{clean_last}"
        if index > 1:
            base = f"{base}{index}"
        return f"{base}@{self.tenant_domain}"

    def build_onboarding_blueprint(self, candidate_id: str) -> Dict[str, Any]:
        """Fetch candidate details and construct the Human-in-the-Loop review payload.

        Args:
            candidate_id: Master HR identifier.

        Returns:
            Dict representing the detailed provisioning proposal requiring manager sign-off.
        """
        correlation_id = f"corr-{uuid.uuid4().hex[:8]}"
        candidate = fetch_candidate(candidate_id)
        
        dept = candidate.get("department", "Default")
        entitlements = DEPARTMENT_ENTITLEMENTS.get(dept, DEPARTMENT_ENTITLEMENTS["Default"])
        
        suggested_upn = self.generate_candidate_upn(candidate["first_name"], candidate["last_name"])
        password_pkg = get_crypto_password(length=16)

        blueprint = {
            "correlation_id": correlation_id,
            "candidate_id": candidate["candidate_id"],
            "employee_name": f"{candidate['first_name']} {candidate['last_name']}",
            "department": candidate["department"],
            "job_title": candidate["job_title"],
            "manager_email": candidate["manager_email"],
            "personal_email": candidate["personal_email"],
            "start_date": candidate["start_date"],
            "shipping_address": candidate.get("shipping_address", "Default HQ Office"),
            "proposed_upn": suggested_upn,
            "assigned_licenses": entitlements["licenses"],
            "hardware_sku": entitlements["hardware_sku"],
            "security_groups": entitlements["groups"],
            "estimated_monthly_cost": entitlements["cost_per_month"],
            "temp_password": password_pkg["password"],
            "hitl_approval_required": True,
            "status": "Awaiting_Manager_Approval",
        }

        self._log_event(correlation_id, "blueprint_generated", {
            "candidate_id": candidate_id,
            "proposed_upn": suggested_upn,
            "hardware_sku": entitlements["hardware_sku"],
        })

        return blueprint

    def execute_unified_onboarding(
        self,
        blueprint: Dict[str, Any],
        approved: bool,
        approver_email: str,
        comments: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute Workflow 1: End-to-End Automated Onboarding Orchestration.

        Args:
            blueprint: The pre-generated onboarding proposal.
            approved: Manager approval decision boolean.
            approver_email: Email of approving manager.
            comments: Optional comments or rejection reason.

        Returns:
            Dict summarizing the completed orchestration state.
        """
        correlation_id = blueprint.get("correlation_id", f"corr-{uuid.uuid4().hex[:8]}")
        candidate_id = blueprint["candidate_id"]

        # Case 1: Human-in-the-Loop Rejection
        if not approved:
            rejection_reason = comments or "Manager rejected the onboarding configuration."
            self._log_event(correlation_id, "hitl_rejected", {
                "candidate_id": candidate_id,
                "approver": approver_email,
                "reason": rejection_reason,
            })
            
            # Update HR status to Onboarding Aborted
            update_status(candidate_id, "Onboarding Aborted")
            
            return {
                "correlation_id": correlation_id,
                "candidate_id": candidate_id,
                "status": "Aborted",
                "message": f"Onboarding aborted by {approver_email}: {rejection_reason}",
                "accounts_created": 0,
                "tickets_opened": 0,
                "audit_timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            }

        # Case 2: Human-in-the-Loop Approval - Execute Orchestrated Actions
        self._log_event(correlation_id, "hitl_approved", {
            "candidate_id": candidate_id,
            "approver": approver_email,
            "comments": comments or "Approved",
        })

        candidate = fetch_candidate(candidate_id)
        first_name = candidate["first_name"]
        last_name = candidate["last_name"]
        display_name = f"{first_name} {last_name}"
        temp_pw = blueprint["temp_password"]

        # Step 1: Create Microsoft Entra ID Account with collision recovery
        upn_attempt = blueprint["proposed_upn"]
        created_user: Optional[Dict[str, Any]] = None
        attempt_index = 1
        
        while attempt_index <= 5:
            try:
                created_user = create_ad_user(
                    user_principal_name=upn_attempt,
                    display_name=display_name,
                    given_name=first_name,
                    surname=last_name,
                    department=blueprint["department"],
                    job_title=blueprint["job_title"],
                    temp_password=temp_pw,
                )
                self._log_event(correlation_id, "entra_id_created", {
                    "user_id": created_user["user_id"],
                    "upn": upn_attempt,
                    "attempt": attempt_index,
                })
                break
            except ValueError as e:
                if "Directory_User_UPN_Exists" in str(e):
                    attempt_index += 1
                    upn_attempt = self.generate_candidate_upn(first_name, last_name, index=attempt_index)
                    self._log_event(correlation_id, "upn_collision_deduplicated", {
                        "collision_attempt": attempt_index - 1,
                        "next_upn_attempt": upn_attempt,
                    })
                else:
                    raise

        if not created_user:
            raise RuntimeError(f"Failed to create Entra ID account after {attempt_index} attempts.")

        final_upn = created_user["user_principal_name"]
        user_id = created_user["user_id"]

        # Step 2: Assign Software Licenses
        license_res = apply_licenses(user_id=user_id, sku_ids=blueprint["assigned_licenses"])
        self._log_event(correlation_id, "licenses_assigned", {
            "user_id": user_id,
            "assigned_licenses": license_res["assigned_licenses"],
        })

        # Step 3: Assign Security Groups
        group_res = add_user_to_groups(user_id=user_id, group_ids=blueprint["security_groups"])
        self._log_event(correlation_id, "security_groups_assigned", {
            "user_id": user_id,
            "memberships": group_res["memberships"],
        })

        # Step 4: Create ServiceNow IT Provisioning Ticket
        sn_res = book_equipment_ticket(
            requested_for_email=final_upn,
            item_sku=blueprint["hardware_sku"],
            shipping_address=blueprint["shipping_address"],
            urgency="medium",
        )
        ticket_number = sn_res["request_number"]
        self._log_event(correlation_id, "servicenow_ticket_created", {
            "ticket_number": ticket_number,
            "sku": blueprint["hardware_sku"],
        })

        # Step 5: Dispatch External Welcome Email to Candidate Personal Inbox
        email_res = dispatch_welcome_letter(
            to_email=blueprint["personal_email"],
            employee_name=display_name,
            corporate_email=final_upn,
            temp_password=temp_pw,
            start_date=blueprint["start_date"],
        )
        self._log_event(correlation_id, "welcome_email_dispatched", {
            "message_id": email_res["message_id"],
            "recipient": blueprint["personal_email"],
        })

        # Step 6: Write-Back System Identifiers to Core HR Database
        update_status(
            candidate_id=candidate_id,
            status="Active - Provisioned",
            corporate_email=final_upn,
            servicenow_ticket_id=ticket_number,
        )
        self._log_event(correlation_id, "hr_status_synchronized", {
            "candidate_id": candidate_id,
            "status": "Active - Provisioned",
            "corporate_email": final_upn,
            "servicenow_ticket_id": ticket_number,
        })

        return {
            "correlation_id": correlation_id,
            "candidate_id": candidate_id,
            "status": "Provisioned",
            "corporate_email": final_upn,
            "entra_id_user_id": user_id,
            "servicenow_ticket_id": ticket_number,
            "estimated_delivery": sn_res["estimated_delivery"],
            "welcome_email_message_id": email_res["message_id"],
            "completed_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }

    def track_onboarding_progress(self, request_number: str) -> Dict[str, Any]:
        """Execute Workflow 2: Onboarding Progress Tracker.

        Args:
            request_number: Target ServiceNow REQ ticket number.

        Returns:
            Dict containing detailed fulfillment status and delivery tracking.
        """
        ticket = query_ticket(request_number)
        return {
            "request_number": ticket["request_number"],
            "requested_for": ticket["requested_for_email"],
            "item_sku": ticket["item_sku"],
            "ticket_status": ticket["ticket_status"],
            "fulfillment_stage": ticket["fulfillment_stage"],
            "carrier": ticket.get("carrier"),
            "tracking_number": ticket.get("tracking_number"),
            "estimated_delivery": ticket["estimated_delivery"],
        }
