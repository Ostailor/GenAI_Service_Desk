Phase 0 – Project Skeleton & Tooling
The goal of Phase 0 is to stand-up a clean, reproducible project skeleton that already behaves like production software: it lints, unit-tests, containerises, boot-straps CI, and proves everything works through a single “smoke” command. Below is a purely descriptive expansion—no code—showing what you put in place and why each piece matters. Follow it step by step and you will finish Phase 0 with green lights locally and in GitHub Actions.

1 — Repository shape
Create a top-level directory for the project and inside it add three first-class folders:

src/ for all importable Python packages.
Why? The “src-layout” forces tests and scripts to import the installed copy of your code rather than the unchecked-out files, catching path-leak errors early.
packaging.python.org
reddit.com

tests/ for unit, integration, and later smoke tests.

infra/ for anything DevOps-related (Dockerfiles, Compose, Terraform, Kubernetes charts).

In src/ create an empty package directory such as helpdesk_ai/ that contains only an __init__.py. This is enough for the package installer and import system to work.
docs.python-guide.org
stackoverflow.com

Add placeholder files at the root:

pyproject.toml (single source of truth for dependencies, build back-end, Ruff lint rules, and pytest options).
pytest-cov.readthedocs.io

.pre-commit-config.yaml declares pre-commit hooks, starting with Ruff’s lint and Ruff’s formatter (lint first, format second, as recommended).
github.com
docs.astral.sh

README.md brief purpose statement so the repo is never empty.

smoke.sh a small shell script you will write later; for now leave a one-line comment describing its purpose.

2 — Developer ergonomics
Ruff as the linter/formatter.
Configure it in pyproject.toml (or ruff.toml) with your preferred line length and the rule sets you want enforced. The key advice from the Ruff maintainers is to place the lint hook before the formatter hook in pre-commit so auto-fixes are formatted afterwards.
github.com

pre-commit
Install the framework globally (pre-commit install) so every local commit is checked before reaching GitHub. The hook list initially runs only Ruff lint and Ruff format; add others later as the codebase grows.
stackoverflow.com

pytest & pytest-cov
Even though Phase 0 has no functional code, include these dev dependencies so pytest -q runs—and exits with zero tests collected—proving the harness is wired up.
pytest-cov.readthedocs.io
pytest-cov.readthedocs.io

3 — Container baseline with Docker Compose
Compose file lives in infra/compose.yml. Define three services you will flesh out later:

api (FastAPI app)

qdrant (vector store)

ollama (local LLM runner)

Add a HEALTHCHECK to every service. Each container must run a short command—usually a curl or wget against the service’s /health or /status endpoint—and exit 0 when the service is ready. Docker marks the container “healthy” once the command has succeeded a fixed number of times; retries and time-outs are part of the spec.
stackoverflow.com
paulsblog.dev

Build arguments, volumes and environment variables can stay minimal for now because Phase 0 is only about plumbing.

4 — CI bootstrap with GitHub Actions
Primary job – test.

Matrix over Python 3.11 and 3.12.

Steps: check out, set up chosen Python version, install the project with dev extras, run Ruff lint, run pytest.
GitHub’s own “Building and testing Python” guide shows the canonical pattern.
docs.github.com

Secondary job – smoke.
Triggered after test succeeds. Spins up Docker Compose in exactly the same way your local script will and fails the workflow if any service reports unhealthy. The long-standing feature request for Compose to “wait for healthy” reminds us that a custom helper script is still the simplest solution.
github.com

Limit the workflow trigger to push and pull_request events so forks can run their own pipelines without affecting you.

5 — The smoke test script (conceptual)
Purpose Bring the container stack up, poll Docker until every service is marked healthy, then tear the stack down. If any health check fails or times out the script exits 1.

Implementation outline

Change into the infra directory.

docker compose up -d --build to start services.

Poll docker compose ps --format json (or docker inspect) every few seconds, checking the Health.Status field.

After a maximum number of retries, exit with success or failure.

On success, docker compose down to leave the system clean for the next run.

The script belongs at repo root so both developers and the CI runner can execute ./smoke.sh identically.

6 — Definition of done for Phase 0
Verification step	Passing condition
Lint	            ruff check . exits 0 in local shell and CI.
Unit harness	    pytest -q exits 0 (even with “collected 0 items”) locally and in CI.
Container stack	    Running ./smoke.sh builds all images, brings them up, waits until Docker reports every container healthy, and exits 0.
CI pipeline	        GitHub Actions shows both test and smoke jobs green on the default branch.

