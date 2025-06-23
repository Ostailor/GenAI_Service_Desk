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
Define Pydantic/SQLAlchemy models for Tenant, User, Ticket, KnowledgeDoc, Embedding, ChatSession; wire migrations with Alembic.

Provide a seed.py script that inserts demo tenants and prints row counts—if counts match the manifest the phase is good. 

Phase 2 – Local LLM Runtime (Ollama)
Package Ollama in its own container, expose /generate, /embeddings, /status; pull Llama-3 weights or another instruction-tuned model. 

check_llm.py sends a 10-token prompt and asserts a non-empty reply under 1 s—pass ⇒ phase complete.

Phase 3 – Vector Store & Knowledge Loader
Stand-up Qdrant; write an ETL that chunks docs, calls Ollama’s embedding endpoint, and loads vectors into per-tenant collections or partitioned payloads. 

recall_check.py runs K-NN on a labelled mini-set and prints recall@5 ≥ 0.80 → success.

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