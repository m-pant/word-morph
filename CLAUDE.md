# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Word Morph API is a Russian-language word manipulation service that finds semantically similar words using Navec word embeddings and applies various text transformations. The service is built with FastAPI and containerized with Docker.

## Key Commands

### Development

```bash
# Local development (without Docker)
python -m venv venv
source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8081
```

### Docker

```bash
# Build and run with Docker Compose
docker-compose up --build

# View logs
docker-compose logs -f word-morph

# Stop service
docker-compose down

# Stop and remove volumes (clears Navec model cache)
docker-compose down -v
```

### Testing API

```bash
# Health check
curl http://localhost:8081/health

# Basic word search (IMPORTANT: Use --data-urlencode for Cyrillic)
curl -G "http://localhost:8081/api/words" \
  --data-urlencode "word=мебель" \
  --data-urlencode "count=5"

# With transformations
curl -G "http://localhost:8081/api/words" \
  --data-urlencode "word=гроза" \
  --data-urlencode "count=5" \
  --data-urlencode "shuffle_letters=true" \
  --data-urlencode "preserve_first=true"
```

## Architecture

### Core Components

**app/embeddings.py** - Navec embeddings service (singleton pattern)
- `EmbeddingsService` manages the Navec model lifecycle
- Downloads model from Yandex Cloud on first run (~300MB, cached locally)
- Model loaded once at application startup via lifespan context manager
- `find_similar_words()` computes cosine similarity across ~500K vocabulary
- Supports stride (sampling every Nth word) and similarity_threshold (filters lexically similar words)
- Random mode (`random_mode=True`) returns random words from vocabulary instead of semantic matches

**app/transformations.py** - Word transformation logic
- `WordTransformer` class applies transformations with configurable filters
- Russian vowels: а,е,ё,и,о,у,ы,э,ю,я / Consonants: б,в,г,д,ж,з,й,к,л,м,н,п,р,с,т,ф,х,ц,ч,ш,щ,ъ,ь
- Three transformation types:
  - `shuffle_letters`: Randomly permutes letters based on filter rules
  - `skip_letters`: Removes letters (optionally shows as `_`)
  - `add_errors`: Replaces letters with phonetically similar alternatives (defined in SIMILAR_LETTERS dict)
- Filters control which letters are transformable:
  - `letter_type`: 'all', 'vowels', or 'consonants'
  - `preserve_first`/`preserve_last`: Keeps boundary letters unchanged
- Transformations applied in order: shuffle → skip → errors

**app/main.py** - FastAPI application
- Single endpoint: `GET /api/words` with 12 query parameters
- Lifespan context manager ensures model is loaded before accepting requests
- Error handling: 400 (invalid params), 404 (word not in vocab), 500 (internal)
- Pydantic models for request validation and response serialization

**app/utils.py** - Parameter validation and logging setup

### Request Flow

1. FastAPI receives request at `/api/words`
2. `validate_parameters()` validates all inputs
3. `embeddings_service.find_similar_words()` returns top N semantically similar words (or random words)
   - Computes cosine similarity for entire vocabulary
   - Sorts by similarity score
   - Applies stride and similarity_threshold filtering
4. `apply_transformations()` modifies words based on flags
5. Returns JSON with query echo and transformed results

### Important Implementation Details

- **Navec Model**: Downloaded to `navec_hudlit_v1_12B_500K_300d_100q.tar` on first run, cached in Docker volume at `/root/.navec`
- **Singleton Pattern**: `embeddings_service` is a global instance to avoid reloading model
- **Cyrillic Handling**: Words are lowercased for lookup; API requires URL-encoded Cyrillic in requests
- **Stride Logic**: When stride > 0, samples every (stride+1)th word from sorted similarity list, then backfills if needed
- **Similarity Filtering**: Uses Jaccard similarity (intersection/union of character sets) to filter lexically similar words

## Configuration

- **PORT**: Environment variable, defaults to 8081 (external) / 8080 (internal container port)
- **Logging**: Configured in app/utils.py at INFO level with timestamp format
- **Limits**: max count=100, max skip_letters=word length, similarity_threshold 0.0-1.0

## API Interactive Docs

- Swagger UI: http://localhost:8081/docs
- ReDoc: http://localhost:8081/redoc
