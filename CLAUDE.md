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

# Filter by part of speech (POS)
curl -G "http://localhost:8081/api/words" \
  --data-urlencode "word=красный" \
  --data-urlencode "count=5" \
  --data-urlencode "pos_filter=adjective"

# Only nouns
curl -G "http://localhost:8081/api/words" \
  --data-urlencode "word=стул" \
  --data-urlencode "count=10" \
  --data-urlencode "pos_filter=noun" \
  --data-urlencode "stride=14" \
  --data-urlencode "similarity_threshold=0.6"

# Normalize to base form (nominative singular)
curl -G "http://localhost:8081/api/words" \
  --data-urlencode "word=стул" \
  --data-urlencode "count=10" \
  --data-urlencode "pos_filter=noun" \
  --data-urlencode "normalize=true"

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
- Single endpoint: `GET /api/words` with 14 query parameters (including pos_filter and normalize)
- Lifespan context manager ensures model is loaded before accepting requests
- Error handling: 400 (invalid params), 404 (word not in vocab), 500 (internal)
- Pydantic models for request validation and response serialization
- POS filtering: searches 5x count, filters by part of speech, then truncates to requested count
- Normalization: converts words to base form (именительный падеж единственного числа) using pymorphy2

**app/utils.py** - Parameter validation, logging setup, POS filtering, and normalization
- `pymorphy2.MorphAnalyzer` singleton for Russian morphological analysis
- `POS_MAPPING`: maps user-friendly names (noun, verb, adjective) to pymorphy2 codes
- `POS_GROUPS`: convenient groupings (adjective = ADJF+ADJS, verb_all = VERB+INFN+PRTF+PRTS+GRND)
- `normalize_word()`: converts word to normal form (nominative singular for nouns)
- `filter_words_by_pos()`: filters word list by part of speech using morphological analysis
- `get_word_pos()`: returns pymorphy2 POS tag for a word

### Request Flow

1. FastAPI receives request at `/api/words`
2. `validate_parameters()` validates all inputs (including pos_filter)
3. Search count is increased to compensate for filtering:
   - If `pos_filter` is set: multiply by 5
   - If `normalize` is set: multiply by 3 (compensates for duplicates after normalization)
4. `embeddings_service.find_similar_words()` returns top N semantically similar words (or random words)
   - Computes cosine similarity for entire vocabulary
   - Sorts by similarity score
   - Applies stride and similarity_threshold filtering
5. If `normalize` is set:
   - `normalize_word()` converts each word to its base form (именительный падеж единственного числа)
   - Duplicates are removed while preserving order (e.g., "стула", "столу" → "стол")
6. If `pos_filter` is set, `filter_words_by_pos()` analyzes and filters words by part of speech
7. Results are truncated to requested count
8. `apply_transformations()` modifies words based on flags
9. Returns JSON with query echo and transformed results

### Important Implementation Details

- **Navec Model**: Downloaded to `navec_hudlit_v1_12B_500K_300d_100q.tar` on first run, cached in Docker volume at `/root/.navec`
- **pymorphy2**: Russian morphological analyzer loaded as singleton; dictionary includes ~5M word forms
- **Singleton Pattern**: `embeddings_service` and `morph` analyzer are global instances to avoid reloading
- **Cyrillic Handling**: Words are lowercased for lookup; API requires URL-encoded Cyrillic in requests
- **Stride Logic**: When stride > 0, samples every (stride+1)th word from sorted similarity list, then backfills if needed
- **Similarity Filtering**: Uses Jaccard similarity (intersection/union of character sets) to filter lexically similar words
- **POS Filter Multiplier**: Searches 5x the requested count when POS filter is active, to ensure enough results after filtering
- **Normalize Multiplier**: Searches 3x the requested count when normalize is enabled, to compensate for duplicates removed after lemmatization
- **Duplicate Removal**: When normalize=true, duplicates are removed while preserving order (first occurrence kept)

## Configuration

- **PORT**: Environment variable, defaults to 8081 (external) / 8080 (internal container port)
- **Logging**: Configured in app/utils.py at INFO level with timestamp format
- **Limits**: max count=100, max skip_letters=word length, similarity_threshold 0.0-1.0

## Part of Speech (POS) Filtering

### Available POS Filters

**Individual parts of speech:**
- `noun` - существительное
- `adjf` - прилагательное полное
- `adjs` - прилагательное краткое
- `verb` - глагол личная форма
- `infn` - глагол инфинитив
- `prtf` - причастие полное
- `prts` - причастие краткое
- `grnd` - деепричастие
- `numr` - числительное
- `advb` - наречие
- `npro` - местоимение-существительное
- `pred` - предикатив
- `prep` - предлог
- `conj` - союз
- `prcl` - частица
- `intj` - междометие

**Convenient groups:**
- `adjective` - все прилагательные (ADJF + ADJS)
- `verb_all` - все глагольные формы (VERB + INFN + PRTF + PRTS + GRND)
- `participle` - причастия (PRTF + PRTS)
- `all` - без фильтрации (по умолчанию)

## API Interactive Docs

- Swagger UI: http://localhost:8081/docs
- ReDoc: http://localhost:8081/redoc
