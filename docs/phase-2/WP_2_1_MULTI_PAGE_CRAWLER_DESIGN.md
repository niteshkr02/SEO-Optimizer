# SEO Optimizer — Work Package 2.1: Multi-Page Asynchronous Website Crawler Design Specification

> **Document ID**: `DOC-DESIGN-WP21-CRAWLER`  
> **Status**: Approved Architectural Specification  
> **Classification**: Core Multi-Page Engine Architecture  
> **Target Release**: Phase 2, Work Package 2.1  
> **Inviolable Invariant**: Zero ML/LLM in diagnostic and scoring paths. Every calculation is pure, deterministic, and verifiable.

---

## 1. Executive Overview & System Purpose

Phase 1 established a verified, production-hardened single-page deterministic SEO scanner (`POST /api/v1/scan`) adhering to strict SSRF boundaries, 20 canonical rules, and mathematical models $E1$–$E5, E8$–$E12, E14, E20, E21, E33$.

**Work Package 2.1** extends this foundation into a secure, asynchronous, multi-page website crawler. The primary objective is to discover, crawl, and analyze multiple interconnected pages within an audited website, retaining full page-level diagnostic evidence while synthesizing site-wide aggregated SEO health reports.

---

## 2. Mandatory Architectural Constraints

1. **Backend**: Python 3.12+ / FastAPI / uv (`apps/api`). Sole backend authority.
2. **Frontend**: Next.js 15+ App Router, React 19, TypeScript 5+, Tailwind CSS (`apps/web`). Presentation and user interaction only.
3. **Database**: Supabase PostgreSQL 17+ for staging/production; SQLite for local offline development.
4. **No Heavy Distributed Middleware**: No Redis, RabbitMQ, or Celery. Background execution is orchestrated using Python `asyncio` background task workers managed within the FastAPI service lifecycle, backed by database-persisted job state.
5. **No Headless Browser in Main Process**: Static HTML fetching via `SafeHttpClient` (with streaming byte limits and SSRF socket pinning). Pages requiring client-side JavaScript execution are reported as `UNKNOWN` / `is_spa_detected=True` rather than generating fabricated findings.
6. **Zero ML/LLM in Core Paths**: Rule evaluation and scoring are strictly deterministic.

---

## 3. URL Discovery, Normalization & Deduplication

### 3.1 Discovery Sources
Candidate URLs are discovered through five deterministic channels:
1. **Seed URL**: The starting URL submitted by the user (crawl depth = 0).
2. **Internal HTML Anchor Links**: `href` attributes extracted from parsed `<a href="...">` elements during HTML DOM parsing.
3. **XML Sitemap Declarations**: URLs parsed from `/robots.txt` `Sitemap:` directives.
4. **Sitemap Index & Child Sitemaps**: Recursive XML parsing of sitemap index files and document locators up to configured limits.
5. **Canonical Link Directives**: Internal `<link rel="canonical" href="...">` tags pointing to canonical variants of audited pages.

### 3.2 Crawl Boundary Enforcement
To prevent uncontrolled spidering, the crawler enforces strict boundaries:
- **Default Boundary**: `SAME_ORIGIN` (scheme + hostname + port must match seed URL).
- **Subdomain Boundary (Configurable)**: `SAME_REGISTRABLE_DOMAIN` (allows crawling across subdomains belonging to the same root domain, e.g. `blog.example.com` and `www.example.com`).
- **External Exclusion**: Links pointing to third-party domains, CDN asset hosts, social networks, or email/telephone schemes (`mailto:`, `tel:`, `javascript:`) are strictly excluded from the crawl frontier.

### 3.3 Safe URL Normalization Protocol
URLs discovered from DOM attributes or sitemaps often contain inconsistencies. The crawler normalizes every URL before deduplication:
1. **Scheme & Host Normalization**: Lowercase scheme and hostname. Strip default ports (`:80` for HTTP, `:443` for HTTPS). Strip trailing host dots.
2. **Fragment Removal**: URL fragments (`#section`, `#top`) are strictly stripped, as fragments reference client-side document positions and do not represent distinct HTTP resources.
3. **Path Canonicalization**:
   - Resolve relative paths against the parent page URL using standard RFC 3986 path resolution (`urllib.parse.urljoin`).
   - Normalize redundant consecutive slashes (`/path//to///page` -> `/path/to/page`).
   - Resolve dot segments (`.` and `..`).
   - Trailing slash preservation: Maintain directory slashes unless redirected by server headers.
