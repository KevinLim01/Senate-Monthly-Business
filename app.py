from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from new_business_parser.pdf_text import extract_lines_by_page
from new_business_parser.parser import parse_records
from new_business_parser.llm_review import review_records_with_gemini
from new_business_parser.district_filter import check_district24_by_locality
from new_business_parser.excel_writer import write_excel


load_dotenv()

st.set_page_config(
    page_title="New Business PDF Parser",
    page_icon="📄",
    layout="wide",
)

st.title("New Business PDF Parser")
st.caption("Upload a city new-business PDF and turn it into a clean Excel sheet.")

with st.sidebar:
    st.header("Options")
    use_llm = st.checkbox(
        "Use Gemini to review business names",
        value=False,
        help="Requires GEMINI_API_KEY in .env or Streamlit secrets. This does not check district status.",
    )
    check_district = st.checkbox(
        "Apply local District 24 filter",
        value=True,
        help="Fast local rule: VA addresses in Newport News, Williamsburg, Yorktown, or Poquoson are kept. Others move to the review section.",
    )
    st.divider()
    st.write("Gemini model")
    st.code(os.getenv("GEMINI_MODEL", "gemini-2.5-flash"), language="text")

uploaded_file = st.file_uploader("Upload New Business PDF", type=["pdf"])


def records_to_preview(records):
    accepted = []
    rejected = []
    for r in records:
        row = {
            "Business Name": r.clean_business_name,
            "Street Address": r.mailing_street,
            "City": r.mailing_city,
            "State": r.mailing_state,
            "ZIP Code": r.mailing_zip,
            "District 24 Check": r.senate_district_24_status,
            "Reason": r.reason,
        }
        if r.status == "accepted":
            accepted.append(row)
        else:
            rejected.append(row)
    return pd.DataFrame(accepted), pd.DataFrame(rejected)


if uploaded_file is None:
    st.info("Upload a PDF to start.")
else:
    st.success(f"Ready: {uploaded_file.name}")

    if st.button("Create Excel Sheet", type="primary"):
        if use_llm and not os.getenv("GEMINI_API_KEY"):
            st.error("Gemini is turned on, but GEMINI_API_KEY is missing. Add it to .env or turn Gemini off.")
            st.stop()

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dir_path = Path(temp_dir)
            pdf_path = temp_dir_path / uploaded_file.name
            output_path = temp_dir_path / "business_mailing_addresses.xlsx"

            pdf_path.write_bytes(uploaded_file.getbuffer())

            progress = st.progress(0)
            status = st.empty()

            try:
                status.write("Reading PDF text...")
                lines = extract_lines_by_page(pdf_path)
                progress.progress(20)

                status.write("Parsing business names and mailing addresses...")
                records = parse_records(lines)
                progress.progress(45)

                if use_llm:
                    status.write("Gemini is reviewing business names...")
                    records = review_records_with_gemini(records)
                else:
                    status.write("Skipping Gemini business-name review...")
                progress.progress(65)

                if check_district:
                    status.write("Applying local District 24 city/state filter...")
                    records = check_district24_by_locality(records)
                else:
                    status.write("Skipping District 24 filter...")
                progress.progress(80)

                status.write("Writing Excel file...")
                write_excel(records, output_path)
                progress.progress(100)

                accepted_count = sum(1 for r in records if r.status == "accepted")
                rejected_count = len(records) - accepted_count
                district_yes = sum(1 for r in records if r.senate_district_24_status == "yes")
                district_no = sum(1 for r in records if r.senate_district_24_status == "no")

                status.success("Done.")

                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Parsed records", len(records))
                c2.metric("Accepted", accepted_count)
                c3.metric("Review / rejected", rejected_count)
                c4.metric("District filter yes", district_yes if check_district else "Off")

                with open(output_path, "rb") as f:
                    st.download_button(
                        "Download Excel File",
                        data=f,
                        file_name="business_mailing_addresses.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )

                accepted_df, rejected_df = records_to_preview(records)

                st.subheader("Accepted preview")
                st.dataframe(accepted_df, use_container_width=True, hide_index=True)

                st.subheader("Review / rejected preview")
                st.dataframe(rejected_df, use_container_width=True, hide_index=True)

                if check_district:
                    st.caption(f"Local district filter marked yes={district_yes}, no={district_no}.")

            except Exception as exc:
                progress.empty()
                status.empty()
                st.error(f"The parser failed: {exc}")
                st.exception(exc)
