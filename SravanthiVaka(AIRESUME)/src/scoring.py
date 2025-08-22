from __future__ import annotations

from typing import List, Tuple, Dict


def dot(a: List[float], b: List[float]) -> float:
    return float(sum(x * y for x, y in zip(a, b)))


def norm(a: List[float]) -> float:
    return float(sum(x * x for x in a) ** 0.5)


def cosine_similarity(a: List[float], b: List[float]) -> float:
    denom = (norm(a) * norm(b)) or 1.0
    return dot(a, b) / denom


def compute_match_score(resume_vec: List[float], job_vec: List[float], resume_skills: List[str], job_skills: List[str]) -> Dict[str, object]:
    sim = cosine_similarity(resume_vec, job_vec)
    rs = set(s.lower() for s in resume_skills)
    js = set(s.lower() for s in job_skills)
    skill_overlap = len(rs & js)
    skill_union = len(rs | js) or 1
    jaccard = skill_overlap / skill_union

    score = 0.7 * sim + 0.3 * jaccard
    score_pct = max(0.0, min(1.0, score)) * 100.0
    confidence = 0.5 + 0.5 * min(sim, 1.0)

    missing_skills = sorted(list(js - rs))

    explanation = (
        f"Semantic similarity: {sim:.2f}. Skill overlap: {skill_overlap}/{skill_union}. Combined score: {score_pct:.1f}%."
    )
    return {
        "similarity": sim,
        "jaccard": jaccard,
        "score": score_pct,
        "confidence": confidence,
        "missing_skills": missing_skills,
        "explanation": explanation,
    }


def top_k_matches(query_vec: List[float], corpus_texts: List[str], corpus_vecs: List[List[float]], k: int = 5) -> List[Tuple[str, float]]:
    sims = [(text, cosine_similarity(query_vec, vec)) for text, vec in zip(corpus_texts, corpus_vecs)]
    sims.sort(key=lambda x: x[1], reverse=True)
    return sims[:k]
