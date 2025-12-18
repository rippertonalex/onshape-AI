# onshape-AI

Onshape-AI is a Flask API (and optional Streamlit demo) that:

- **Chats about CAD** using OpenAI models
- **Analyzes Onshape Part Studios** by calling the Onshape REST API (v10) using your Onshape API keys
- **Runs a long pre-processing pipeline asynchronously** (to avoid API Gateway timeouts) and exposes a job status polling endpoint

## Quickstart (local dev)

### Prerequisites

- **Python**: 3.10 recommended (matches `zappa_settings.json`)
- **Onshape API keys**: `ACCESS_KEY` and `SECRET_KEY`
- **OpenAI API key**: `OPENAI_API_KEY`

### 1) Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2) Create a `.env` in the repo root

`application.py` will auto-load a `.env` from the repository root.

```bash
cat > .env <<'EOF'
# Required (Onshape)
ACCESS_KEY=...
SECRET_KEY=...

# Required (OpenAI)
OPENAI_API_KEY=...

# Optional (protect routes with a bearer token; see "Auth" below)
BEARER_TOKEN=...

# Optional (persist async job status/results to S3; useful in AWS)
S3_BUCKET_NAME=zappa-ylghz6vxt

# Optional (DB; only needed if you use the SQLAlchemy models/migrations)
SQLALCHEMY_DATABASE_URI=postgresql+psycopg2://user:pass@host:5432/dbname

# Optional
LOG_LEVEL=INFO
FLASK_CONFIG=DEV
EOF
```

### 3) Run the API

Flask 3.x recommended invocation:

```bash
flask --app application run --port 5000 --debug
```

Then verify it’s up:

```bash
curl -s http://localhost:5000/v1/ | python -m json.tool
```

## API overview

This service mounts routes under the `/v1` base path. The chat blueprint is mounted under `/chat`, so endpoints look like `/v1/chat/...`.

### Endpoints

- **POST** `/v1/chat/`
  - **Body**: `{ "message": string, "history"?: [{ "role": "user"|"assistant", "content": string }...] }`
  - **Response**: includes `response` plus the updated `history` and some debugging metadata (`total_time_seconds`, `tools_called_summary`, etc.)

- **POST** `/v1/chat/onshape`
  - **Body**: `{ "message": string, "part_studio_url": string, "history"?: [...] }`
  - **Response**: includes `response`, `enriched_feature_summary`, `parsed_features`, and updated `history`

- **POST** `/v1/chat/pre_processing`
  - Starts the long-running preprocessing pipeline asynchronously
  - **Body**: `{ "part_studio_url": string }`
  - **Response**: returns a `job_id` immediately

- **GET** `/v1/chat/job_status/<job_id>`
  - Poll for status/progress/result of a preprocessing job

## Curl examples (local dev + production)

These are intended to be copy/paste friendly for both local dev and AWS prod.

### Basic chat (local)

```bash
curl -X POST "http://localhost:5000/v1/chat/" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hello! What can you do?"
  }'
```

### Onshape chat (local)

```bash
curl -X POST "http://localhost:5000/v1/chat/onshape" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What features are in this part studio?",
    "part_studio_url": "https://cad.onshape.com/documents/34194a7792ea9db6d10188d3/w/2603dadfb9d5ccf8117390d0/e/140112c65afa2d3dddb074ba"
  }'
```

### Start async preprocessing (local)

```bash
curl -X POST "http://localhost:5000/v1/chat/pre_processing" \
  -H "Content-Type: application/json" \
  -d '{
    "part_studio_url": "https://cad.onshape.com/documents/34194a7792ea9db6d10188d3/w/2603dadfb9d5ccf8117390d0/e/140112c65afa2d3dddb074ba"
  }'
```

### Poll job status (local)

```bash
curl -X GET "http://localhost:5000/v1/chat/job_status/{job_id}" \
  -H "Content-Type: application/json"
```

### Production base URL

If you deployed via Zappa, your API Gateway base will look like:

- `https://<api-id>.execute-api.<region>.amazonaws.com/<stage>`

This repo includes an example stage URL in `curl_examples.md`.

For a full set of scripts (including a `jq` polling loop), see `curl_examples.md`.

## Auth (optional bearer token)

There is a `token_required` decorator in `app/decorators.py` which expects:

- Header: `Authorization: Bearer <token>`
- Env var: `BEARER_TOKEN=<token>`

Note: the decorator is currently **commented out** on `POST /v1/chat/` in `app/routes/chat_routes.py`. If you enable it, your curl needs the header:

```bash
curl -X POST "http://localhost:5000/v1/chat/" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $BEARER_TOKEN" \
  -d '{"message":"Hello"}'
```

## Async preprocessing notes

Why async exists: API Gateway has a ~30s timeout, but preprocessing can take minutes. The async approach:

- Returns a `job_id` immediately
- Runs the pipeline in a background thread (Lambda and local are handled slightly differently)
- Stores job metadata in-memory and (optionally) persists completed jobs to S3

Docs:

- `ASYNC_PREPROCESSING_GUIDE.md`
- `DEPLOY_LAMBDA_FIXES.md`

## Streamlit demo (optional)

There’s a demo UI in `streamlit_app.py`. Streamlit is not pinned in `requirements.txt`, so install it separately:

```bash
pip install streamlit
streamlit run streamlit_app.py
```

## Deployment (AWS Lambda via Zappa)

Zappa config lives in `zappa_settings.json` (stage: `dev`).

Common commands:

```bash
zappa deploy dev
zappa update dev
zappa status dev
zappa tail dev
```

Key settings to sanity-check for long jobs:

- `timeout_seconds`: should be high enough (e.g. 900)
- `memory_size`: 1024+ recommended for preprocessing

## Troubleshooting

- **`OPENAI_API_KEY is not configured`**: set `OPENAI_API_KEY` in `.env` (local) or in Zappa env vars (AWS).
- **`Error: Onshape ACCESS_KEY or SECRET_KEY not found`**: set `ACCESS_KEY` + `SECRET_KEY`.
- **Jobs “disappear” in AWS**: Lambda is ephemeral. Set `S3_BUCKET_NAME` so completed job records can be reloaded from S3.
- **`ModuleNotFoundError: onshape_client`**: this project imports `onshape_client.onshape_url.OnshapeElement`. Ensure the corresponding dependency is installed in your environment (or add it to `requirements.txt` for deploys).

## Repo map (high level)

- **API entrypoint**: `application.py` → `app.create_app(...)`
- **Routes**: `app/routes/chat_routes.py`
- **Async preprocessing**: `app/commands/async_pre_processing.py` + `app/utils/job_manager.py`
- **Core Onshape tools**: `app/utils/onshape_tools.py`
- **Docs**: `curl_examples.md`, `ASYNC_PREPROCESSING_GUIDE.md`, `DEPLOY_LAMBDA_FIXES.md`