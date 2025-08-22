from __future__ import annotations

import io
import re
from dataclasses import dataclass
from typing import Dict, List, Optional

import pdfplumber


BASIC_SKILLS = {
    # programming
    "python", "java", "javascript", "typescript", "c++", "c#", "go", "rust", "sql",
    # data
    "pandas", "numpy", "scikit-learn", "tensorflow", "pytorch", "nlp", "spacy", "nltk",
    # cloud/devops
    "aws", "azure", "gcp", "docker", "kubernetes", "ci/cd", "git",
    # web
    "react", "node", "streamlit", "flask", "django",
}


@dataclass
class ResumeData:
    raw_text: str
    name: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    skills: List[str]


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    text_parts: List[str] = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            txt = page.extract_text() or ""
            text_parts.append(txt)
    return "\n".join(text_parts)


def extract_email(text: str) -> Optional[str]:
    match = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
    return match.group(0) if match else None


def extract_phone(text: str) -> Optional[str]:
    match = re.search(r"(\+?\d[\d\-\s]{7,}\d)", text)
    return match.group(0) if match else None


def extract_name(text: str) -> Optional[str]:
    first_line = (text.splitlines() or [""])[0].strip()
    if 2 <= len(first_line.split()) <= 5 and len(first_line) <= 64:
        return first_line
    return None


def extract_skills(text: str) -> List[str]:
    tokens = set(re.findall(r"[A-Za-z#+.\-]+", text.lower()))
    matched = sorted(s for s in BASIC_SKILLS if s in tokens)
    return matched


def parse_resume_pdf(pdf_bytes: bytes) -> ResumeData:
    raw = extract_text_from_pdf(pdf_bytes)
    return ResumeData(
        raw_text=raw,
        name=extract_name(raw),
        email=extract_email(raw),
        phone=extract_phone(raw),
        skills=extract_skills(raw),
    )


def parse_job_description(text: str) -> Dict[str, List[str]]:
    text = text or ""
    skills = extract_skills(text)
    return {"skills": skills}
