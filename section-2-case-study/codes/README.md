# History Exam Paper Alignment Tool

Dockerized MVP for Section 2 Scenario 4. The product is scoped to History exam-paper PDFs and compares uploaded papers against the latest configured 2026 History syllabus.

## Run Locally With Make

Install dependencies:

```bash
make install
```

Start the FastAPI backend and Vite frontend together:

```bash
make dev
```

`make dev` disables backend analysis caching so repeated uploads exercise the full pipeline during end-to-end testing.

Run a production-like local build with backend analysis caching enabled:

```bash
make prod
```

Open:

```text
http://localhost:5173
```

Backend API:

```text
http://localhost:8000/docs
```

The root `main.py` is the executable backend launcher used by `make backend` and `make dev`.

## Run With Docker

```bash
cp .env.example .env
make docker-up
```

Open:

```text
http://localhost:5173
```

Backend API:

```text
http://localhost:8000/docs
```

Docker uses a single multi-stage `Dockerfile`; Docker Compose selects the `backend` and `frontend` targets.

## Local Model Options

Default model settings live in `config.yaml` at the repository root:

```yaml
model:
  provider: openai-compatible
  llm_endpoint: http://localhost:1234/v1
  name: qwen/qwen3.6-35b-a3b
```

Environment variables such as `MODEL_PROVIDER`, `MODEL_BASE_URL`, and `MODEL_NAME` can still override the root config for one-off runs. For deterministic local pipeline testing without a running model, set:

```bash
MODEL_PROVIDER=mock
```

## End-To-End Local Test

```bash
python3 scripts/run_e2e_local_model_test.py \
  --pdf data/raw/exam_pdfs/2174_specimen_paper_1.pdf \
  --provider mock
```

For LM Studio:

```bash
python3 scripts/run_e2e_local_model_test.py \
  --pdf data/raw/exam_pdfs/2174_specimen_paper_1.pdf \
  --provider openai-compatible \
  --base-url http://localhost:1234/v1 \
  --model qwen/qwen3.6-35b-a3b \
  --require-real-model
```

For Ollama:

```bash
python3 scripts/run_e2e_local_model_test.py \
  --pdf data/raw/exam_pdfs/2174_specimen_paper_1.pdf \
  --provider ollama \
  --base-url http://localhost:11434 \
  --model qwen2.5vl:latest \
  --require-real-model
```

Reports are written to `data/processed/json/{job_id}/comparison_report.json`.

If `--require-real-model` is omitted, the script still runs end to end but will only fail when the model call itself fails. With `--require-real-model`, it first checks `/v1/models` for LM Studio/OpenAI-compatible servers or `/api/tags` for Ollama.
