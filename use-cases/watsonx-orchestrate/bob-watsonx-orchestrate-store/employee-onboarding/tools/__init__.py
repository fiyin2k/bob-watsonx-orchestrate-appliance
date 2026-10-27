"""Onboarding tools suite for watsonx Orchestrate agent."""

from .core_hr import fetch_candidate, update_status
from .m365 import create_ad_user, apply_licenses, add_user_to_groups
from .servicenow import book_equipment_ticket, query_ticket
from .utils import get_crypto_password
from .notifier import dispatch_welcome_letter

__all__ = [
    "fetch_candidate",
    "update_status",
    "create_ad_user",
    "apply_licenses",
    "add_user_to_groups",
    "book_equipment_ticket",
    "query_ticket",
    "get_crypto_password",
    "dispatch_welcome_letter",
]
