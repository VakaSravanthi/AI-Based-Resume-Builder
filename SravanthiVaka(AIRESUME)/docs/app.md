# App UI and Flow (`app.py`)

This is the entry point. It shows the pages and connects the pieces.

- Sets the page title and loads `.env` so environment variables are available
- Lets you pick between two modes: "Resume Matching" or "Resume Builder"

## Resume Matching mode

1. Upload your resume PDF
2. Paste the job description
3. Click "Match Resume"
4. The app:
   - Reads your PDF (ResumeParser)
   - Parses the job text (JobParser)
   - Suggests better bullets (ContentEnhancer)
   - Computes match and reasons (MatcherScorer)
5. Shows a diagram of the steps, a score summary, and details
6. Lets you download a PDF report

## Resume Builder mode

- Choose which sections you want (Contact, Summary, Skills, Experience, Education, Projects, Certifications)
- Fill only the shown fields
- Generate an ATS-friendly PDF resume

## Important lines (short tour)

- `st.set_page_config(...)`: Sets the Streamlit page layout and title
- `load_dotenv()`: Loads `.env` so `GEMINI_API_KEY` is available
- `mode = st.radio(...)`: Toggle between matching and builder
- File upload / text areas: Collect user inputs
- Agents are called in sequence, their outputs are collected and shown
- `generate_pdf_report(...)` and `generate_ats_resume_pdf(...)`: Create downloadable PDFs
