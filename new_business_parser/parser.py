from __future__ import annotations

import re

from .cleaner import clean_business_name, normalize_address, looks_like_person_name, title_case_address, title_case_city, normalize_state
from .models import BusinessRecord

PHONE_RE = re.compile(r"\(?\d{3}\)?[-\s]?\d{3}[-\s]?\d{4}")
DATE_RE = re.compile(r"^\d{1,2}/\d{1,2}/\d{4}$")
RECORD_LICENSE_RE = re.compile(r"#\s*(\d{4,6})\s*$")
ADDRESS_END_RE = re.compile(r"(?P<city>[A-Z][A-Z .'-]+?)\s+VA\s+(?P<zip>\d{5})(?:-\d{4})?")
ADDRESS_END_ANCHORED_RE = re.compile(r"^(?P<city>[A-Z][A-Z .'-]+?)\s+VA\s+(?P<zip>\d{5})(?:-\d{4})?$")
CATEGORY_SPLIT_RE = re.compile(r"\s+\d+\)\s+23-\d{3}-\d{3}.*$", re.I)


def is_phone(line: str) -> bool:
    return bool(PHONE_RE.search(line))


def is_date(line: str) -> bool:
    return bool(DATE_RE.match(line.strip()))


def is_record_start(lines_by_page: list[tuple[int, str]], idx: int) -> bool:
    line = lines_by_page[idx][1]
    if "#" not in line or "___" in line:
        return False
    if not RECORD_LICENSE_RE.search(line):
        return False
    if idx + 1 >= len(lines_by_page):
        return False
    return is_date(lines_by_page[idx + 1][1])


def split_into_record_blocks(lines_by_page: list[tuple[int, str]]) -> list[tuple[int, list[str]]]:
    """Split records by name/license lines followed by a date.

    In this PDF, each record starts like: BUSINESS NAME # 81394, then the date on the next line.
    """
    starts = [idx for idx in range(len(lines_by_page)) if is_record_start(lines_by_page, idx)]
    blocks: list[tuple[int, list[str]]] = []

    for pos, start_idx in enumerate(starts):
        end_idx = starts[pos + 1] if pos + 1 < len(starts) else len(lines_by_page)
        page = lines_by_page[start_idx][0]
        block = [line for _, line in lines_by_page[start_idx:end_idx]]
        blocks.append((page, block))

    return blocks


def extract_business_name(block: list[str]) -> str | None:
    if not block:
        return None
    first_line = block[0]
    name = re.sub(r"\s*#\s*\d{4,6}\s*$", "", first_line).strip()
    return name or None


def extract_mailing_address_parts(block: list[str]) -> tuple[str, str, str, str, str] | None:
    """Return: full_address, street/address line, city, state, zip_code."""
    phone_index = None
    for idx, line in enumerate(block):
        if is_phone(line):
            phone_index = idx
            break

    if phone_index is None:
        return None

    parts: list[str] = []
    for line in block[phone_index + 1:]:
        cleaned = clean_address_candidate(line)
        if not cleaned:
            continue
        parts.append(cleaned)
        if ADDRESS_END_RE.search(cleaned.upper()):
            break

    if not parts:
        return None

    return split_address_parts(parts)


def clean_address_candidate(line: str) -> str:
    line = normalize_address(line)
    if not line:
        return ""

    # Remove category text that sometimes appears on the same physical line as an address.
    line = CATEGORY_SPLIT_RE.sub("", line)

    # Some layout extraction puts a category phrase before the mailing street,
    # for example: "CHILD CARE SERVICE 558 DENBIGH BLVD".
    address_start = re.search(r"\b(?:\d{1,6}\s+|P\s*O\s+BOX\s+|PO\s+BOX\s+|#\d+)", line, re.I)
    if address_start and address_start.start() > 0:
        prefix = line[: address_start.start()].upper()
        if any(word in prefix for word in ["SERVICE", "CONSULTANT", "ARTIST", "PEDDLER", "TAG", "CARE", "GOODS", "CERTIFICATION"]):
            line = line[address_start.start():].strip(" ,")

    # If a category description got merged after CITY VA ZIP, cut it off after ZIP.
    upper = line.upper().replace(",", "")
    match = ADDRESS_END_RE.search(upper)
    if match:
        # Rebuild only through the matched ZIP by splitting on the exact ZIP.
        zip_code = match.group("zip")
        zip_pos = line.find(zip_code)
        if zip_pos != -1:
            return line[: zip_pos + len(zip_code)].strip(" ,")

    return line.strip(" ,")


