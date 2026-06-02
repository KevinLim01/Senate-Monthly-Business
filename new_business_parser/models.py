from dataclasses import dataclass


@dataclass
class BusinessRecord:
    raw_business_name: str
    clean_business_name: str
    mailing_address: str
    mailing_street: str
    mailing_city: str
    mailing_state: str
    mailing_zip: str
    status: str
    reason: str
    page: int | None = None
    senate_district_24_status: str = "not checked"
    senate_district_24_reason: str = ""