Once those four lights are green you’ve locked down a testable, reproducible foundation. All team-mates (and any future recruiter who clones the repo) can run one command, see everything pass, and trust that later phases will slot neatly into place.

Phase 1 – Domain & Data Model
You will (1) decide how tenant data is isolated, (2) design the core entities—Tenant, User, Ticket, KnowledgeDoc, Embedding, ChatSession—plus their relationships, (3) implement them twice: as Pydantic v2 models for I/O validation and as SQLAlchemy 2.0 ORM classes for persistence, (4) scaffold automated, repeatable Alembic migrations, (5) load a handful of seed rows so every developer or CI job starts with identical demo data, and (6) extend the project’s smoke script/CI so they fail fast if the schema or seeds break. At the end of the phase you can run a single command that builds containers, applies migrations, inserts seeds, and prints a health summary—independent of all later RAG, LLM, or API work.

1 — Choose your multi-tenant isolation strategy
Pick a tenancy model: shared-database with a tenant_id column on every business table is the lightest operationally and pairs well with PostgreSQL Row-Level Security (RLS) for guard-rails at the SQL layer.

Enable RLS in the compose-supplied Postgres image (add ALTER TABLE … ENABLE ROW LEVEL SECURITY;). AWS, Azure and Logto blog posts show canonical patterns for pooling models; copy their approach.

Create one application role per service (e.g., api_srv) and grant it only SELECT/INSERT/UPDATE on rows where tenant_id matches the current setting of current_setting('app.tenant_id'). This keeps isolation logic out of ORM code.

2 — Draw the entity-relationship diagram (ERD)
Entity	           Key attributes	                                                                            Notes
Tenant	           id (UUID PK), name, plan, created_at	                                                      One row per customer organisation.
User	             id, tenant_id (FK), email, role, hashed_pw, created_at	                                    Composite uniqueness on (tenant_id, email) prevents cross-tenant collision.
Ticket	           id, tenant_id, owner_id (FK→User), status, priority, subject, body, created_at, updated_at	Matches common help-desk schemas used by DrawSQL and Reddit threads.
KnowledgeDoc	     id, tenant_id, title, path, checksum, added_at	                                            Points to PDF or Markdown in object storage.
Embedding	         id, doc_id (FK), chunk_index, vector (FLOAT[] 768), token_count	                          Store as PostgreSQL vector or FLOAT8[];
ChatSession	       id, tenant_id, user_id, created_at, summary	                                              Session-level metadata for analytics.

Keep polymorphism minimal—six tables, clear FKs, and a single tenant_id column lets RLS do its job.

3 — Implement dual models: Pydantic v2 & SQLAlchemy 2.0
Pydantic I/O models live in src/helpdesk_ai/schemas.py. Use field types (EmailStr, PositiveInt) and model-level validators for cross-field logic such as “closed tickets must have a closed_at timestamp”.

SQLAlchemy ORM classes sit in src/helpdesk_ai/models.py. Map with the recommended 2.0 declarative syntax (registry().map_imperatively() or MappedAsDataclass).

Naming conventions (snake_case, date prefixes in constraint names) and avoiding model imports inside migrations follow Alembic best-practice articles; document them in docs/style.md.

4 — Wire Alembic migrations
Initialise Alembic in infra/migrations/ and point it at your SQLAlchemy Base.metadata.

Configure the env script to read DB connection details from environment variables so it works in both local Docker and CI.

Use alembic revision --autogenerate -m "init" to create migration 0001, then freeze it. Autogenerate is fine for the first cut; later use hand-written upgrades when changes get non-trivial.
pingcap.com

Add a “migrations” target to smoke.sh: after the Compose database is up, run alembic upgrade head inside the database container or a one-shot migration container.

5 — Seed repeatable demo data
Write scripts/seed_demo.py that connects using SQLAlchemy’s async engine, inserts two tenants (e.g., “Acme Corp”, “Globex”), three users per tenant, and three open tickets per user.

Capture primary keys into a seed_manifest.json; later test phases can reference known IDs.

The script should be idempotent: running it twice must leave row counts unchanged (upserts or “skip-if-exists”). This pattern is described in multiple SQLAlchemy testing tutorials.
coderpad.io

Add the seed step to smoke.sh right after alembic upgrade head.

6 — Local health probe for Phase 1
Create scripts/db_health.py that:

Imports the ORM models.

Counts rows in each table and prints them formatted (“Tenants = 2, Users = 6…”).

