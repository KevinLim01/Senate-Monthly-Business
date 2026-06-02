from __future__ import annotations

import json
import os
from typing import Any

from .models import BusinessRecord
from .cleaner import clean_business_name, title_case_address, title_case_city, normalize_state


def _get_gemini_model():
    """Create a Gemini model lazily so normal non-LLM runs do not need Gemini imported."""
    try:
        import google.generativeai as genai
    except ImportError as exc:
        raise ImportError(
            "Gemini support requires google-generativeai. Run: pip install -r requirements.txt"
        ) from exc

    api_key = os.getenv("GEMINI_API_KEY")
    model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    if not api_key:
        raise ValueError("Missing GEMINI_API_KEY. Add it to .env or your shell environment.")

    genai.configure(api_key=api_key)
    return genai.GenerativeModel(model_name)


def review_records_with_gemini(records: list[BusinessRecord]) -> list[BusinessRecord]:
    """Use Gemini to review accepted/rejected status and cleaned names.

    This is optional. The rule-based parser works without Gemini.
    Run with --use-llm only when you want Gemini to judge weird names.
    """
    model = _get_gemini_model()

    payload = [
        {
            "raw_business_name": r.raw_business_name,
            "clean_business_name": r.clean_business_name,
            "street_address": r.mailing_street,
            "city": r.mailing_city,
            "state": r.mailing_state,
            "zip_code": r.mailing_zip,
            "status": r.status,
            "reason": r.reason,
            "page": r.page,
        }
        for r in records
    ]

    prompt = f"""
You are cleaning a city new-business list for a mailing-address spreadsheet.

For each record, decide whether the business name should stay in the accepted business list or be moved to the rejected review section.

Rules:
- Remove legal endings from clean_business_name, including LLC, L.L.C., INC, INC., PLLC, CORP, CORPORATION, COMPANY, CO, LTD, LLP, LP, PC.
- Capitalize clean_business_name in normal title case, not all caps. Example: A NEW BEGINNING JANITORIAL SERVICE becomes A New Beginning Janitorial Service.
- Capitalize street_address and city in normal title case. Keep state as VA.
- Keep real business names and trade names.
- Reject names that are only a person's name, like JACKSON AUDREY MARIE or HASAN SALAAM.
- Keep names that have clear business terms like CLEANING, PAINTING, STUDIO, TRANSPORTATION, BOUTIQUE, LAWN, CONTRACTORS, SALON, COFFEE, RESTAURANT, SERVICES, SOLUTIONS, DENTAL, CLIMATE, ELECTRIC, FLOORING.
- Keep street_address, city, state, and zip_code exactly as given unless there is a clear typo from parsing.
- Do not invent addresses.
- Do not add records.
- Return JSON only. No markdown.

Input records:
{json.dumps(payload, indent=2)}

Return a JSON list. Each object must have exactly:
- raw_business_name
- clean_business_name
- street_address
- city
- state
- zip_code
- status: accepted or rejected
- reason
- page
"""

    response = model.generate_content(prompt)
    text = (response.text or "").strip()
    text = _strip_markdown_json_fence(text)
    reviewed = json.loads(text)

    return [_record_from_llm_item(item) for item in reviewed]


def _strip_markdown_json_fence(text: str) -> str:
    if text.startswith("```"):
        text = text.replace("```json", "", 1)
        text = text.replace("```", "")
    return text.strip()


def _record_from_llm_item(item: dict[str, Any]) -> BusinessRecord:
    status = str(item.get("status", "rejected")).lower().strip()
    if status not in {"accepted", "rejected"}:
        status = "rejected"

    street = title_case_address(str(item.get("street_address", "")).strip())
    city = title_case_city(str(item.get("city", "")).strip())
    state = normalize_state(str(item.get("state", "VA") or "VA"))
    zip_code = str(item.get("zip_code", "")).strip()
    full_address = ", ".join([p for p in [street, f"{city} {state} {zip_code}".strip()] if p]).strip(" ,")
    cleaned_name = clean_business_name(str(item.get("clean_business_name", "")).strip() or str(item.get("raw_business_name", "")).strip())

    return BusinessRecord(
        raw_business_name=str(item.get("raw_business_name", "")).strip(),
        clean_business_name=cleaned_name,
        mailing_address=full_address,
        mailing_street=street,
        mailing_city=city,
        mailing_state=state,
        mailing_zip=zip_code,
        status=status,
        reason=str(item.get("reason", "Gemini reviewed")).strip(),
        page=item.get("page"),
    )
