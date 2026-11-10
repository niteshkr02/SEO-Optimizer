# SEO Optimizer — Implementation Roadmap & Test Strategy

> **Version**: 2.0.0 (Foundation Alignment)  
> **Status**: Approved Implementation Plan  
> **Backend Implementation**: Python 3.x (FastAPI, Pydantic v2, uv, pytest, Hypothesis)  
> **Frontend Implementation**: Next.js 15 (TypeScript, React, Tailwind CSS, pnpm)  

---

## 1. Roadmap Overview & Phasing

The implementation of SEO Optimizer is structured into seven focused, incremental phases (Phase 0 through Phase 6). Every phase delivers a verifiable, end-to-end slice of functionality while adhering to the core architectural principles: zero hallucination, pure deterministic mathematics, verifiable evidence, strict SSRF defense, and explicit human approval gates.

```
+----------------------------------------------------------------------------------+
| PHASE 0: Foundation Alignment (CURRENT TASK)                                     |
| Python FastAPI + Next.js architecture alignment, E1-E36 models, data dictionary  |
+----------------------------------------+-----------------------------------------+
                                         |
                                         v
+----------------------------------------------------------------------------------+
| PHASE 1: Public Deterministic Page Scanner                                       |
| Single-page URL audit, SSRF guard, BS4/lxml parser, 5-state rules, E1-E5, E8-E14 |
+----------------------------------------+-----------------------------------------+
                                         |
                                         v
+----------------------------------------------------------------------------------+
| PHASE 2: Performance, Persistence & Lead Management                              |
| PageSpeed Insights (CrUX vs Lab), Supabase PostgreSQL, RLS, Leads, E6, E7, E29-E32|
+----------------------------------------+-----------------------------------------+
                                         |
                                         v
+----------------------------------------------------------------------------------+
| PHASE 3: Competitor & Data Intelligence                                          |
| Licensed SERP provider, competitor crawler, gaps, E15, E16, E17, E18, E22, E23   |
+----------------------------------------+-----------------------------------------+
                                         |
                                         v
+----------------------------------------------------------------------------------+
| PHASE 4: Mathematical Resolution Center                                          |
| Admin workspace, DOM triggers, runbooks, triage composite & RICE, E19, E20, E21  |
+----------------------------------------+-----------------------------------------+
                                         |
                                         v
+----------------------------------------------------------------------------------+
| PHASE 5: Secure Code Remediation & Sandboxed Patching                            |
| Client ZIP quarantine, static AST transforms, Git diffs, ephemeral micro-sandbox |
+----------------------------------------+-----------------------------------------+
                                         |
                                         v
+----------------------------------------------------------------------------------+
| PHASE 6: Authorized GSC & Outcome Analytics                                      |
| OAuth2 GSC, Search Analytics, URL inspection, E13, E24-E28, E33-E36 (DiD)       |
+----------------------------------------------------------------------------------+
```

---

## 2. Mathematical Model Implementation Matrix (E1–E36)

Every mathematical model documented in `docs/MATHEMATICAL_MODEL_CATALOG.md` is assigned to a specific phase, module, and testing file:

| Model ID | Formula Name | Target Phase | Implementation Module | Test File Path |
| :--- | :--- | :--- | :--- | :--- |
| **E1** | Deterministic SEO Check Values | Phase 1 | `apps/api/app/rules/evaluator.py` | `tests/unit/scoring/test_e1_check_mapping.py` |
| **E2** | Category Weighted SEO Health Score | Phase 1 | `apps/api/app/scoring/category.py` | `tests/unit/scoring/test_e2_category_score.py` |
| **E3** | Overall SEO Health Score | Phase 1 | `apps/api/app/scoring/overall.py` | `tests/unit/scoring/test_e3_overall_score.py` |
| **E4** | Legacy Severity-Deduction Model | Phase 1 | `apps/api/app/scoring/calibration.py` | `tests/unit/scoring/test_e4_legacy_deduction.py` |
| **E5** | Report Completeness Index | Phase 1 | `apps/api/app/scoring/completeness.py` | `tests/unit/scoring/test_e5_completeness.py` |
| **E6** | Core Web Vitals Thresholds | Phase 2 | `apps/api/app/metrics/cwv.py` | `tests/unit/metrics/test_e6_e7_cwv_normalization.py` |
| **E7** | Lower-is-Better Metric Normalization | Phase 2 | `apps/api/app/metrics/normalization.py` | `tests/unit/metrics/test_e6_e7_cwv_normalization.py` |
| **E8** | Broken Internal Link Ratio (BLR) | Phase 1 | `apps/api/app/metrics/links.py` | `tests/unit/metrics/test_e8_e9_internal_links.py` |
| **E9** | Internal Link Health (ILH) | Phase 1 | `apps/api/app/metrics/links.py` | `tests/unit/metrics/test_e8_e9_internal_links.py` |
| **E10** | Image Alt Attribute Coverage (IAC) | Phase 1 | `apps/api/app/metrics/assets.py` | `tests/unit/metrics/test_e10_image_alt.py` |
| **E11** | Redirect Hop Count & Loop Detection | Phase 1 | `apps/api/app/crawler/redirects.py` | `tests/unit/metrics/test_e11_redirects.py` |
| **E12** | Sitemap URL Health (SH) | Phase 1 | `apps/api/app/metrics/sitemap.py` | `tests/unit/metrics/test_e12_sitemap.py` |
| **E13** | Inspected Sample Indexation Rate (IR) | Phase 6 | `apps/api/app/integrations/gsc/metrics.py` | `tests/unit/verification/test_e13_indexation.py` |
| **E14** | JSON-LD Syntax Validity Ratio (JVR) | Phase 1 | `apps/api/app/parsers/jsonld.py` | `tests/unit/metrics/test_e14_jsonld.py` |
| **E15** | Competitor Visibility Score (CV) | Phase 3 | `apps/api/app/competitor/visibility.py` | `tests/unit/gap_analysis/test_e15_competitor_visibility.py` |
| **E16** | Weighted Content Coverage Gap ($G$) | Phase 3 | `apps/api/app/gap_analysis/content.py` | `tests/unit/gap_analysis/test_e16_content_gap.py` |
| **E17** | Keyword Opportunity Score (KO) | Phase 3 | `apps/api/app/gap_analysis/keywords.py` | `tests/unit/gap_analysis/test_e17_keyword_opportunity.py` |
| **E18** | Potential Click Opportunity (PCO) | Phase 3 | `apps/api/app/gap_analysis/clicks.py` | `tests/unit/gap_analysis/test_e18_clicks.py` |
| **E19** | Content Section Placement Score ($L$) | Phase 4 | `apps/api/app/resolution/placement.py` | `tests/unit/resolution/test_e19_placement.py` |
| **E20** | Root-Cause Triage Composite (RC) | Phase 4 | `apps/api/app/resolution/triage.py` | `tests/unit/resolution/test_e20_triage_composite.py` |
| **E21** | Resolution Priority (RICE-inspired) | Phase 4 | `apps/api/app/resolution/priority.py` | `tests/unit/resolution/test_e21_rice_priority.py` |
| **E22** | Referring Domain Gap (RDG) | Phase 3 | `apps/api/app/gap_analysis/backlinks.py` | `tests/unit/gap_analysis/test_e22_backlinks.py` |
| **E23** | Link Opportunity Relevance (LO) | Phase 3 | `apps/api/app/gap_analysis/backlinks.py` | `tests/unit/gap_analysis/test_e23_link_relevance.py` |
| **E24** | Search Console CTR | Phase 6 | `apps/api/app/integrations/gsc/analytics.py` | `tests/unit/verification/test_e24_e28_gsc_trends.py` |
| **E25** | Impression Decline Rate ($D_I$) | Phase 6 | `apps/api/app/metrics/trends.py` | `tests/unit/verification/test_e24_e28_gsc_trends.py` |
| **E26** | Click Decline Rate ($D_C$) | Phase 6 | `apps/api/app/metrics/trends.py` | `tests/unit/verification/test_e24_e28_gsc_trends.py` |
| **E27** | Average Position Change ($\Delta P$) | Phase 6 | `apps/api/app/metrics/trends.py` | `tests/unit/verification/test_e24_e28_gsc_trends.py` |
| **E28** | Potential Keyword Cannibalization ($K$)| Phase 6 | `apps/api/app/metrics/cannibalization.py`| `tests/unit/verification/test_e24_e28_gsc_trends.py` |
| **E29** | Scan Completion Rate (SCR) | Phase 2 | `apps/api/app/metrics/operational.py` | `tests/unit/verification/test_e29_e32_operational.py` |
| **E30** | Lead Conversion Rate (LCR) | Phase 2 | `apps/api/app/metrics/operational.py` | `tests/unit/verification/test_e29_e32_operational.py` |
| **E31** | Qualified Lead Rate (QLR) | Phase 2 | `apps/api/app/metrics/operational.py` | `tests/unit/verification/test_e29_e32_operational.py` |
| **E32** | Client Conversion Rate (CCR) | Phase 2 | `apps/api/app/metrics/operational.py` | `tests/unit/verification/test_e29_e32_operational.py` |
| **E33** | Issue Resolution Rate (IRR) | Phase 6 | `apps/api/app/verification/resolution.py`| `tests/unit/verification/test_e33_e36_resolution_did.py` |
| **E34** | Performance Improvement ($PI_X$) | Phase 6 | `apps/api/app/verification/performance.py`| `tests/unit/verification/test_e33_e36_resolution_did.py` |
| **E35** | Audit Regression Rate (RR) | Phase 6 | `apps/api/app/verification/regression.py` | `tests/unit/verification/test_e33_e36_resolution_did.py` |
| **E36** | Difference-in-Differences (DiD) | Phase 6 | `apps/api/app/verification/did.py` | `tests/unit/verification/test_e33_e36_resolution_did.py` |