Verifies at least one ticket row per tenant and one embedding row per knowledge doc; exit code 0 on success.

smoke.sh now calls:

alembic upgrade head && python scripts/seed_demo.py && python scripts/db_health.py

If any assertion fails the smoke exits non-zero, flagging Phase 1 problems immediately.

7 — CI integration
Extend the “test” job to spin up the database container and run only the model/seed health checks—these tests are independent of future API or Ollama code.

Keep the “smoke” job from Phase 0 unchanged; it automatically benefits from the new migration + seed steps you added to smoke.sh.

8 — Success criteria for Phase 1
Signal	                Passing condition
Alembic migration runs	alembic upgrade head finishes with no errors.
Seed script idempotent	Invoking twice results in same row counts.
Health probe	          python scripts/db_health.py exits 0 and prints counts ≥ expected.
CI	                    Both “test” and “smoke” jobs green after merge.
Docs	                  docs/style.md explains naming conventions, RLS strategy, and entity list.

Complete those items and you have a self-contained, proven data layer ready for whichever next phase (LLM engine, vector store, API) you decide to tackle—yet still usable on its own for demos, tests, or further ERD tweaks.


Phase 2 – Local LLM Runtime (Ollama)
Building on the green baseline from Phases 0 and 1, Phase 2 turns the project into a working “mini-LLMOps” layer: a locally-hosted Ollama server running Meta Llama-3, containerised with GPU support, exposed through stable REST endpoints (/generate, /embeddings, /status) and protected by health-checks and repeatable tests. When this phase is done you will be able to spin-up the stack, hit the model, measure latency / tokens-per-second, and see every test pass in CI—without touching any later phases.

1 Choose the model & verify resource needs
Model Pick Llama-3-8B-Instruct first; it is openly licensed, ~16 GB on disk and ~20 GB VRAM in FP16 so it fits a single modern GPU or an Apple-M-series machine.

Upgrade path Document that the 70 B variant needs ≈140 GB VRAM and >140 GB disk; keep it optional for multi-GPU nodes.

2 Local installation proof-of-life
Install the CLI (brew install ollama or Linux tarball) and pull the model with
ollama pull llama3—the CLI only downloads the diff on updates.

Start the daemon (ollama serve). By default it listens on port 11434.

Run a one-line smoke prompt:
curl http://localhost:11434/api/generate -d '{"model":"llama3","prompt":"ping"}'.
A non-empty JSON reply proves the local binary works.

3 Container-first deployment
Base image Use the official ollama/ollama image; it already carries the daemon and entry-point.

GPU runtime Follow NVIDIA Container Toolkit instructions so docker run --gpus all exposes the card to the container; same flags work in Compose.

Dockerfile tweaks

Pin the Ollama tag to avoid silent upgrades.

Add a HEALTHCHECK that GETs /status (returns {"status":"ok"} when the model is loaded).

Keep layers slim: copy only the small wrapper script, adopt Docker “best practice” list (multi-stage, .dockerignore, no extra packages).

4 Python access layer
Write ollama_client.py under src/helpdesk_ai/llm/ that wraps /generate, /embeddings, /status. Switch between streaming and non-streaming, add retry/back-off. API specs are published in the public docs and Postman collection.

Expose generate(prompt, system=None, temperature=0.7) and embed(text) helpers so later phases (RAG, chat) can stay model-agnostic.

Log timings; Ollama community threads show tokens-per-second benchmarks and a feature request for a built-in metric flag.

5 Compose integration & health route
Add a new service block ollama to infra/compose.yml (if not already stubbed):

Map 11434:11434.

Mount an anonymous volume for downloaded models so CI containers don’t re-pull on every run.

Include the Dockerfile’s HEALTHCHECK—Compose surfaces it via docker compose ps.

Update smoke.sh: after the database checks from Phase 1, poll docker compose ps until ollama is healthy, then run a single test prompt via curl and exit on non-zero.

6 Tests you add in this phase
Test focus	Tooling	Pass condition
Daemon status	pytest + httpx	GET /status returns 200 JSON {"status":"ok"} under 200 ms. 
Text generation	pytest (non-stream)	POST /generate with prompt “Hello” returns non-empty response field. 
Embeddings	pytest	POST /embeddings on “hello world” returns a vector length 768 (the default from many Ollama embedding models).
Latency budget	pytest-benchmark	20-token prompt P95 < 1 s on dev machine or < 2 s on CI CPU box. Benchmarks inspired by community scripts measuring t/s.
Concurrent safety	pytest + trio/anyio	Fire 10 parallel /generate calls; all must complete, none returns 5xx.

