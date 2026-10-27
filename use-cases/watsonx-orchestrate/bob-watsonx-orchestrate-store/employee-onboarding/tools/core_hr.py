"""Core HR Integration Tool Module.

Provides deterministic candidate retrieval and status tracking capabilities.
"""

from typing import Any, Dict, Optional
import re

# Mock HR In-Memory Database
MOCK_HR_DATABASE: Dict[str, Dict[str, Any]] = {
    "CAND-98342": {
        "candidate_id": "CAND-98342",
        "first_name": "Sarah",
        "last_name": "Connor",
        "department": "Engineering",
        "job_title": "Software Engineer II",
        "manager_email": "m.silva@enterprise.com",
        "personal_email": "sconnor@gmail.com",
        "shipping_address": "742 Evergreen Terrace, Springfield, OR 97477",
        "start_date": "2026-11-15",
        "onboarding_status": "Offer Accepted",
        "corporate_email": None,
        "servicenow_ticket_id": None,
    },
    "CAND-55410": {
        "candidate_id": "CAND-55410",
        "first_name": "John",
        "last_name": "Doe",
        "department": "Sales",
        "job_title": "Account Executive",
        "manager_email": "r.sterling@enterprise.com",
        "personal_email": "jdoe.personal@gmail.com",
        "shipping_address": "100 Market St, San Francisco, CA 94105",
        "start_date": "2026-11-20",
        "onboarding_status": "Offer Accepted",
        "corporate_email": None,
        "servicenow_ticket_id": None,
    },
    "CAND-11029": {
        "candidate_id": "CAND-11029",
        "first_name": "Alex",
        "last_name": "Morgan",
        "department": "Product",
        "job_title": "Product Manager",
        "manager_email": "k.patel@enterprise.com",
        "personal_email": "alex.morgan.work@outlook.com",
        "shipping_address": "500 Madison Ave, New York, NY 10022",
        "start_date": "2026-12-01",
        "onboarding_status": "Offer Accepted",
        "corporate_email": None,
        "servicenow_ticket_id": None,
    },
}

VALID_STATUSES = {
    "Offer Accepted",
    "Approval Pending",
    "Provisioning Active",
    "Active - Provisioned",
    "Failed",
    "Onboarding Aborted",
}


def fetch_candidate(candidate_id: str) -> Dict[str, Any]:
    """Retrieve new-hire candidate onboarding profile details from Core HR.

    Args:
        candidate_id: Unique candidate reference identifier (e.g., CAND-98342).

    Returns:
        Dict containing candidate details such as candidate_id, first_name,
        last_name, department, job_title, manager_email, personal_email,
        shipping_address, start_date, and onboarding_status.

    Raises:
        ValueError: If candidate_id is invalid or candidate is not found.
    """
    if not candidate_id or not re.match(r"^CAND-\d+$", candidate_id):
        raise ValueError(f"Invalid candidate_id format: '{candidate_id}'. Expected format 'CAND-<digits>'.")

    candidate = MOCK_HR_DATABASE.get(candidate_id)
    if not candidate:
        raise ValueError(f"Candidate not found in Core HR database: {candidate_id}")

    # Return a shallow copy to prevent unauthorized direct mutation
    return dict(candidate)


def update_status(
    candidate_id: str,
    status: str,
    corporate_email: Optional[str] = None,
    servicenow_ticket_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Update onboarding status, enterprise email, and ticket IDs in Core HR.

    Args:
        candidate_id: Target candidate identifier.
        status: Updated lifecycle status.
        corporate_email: Optional generated enterprise email address.
        servicenow_ticket_id: Optional IT provisioning ticket reference.

    Returns:
        Dict indicating operation success and updated timestamp.

    Raises:
        ValueError: If candidate is not found or status is unrecognized.
    """
    if candidate_id not in MOCK_HR_DATABASE:
        raise ValueError(f"Candidate not found in Core HR database: {candidate_id}")

    if status not in VALID_STATUSES:
        raise ValueError(f"Invalid status '{status}'. Allowed statuses: {sorted(list(VALID_STATUSES))}")

    record = MOCK_HR_DATABASE[candidate_id]
    record["onboarding_status"] = status
    if corporate_email:
        record["corporate_email"] = corporate_email
    if servicenow_ticket_id:
        record["servicenow_ticket_id"] = servicenow_ticket_id

    return {
        "success": True,
        "candidate_id": candidate_id,
        "status": status,
        "corporate_email": record.get("corporate_email"),
        "servicenow_ticket_id": record.get("servicenow_ticket_id"),
    }
