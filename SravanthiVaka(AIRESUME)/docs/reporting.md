# Reporting (`src/reporting.py`)

Makes two kinds of PDFs:

1) Match Report
- Title, candidate name
- Score, confidence
- Explanation and missing skills
- Top matching snippets (table)

2) ATS Resume
- Clean, single-column layout with clear headings
- Sections: Contact, Summary, Skills, Experience, Education, Projects, Certifications
- Bullet points with light indentation

## Key functions

- `generate_pdf_report(...)`: builds the match report
- `generate_ats_resume_pdf(data)`: builds the resume from a structured dictionary

## Libraries used

- `reportlab` for layout (Paragraph, Table, ListFlowable, etc.)

## Customization ideas

- Add more sections or tweak spacing
- Include icons only if you keep it ATS-safe (plain text is safest)