4. **Query Parameter Sorting & Sanitization**:
   - Strip known non-semantic marketing and analytics query parameters (`utm_*`, `gclid`, `fbclid`, `mc_eid`).
   - Preserve functional parameters (e.g. `?page=2`, `?category=books`).
   - Sort remaining query parameters alphabetically by key to ensure identical query parameter combinations produce identical normalized URL hashes (`?b=2&a=1` -> `?a=1&b=2`).
5. **Canonical URL De-aliasing**: If a crawled page declares a canonical URL that is internal and valid, the canonical URL is recorded, preventing duplicate diagnostic penalty across mirror URLs.

---

## 4. Crawl Job Lifecycle & State Machine

Every multi-page crawl operation is represented by a persistent `CrawlJob` state machine.

```
                  +---------+
                  |  QUEUED |
                  +----+----+
                       |
                       v
                 +-----+-----+
                 |  RUNNING  |
                 +--+---+----+
                    |   |
      +-------------+   +---------------+
      |                 |               |
      v                 v               v
+-----+-----+     +-----+-----+   +-----+-----+
| COMPLETED |     |  PARTIAL  |   | CANCELLED |
+-----------+     +-----------+   +-----------+
      ^                 ^
      |                 |
      +--------+--------+
               | (Fatal Error)
               v
         +-----+-----+
         |   FAILED  |
         +-----------+
```

### 4.1 State Definitions
- **`QUEUED`**: The job has been received, validated, and assigned a `job_id`. Initial frontier contains the seed URL.
- **`RUNNING`**: The crawler is actively fetching pages, evaluating rules, and discovering links.
- **`COMPLETED`**: The frontier was completely exhausted without hitting `max_pages`, `max_depth`, or timeout limits. All discovered allowed pages were processed.
- **`PARTIAL`**: Crawl finished because a safety boundary was reached (`max_pages` ceiling reached, `max_depth` ceiling reached, or `duration_limit_seconds` expired), with un-crawled URLs still remaining in the frontier.
- **`FAILED`**: The job failed due to a fatal, non-recoverable error (e.g. seed URL SSRF violation, seed host completely unreachable, DNS failure).
- **`CANCELLED`**: The crawl was gracefully terminated by a client request via `POST /api/v1/crawl/{job_id}/cancel`.

### 4.2 Job Progress Telemetry
Clients observe progress by querying `GET /api/v1/crawl/{job_id}`:
- `jobId`: Unique UUID.
- `status`: Current state (`QUEUED`, `RUNNING`, `COMPLETED`, `PARTIAL`, `FAILED`, `CANCELLED`).
- `progressPercentage`: Calculated as $\min(100.0, \frac{\text{crawled\_count}}{\min(\text{discovered\_count}, \text{max\_pages})} \times 100)$.
- `pagesDiscovered`: Total unique internal URLs identified.
- `pagesCrawled`: Total pages successfully fetched and analyzed.
- `pagesRemaining`: Discovered URLs currently waiting in the frontier queue.
- `pagesFailed`: Count of pages that returned HTTP 4xx/5xx or timed out.
- `currentDepth`: Maximum crawl depth reached so far.
- `startedAt`, `completedAt`: ISO 8601 timestamps.
- `errorMessage`: Sanitized error description if failed.

---

## 5. Crawl Controls, Safety & Politeness

### 5.1 Configurable Boundaries

