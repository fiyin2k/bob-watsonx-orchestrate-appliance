"""Integration tests for Enterprise Onboarding Orchestrator Agent Workflows.

Covers:
- TC-OB-001: End-to-End Success Path (Happy Path with Sarah Connor CAND-98342)
- TC-OB-002: Username Collision Handling (Entra ID Conflict Deduplication with John Doe CAND-55410)
- TC-OB-003: Rejection Handling (Manager Rejection cleanly aborts workflow with zero side effects)
- TC-OB-004: Validation & Exception Handling (Invalid/Missing Candidate)
- TC-OB-005: Hardware Status Monitoring Workflow
"""

import sys
import os
import pytest

# Ensure parent directory is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agent import OnboardingOrchestratorAgent
from tools.core_hr import fetch_candidate, MOCK_HR_DATABASE
from tools.m365 import MOCK_M365_DIRECTORY
from tools.servicenow import MOCK_SERVICENOW_TICKETS


class TestOnboardingWorkflows:

    def setup_method(self):
        self.agent = OnboardingOrchestratorAgent(tenant_domain="enterprise.com")

    def test_tc_ob_001_happy_path(self):
        """TC-OB-001: Verify successful end-to-end multi-system provisioning."""
        candidate_id = "CAND-98342"
        
        # Step 1: Generate blueprint for HITL review
        blueprint = self.agent.build_onboarding_blueprint(candidate_id)
        assert blueprint["candidate_id"] == candidate_id
        assert blueprint["employee_name"] == "Sarah Connor"
        assert blueprint["department"] == "Engineering"
        assert blueprint["proposed_upn"] == "sconnor@enterprise.com"
        assert blueprint["hardware_sku"] == "LAPTOP-DEV-MAC-16"
        assert blueprint["hitl_approval_required"] is True
        assert "M365-E5" in blueprint["assigned_licenses"]

        # Step 2: Simulate Manager Approval
        result = self.agent.execute_unified_onboarding(
            blueprint=blueprint,
            approved=True,
            approver_email="m.silva@enterprise.com",
            comments="Approved for Engineering new hire setup",
        )

        # Step 3: Verify execution outputs
        assert result["status"] == "Provisioned"
        assert result["corporate_email"] == "sconnor@enterprise.com"
        assert result["servicenow_ticket_id"].startswith("REQ")
        assert "entra_id_user_id" in result
        assert "welcome_email_message_id" in result

        # Step 4: Verify external systems state
        # Core HR
        updated_hr = fetch_candidate(candidate_id)
        assert updated_hr["onboarding_status"] == "Active - Provisioned"
        assert updated_hr["corporate_email"] == "sconnor@enterprise.com"
        assert updated_hr["servicenow_ticket_id"] == result["servicenow_ticket_id"]

        # Entra ID
        entra_user = MOCK_M365_DIRECTORY["sconnor@enterprise.com"]
        assert entra_user["display_name"] == "Sarah Connor"
        assert "M365-E5" in entra_user["licenses"]
        assert "grp-engineering-all" in entra_user["groups"]

        # ServiceNow
        ticket = MOCK_SERVICENOW_TICKETS[result["servicenow_ticket_id"]]
        assert ticket["requested_for_email"] == "sconnor@enterprise.com"
        assert ticket["item_sku"] == "LAPTOP-DEV-MAC-16"

        # Audit Logs
        assert any(log["stage"] == "hitl_approved" for log in self.agent.audit_log)
        assert any(log["stage"] == "hr_status_synchronized" for log in self.agent.audit_log)

    def test_tc_ob_002_username_collision_deduplication(self):
        """TC-OB-002: Ensure robust recovery and UPN deduplication when conflict occurs in Entra ID."""
        candidate_id = "CAND-55410"  # John Doe -> standard UPN would be jdoe@enterprise.com
        
        # Verify jdoe@enterprise.com already exists in Entra ID directory
        assert "jdoe@enterprise.com" in MOCK_M365_DIRECTORY

        # Step 1: Generate blueprint (proposes jdoe@enterprise.com initially)
        blueprint = self.agent.build_onboarding_blueprint(candidate_id)
        assert blueprint["proposed_upn"] == "jdoe@enterprise.com"

        # Step 2: Execute onboarding with approval
        result = self.agent.execute_unified_onboarding(
            blueprint=blueprint,
            approved=True,
            approver_email="r.sterling@enterprise.com",
            comments="Approved Sales executive setup",
        )

        # Step 3: Verify deduplication handled conflict by assigning jdoe2@enterprise.com
        assert result["status"] == "Provisioned"
        assert result["corporate_email"] == "jdoe2@enterprise.com"
        assert "jdoe2@enterprise.com" in MOCK_M365_DIRECTORY

        # Verify audit log captures deduplication event
        assert any(log["stage"] == "upn_collision_deduplicated" for log in self.agent.audit_log)

    def test_tc_ob_003_rejection_handling(self):
        """TC-OB-003: Ensure workflow terminates cleanly when manager rejects without side effects."""
        candidate_id = "CAND-11029"  # Alex Morgan
        
        blueprint = self.agent.build_onboarding_blueprint(candidate_id)
        
        # Simulate manager rejection
        result = self.agent.execute_unified_onboarding(
            blueprint=blueprint,
            approved=False,
            approver_email="k.patel@enterprise.com",
            comments="Incorrect department assigned - must be Engineering not Product",
        )

        assert result["status"] == "Aborted"
        assert result["accounts_created"] == 0
        assert result["tickets_opened"] == 0
        assert "Incorrect department assigned" in result["message"]

        # Verify no Entra ID account was created for Alex Morgan
        assert "amorgan@enterprise.com" not in MOCK_M365_DIRECTORY

        # Verify HR status updated to Onboarding Aborted
        updated_hr = fetch_candidate(candidate_id)
        assert updated_hr["onboarding_status"] == "Onboarding Aborted"

    def test_tc_ob_004_invalid_candidate_exception(self):
        """TC-OB-004: Validate exception handling for missing candidate."""
        with pytest.raises(ValueError, match="Candidate not found"):
            self.agent.build_onboarding_blueprint("CAND-00000")

    def test_tc_ob_005_status_monitoring_workflow(self):
        """TC-OB-005: Validate Workflow 2 (Onboarding progress tracking)."""
        tracking_info = self.agent.track_onboarding_progress("REQ0049281")
        assert tracking_info["request_number"] == "REQ0049281"
        assert tracking_info["ticket_status"] == "In Progress"
        assert tracking_info["fulfillment_stage"] == "Shipped"
        assert tracking_info["carrier"] == "FedEx"
        assert tracking_info["tracking_number"] == "FX-88910293"