def _addressish(line: str) -> bool:
    return bool(re.search(r"^(?:\d{1,6}\b|P\s*O\s+BOX\b|PO\s+BOX\b|#\d+)", line.strip(), re.I))


def _clean_street_parts(parts: list[str]) -> list[str]:
    fixed: list[str] = []
    for part in parts:
        cleaned = clean_address_candidate(part)
        if cleaned:
            fixed.append(cleaned)

    # Drop category-only chunks before the actual street/PO Box.
    first_addr_idx = None
    for idx, part in enumerate(fixed):
        if _addressish(part):
            first_addr_idx = idx
            break
    if first_addr_idx is not None:
        fixed = fixed[first_addr_idx:]

    return fixed


def split_address_parts(parts: list[str]) -> tuple[str, str, str, str, str] | None:
    cleaned_parts = [normalize_address(p) for p in parts if normalize_address(p)]
    if not cleaned_parts:
        return None

    # Best case: the last captured line is exactly CITY VA ZIP.
    final_line_upper = cleaned_parts[-1].upper().replace(",", "")
    final_match = ADDRESS_END_ANCHORED_RE.match(final_line_upper)
    if final_match:
        city = title_case_city(final_match.group("city").strip())
        zip_code = final_match.group("zip").strip()
        street = title_case_address(normalize_address(", ".join(_clean_street_parts(cleaned_parts[:-1]))))
        state = "VA"
        full_address = normalize_address(", ".join([p for p in [street, f"{city} {state} {zip_code}".strip()] if p]))
        return full_address, street, city, state, zip_code

    combined = normalize_address(", ".join(cleaned_parts))
    combined_upper = combined.upper().replace(",", "")
    match = ADDRESS_END_RE.search(combined_upper)

    if not match:
        # Keep a stable 5-field return shape even when the PDF text
        # has an odd/incomplete address. This prevents parse_records()
        # from crashing on malformed rows.
        return title_case_address(combined), title_case_address(combined), "", "VA", ""

    city = title_case_city(match.group("city").strip())
    zip_code = match.group("zip").strip()
    before_city = combined_upper[: match.start()].strip(" ,")
    street = title_case_address(normalize_address(", ".join(_clean_street_parts([before_city]))))
    state = "VA"
    full_address = normalize_address(", ".join([p for p in [street, f"{city} {state} {zip_code}".strip()] if p]))
    return full_address, street, city, state, zip_code


def parse_records(lines_by_page: list[tuple[int, str]]) -> list[BusinessRecord]:
    blocks = split_into_record_blocks(lines_by_page)
    records: list[BusinessRecord] = []

    for page, block in blocks:
        raw_name = extract_business_name(block)
        address_parts = extract_mailing_address_parts(block)

        if not raw_name or not address_parts:
            continue

        # Older/odd address parsing should never kill the whole run.
        # Normalize the tuple defensively to: full, street, city, state, zip.
        address_parts = tuple(address_parts)
        if len(address_parts) < 5:
            address_parts = address_parts + ("",) * (5 - len(address_parts))
        mailing_address, mailing_street, mailing_city, mailing_state, mailing_zip = address_parts[:5]
        mailing_street = title_case_address(mailing_street)
        mailing_city = title_case_city(mailing_city)
        mailing_state = normalize_state(mailing_state)
        mailing_address = normalize_address(", ".join([p for p in [mailing_street, f"{mailing_city} {mailing_state} {mailing_zip}".strip()] if p]))
        clean_name = clean_business_name(raw_name)
        if not clean_name:
            continue

        if looks_like_person_name(clean_name):
            status = "rejected"
            reason = "Looks like a personal name"
        else:
            status = "accepted"
            reason = "Business-style name"

        records.append(
            BusinessRecord(
                raw_business_name=raw_name,
                clean_business_name=clean_name,
                mailing_address=mailing_address,
                mailing_street=mailing_street,
                mailing_city=mailing_city,
                mailing_state=mailing_state,
                mailing_zip=mailing_zip,
                status=status,
                reason=reason,
                page=page,
            )
        )

    return _dedupe_records(records)


def _dedupe_records(records: list[BusinessRecord]) -> list[BusinessRecord]:
    seen: set[tuple[str, str, str, str]] = set()
    deduped: list[BusinessRecord] = []
    for record in records:
        key = (
            record.clean_business_name.upper(),
            record.mailing_street.upper(),
            record.mailing_city.upper(),
            record.mailing_zip,
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(record)
    return deduped
