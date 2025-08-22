# Embeddings (`src/embeddings.py`)

Turns text into numbers (vectors) so we can compare meanings.

## Two modes

- Gemini mode (cloud): requires `GEMINI_API_KEY` in `.env`
- Local mode (fallback): a simple hashed vector; works offline

## How it decides

- If `GEMINI_API_KEY` exists, it uses Gemini. Otherwise, local.

## Important parts

- `EmbeddingConfig`: holds settings like provider and model
- `EmbeddingService.__init__`: reads env, configures Gemini if needed
- `embed_texts(texts)`: returns a list of vectors, one per text
- `embed_query(text)`: convenience wrapper for a single text

## Similarity

- We later use cosine similarity between vectors to see how close two texts are

## Changing the model

- You can set `GEMINI_EMBED_MODEL` in `.env` to pick a different model; default is `text-embedding-004`
