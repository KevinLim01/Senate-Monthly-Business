# New Business PDF Parser Website

A local Streamlit website for turning city new-business PDFs into a clean Excel sheet.

The app extracts:

- Business Name
- Street Address
- City
- State
- ZIP Code
- District 24 Check

It keeps accepted businesses at the top of the Excel sheet and puts rejected/review rows at the bottom.

## What is included

- PDF parser
- Capitalization cleanup for business names and addresses
- Optional Gemini business-name review
- Fast local District 24-style filter
- Excel download
- Browser-based upload page

## Local District 24 filter

This no longer uses Gemini. It is fast and rule-based.

It keeps only addresses with:

- State: VA
- City: Newport News, Williamsburg, Yorktown, or Poquoson

Other cities or non-VA addresses move to the review section at the bottom.

## Install

```bash
cd new_business_pdf_parser_website
python -m pip install -r requirements.txt
```

## Run the website

```bash
streamlit run app.py
```

Then upload a PDF in the browser and click **Create Excel Sheet**.

## Use Gemini for business-name review

Gemini is optional. It is only used when the checkbox is turned on.

Create a `.env` file:

```bash
cp .env.example .env
```

Then put your key in `.env`:

```bash
GEMINI_API_KEY=your_actual_key_here
GEMINI_MODEL=gemini-2.5-flash
```

Run again:

```bash
streamlit run app.py
```

If you do not use Gemini, the website works without an API key.

## Command-line use still works

No Gemini:

```bash
python run.py input/NewBusinesses.pdf --output output/business_mailing_addresses.xlsx --check-district24
```

With Gemini business-name review:

```bash
python run.py input/NewBusinesses.pdf --output output/business_mailing_addresses.xlsx --use-llm --check-district24
```