---

## 3. Phase 1: MVP Core Scanner (Immediate Implementation Target)

### 3.1 Work Packages

```
+---------------------------------------------------------------------------------------+
| Phase 1 Work Packages                                                                 |
+--------------------+------------------------------------------------------------------+
| WP-1.1: Scaffolding| apps/api: pyproject.toml, uv setup, FastAPI main.py, Pydantic v2 |
|                    | domain models (contracts/scan.py, contracts/findings.py).        |
+--------------------+------------------------------------------------------------------+
| WP-1.2: SSRF Guard | apps/api/app/crawler/: DNS pre-resolver, CIDR denylist matcher,  |
|                    | custom httpx transport with socket pinning, redirect validator.  |
+--------------------+------------------------------------------------------------------+
| WP-1.3: Crawler    | apps/api/app/crawler/: streaming HTTP client, headers extractor, |
|                    | redirect hop tracker (E11), robots.txt & sitemap.xml detector.   |
+--------------------+------------------------------------------------------------------+
| WP-1.4: Parsers    | apps/api/app/parsers/: BeautifulSoup 4 + lxml, metadata parser,  |
|                    | heading hierarchy tree, image auditor (E10), JSON-LD validator(E14)|
+--------------------+------------------------------------------------------------------+
| WP-1.5: Rules &    | apps/api/app/rules/ & scoring/: 5-state evaluator (E1), Category |
| Scoring Engine     | Health Score (E2), Overall Score (E3), Legacy Deduction (E4),    |
|                    | Report Completeness (E5), Internal Link Health (E8, E9, E12).    |
+--------------------+------------------------------------------------------------------+
| WP-1.6: FastAPI API| apps/api/app/api/v1/: /scan and /health endpoints, rate limiting |
|                    | middleware, OpenAPI 3.1 export to contracts/openapi_v1.json.     |
+--------------------+------------------------------------------------------------------+
| WP-1.7: Next.js UI | apps/web: Next.js App Router, generated TypeScript API client,   |
|                    | interactive report cards, 5-state badges, evidence inspection.   |
+--------------------+------------------------------------------------------------------+
```

### 3.2 Phase 1 Rule Inventory (Deterministic Audits)

