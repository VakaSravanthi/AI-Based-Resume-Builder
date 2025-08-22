# Agents (`src/agents.py`)

Agents are small workers. Each one takes inputs and returns outputs with a name and a short reasoning note.

## AgentResult
- `name`: which agent ran
- `inputs`: what it received
- `outputs`: what it produced
- `reasoning`: a short note about how it worked

## ResumeParser
- Input: resume PDF bytes
- Output: raw text, name, email, phone, skills
- How: uses `parsing.py` to read PDF and apply simple extraction rules

## JobParser
- Input: job description text
- Output: list of skills
- How: uses `parsing.py` skill extraction

## ContentEnhancer
- Input: resume text
- Output: 1–3 improved bullet suggestions
- How: if `GEMINI_API_KEY` is set, calls Gemini; otherwise makes heuristic rewrites

## MatcherScorer
- Inputs: resume text, job text, resume skills, job skills, embedding service
- Outputs: score (0–100%), confidence, similarity, missing skills, explanation, top snippets
- How:
  - Embeds text into vectors (Gemini or local hashed)
  - Finds top matching lines from the resume
  - Computes final score using similarity and skill overlap