| Parameter | Type | Default | Permitted Range | Purpose |
| :--- | :--- | :--- | :--- | :--- |
| `max_pages` | Integer | `25` | `1` to `100` | Hard cap on total pages fetched per job. |
| `max_depth` | Integer | `3` | `0` to `5` | Maximum distance from seed URL (seed = 0). |
| `max_concurrency` | Integer | `2` | `1` to `5` | Simultaneous requests allowed to target host. |
| `request_delay_seconds` | Float | `0.25` | `0.1` to `2.0` | Minimum interval between requests (politeness). |
| `request_timeout_seconds`| Float | `5.0` | `1.0` to `15.0`| Network timeout per individual page fetch. |
| `crawl_timeout_seconds` | Float | `300.0` | `10.0` to `600.0`| Overall crawl job execution timeout. |
| `max_response_bytes` | Integer | `10 MB` | Fixed | Hard ceiling on response payload size. |

### 5.2 RFC 9309 Robots.txt Compliance
The crawler respects robots.txt directives per the RFC 9309 specification, evaluating path permissions before fetching any page.

Five distinct robots.txt outcomes are tracked:
1. **`SUCCESSFULLY_RETRIEVED`**: HTTP 200 with parseable rules. Disallow directives strictly respected via longest-matching prefix algorithm.
2. **`MISSING_UNAVAILABLE`**: HTTP 404/410. Crawler assumes standard full crawl access allowed per RFC 9309 § 2.3.1.
3. **`SERVER_ERROR`**: HTTP 5xx. Crawler adopts fail-safe posture, pausing or treating all non-seed paths as restricted until server stabilizes.
4. **`INVALID_SYNTAX`**: Malformed text. Valid lines parsed; unparseable lines ignored safely without crashing.
5. **`REDIRECTED`**: Follows redirects up to 5 hops, revalidating SSRF rules on each hop.

> [!IMPORTANT]
> Robots.txt is an operational crawl directive, **never** an access-control or security boundary. Content behind disallowed paths is not crawled, but its presence in sitemaps or links is reported as `DISALLOWED`.

### 5.3 Defense-in-Depth SSRF Validation on Discovered Links
Every discovered URL (from HTML, sitemaps, or redirects) **MUST** undergo full SSRF validation before being queued or fetched:
- Pre-crawl DNS resolution checking against IPv4/IPv6 private CIDR ranges (RFC 1918, RFC 3927, RFC 4193, loopback `127.0.0.0/8`, `::1`, multicast, and cloud metadata `169.254.169.254`).
- Socket pinning using custom transport (`SSRFBlockTransport`) ensuring the socket connects exclusively to the pre-validated IP.
- Discovered URLs attempting to target localhost, private IPs, or non-whitelisted ports (only 80, 443 permitted) are immediately dropped and recorded as `BLOCKED_SSRF`.

---

## 6. SEO Analysis Integration & Multi-Page Aggregation

### 6.1 Per-Page Evidence & Finding Preservation
For each crawled page, the engine evaluates all 20 canonical SEO rules:
- Crawlability (7 rules): `http-status-200`, `redirect-chain-length`, `https-enforced`, `robots-txt-present`, `robots-meta-indexable`, `x-robots-tag-indexable`, `sitemap-referenced`.
- Indexability (6 rules): `canonical-presence`, `canonical-format`, `title-presence`, `title-length`, `meta-description-presence`, `meta-description-length`.
- Structure (3 rules): `h1-presence`, `h1-single`, `heading-hierarchy`.
- Assets/Content (2 rules): `image-alt-coverage`, `image-dimensions`.
- Structured Data (2 rules): `jsonld-valid-syntax`, `jsonld-schema-type`.

Every page retains its own immutable findings, evidence snapshots, HTTP status codes, latency, and crawl depth.

### 6.2 Site-Wide Score Aggregation
The site-wide overall score is the unweighted arithmetic mean of overall scores across all successfully analyzed pages $\mathcal{P}$:

$$S_{\text{site}} = \frac{1}{|\mathcal{P}|} \sum_{p \in \mathcal{P}} S_p$$

Similarly, site-wide category health scores are computed per category $c$:

$$S_{c,\text{site}} = \frac{1}{|\mathcal{P}_c|} \sum_{p \in \mathcal{P}_c} S_{c,p}$$

where $\mathcal{P}_c$ denotes the subset of pages having at least one applicable check in category $c$. If $|\mathcal{P}_c| = 0$, $S_{c,\text{site}} = \text{NULL}$.

