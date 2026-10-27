"""Candidate Orientation & Notification Tool Module.

Delivers secure temporary credentials and orientation package to new hire's personal email.
"""

from typing import Any, Dict
import datetime
import uuid
import re


def dispatch_welcome_letter(
    to_email: str,
    employee_name: str,
    corporate_email: str,
    temp_password: str,
    start_date: str,
) -> Dict[str, Any]:
    """Deliver security credentials and orientation pack to candidate's personal email.

    Args:
        to_email: Candidate's personal email address.
        employee_name: Employee's full display name.
        corporate_email: Allocated enterprise email address.
        temp_password: Cryptographically generated temporary password.
        start_date: Official first day of employment (YYYY-MM-DD).

    Returns:
        Dict detailing message dispatch UUID, delivery channel, timestamp, and status.

    Raises:
        ValueError: If email format is invalid or required fields are missing.
    """
    if not to_email or not re.match(r"^[\w\.-]+@[\w\.-]+\.\w+$", to_email):
        raise ValueError(f"Invalid recipient email format: '{to_email}'")

    if not employee_name or not corporate_email or not temp_password or not start_date:
        raise ValueError("All notification parameters (to_email, employee_name, corporate_email, temp_password, start_date) are required.")

    message_id = f"msg-{uuid.uuid4().hex[:12]}"
    dispatch_time = datetime.datetime.now(datetime.timezone.utc).isoformat()

    # Formulate masked receipt (preventing plain-text password leakage in return payload)
    masked_pw = f"{temp_password[:2]}***{temp_password[-2:]}" if len(temp_password) >= 4 else "***"

    return {
        "message_id": message_id,
        "recipient": to_email,
        "employee_name": employee_name,
        "corporate_email": corporate_email,
        "password_delivery": "Encrypted Secure Channel",
        "masked_password_verification": masked_pw,
        "start_date": start_date,
        "status": "Delivered",
        "dispatch_timestamp": dispatch_time,
    }