Tests live in tests/llm/ so CI can run them before any later-phase tests.

7 CI workflow updates
Install GPU driver layer only on self-hosted runners; on GitHub-hosted Ubuntu, stay CPU-only and accept slower latency threshold.

Add a new job llm-tests after lint but before the Phase 1 smoke; use the same Compose stack, then run pytest tests/llm -q.

8 Success criteria for Phase 2
Signal	                                Requirement
Local prompt works	                    curl …/generate returns text.
Compose container healthy	              docker compose ps shows healthy within 60 s of start-up.
Test suite green	                      pytest tests/llm passes locally and in CI.
Performance goal met	                  P95 latency & tokens/sec within documented budget on dev hardware.
Smoke script updated	                  ./smoke.sh now validates DB and LLM in one pass, still exits 0.


Phase 3 – Vector Store & Knowledge Loader
Phase 3 turns the project into a self-contained “knowledge layer”: every tenant can upload docs, the pipeline chunks them, creates embeddings with your local Ollama model, inserts them into Qdrant, and proves the vectors can be recalled with good accuracy. All of this is fully test-driven and independent of later RAG or API work.

1 Overview of the work in this phase
You will (1) decide how multitenancy is represented inside the vector store, (2) build a document-loader & chunker that handles PDFs, Markdown and HTML, (3) call Ollama’s /embeddings route to produce 768-dim vectors, (4) tune and create Qdrant collections/HNSW indexes, (5) write an idempotent ETL script that ingests and updates content, (6) expose health metrics, and (7) extend both your pytest suite and smoke.sh so Phase 3 breaks loudly if anything drifts. When complete you can start the stack, run python scripts/load_docs.py, and immediately query the store for top-k results—tests verify isolation, dimension, recall and latency.

2 Multitenancy design in Qdrant
Partition by payload, not by collection. Qdrant recommends a single collection with a tenant_id payload filter for most SaaS cases, calling the pattern “multitenancy” and warning that per-tenant collections waste RAM and complicate scaling 

Security guard-rail. Add a Postgres-style Row-Level Security analogue: every query the back-end issues includes filter={"must":[{"key":"tenant_id","match":{"value":<uuid>}}]}—this is enforced in a thin repository layer so later RAG code cannot forget it.

3 Document loading & chunking
Step	              Recommended tech & rationale
Parsing             PDFs/HTML	 Use the Unstructured loader from LangChain; it converts many formats and already emits layout metadata 

Chunk strategy	    LangChain’s RecursiveCharacterTextSplitter (or Unstructured chunker) at 512 tokens with 20 token overlap balances context retention and vector length 

File watcher	      A simple watchdog loop scans an uploads/ folder and feeds new or changed files into the ETL.

Each chunk inherits the file’s checksum & path so the loader can upsert instead of duplicating.

4 Embedding generation with Ollama
Model choice Start with llama3’s default embedding head; Ollama officially exposes /api/embeddings returning vectors (size 768 for Llama and most BGE-family models) 
ollama.com

Python wrapper Extend the ollama_client.py from Phase 2 with embed(text: str) -> list[float], handling batch requests and retry/back-off.

Latency goal < 100 ms per 512-token chunk on your GPU dev box (documented benchmarks put Llama-3-base in that range) 

5 Qdrant collection & index tuning
Create one collection called docs.

Vector size = 768, distance = Cosine.

HNSW params m=16, ef_construct=64; later raise ef_search at query time—Qdrant’s optimisation guide shows these as balanced defaults 

Payload schema tenant_id (UUID), doc_id, chunk_index, source (“pdf” | “html” | “md”), text.

Monitoring Enable /metrics and /healthz endpoints (available since v1.5.0) to integrate with Prometheus and your smoke test 

6 Idempotent loader script
Create scripts/load_docs.py that:

Reads a manifest (YAML/JSON) listing doc paths and tenant IDs.

Calculates SHA-256 checksum; skips re-ingestion if unchanged.

Runs the chunker, calls embed() in batches of 32.

Builds Qdrant “points” with {id, vector, payload} structure 

Upserts via the Python client’s upsert() method 

Logs total vectors, mean latency, failures.

Run it once during smoke.sh so the stack always contains predictable demo data.

7 Observability additions
Custom Prom metrics doc_loader_ingest_seconds, qdrant_upsert_vectors_total.