### 6.3 Site-Wide Issue Rollup & Deduplication
To prevent issue inflation (e.g. a missing `<meta name="description">` on 20 pages generating 20 separate top-level issues):
- **Unique Issues**: Grouped by `rule_id` and `severity`.
- **Affected Count**: The number of distinct pages where the rule yielded `FAIL`.
- **Sample Evidence**: Up to 5 sample URLs and verbatim evidence snippets are preserved per unique issue.
- **Five-State Conformity**: All aggregated findings conform strictly to `PASS`, `FAIL`, `UNKNOWN`, `NOT_TESTED`, or `NOT_APPLICABLE`.

---

## 7. Mathematical Model Integrity Grounding

We cross-reference `docs/MATHEMATICAL_MODEL_CATALOG.md`:

| Formula ID | Formula Name | Role in Multi-Page Crawler |
| :--- | :--- | :--- |
| **E1** | Deterministic Check Values | Evaluated on every page for all 20 checks ($q_{i,p} \in \{1.0, 0.0, \text{NULL}\}$). |
| **E2** | Category Weighted Health Score | Computed per page ($S_{c,p}$) and aggregated site-wide ($S_{c,\text{site}}$). |
| **E3** | Overall SEO Health Score | Computed per page ($S_p$) and aggregated site-wide ($S_{\text{site}}$). |
| **E4** | Legacy Severity-Deduction | Computed for calibration comparison; never double-penalized. |
| **E5** | Report Completeness Index | Tracked per page and averaged site-wide ($C_{\text{site}}$). |
| **E8, E9** | Internal Link Ratio & Health | Cross-page internal links are aggregated to detect site-wide broken link patterns. |
| **E10** | Image Alt Coverage | Computed across all images on all crawled pages. |
| **E11** | Redirect Hop Count & Loops | Evaluated on every redirect hop for all crawled URLs. |
| **E12** | Sitemap URL Health | Evaluated against discovered sitemaps. |
| **E14** | JSON-LD Syntax Validity | Evaluated on every page containing structured data. |
| **E20, E21**| Triage Composite & RICE Priority | Applied to prioritize site-wide unique issues for remediation. |

> [!WARNING]
> **Model E13 Clarification**:
> In `docs/MATHEMATICAL_MODEL_CATALOG.md`, **Model E13** is strictly designated as **Inspected Sample Indexation Rate (IR)** belonging to **Phase 6** (Search Console API).
> Crawl depth scheduling is an **operational crawl algorithm**, NOT a mathematical model ID. We do not reassign or invent a mathematical formula ID for depth scheduling.

---

## 8. Database Schema Design & Migration Strategy

### 8.1 Table Specifications (`003_multi_page_crawler.sql`)

