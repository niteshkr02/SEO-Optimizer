# SEO Optimizer

> Evidence-based Technical SEO Diagnosis, Competitor Intelligence, and Website Code Resolution Platform.

SEO Optimizer is an enterprise-grade platform designed to identify technical SEO bottlenecks with 100% deterministic, reproducible evidence (raw HTTP headers, DOM selectors, parsed JSON-LD payloads, status code timelines), provide transparent mathematical category scoring, calculate competitor gaps, and facilitate human-approved source-code remediation.

---

## Key Principles

- **Zero-Hallucination & Rule-Based Core**: No ML/LLMs used for diagnostic detection, severity rating, competitor gaps, or mathematical scoring.
- **5-State Audit Outcomes**: Every audit rule evaluates deterministically to `PASS`, `FAIL`, `UNKNOWN`, `NOT_TESTED`, or `NOT_APPLICABLE`.
- **Verifiable Proof**: Every finding includes exact observed vs. expected values, raw HTML/header snippets, and DOM selectors.
- **Decoupled Scoring**: The internal Technical SEO Health Score (0–100) measures web standards compliance, strictly decoupled from Google ranking signals.
- **Complete Mathematical Model Governance**: 36 deterministic models ($E1$–$E36$) with explicit provenance, denominator safety, and null handling (never fabricated zeros).
- **Zero-Trust SSRF Protection**: Comprehensive CIDR denylists, DNS pre-resolution, and socket pinning to eliminate SSRF and DNS rebinding attacks.
- **Zero Host Execution of Client Code**: Untrusted client code is never executed on the host. Remediation is handled via static AST analysis and containerized micro-sandboxes.
- **Human Approval Gates**: All code modifications and paid third-party API calls require explicit, auditable confirmation.

---

## Monorepo Architecture

```
seo-optimizer/
├── apps/
│   ├── web/                         # Next.js 15 App Router (React, TypeScript, Tailwind CSS)
│   │   ├── src/app/                 # Public scan interface & Admin Resolution Center
│   │   ├── src/components/          # Reusable UI components & evidence modals
│   │   ├── src/features/            # Feature-specific client state
│   │   └── src/lib/api/generated/   # Auto-generated TypeScript client from FastAPI OpenAPI
│   └── api/                         # Single primary backend (Python 3.12+ / FastAPI)
│       ├── pyproject.toml           # Python dependency specification (uv managed)
│       ├── uv.lock                  # Pinned dependency lockfile
│       ├── app/
│       │   ├── main.py              # FastAPI application initialization
│       │   ├── api/v1/endpoints/    # REST endpoints (/scan, /leads, /health)
│       │   ├── core/                # Settings, logging, security, errors
│       │   ├── contracts/           # Pydantic v2 domain schemas (single source of truth)
│       │   ├── crawler/             # Safe HTTP fetcher, socket pinning, SSRF guard
│       │   ├── parsers/             # BeautifulSoup 4, lxml, JSON-LD, robots, sitemaps
│       │   ├── rules/               # Deterministic 5-state rules engine
│       │   ├── scoring/             # Category & Overall Health Scores (E1-E5)
│       │   ├── metrics/             # Technical, CWV, asset, and trend metrics
│       │   ├── competitor/          # SERP records, competitor page observations
│       │   ├── gap_analysis/        # Topic, keyword, backlink gap models (E16-E18, E22)
│       │   ├── resolution/          # Runbooks, triage composite, placement, RICE priority
│       │   ├── verification/        # Fix validation, regression, before/after metrics, DiD
│       │   ├── integrations/        # PSI, GSC OAuth2, licensed SERP provider
│       │   ├── persistence/         # Supabase PostgreSQL models & Alembic migrations
│       │   └── workers/             # Isolated asynchronous workers (as needed)
│       └── tests/                   # Pytest & Hypothesis property-based test suites
├── docs/                            # Comprehensive architectural and mathematical specifications
├── contracts/                       # Exported OpenAPI schemas (contracts/openapi_v1.json)
├── .github/                         # Workflows for CI/CD, linting, and security audits
├── package.json                     # Frontend workspace descriptor (pnpm)
├── pnpm-workspace.yaml              # Frontend workspace definition
└── README.md
```

---

## Documentation

Comprehensive architecture, security, and mathematical specifications are located in the [`docs/`](./docs) directory:

- [Project Brief](./docs/PROJECT_BRIEF.md) — Vision, business model, personas, core workflow, and roadmap scope.
- [System Architecture](./docs/ARCHITECTURE.md) — Technology stack, component boundaries, sequence flows, and persistence schema.
- [Mathematical Model Catalogue](./docs/MATHEMATICAL_MODEL_CATALOG.md) — Complete specifications for all 36 deterministic mathematical models ($E1$–$E36$).
- [Data Provenance & Dictionary](./docs/DATA_PROVENANCE_AND_DICTIONARY.md) — Telemetry taxonomy, schema dictionary, zero-fabrication policies, and token encryption.
- [Security Requirements](./docs/SECURITY_REQUIREMENTS.md) — SSRF defense, CIDR denylists, socket pinning, ZIP quarantine, and sandbox isolation.
- [Architecture Decisions (ADRs)](./docs/ARCHITECTURE_DECISIONS.md) — Formal records of key architectural decisions.
- [Implementation Roadmap](./docs/IMPLEMENTATION_ROADMAP.md) — Phase-by-phase deliverables, work packages, rule inventory, and testing strategy.

---

## Development Prerequisites

### Tooling
- **Python**: `>= 3.12`
- **uv**: Package and virtual environment manager (`curl -LsSf https://astral.sh/uv/install.sh` or `winget install astral-sh.uv`)
- **Node.js**: `>= 20.0.0` (for Next.js frontend only)
- **pnpm**: `>= 9.0.0` (`npm install -g pnpm`)
- **Database**: Supabase PostgreSQL project (dedicated development instance)

---

## Core Workflow

$$\text{Diagnose} \longrightarrow \text{Collect Data} \longrightarrow \text{Discover Competitors} \longrightarrow \text{Compare} \longrightarrow \text{Calculate Gaps} \longrightarrow \text{Plan Resolution}$$
$$\longrightarrow \text{Approve (Human)} \longrightarrow \text{Modify (AST)} \longrightarrow \text{Test (Sandbox)} \longrightarrow \text{Deploy (Client)} \longrightarrow \text{Verify} \longrightarrow \text{Monitor}$$
