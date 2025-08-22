# AI-Powered Resume Builder with Job Matching System

## Quick start

1. Create and activate a virtual environment (recommended). On Windows with Python 3.11:
```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
```
2. Install dependencies:
```powershell
python -m pip install -r sivanesh\requirements.txt
```
3. Create a .env file with your API key (required). The app uses Gemini models via LangChain for embeddings and LLM, and ChromaDB for persistent vectors.
```env
GEMINI_API_KEY=your-key-here
# Or use GOOGLE_API_KEY instead of GEMINI_API_KEY
# GOOGLE_API_KEY=your-key-here

# Optional: change Gemini chat/embedding models
# GEMINI_CHAT_MODEL=gemini-1.5-flash
# GEMINI_EMBED_MODEL=text-embedding-004
# ChromaDB persistence options
# CHROMA_DIR=.chroma
# CHROMA_COLLECTION=resume_snippets
# CHROMA_METRIC=cosine
```
4. Run the app:
```powershell
streamlit run sivanesh\app.py
```

## Features
- Resume PDF parsing and basic structured extraction
- Multi-agent workflow (parse → analyze → match → score → report)
- Embeddings via Gemini (`text-embedding-004`) or local hashed fallback
- Interactive Streamlit UI with workflow visualization
- PDF report generation of results
- ATS-friendly Resume Builder (choose sections, fill a simple form, download a clean 1-column PDF)

## A kid-friendly tour (what happens here?)

Think of the app like a team of helpful robots working together:

- The Uploader robot opens your resume PDF and reads the words.
- The Job Reader robot looks at the job description and spots important skills.
- The Helper robot suggests nicer, clearer bullet points.
- The Matcher robot compares your resume to the job and gives a score with reasons.
- The Report robot prints a simple PDF with your score and highlights.
- The Builder robot can also make a clean resume for you if you fill in a form.

That’s it: read → understand → match → explain → print.

## How to use the two modes

- Resume Matching:
  1. Choose “Resume Matching”.
  2. Upload your resume PDF and paste a job description.
  3. Click “Match Resume”.
  4. See the score, missing skills, and top matching lines; download a report PDF.

- Resume Builder:
  1. Choose “Resume Builder”.
  2. Pick which sections you want (Contact, Summary, Skills, Experience, Education, Projects, Certifications).
  3. Fill only the parts you want.
  4. Click “Generate Resume” and download an ATS-friendly PDF.

## What each file does (simple words)

- `app.py`: The main screen. Shows buttons and forms, and connects all parts.
- `src/parsing.py`: Teaches the robots how to read PDFs and find things like name, email, and skills.
- `src/embeddings.py`: Gives the robots “understanding glasses” so they can compare meanings, not just words. Uses Gemini if you set `GEMINI_API_KEY`, otherwise a local fallback.
- `src/agents.py`: The robots themselves (Parser, Job Reader, Helper, Matcher). Each one does one clear job.
- `src/scoring.py`: The math for comparing your resume and the job (similarity and skills overlap) and making a final score.
- `src/reporting.py`: Makes PDFs: the match report and the ATS resume from the form.
- `src/workflow.py`: Draws a little map of the robots and how they pass work to each other.
- `src/ui_components.py`: Small UI pieces to show the diagram, results, and details.

## Behind the scenes (a tiny bit of detail)

- Parsing uses `pdfplumber` to read text, then simple rules to find email/phone/skills.
- Embeddings turn text into numbers (vectors). We compare vectors with cosine similarity to see how close the meanings are.
- Scoring mixes similarity (70%) and skill overlap (30%) to make a percentage.
- The builder makes a single-column, clean PDF with clear headings and bullet points so ATS scanners can read it easily.

## Notes
- Gemini is preferred. The app uses Gemini models via LangChain for embeddings and LLM when keys are available; otherwise it falls back to a local hashing embedder and heuristic content suggestions so the app keeps working without network access.
- ChromaDB is used as the persistent vector store by default. Configure directory/collection with the env vars above.
- If you add `.env` at the project root, it will be loaded automatically.
- No compiled dependencies required.
