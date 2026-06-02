from __future__ import annotations

import argparse
from pathlib import Path

from dotenv import load_dotenv

from new_business_parser.pdf_text import extract_lines_by_page
from new_business_parser.parser import parse_records
from new_business_parser.llm_review import review_records_with_gemini
from new_business_parser.district_filter import check_district24_by_locality
from new_business_parser.excel_writer import write_excel
from new_business_parser.progress import log, ticker


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract cleaned business names plus street, city, state, ZIP, and fast local Virginia Senate District 24-style locality screening from new-business PDFs."
    )
    parser.add_argument("pdf", help="Path to the input PDF")
    parser.add_argument(
        "--output",
        default="output/business_mailing_addresses.xlsx",
        help="Path to output Excel file",
    )
    parser.add_argument(
        "--use-llm",
        action="store_true",
        help="Use Gemini to review weird names and rejection decisions",
    )
    parser.add_argument(
        "--check-district24",
        action="store_true",
        help="Fast local filter: keep VA addresses in Newport News, Williamsburg, Yorktown, or Poquoson. Others move to the rejected review section. No Gemini/API call.",
    )
    args = parser.parse_args()

    load_dotenv()

    pdf_path = Path(args.pdf)
    output_path = Path(args.output)

    log(f"Starting parser for: {pdf_path}")

    with ticker("Reading PDF text"):
        lines = extract_lines_by_page(pdf_path)
    log(f"Read {len(lines)} text lines from PDF")

    with ticker("Parsing business names and mailing addresses"):
        records = parse_records(lines)
    log(f"Parsed {len(records)} business records")

    if args.use_llm:
        log("Gemini business-name review is ON")
        with ticker("Gemini reviewing business names"):
            records = review_records_with_gemini(records)
        log(f"Gemini returned {len(records)} reviewed records")
    else:
        log("Gemini business-name review is OFF")

    if args.check_district24:
        with ticker("Applying local District 24 city/state filter"):
            records = check_district24_by_locality(records)
    else:
        log("Local District 24 filter is OFF")

    with ticker("Writing Excel workbook"):
        write_excel(records, output_path)

    accepted_count = sum(1 for r in records if r.status == "accepted")
    rejected_count = len(records) - accepted_count

    print(f"Created: {output_path}")
    print(f"Accepted rows: {accepted_count}")
    print(f"Rejected/review rows: {rejected_count}")
    if args.check_district24:
        yes_count = sum(1 for r in records if r.senate_district_24_status == "yes")
        no_count = sum(1 for r in records if r.senate_district_24_status == "no")
        uncertain_count = sum(1 for r in records if r.senate_district_24_status == "uncertain")
        print(f"District 24 yes: {yes_count}")
        print(f"District 24 no: {no_count}")
        print(f"District 24 uncertain: {uncertain_count}")


if __name__ == "__main__":
    main()
