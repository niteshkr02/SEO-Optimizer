# SEO Optimizer — Architectural Decision Records (ADRs)

> **Version**: 2.0.0 (Foundation Alignment)  
> **Status**: Approved Foundation Records  
> **Backend Architecture**: Python 3.x | FastAPI  
> **Frontend Architecture**: Next.js (TypeScript) | React  

---

## Index of Architectural Decisions

- [ADR-001: Decoupled Application Architecture with Next.js Frontend and Python FastAPI Backend](#adr-001-decoupled-application-architecture-with-nextjs-frontend-and-python-fastapi-backend)
- [ADR-002: Python + FastAPI as the Single Primary Backend Framework (Replacing Fastify/Node.js)](#adr-002-python--fastapi-as-the-single-primary-backend-framework-replacing-fastifynodejs)
- [ADR-003: Pure Deterministic Rule Engine vs. ML/LLM for Diagnostic Scoring and Gap Analysis](#adr-003-pure-deterministic-rule-engine-vs-mlllm-for-diagnostic-scoring-and-gap-analysis)
- [ADR-004: BeautifulSoup 4 + lxml Static Parsing for Phase 1 vs. Headless Browser](#adr-004-beautifulsoup-4--lxml-static-parsing-for-phase-1-vs-headless-browser)
- [ADR-005: Defense-in-Depth SSRF Defense via Socket Pinning and Comprehensive CIDR Filtering](#adr-005-defense-in-depth-ssrf-defense-via-socket-pinning-and-comprehensive-cidr-filtering)
- [ADR-006: Supabase PostgreSQL for Relational Persistence, JSONB Proofs, and Row-Level Security](#adr-006-supabase-postgresql-for-relational-persistence-jsonb-proofs-and-row-level-security)
- [ADR-007: Ephemeral Sandboxing and Static AST Rewriting for Code Remediation](#adr-007-ephemeral-sandboxing-and-static-ast-rewriting-for-code-remediation)
- [ADR-008: 5-State Finding Results Model](#adr-008-5-state-finding-results-model)
- [ADR-009: Decoupling Internal Health Score from Search Engine Ranking Signals](#adr-009-decoupling-internal-health-score-from-search-engine-ranking-signals)
- [ADR-010: Mandatory Human Approval Gate for Code Modifications and Paid External APIs](#adr-010-mandatory-human-approval-gate-for-code-modifications-and-paid-external-apis)
- [ADR-011: Complete Mathematical Model Catalogue (E1–E36) and Provenance Versioning](#adr-011-complete-mathematical-model-catalogue-e1e36-and-provenance-versioning)
- [ADR-012: Package Management Strategy: `uv` for Python Backend and `pnpm` for Next.js Frontend](#adr-012-package-management-strategy-uv-for-python-backend-and-pnpm-for-nextjs-frontend)
- [ADR-013: Architectural Boundary and Deferral Strategy for Distributed Task Queues](#adr-013-architectural-boundary-and-deferral-strategy-for-distributed-task-queues)

---

### ADR-001: Decoupled Application Architecture with Next.js Frontend and Python FastAPI Backend

- **Status**: Accepted (Supersedes ADR-001 v1.0)
- **Context**:
  The system consists of a web presentation tier (marketing, scan submission, interactive report viewer, admin diff review) and a high-integrity analytical scanning engine that executes low-level networking, HTML parsing, and complex mathematical algorithms. Maintaining a monolithic Next.js application for scanning would limit socket-level egress controls and mathematical testing. Conversely, a monolithic Node.js monorepo compromises numerical computing ergonomics.
- **Decision**:
  Adopt a clean, decoupled two-tier application repository:
  - Frontend: Next.js App Router (`apps/web`), TypeScript, Tailwind CSS.
  - Backend: Python 3.12+ with FastAPI (`apps/api`).
  The frontend consumes the backend via auto-generated TypeScript API clients derived directly from FastAPI's OpenAPI 3.1 schema (`apps/web/src/lib/api/generated/`). No duplicate DTO definitions are maintained by hand.
- **Consequences**:
  - *Positive*: Clear architectural boundary; type safety synchronized via OpenAPI; optimal technology choices for both presentation and scientific calculation.
  - *Negative*: Two runtime environments (Python and Node.js for frontend tooling) managed across development workflows.

---

### ADR-002: Python + FastAPI as the Single Primary Backend Framework (Replacing Fastify/Node.js)

- **Status**: Accepted (Supersedes ADR-002 v1.0)
- **Context**:
  Previously, Fastify (Node.js) was proposed as the scanner microservice. However, the product's primary priorities are **data quality, mathematical analysis, data provenance, competitor gap calculations, and verifiable resolution modeling**. Python is the undisputed industry standard for scientific and mathematical computing, property-based verification (Hypothesis), string and AST parsing, and statistical analysis. Maintaining a Node.js backend would hinder mathematical verification and duplicate analytical logic.
- **Decision**:
  Designate Python 3.x with FastAPI as the **sole primary backend framework** for SEO Optimizer (`apps/api`). Node.js/Fastify/Express is completely eliminated from the backend architecture. TypeScript is strictly confined to the Next.js frontend application.
- **Consequences**:
  - *Positive*: First-class support for mathematical and statistical models ($E1$–$E36$); robust type validation via Pydantic v2; access to standard scientific libraries (NumPy, Pandas) where justified; property-based test suites using Hypothesis.
  - *Negative*: Requires Python-based SSRF socket pinning implementation (handled via custom `httpx` transport hooks).

---

### ADR-003: Pure Deterministic Rule Engine vs. ML/LLM for Diagnostic Scoring and Gap Analysis

- **Status**: Accepted
- **Context**:
  Modern SEO tools frequently advertise "AI audits," which produce non-deterministic scores, hallucinated advice, and unrepeatable diagnostic findings across scans of identical pages. This destroys credibility with clients and software engineers.
- **Decision**:
  SEO Optimizer strictly prohibits Machine Learning, LLMs, or probabilistic heuristics in its core diagnostic, scoring, competitor gap, prioritization, and verification engines. All evaluations must be pure, deterministic functions returning reproducible findings backed by verbatim evidence. AI may be added in later phases strictly as an optional, clearly-labeled drafting/explanation assistant.
- **Consequences**:
  - *Positive*: 100% reproducible audits; zero hallucinations; legally and technically defensible findings; high execution speed; zero third-party LLM operational costs.
  - *Negative*: Edge cases not explicitly covered by the rule registry evaluate to `UNKNOWN` until explicit rules are authored.

---

### ADR-004: BeautifulSoup 4 + lxml Static Parsing for Phase 1 vs. Headless Browser

- **Status**: Accepted
- **Context**:
  Rendering pages with headless Chrome/Playwright consumes 200–500MB of RAM per instance, takes 2–5 seconds per page load, and introduces substantial container escape and browser exploit surfaces. In Phase 1, critical technical SEO signals (HTTP status, headers, redirects, meta robots, canonical URLs, titles, headings, image alts, JSON-LD) are embedded directly in the initial server-rendered HTML.
- **Decision**:
  Use BeautifulSoup 4 with the `lxml` C-parser for Phase 1 static page auditing. Single-Page Applications (SPAs) that fail to render meaningful DOM content are detected statically, flagged with `SPA_DETECTED`, and affected checks return `UNKNOWN` or `NOT_TESTED`. Playwright headless browser rendering is deferred to a dedicated, containerized worker in later phases.
- **Consequences**:
  - *Positive*: Sub-40ms parsing time, minimal memory footprint, high scanning concurrency on modest server infrastructure.
  - *Negative*: Cannot audit content injected exclusively via client-side JavaScript execution in Phase 1 (disclosed transparently).

---

### ADR-005: Defense-in-Depth SSRF Defense via Socket Pinning and Comprehensive CIDR Filtering

- **Status**: Accepted
- **Context**:
  Accepting arbitrary user-submitted URLs for server-side fetching creates a high-severity Server-Side Request Forgery (SSRF) and DNS rebinding (TOCTOU) vulnerability. Standard HTTP libraries perform DNS resolution internally during TCP connection, creating a race condition where a benign IP at validation time resolves to `127.0.0.1` or `169.254.169.254` at fetch time.
- **Decision**:
  Implement defense-in-depth SSRF protection in `apps/api/app/crawler/`:
  1. Strict protocol (`http`, `https`) and port (`80`, `443`) whitelist.
  2. DNS pre-resolution inspecting all A and AAAA records, rejecting unsafe or mixed internal/public answers.
  3. Comprehensive CIDR denylist covering private (RFC 1918), loopback, link-local, cloud metadata (`169.254.169.254`), multicast, and IPv4-mapped IPv6.
  4. Socket pinning to the pre-validated IP address (or egress firewall/proxy enforcement), passing the original domain via the `Host` header and TLS SNI.
  5. Manual hop-by-hop redirect validation (max 5 hops).
- **Consequences**:
  - *Positive*: Mathematically eliminates DNS rebinding; blocks access to internal cloud metadata and VPC infrastructure.
  - *Negative*: Requires custom `httpx` transport hooks to manage pinned IP connections and TLS handshakes.

---

### ADR-006: Supabase PostgreSQL for Relational Persistence, JSONB Proofs, and Row-Level Security

- **Status**: Accepted
- **Context**:
  The application requires structured relational models for accounts, sites, scans, pages, competitor records, resolution tasks, and leads, while simultaneously needing flexible schema storage for diverse raw evidence snapshots (JSON-LD schemas, header dictionaries, DOM node trees).
- **Decision**:
  Adopt Supabase-hosted PostgreSQL 15+ as the primary database. Use normalized relational tables for core business entities, typed `JSONB` columns for variable proof objects, Alembic for versioned schema migrations, and PostgreSQL Row-Level Security (RLS) for tenant isolation.
- **Consequences**:
  - *Positive*: Enterprise ACID guarantees, fast relational joins, JSON indexing and queryability, native RLS security, and real-time subscription capabilities.
  - *Negative*: Schema changes require disciplined Alembic migration scripts.

---

### ADR-007: Ephemeral Sandboxing and Static AST Rewriting for Code Remediation

- **Status**: Accepted
- **Context**:
  Phase 5 involves patching client codebases from uploaded ZIP archives. Executing untrusted client code (e.g. running `npm install`, build scripts, or test runners) on the API host introduces critical Remote Code Execution (RCE) risks.
- **Decision**:
  Never execute client code on the main application server. Code remediation will operate via static Abstract Syntax Tree (AST) inspection and rewriting. Build and test verification will execute exclusively within ephemeral, unprivileged microVMs / sandboxes (e.g., gVisor, Firecracker) with zero network egress, destroyed immediately after execution.
- **Consequences**:
  - *Positive*: Complete elimination of host RCE vulnerabilities; deterministic, reviewable Git unified diffs (`.patch`).
  - *Negative*: Requires containerized sandbox infrastructure for Phase 5.

---

### ADR-008: 5-State Finding Results Model

- **Status**: Accepted
- **Context**:
  Traditional SEO scanners enforce a binary Pass/Fail model. When a check cannot be completed (e.g. target timeout fetching `robots.txt`) or is irrelevant (e.g. multilingual checks on a monolingual site), binary models assign unfair penalties or false confidence.
- **Decision**:
  Standardize all audit rule outputs on a 5-state enum: `PASS`, `FAIL`, `UNKNOWN`, `NOT_TESTED`, and `NOT_APPLICABLE`.
- **Consequences**:
  - *Positive*: Eliminates false positives and false negatives; enables accurate calculation of the Report Completeness Index ($E5$); establishes technical trust.
  - *Negative*: Requires UI components to cleanly distinguish and explain 5 distinct evaluation states.

---

### ADR-009: Decoupling Internal Health Score from Search Engine Ranking Signals

- **Status**: Accepted
- **Context**:
  Many SEO platforms mislead clients by claiming their proprietary health scores correlate directly with Google ranking algorithms, creating customer disputes when rankings do not move in tandem with score increases.
- **Decision**:
  Formally define our scores as **Technical SEO Health Scores (0–100)**, measuring strict adherence to web standards, schema specifications, and search crawler guidelines. All documentation and user-facing reports must explicitly state that the health score measures technical compliance and crawl efficiency, not Google ranking favoritism.
- **Consequences**:
  - *Positive*: Protects brand integrity and legal defensibility; establishes credibility with software engineers.
  - *Negative*: Requires client education to manage expectations regarding ranking guarantees.

---

### ADR-010: Mandatory Human Approval Gate for Code Modifications and Paid External APIs

- **Status**: Accepted
- **Context**:
  Unattended automated code deployment and unchecked third-party API consumption (PageSpeed Insights, paid SERP APIs) create liabilities for client site outages and runaway vendor billing.
- **Decision**:
  Enforce strict manual approval gates. Code patches generated in the Admin Resolution Center must be explicitly reviewed and approved by both an engineer and the client before being applied or downloaded. Paid third-party API integrations require explicit user activation and confirmation.
- **Consequences**:
  - *Positive*: Complete auditability; zero unexpected vendor charges; zero risk of unattended client outages.
  - *Negative*: Prevents fully hands-off automated remediation (deliberate safety trade-off).

---

### ADR-011: Complete Mathematical Model Catalogue (E1–E36) and Provenance Versioning

- **Status**: Accepted
- **Context**:
  Brainstorming identified 36 distinct mathematical models spanning diagnostics, category scoring, competitor visibility, content gaps, keyword opportunities, resolution triage, and econometric outcome evaluation. Silently omitting formulas or burying them in ad-hoc code creates technical debt and inconsistent behavior.
- **Decision**:
  Formally catalogue every formula ($E1$ through $E36$) in `docs/MATHEMATICAL_MODEL_CATALOG.md`. Every model is implemented in Python as a pure function, mapped to a specific project phase, versioned, and verified via `pytest` and `Hypothesis`. Missing inputs evaluate to `NULL` / `UNKNOWN`, never fabricated zeros.
- **Consequences**:
  - *Positive*: Full architectural transparency; reproducible calculations; guaranteed formula governance.
  - *Negative*: Requires maintaining comprehensive unit and property-based test suites for all 36 models.

---

### ADR-012: Package Management Strategy: `uv` for Python Backend and `pnpm` for Next.js Frontend

- **Status**: Accepted
- **Context**:
  The repository combines a Python analytical backend and a TypeScript Next.js frontend. Standard Python tooling (`pip`, `pip-tools`) can be slow and lacks unified lockfile ergonomics. For the frontend, `pnpm` provides fast, disk-efficient workspace management.
- **Decision**:
  Standardize on `uv` for Python virtual environment and dependency management under `apps/api` (`pyproject.toml`, `uv.lock`). Standardize on `pnpm` for frontend dependency management under `apps/web` (`package.json`, `pnpm-lock.yaml`).
- **Consequences**:
  - *Positive*: 10–100x faster Python dependency resolution; deterministic cross-platform lockfiles; clean workspace boundaries.
  - *Negative*: Developers must have both `uv` and `pnpm` installed in their local development environments.

---

### ADR-013: Architectural Boundary and Deferral Strategy for Distributed Task Queues

- **Status**: Accepted
- **Context**:
  Phase 1 focuses on a public single-page scanner with a strict 10-second timeout. Introducing distributed broker infrastructure (Redis + Celery / Arq) prematurely adds unnecessary operational complexity to the local development environment and MVP deployment.
- **Decision**:
  Implement Phase 1 scans synchronously via bounded FastAPI request-response handlers with lightweight concurrency controls. Distributed queues (Redis / Arq / Celery) are deferred to Phases 3–5 when multi-page crawling, bulk SERP batches, and microVM remediation workloads justify them. All domain services must be designed as stateless, callable Python functions so they can be dispatched by queue worker entrypoints without refactoring.
- **Consequences**:
  - *Positive*: Fast local onboarding; zero Redis dependency for Phase 1; simplified CI/CD pipeline.
  - *Negative*: Long-running batch crawls cannot be initiated in Phase 1 (aligned with MVP scope).