| Category | Rule ID | Audit Description | Severity | Success Criteria |
| :--- | :--- | :--- | :--- | :--- |
| **Crawlability & Network** | `http-status-200` | Verifies final HTTP response status is 200 OK | CRITICAL | Status code == 200 |
| | `redirect-chain-length` | Audits redirect hops (max 1 hop recommended, max 5 allowed) | HIGH | Hops <= 1 ($E11$) |
| | `https-enforced` | Ensures URL protocol is HTTPS and TLS is valid | HIGH | Protocol == 'https:' |
| | `robots-meta-indexable`| Checks `<meta name="robots">` does not contain `noindex` | CRITICAL | `noindex` absent |
| | `x-robots-tag-indexable`| Checks HTTP header `X-Robots-Tag` does not block indexing | CRITICAL | `noindex` absent |
| | `robots-txt-present` | Checks existence and accessibility of `/robots.txt` | MEDIUM | Status 200 on `/robots.txt` |
| | `sitemap-referenced` | Verifies `Sitemap:` directive in `robots.txt` or header | LOW | Sitemap URL declared ($E12$) |
| **Indexability & Meta** | `title-presence` | Validates presence of non-empty `<title>` tag | HIGH | Tag present & non-empty |
| | `title-length` | Checks title length is optimal (30–60 characters) | MEDIUM | 30 <= len <= 60 |
| | `meta-description-presence`| Checks `<meta name="description">` exists | HIGH | Tag present & non-empty |
| | `meta-description-length`| Checks description length (120–160 characters) | LOW | 120 <= len <= 160 |
| | `canonical-presence` | Validates presence of `<link rel="canonical">` | HIGH | Canonical present |
| | `canonical-format` | Validates canonical is an absolute, valid URL matching host | HIGH | Absolute URL matching host |
| **Document Structure** | `h1-presence` | Checks presence of `<h1>` heading | HIGH | Exactly 1 `<h1>` tag |
| | `h1-single` | Flags multiple `<h1>` tags on a single page | MEDIUM | Count of `<h1>` == 1 |
| | `heading-hierarchy` | Checks that heading levels are not skipped (e.g. H2 to H4) | LOW | No skipped levels |
| **Assets & Content** | `image-alt-coverage` | Audits all `<img>` tags for non-empty `alt` attributes | HIGH | 100% of non-decorative images ($E10$) |
| | `image-dimensions` | Checks for explicit `width` and `height` (prevents CLS) | LOW | Width & height declared |
| **Structured Data** | `jsonld-valid-syntax`| Validates all `<script type="application/ld+json">` are valid JSON | HIGH | RFC 8259 valid JSON ($E14$) |
| | `jsonld-schema-type` | Checks for recognized `@type` (Organization, WebSite, Article, etc.) | MEDIUM | Recognized Schema.org type |

### 3.3 Phase 1 Acceptance Criteria
1. **Deterministic Execution**: Identical target pages scanned 10 times produce byte-for-byte identical JSON findings and scores.
2. **Evidence Attachment**: 100% of findings include a typed `FindingEvidence` object with observed value, expected value, and raw snippet.
3. **SSRF Immunity**: Probing `127.0.0.1`, `localhost`, `169.254.169.254`, `10.0.0.1`, or IPv6 equivalents is rejected with HTTP 400 Bad Request without dispatching outbound TCP connections.
4. **SPA Transparency**: If the crawled page lacks server-rendered DOM content, the scanner emits `SPA_DETECTED`, marks affected rules `UNKNOWN` or `NOT_TESTED`, and lowers report completeness rather than fabricating false scores.

---

## 3.4 Phase 2: WP 2.1 Multi-Page Asynchronous Website Crawler (Delivered)

