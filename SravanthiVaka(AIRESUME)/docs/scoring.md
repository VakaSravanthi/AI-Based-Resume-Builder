# Scoring and Matching (`src/scoring.py`)

This part turns vectors and skills into a final match score.

## Core ideas

- Cosine similarity: compares two vectors; 1.0 means very close
- Skill overlap: how many skills are shared, adjusted by total unique skills (Jaccard)

## Functions

- `cosine_similarity(a, b)`: dot(a,b) / (||a|| * ||b||)
- `compute_match_score(resume_vec, job_vec, resume_skills, job_skills)`:
  - similarity = cosine(resume_vec, job_vec)
  - jaccard = overlap(resume_skills, job_skills)
  - score = 0.7 * similarity + 0.3 * jaccard
  - returns percent score, confidence, missing skills, and explanation text
- `top_k_matches(query_vec, texts, vectors, k)`: lists the top-k text lines most similar to the job

## Why this blend?

- Similarity checks content meaning
- Skills ensure specific requirements are considered
- Weighting can be tuned later
