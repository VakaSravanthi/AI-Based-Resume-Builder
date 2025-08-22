from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .embeddings import EmbeddingService
from .parsing import ResumeData, parse_job_description, parse_resume_pdf
from .scoring import compute_match_score, top_k_matches
from .vectorstore import create_vector_store, create_vector_store_for
import numpy as np

try:
    from langchain_google_genai import ChatGoogleGenerativeAI  # type: ignore
except Exception:
    ChatGoogleGenerativeAI = None  # type: ignore


@dataclass
class AgentResult:
    name: str
    inputs: Dict[str, Any]
    outputs: Dict[str, Any]
    reasoning: str


def resume_parser_agent(pdf_bytes: bytes) -> AgentResult:
    resume: ResumeData = parse_resume_pdf(pdf_bytes)
    return AgentResult(
        name="ResumeParser",
        inputs={"bytes_len": len(pdf_bytes)},
        outputs={
            "raw_text": resume.raw_text,
            "name": resume.name,
            "email": resume.email,
            "phone": resume.phone,
            "skills": resume.skills,
        },
        reasoning="Extracted text and basic entities from resume PDF.",
    )


def job_parser_agent(job_text: str) -> AgentResult:
    parsed = parse_job_description(job_text)
    return AgentResult(
        name="JobParser",
        inputs={"job_text_len": len(job_text or "")},
        outputs={"skills": parsed.get("skills", [])},
        reasoning="Parsed job description and extracted skills.",
    )


def content_enhancer_agent(resume_text: str) -> AgentResult:
    suggestions: List[str] = []
    reasoning = ""
    prompt = (
        "Improve these resume bullet points for clarity, impact, and metrics. "
        "Return 3 concise bullets.\n\n" + (resume_text or "")[:1500]
    )

    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    can_use_llm = bool(api_key and ChatGoogleGenerativeAI is not None)

    if can_use_llm:
        try:
            chat_model = os.getenv("GEMINI_CHAT_MODEL", "gemini-1.5-flash")
            llm = ChatGoogleGenerativeAI(model=chat_model, google_api_key=api_key)  # type: ignore
            resp = llm.invoke(prompt)
            content = getattr(resp, "content", "") or str(resp)
            suggestions = [s.strip("- ") for s in content.strip().splitlines() if s.strip()][:3]
            reasoning = "Generated with Gemini via LangChain."
        except Exception as exc:  # quota errors and others
            can_use_llm = False

    if not can_use_llm:
        # Heuristic fallback: craft 3 generic improvement bullets
        base = (resume_text or "").strip().splitlines()
        sample = next((b for b in base if b.strip()), "Your bullet here")
        suggestions = [
            f"Quantified impact: {sample[:60]} (add metrics like % or $)",
            "Active verbs first; remove filler; keep to one line.",
            "Match keywords from the job description; highlight tools/results.",
        ]
        reasoning = "Fallback suggestions due to unavailable LLM (e.g., quota exceeded)."

    return AgentResult(
        name="ContentEnhancer",
        inputs={"resume_text_len": len(resume_text)},
        outputs={"suggestions": suggestions},
        reasoning=reasoning,
    )


def matcher_and_scoring_agent(
    resume_text: str,
    job_text: str,
    resume_skills: List[str],
    job_skills: List[str],
    embedding_service: EmbeddingService,
) -> AgentResult:
    texts = [resume_text, job_text]
    vecs = embedding_service.embed_texts(texts)
    resume_vec, job_vec = vecs[0], vecs[1]

    resume_snippets = [s for s in resume_text.split("\n") if len(s.strip()) > 20][:20]
    if not resume_snippets:
        resume_snippets = [resume_text[:300]]
    snippet_vecs = embedding_service.embed_texts(resume_snippets)

    # Persist snippet embeddings in the configured vector store and retrieve top matches
    try:
        store = create_vector_store(dimension=len(job_vec))
        metas = [{"i": i} for i in range(len(resume_snippets))]
        store.add_texts(
            texts=resume_snippets,
            vectors=np.array(snippet_vecs, dtype=np.float32),
            metadatas=metas,
        )
        store_results = store.similarity_search(np.array(job_vec, dtype=np.float32), k=5)
        top_snips = [(text, float(score)) for text, score, _ in store_results]
    except Exception:
        # Fallback to in-memory similarity if vector store is unavailable
        top_snips = top_k_matches(job_vec, resume_snippets, snippet_vecs, k=5)

    # Persist the holistic resume and job vectors too, and a match record
    try:
        resume_store = create_vector_store_for(collection_name="resumes", dimension=len(resume_vec))
        job_store = create_vector_store_for(collection_name="jobs", dimension=len(job_vec))
        match_store = create_vector_store_for(collection_name="matches", dimension=len(job_vec))

        resume_store.add_texts(
            texts=[resume_text],
            vectors=np.array([resume_vec], dtype=np.float32),
            metadatas=[{"type": "resume"}],
        )
        job_store.add_texts(
            texts=[job_text],
            vectors=np.array([job_vec], dtype=np.float32),
            metadatas=[{"type": "job"}],
        )
        # store a small summary doc embedding equal to the job vector for quick reverse lookups
        match_summary = f"Match score {compute_match_score(resume_vec, job_vec, resume_skills, job_skills)['score']:.1f}%"
        match_store.add_texts(
            texts=[match_summary],
            vectors=np.array([job_vec], dtype=np.float32),
            metadatas=[{"type": "match", "resume_len": len(resume_text), "job_len": len(job_text)}],
        )
    except Exception:
        pass
    scoring = compute_match_score(resume_vec, job_vec, resume_skills, job_skills)

    outputs: Dict[str, Any] = {
        "score": scoring["score"],
        "confidence": scoring["confidence"],
        "similarity": scoring["similarity"],
        "missing_skills": scoring["missing_skills"],
        "explanation": scoring["explanation"],
        "top_snippets": top_snips,
    }

    return AgentResult(
        name="MatcherScorer",
        inputs={
            "resume_text_len": len(resume_text),
            "job_text_len": len(job_text),
            "resume_skills": resume_skills,
            "job_skills": job_skills,
        },
        outputs=outputs,
        reasoning="Computed semantic similarity, skill overlap, and top matching snippets.",
    )