### 3.4.1 Work Package 2.1 Scope & Verification
- **URL Normalization**: Canonical normalization (`normalize_url`) handling trailing slashes, redundant slashes, default ports (:80, :443), relative links resolution, tracking parameter stripping (`utm_*`, `gclid`, `fbclid`), query parameter sorting, and fragment stripping.
- **RFC 9309 Robots.txt Verification**: Comprehensive path directive matching with 5 distinct outcome states (`ALLOWED`, `DISALLOWED`, `ABSENT_ALLOWED`, `UNREACHABLE_ALLOWED`, `INVALID_ALLOWED`).
- **XML Sitemap Link Ingestion**: Samples canonical URLs from discovered sitemaps into the initial crawl frontier.
- **Breadth-First Search (BFS) Frontier Engine**: Ordered queue progression bounded by polite concurrency (`max_concurrency = 2`, `request_delay_seconds = 0.25s`) and strict page ceiling limit enforcement.
- **Zero-Trust SSRF Safety**: Continuous IP validation and DNS re-checking before every page fetch.
- **Continuous 20-Rule SEO Auditing**: Evaluates all canonical SEO rules on every crawled page without heuristic approximation or LLM hallucination.
- **Pure Deterministic Site Aggregation**: Computes unweighted arithmetic mean site-wide scores ($S_{\text{site}}$, $S_{c,\text{site}}$, $C_{\text{site}}$) and deduplicated unique issues sorted by severity and impact percentage.
- **Six-State Job Lifecycle**: Robust background execution management supporting `QUEUED`, `RUNNING`, `COMPLETED`, `PARTIAL`, `CANCELLED`, `FAILED`.
- **Database Durability**:
  - SQLite adapter (`SQLiteCrawlRepository`) with foreign keys and WAL mode for local offline development.
  - PostgreSQL schema (`003_multi_page_crawler.sql` & `003_rollback.sql`) with RLS and least-privilege security.
- **REST Endpoints & Frontend UI**:
  - `POST /api/v1/crawl`, `GET /api/v1/crawl/{job_id}`, `GET /api/v1/crawl/{job_id}/pages`, `GET /api/v1/crawl/{job_id}/pages/{page_id}`, `GET /api/v1/crawl/{job_id}/report`, `POST /api/v1/crawl/{job_id}/cancel`.
  - Next.js UI components: `ScanForm` (mode toggle, page ceiling, depth selector), `CrawlProgressView` (animated progress bar, counters, cancel button), and `MultiPageReportView` (health score, category breakdown, deduplicated unique issues, crawled pages table with in-place inspection drawer).

---

## 4. Testing Strategy & Quality Assurance

```
+-----------------------------------------------------------------------+
|                           TESTING PYRAMID                             |
+-----------------------------------------------------------------------+
|              E2E Tests (Playwright: Next.js + FastAPI)                |
|       Security Test Suite (SSRF, DNS Rebinding, CIDR Fuzzing)         |
|   Integration Tests (Mock HTTP Server, Redirects, robots.txt, HTML)   |
|   Property-Based Tests (Hypothesis: Invariants for E1-E36 Models)     |
|   Unit Tests (Pytest: Rules Engine, BS4 Extractors, Scorer, CIDR)     |
+-----------------------------------------------------------------------+
```

### 4.1 Property-Based Testing with Hypothesis
Hypothesis is used to test mathematical model invariants across millions of randomized inputs:
- **Score Bounds**: Category and Overall Health Scores must remain strictly bounded in $[0.0, 100.0]$.
- **Monotonicity**: Improving a check from `FAIL` to `PASS` must never decrease a category score.
- **Denominator Safety**: Any zero denominator must return `None` / `NULL`, never raise unhandled exceptions or produce `inf` / `NaN`.
- **Completeness Invariant**: If all checks are `PASS` or `FAIL`, Completeness must be exactly $100.0\%$.

### 4.2 Security & Penetration Testing Suite
Automated security tests verify SSRF defenses against adversarial URLs:
- `http://127.0.0.1:80`
- `http://localhost`
- `http://169.254.169.254/latest/meta-data/`
- `http://[::1]`
- `http://0177.0.0.1` (Octal representation)
- `http://2130706433` (Integer IP representation)
- `http://[::ffff:127.0.0.1]` (IPv4-mapped IPv6)
- Simulating DNS rebinding race conditions.

---

## 5. Definition of Done (DoD) per Milestone

A work package or phase is considered **Done** only when:
1. **Code & Typing**: 100% of Python code passes strict type checking (`mypy --strict` or `pyright`) with zero errors. All Next.js TypeScript code compiles cleanly.
2. **Test Coverage**: Minimum 90% unit test coverage on core engines (`app/crawler`, `app/rules`, `app/scoring`, `app/parsers`).
3. **Formula Verification**: Every active mathematical model has unit tests and Hypothesis property tests verifying boundary conditions and null handling.
4. **Security Sign-Off**: All security tests pass; zero static analysis findings in automated vulnerability scans.
5. **Zero Hallucination Verification**: Diagnostic output verified to contain zero probabilistic or ML-generated claims.
