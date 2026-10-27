"""Unit tests for Employee Onboarding Tool Modules."""

import sys
import os
import pytest

# Ensure parent directory is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tools.core_hr import fetch_candidate, update_status, MOCK_HR_DATABASE
from tools.m365 import create_ad_user, apply_licenses, add_user_to_groups, MOCK_M365_DIRECTORY
from tools.servicenow import book_equipment_ticket, query_ticket, MOCK_SERVICENOW_TICKETS
from tools.utils import get_crypto_password
from tools.notifier import dispatch_welcome_letter


class TestCoreHRTools:
    def test_fetch_candidate_success(self):
        cand = fetch_candidate("CAND-98342")
        assert cand["candidate_id"] == "CAND-98342"
        assert cand["first_name"] == "Sarah"
        assert cand["last_name"] == "Connor"
        assert cand["department"] == "Engineering"
        assert cand["job_title"] == "Software Engineer II"

    def test_fetch_candidate_invalid_format(self):
        with pytest.raises(ValueError, match="Invalid candidate_id format"):
            fetch_candidate("INVALID-ID-123")

    def test_fetch_candidate_not_found(self):
        with pytest.raises(ValueError, match="Candidate not found"):
            fetch_candidate("CAND-99999")

    def test_update_status_success(self):
        res = update_status(
            candidate_id="CAND-98342",
            status="Active - Provisioned",
            corporate_email="sconnor@enterprise.com",
            servicenow_ticket_id="REQ0050001",
        )
        assert res["success"] is True
        assert res["status"] == "Active - Provisioned"
        assert res["corporate_email"] == "sconnor@enterprise.com"
        assert res["servicenow_ticket_id"] == "REQ0050001"

    def test_update_status_invalid_status(self):
        with pytest.raises(ValueError, match="Invalid status"):
            update_status("CAND-98342", "Unapproved Status")


class TestM365Tools:
    def test_create_ad_user_success(self):
        res = create_ad_user(
            user_principal_name="test.user.unit@enterprise.com",
            display_name="Test User",
            given_name="Test",
            surname="User",
            department="Engineering",
            job_title="QA Engineer",
            temp_password="StrongPassword123!@",
        )
        assert res["status"] == "Created"
        assert res["user_principal_name"] == "test.user.unit@enterprise.com"
        assert res["mail_enabled"] is True
        assert "user_id" in res

    def test_create_ad_user_collision_error(self):
        # jdoe@enterprise.com is pre-seeded in MOCK_M365_DIRECTORY
        with pytest.raises(ValueError, match="Directory_User_UPN_Exists"):
            create_ad_user(
                user_principal_name="jdoe@enterprise.com",
                display_name="John Doe",
                given_name="John",
                surname="Doe",
                department="Sales",
                job_title="Account Executive",
                temp_password="StrongPassword123!@",
            )

    def test_create_ad_user_short_password(self):
        with pytest.raises(ValueError, match="temp_password must be at least 12 characters"):
            create_ad_user(
                user_principal_name="short.pw@enterprise.com",
                display_name="Short Pw",
                given_name="Short",
                surname="Pw",
                department="Sales",
                job_title="Rep",
                temp_password="short",
            )

    def test_apply_licenses_success(self):
        res = apply_licenses(user_id="jdoe@enterprise.com", sku_ids=["M365-E5", "EMS-E5"])
        assert res["status"] == "Success"
        assert "M365-E5" in res["assigned_licenses"]

    def test_apply_licenses_user_not_found(self):
        with pytest.raises(ValueError, match="User not found"):
            apply_licenses(user_id="nonexistent-user-id", sku_ids=["M365-E5"])

    def test_add_user_to_groups_success(self):
        res = add_user_to_groups(user_id="jdoe@enterprise.com", group_ids=["grp-security-review"])
        assert res["status"] == "Success"
        assert "grp-security-review" in res["memberships"]


class TestServiceNowTools:
    def test_book_equipment_ticket_success(self):
        res = book_equipment_ticket(
            requested_for_email="sconnor@enterprise.com",
            item_sku="LAPTOP-DEV-MAC-16",
            shipping_address="742 Evergreen Terrace, Springfield, OR 97477",
            urgency="high",
        )
        assert res["ticket_status"] == "Open"
        assert res["request_number"].startswith("REQ")
        assert "sys_id" in res
        assert "estimated_delivery" in res

    def test_book_equipment_ticket_invalid_urgency(self):
        with pytest.raises(ValueError, match="Invalid urgency"):
            book_equipment_ticket(
                requested_for_email="sconnor@enterprise.com",
                item_sku="LAPTOP-DEV-MAC-16",
                shipping_address="Springfield",
                urgency="critical_now",
            )

    def test_query_ticket_success(self):
        ticket = query_ticket("REQ0049281")
        assert ticket["request_number"] == "REQ0049281"
        assert ticket["item_sku"] == "LAPTOP-DEV-MAC-16"
        assert ticket["fulfillment_stage"] == "Shipped"
        assert ticket["carrier"] == "FedEx"

    def test_query_ticket_not_found(self):
        with pytest.raises(ValueError, match="ServiceNow ticket not found"):
            query_ticket("REQ9999999")


class TestUtilsAndNotifier:
    def test_get_crypto_password(self):
        pkg = get_crypto_password(length=18)
        pw = pkg["password"]
        assert len(pw) == 18
        assert pkg["meets_complexity"] is True
        assert any(c.isupper() for c in pw)
        assert any(c.islower() for c in pw)
        assert any(c.isdigit() for c in pw)
        assert any(c in "!@#$%^&*" for c in pw)

    def test_get_crypto_password_min_length(self):
        with pytest.raises(ValueError, match="Password length must be at least 14 characters"):
            get_crypto_password(length=10)

    def test_dispatch_welcome_letter_success(self):
        res = dispatch_welcome_letter(
            to_email="sconnor@gmail.com",
            employee_name="Sarah Connor",
            corporate_email="sconnor@enterprise.com",
            temp_password="SecretPass123!@",
            start_date="2026-11-15",
        )
        assert res["status"] == "Delivered"
        assert res["recipient"] == "sconnor@gmail.com"
        assert res["masked_password_verification"].startswith("Se***")
        assert res["password_delivery"] == "Encrypted Secure Channel"

    def test_dispatch_welcome_letter_invalid_email(self):
        with pytest.raises(ValueError, match="Invalid recipient email format"):
            dispatch_welcome_letter(
                to_email="invalid-email-string",
                employee_name="Sarah Connor",
                corporate_email="sconnor@enterprise.com",
                temp_password="SecretPass123!@",
                start_date="2026-11-15",
            )