```sql
-- 1. Crawl Jobs Table
CREATE TABLE IF NOT EXISTS public.crawl_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    seed_url TEXT NOT NULL,
    base_domain VARCHAR(255) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'QUEUED' 
        CHECK (status IN ('QUEUED', 'RUNNING', 'COMPLETED', 'PARTIAL', 'FAILED', 'CANCELLED')),
    max_pages INTEGER NOT NULL DEFAULT 25 CHECK (max_pages BETWEEN 1 AND 100),
    max_depth INTEGER NOT NULL DEFAULT 3 CHECK (max_depth BETWEEN 0 AND 5),
    pages_discovered INTEGER NOT NULL DEFAULT 1,
    pages_crawled INTEGER NOT NULL DEFAULT 0,
    pages_failed INTEGER NOT NULL DEFAULT 0,
    current_depth INTEGER NOT NULL DEFAULT 0,
    config JSONB NOT NULL DEFAULT '{}'::jsonb,
    error_message TEXT NULL,
    started_at TIMESTAMPTZ NULL,
    completed_at TIMESTAMPTZ NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2. Crawled Pages Table
CREATE TABLE IF NOT EXISTS public.crawl_pages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID NOT NULL REFERENCES public.crawl_jobs(id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    normalized_url TEXT NOT NULL,
    depth INTEGER NOT NULL DEFAULT 0,
    parent_url TEXT NULL,
    discovery_method VARCHAR(32) NOT NULL DEFAULT 'HTML_LINK'
        CHECK (discovery_method IN ('SEED', 'HTML_LINK', 'SITEMAP', 'CANONICAL')),
    status VARCHAR(32) NOT NULL DEFAULT 'PENDING'
        CHECK (status IN ('PENDING', 'FETCHING', 'CRAWLED', 'FAILED', 'DISALLOWED', 'SKIPPED')),
    http_status INTEGER NULL,
    response_time_ms INTEGER NULL,
    title TEXT NULL,
    canonical_url TEXT NULL,
    overall_score NUMERIC(5,2) NULL,
    completeness_score NUMERIC(5,2) NULL,
    error_reason TEXT NULL,
    crawled_at TIMESTAMPTZ NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 3. Page Findings Table
CREATE TABLE IF NOT EXISTS public.crawl_page_findings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID NOT NULL REFERENCES public.crawl_jobs(id) ON DELETE CASCADE,
    page_id UUID NOT NULL REFERENCES public.crawl_pages(id) ON DELETE CASCADE,
    rule_id VARCHAR(64) NOT NULL,
    category VARCHAR(32) NOT NULL,
    state VARCHAR(32) NOT NULL CHECK (state IN ('PASS', 'FAIL', 'UNKNOWN', 'NOT_TESTED', 'NOT_APPLICABLE')),
    severity VARCHAR(32) NOT NULL CHECK (severity IN ('CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO')),
    weight INTEGER NOT NULL DEFAULT 5,
    evidence JSONB NOT NULL DEFAULT '{}'::jsonb,
    remediation_guidance TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 4. Site-Wide Aggregates Table
CREATE TABLE IF NOT EXISTS public.crawl_site_aggregates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID NOT NULL UNIQUE REFERENCES public.crawl_jobs(id) ON DELETE CASCADE,
    overall_score NUMERIC(5,2) NULL,
    completeness_score NUMERIC(5,2) NULL,
    category_scores JSONB NOT NULL DEFAULT '{}'::jsonb,
    unique_issues JSONB NOT NULL DEFAULT '[]'::jsonb,
    total_pages_analyzed INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### 8.2 Security, RLS & Isolation
- RLS enabled on all 4 crawl tables.
- `anon` role has **zero** privileges.
- `service_role` has full backend CRUD access.
- Authenticated admin sessions read/manage crawl jobs.

---

## 9. API Design & Versioned Endpoints

All endpoints are grouped under `/api/v1/crawl`:

1. **`POST /api/v1/crawl`**: Start multi-page crawl. Accepts `CrawlJobCreateRequest` (`url`, `maxPages`, `maxDepth`). Returns `202 Accepted` with initial `CrawlJobDTO`.
2. **`GET /api/v1/crawl/{job_id}`**: Telemetry endpoint. Returns current progress, counters, and status.
3. **`GET /api/v1/crawl/{job_id}/pages`**: Paginated list of discovered/crawled pages. Supports filtering by `depth` and `status`.
4. **`GET /api/v1/crawl/{job_id}/pages/{page_id}`**: Detailed audit report for a specific crawled page (including its 20 findings).
5. **`GET /api/v1/crawl/{job_id}/report`**: Full aggregated site audit report with site-wide score and deduplicated issue rollup.
6. **`POST /api/v1/crawl/{job_id}/cancel`**: Gracefully requests cancellation of a running crawl job.

---

## 10. Frontend Experience

The Next.js frontend (`apps/web`) is updated with:
- **Scan Mode Selector**: Toggle between **Single Page Scan** and **Multi-Page Site Crawl**.
- **Multi-Page Options**: Slider or selector for `Max Pages` (5, 10, 25, 50) and `Max Depth` (1, 2, 3).
- **Live Crawl Progress Bar**: Real-time polling component displaying discovered/crawled counts, progress percentage, and an abort/cancel action.
- **Site-Wide Score Overview**: Displays aggregated overall health score, category breakdown, and site-wide unique issues.
- **Crawled Pages Explorer**: Interactive data table listing all audited URLs, HTTP status codes, depths, and individual page scores, with drill-down into any page's 20 findings.
