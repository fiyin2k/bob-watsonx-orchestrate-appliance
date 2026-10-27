"""ServiceNow ITIL Integration Tool Module.

Provides deterministic IT hardware catalog requests and fulfillment tracking.
"""

from typing import Any, Dict, Optional
import datetime
import uuid

# Mock ServiceNow Table Registry
MOCK_SERVICENOW_TICKETS: Dict[str, Dict[str, Any]] = {
    "REQ0049281": {
        "sys_id": "sn-req-88310923",
        "request_number": "REQ0049281",
        "requested_for_email": "sconnor@enterprise.com",
        "item_sku": "LAPTOP-DEV-MAC-16",
        "shipping_address": "742 Evergreen Terrace, Springfield, OR 97477",
        "urgency": "medium",
        "ticket_status": "In Progress",
        "fulfillment_stage": "Shipped",
        "carrier": "FedEx",
        "tracking_number": "FX-88910293",
        "estimated_delivery": (datetime.date.today() + datetime.timedelta(days=3)).isoformat(),
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
}

VALID_URGENCIES = {"low", "medium", "high"}


def book_equipment_ticket(
    requested_for_email: str,
    item_sku: str,
    shipping_address: str,
    urgency: str = "medium",
) -> Dict[str, Any]:
    """Submit standard asset and security badge catalog requests in ServiceNow.

    Args:
        requested_for_email: Corporate email of recipient.
        item_sku: Standard hardware SKU (e.g., LAPTOP-DEV-MAC-16, LAPTOP-SALES-WIN-14).
        shipping_address: Direct destination address for asset delivery.
        urgency: Urgency level (low, medium, high).

    Returns:
        Dict containing sys_id, request_number, ticket_status, and estimated_delivery date.

    Raises:
        ValueError: If email format is invalid, item_sku is missing, or urgency is unrecognized.
    """
    if not requested_for_email or "@" not in requested_for_email:
        raise ValueError(f"Invalid recipient email: '{requested_for_email}'")

    if not item_sku:
        raise ValueError("item_sku is required.")

    if not shipping_address:
        raise ValueError("shipping_address is required.")

    if urgency not in VALID_URGENCIES:
        raise ValueError(f"Invalid urgency '{urgency}'. Expected one of: {sorted(list(VALID_URGENCIES))}")

    # Generate sequential or unique ticket number
    ticket_count = len(MOCK_SERVICENOW_TICKETS) + 50000
    req_num = f"REQ{ticket_count:07d}"
    sys_id = f"sn-req-{uuid.uuid4().hex[:8]}"
    est_date = (datetime.date.today() + datetime.timedelta(days=5)).isoformat()

    ticket_record = {
        "sys_id": sys_id,
        "request_number": req_num,
        "requested_for_email": requested_for_email,
        "item_sku": item_sku,
        "shipping_address": shipping_address,
        "urgency": urgency,
        "ticket_status": "Open",
        "fulfillment_stage": "Procurement Approved",
        "carrier": "TBD",
        "tracking_number": None,
        "estimated_delivery": est_date,
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }

    MOCK_SERVICENOW_TICKETS[req_num] = ticket_record

    return {
        "sys_id": sys_id,
        "request_number": req_num,
        "ticket_status": "Open",
        "estimated_delivery": est_date,
    }


def query_ticket(request_number: str) -> Dict[str, Any]:
    """Track shipment, fulfillment, and closure state of standard IT catalog requests.

    Args:
        request_number: Target REQ ticket identifier (e.g., REQ0049281).

    Returns:
        Dict containing full ticket fulfillment state, tracking information, and status.

    Raises:
        ValueError: If request_number is missing or not found.
    """
    if not request_number:
        raise ValueError("request_number is required.")

    ticket = MOCK_SERVICENOW_TICKETS.get(request_number)
    if not ticket:
        raise ValueError(f"ServiceNow ticket not found: {request_number}")

    return dict(ticket)
