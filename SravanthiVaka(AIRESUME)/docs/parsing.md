# Parsing (`src/parsing.py`)

Reads PDF files and pulls out useful bits.

## Key pieces

- `extract_text_from_pdf(pdf_bytes)`: reads text from each PDF page using `pdfplumber`
- `extract_email(text)`: finds email using a regex
- `extract_phone(text)`: finds phone numbers using a regex
- `extract_name(text)`: guesses the name from the first line
- `extract_skills(text)`: matches known skills from a small list
- `parse_resume_pdf(pdf_bytes)`: builds a `ResumeData` with raw_text, name, email, phone, skills
- `parse_job_description(text)`: extracts `skills` from job text

## Why so simple?

- Keeps it predictable and fast
- Easy to improve later (add more skills, smarter name/phone rules)

## Tips to extend

- Expand `BASIC_SKILLS`
- Improve `extract_name` by checking ALL-CAPS or title case patterns
- Add section detection (Experience, Education) if needed
