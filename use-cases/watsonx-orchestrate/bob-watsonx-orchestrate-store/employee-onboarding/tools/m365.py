"""Microsoft 365 (Entra ID / Graph API) Integration Tool Module.

Provides deterministic identity lifecycle operations and group management.
"""

from typing import Any, Dict, List, Optional
import uuid

# Mock Active Directory / Entra ID User Registry
MOCK_M365_DIRECTORY: Dict[str, Dict[str, Any]] = {
    # Pre-existing user to demonstrate collision handling
    "jdoe@enterprise.com": {
        "user_id": "aad-0001-existing-user",
        "user_principal_name": "jdoe@enterprise.com",
        "display_name": "Jonathan Doe",
        "department": "Finance",
        "job_title": "Senior Accountant",
        "mail_enabled": True,
        "licenses": ["M365-E3"],
        "groups": ["grp-finance-all"],
    }
}


def create_ad_user(
    user_principal_name: str,
    display_name: str,
    given_name: str,
    surname: str,
    department: str,
    job_title: str,
    temp_password: str,
) -> Dict[str, Any]:
    """Register a new corporate identity inside Microsoft Entra ID.

    Args:
        user_principal_name: Target corporate UPN / email (e.g., sconnor@enterprise.com).
        display_name: Full display name (e.g., Sarah Connor).
        given_name: First name.
        surname: Last name.
        department: Corporate department name.
        job_title: Official corporate job title.
        temp_password: Secure initial temporary password.

    Returns:
        Dict containing user_id, user_principal_name, status, and mail_enabled boolean.

    Raises:
        ValueError: If required fields are missing or if user_principal_name already exists (collision).
    """
    if not user_principal_name or "@" not in user_principal_name:
        raise ValueError(f"Invalid user_principal_name: '{user_principal_name}'")

    if not temp_password or len(temp_password) < 12:
        raise ValueError("temp_password must be at least 12 characters.")

    upn = user_principal_name.lower().strip()
    if upn in MOCK_M365_DIRECTORY:
        raise ValueError(f"Directory_User_UPN_Exists: User principal name '{upn}' already exists in Entra ID.")

    user_id = f"aad-{uuid.uuid4().hex[:8]}-{uuid.uuid4().hex[:4]}"
    record = {
        "user_id": user_id,
        "user_principal_name": upn,
        "display_name": display_name,
        "given_name": given_name,
        "surname": surname,
        "department": department,
        "job_title": job_title,
        "mail_enabled": True,
        "licenses": [],
        "groups": [],
    }
    MOCK_M365_DIRECTORY[upn] = record

    return {
        "user_id": user_id,
        "user_principal_name": upn,
        "status": "Created",
        "mail_enabled": True,
    }


def apply_licenses(user_id: str, sku_ids: List[str]) -> Dict[str, Any]:
    """Assign product license SKUs to an active Entra ID account.

    Args:
        user_id: Active Entra ID UUID or UPN.
        sku_ids: List of license SKUs to attach (e.g., ["M365-E5", "EMS-E5"]).

    Returns:
        Dict detailing assignment status and assigned SKU list.

    Raises:
        ValueError: If user is not found or sku_ids list is empty.
    """
    if not sku_ids:
        raise ValueError("sku_ids must contain at least one license SKU.")

    target_record: Optional[Dict[str, Any]] = None
    for rec in MOCK_M365_DIRECTORY.values():
        if rec.get("user_id") == user_id or rec.get("user_principal_name") == user_id:
            target_record = rec
            break

    if not target_record:
        raise ValueError(f"User not found in Entra ID directory: {user_id}")

    current_licenses = set(target_record.get("licenses", []))
    current_licenses.update(sku_ids)
    target_record["licenses"] = sorted(list(current_licenses))

    return {
        "user_id": target_record["user_id"],
        "user_principal_name": target_record["user_principal_name"],
        "status": "Success",
        "assigned_licenses": target_record["licenses"],
    }


def add_user_to_groups(user_id: str, group_ids: List[str]) -> Dict[str, Any]:
    """Add an active user account to targeted directory security and distribution groups.

    Args:
        user_id: Target user UUID or UPN.
        group_ids: List of group IDs or aliases to join.

    Returns:
        Dict confirming group memberships.

    Raises:
        ValueError: If user is not found or group_ids is empty.
    """
    if not group_ids:
        raise ValueError("group_ids must contain at least one group identifier.")

    target_record: Optional[Dict[str, Any]] = None
    for rec in MOCK_M365_DIRECTORY.values():
        if rec.get("user_id") == user_id or rec.get("user_principal_name") == user_id:
            target_record = rec
            break

    if not target_record:
        raise ValueError(f"User not found in Entra ID directory: {user_id}")

    current_groups = set(target_record.get("groups", []))
    current_groups.update(group_ids)
    target_record["groups"] = sorted(list(current_groups))

    return {
        "user_id": target_record["user_id"],
        "user_principal_name": target_record["user_principal_name"],
        "status": "Success",
        "memberships": target_record["groups"],
    }