Health endpoint Expose GET /knowledge/ready in a tiny FastAPI app; it pings /healthz on Qdrant and /status on Ollama and returns 200 only if both pass.

8 Tests introduced in Phase 3
Test file	                               What it proves	                            Pass criteria
tests/knowledge/test_embedding_dim.py	   Ollama returns vectors of expected length.	                          len(vec)==768 
tests/knowledge/test_chunk_counts.py	   Chunker splits a sample PDF into ≥ N expected chunks (sanity).	      count >= expected_min
tests/knowledge/test_qdrant_insert.py	   Upsert returns status ok; total vector count equals chunk count.	    sums match
tests/knowledge/test_tenant_isolation.py Query with wrong tenant_id filter returns 0 hits.	                  assert empty
tests/knowledge/test_recall_at_5.py	     On a labelled mini-set of 50 Q/A pairs recall@5 ≥ 0.80.              Uses the same evaluation logic as VectorDBBench 
tests/knowledge/test_latency.py	         Median search latency under 50 ms for 10 random queries (CPU CI target 150 ms).	

All tests use the Compose stack; they live in tests/knowledge/ so they can run immediately after the Phase 2 suite.

9 CI & smoke script changes
New GitHub job knowledge-tests—depends on llm-tests; spins up Compose, runs loader script, then pytest tests/knowledge -q.

smoke.sh additions

After Ollama health check, call python scripts/load_docs.py --demo.

Curl GET /knowledge/ready; exit non-zero if not 200.

10 Definition of done for Phase 3
Signal	Requirement
Loader script	Runs idempotently; prints counts; exits 0.
Qdrant health	/readyz returns 200 in < 5 s after container start 
qdrant.tech
.
Tests green	All knowledge tests pass locally & in CI.
Smoke script	Builds stack, loads docs, verifies health, exits 0.
Docs updated	docs/knowledge.md explains chunk sizes, embedding model, HNSW params, multitenancy filter.

Meet these and you now own a robust, test-backed vector knowledge base—ready for Phase 4’s RAG chain yet fully verifiable on its own.

Phase 4 – Retrieval-Augmented Generation Chain
Assemble a LangChain pipeline (Retriever → (optional reranker) → LLM) with inline source citations. 

rag_smoke.py feeds a known query (“reset SSO password”) and verifies at least one citation matches a KB doc ID.

Phase 5 – Ticket Classifier & Workflow
Fine-tune/host a DistilBERT (or similar) model on an open IT-support dataset for ticket routing. 

Trigger routing inside a Temporal workflow with activities for assignment and escalation. 

route_demo.py injects 20 sample tickets; the script prints counts per queue—manual eyeball ≈ expected distribution → phase done.

Phase 6 – Multi-Tenancy, Auth & RBAC
Issue JWTs via OIDC, include tenant_id claim; enforce Casbin domain-aware RBAC in FastAPI middleware. 

auth_probe.py logs in as three roles and runs a CRUD matrix; if forbidden actions return 403, you’re good.

Phase 7 – Public API & SDK
Expose REST/WebSocket endpoints /chat, /tickets, /search, /metrics; autogenerate Python & TypeScript SDKs from the OpenAPI spec.

spec_lint.sh validates the OpenAPI JSON and imports the generated client to fetch /status.

Phase 8 – Observability & Cost Telemetry
Instrument with OpenTelemetry; export traces to Jaeger or LangSmith and metrics to Prometheus/Grafana. 

otel_check.py starts one chat session and asserts a new span named rag.generate_answer appears in the collector.

Phase 9 – Front-End UX
Deliver a React/Next.js SPA with multi-tenant theming and live chat via WebSockets.

npm run cypress:smoke opens a ticket, receives a bot answer, and checks the DOM contains the citation tags—pass → phase done.

Phase 10 – CI/CD & IaC
Define Terraform/CDK modules for the stack; wire GitHub Actions for build, test, deploy→staging.

pipeline_test.yml runs terraform validate and the compose smoke job; a green check on PR merge marks the phase complete.

Phase 11 – Security, Compliance & Governance
Add mTLS between services, eBPF pod firewalls, and structured audit logs to meet SOC-2 CC7 guidelines. 

security_smoke.py posts a ticket containing a dummy SSN and checks that the prompt sent to the LLM is redacted.

Phase 12 – Performance & Red-Team Suite
Load-test with Locust (200 rps, ≤1 % err) and run automated jailbreak/PII-leak probes.

perf_report.sh prints P95 latency and token-per-second stats; if thresholds met and all red-team probes “safe”, the platform is launch-ready.
