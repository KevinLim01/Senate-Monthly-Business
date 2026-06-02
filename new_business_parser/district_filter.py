from __future__ import annotations

from .models import BusinessRecord
from .cleaner import title_case_city, normalize_state

ALLOWED_LOCALITIES = {
    "NEWPORT NEWS",
    "WILLIAMSBURG",
    "YORKTOWN",
    "POQUOSON",
}


def check_district24_by_locality(records: list[BusinessRecord]) -> list[BusinessRecord]:
    """Fast local District 24 screening.

    No LLM/API call. This uses the user's requested practical rule:
    keep only VA mailing addresses in Newport News, Williamsburg, Yorktown, or Poquoson.
    Anything else is moved to the rejected/review section.
    """
    updated: list[BusinessRecord] = []

    for record in records:
        state = normalize_state(record.mailing_state)
        city = title_case_city(record.mailing_city)
        city_key = city.upper().strip()

        record.mailing_state = state
        record.mailing_city = city

        if state != "VA":
            record.senate_district_24_status = "no"
            record.senate_district_24_reason = "Mailing address is not in Virginia"
            if record.status == "accepted":
                record.status = "rejected"
                record.reason = "Outside District 24 locality filter"
        elif city_key not in ALLOWED_LOCALITIES:
            record.senate_district_24_status = "no"
            record.senate_district_24_reason = (
                "Mailing city is not Newport News, Williamsburg, Yorktown, or Poquoson"
            )
            if record.status == "accepted":
                record.status = "rejected"
                record.reason = "Outside District 24 locality filter"
        else:
            record.senate_district_24_status = "yes"
            record.senate_district_24_reason = (
                "Virginia address in Newport News, Williamsburg, Yorktown, or Poquoson"
            )

        updated.append(record)

    return updated
