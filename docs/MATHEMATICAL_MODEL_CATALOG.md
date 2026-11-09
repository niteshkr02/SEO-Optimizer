# SEO Optimizer — Mathematical Model Catalogue & Formula Implementation Specification

> **Version**: 1.0.0  
> **Status**: Approved Foundation Specification  
> **Classification**: Core Analytical & Mathematical Engine  
> **Inviolable Principle**: Zero ML/LLM in diagnostic and scoring paths. Every formula is pure, deterministic, reproducible, and versioned. Missing inputs evaluate to `NULL` / `UNKNOWN`, never fabricated zeros.

---

## 1. Governance, Conventions & Mathematical Invariants

### 1.1 Core Principles
1. **Determinism**: Given identical inputs, every formula must yield identical outputs regardless of runtime, architecture, or environment.
2. **Missing Data Policy**: Missing or unobserved inputs are strictly represented as `NULL` / `None` / `UNKNOWN`. Missing data must **never** be replaced with fabricated zeros, synthetic medians, or default placeholders unless explicitly defined by the model specification.
3. **Provenance & Attribution**: Every output must be explicitly classified as:
   - **Direct Deterministic Observation** (crawler network headers, raw DOM, parsed status codes).
   - **Official External Measurement** (Chrome UX Report 75th percentile field data, Search Console API inspection).
   - **Third-Party Licensed Estimate** (SERP position, search volume estimate, keyword difficulty score).
   - **Internal Deterministic Composite / Heuristic** (Category Health Score, RICE Priority, Placement Heuristic).
4. **Rounding Policy**: Intermediate calculations must retain full floating-point precision (IEEE 754 64-bit float). Rounding is performed exclusively at presentation or contract export time (defaulting to 2 decimal places for percentages, 1 decimal place for composite scores).
5. **No Double Penalization**: The primary public score is the Category Weighted SEO Health Score ($S_c$) and Overall Health Score ($S$). The legacy deduction model ($S_d$) is retained strictly for benchmarking and calibration; they must never be combined to penalize the same issue twice.
6. **Denominator Safety**: Every formula with a denominator must implement an explicit check for zero, returning `NULL` / `UNKNOWN` and disclosing the condition in report telemetry.
7. **Implementation Ownership**: All mathematical models are implemented as pure, tested Python functions under `apps/api/app/scoring/`, `apps/api/app/metrics/`, `apps/api/app/gap_analysis/`, `apps/api/app/resolution/`, or `apps/api/app/verification/`.

### 1.2 Formula Registry Index

| ID | Formula Name | Category | Implementation Phase | Python Module Path |
| :--- | :--- | :--- | :--- | :--- |
| **E1** | Deterministic SEO Check Values | Quality Mapping | Phase 1 | `app/rules/evaluator.py` |
| **E2** | Category Weighted SEO Health Score | Scoring | Phase 1 | `app/scoring/category.py` |
| **E3** | Overall SEO Health Score | Scoring | Phase 1 | `app/scoring/overall.py` |
| **E4** | Legacy Severity-Deduction Model | Calibration | Phase 1 | `app/scoring/calibration.py` |
| **E5** | Report Completeness Index | Coverage | Phase 1 | `app/scoring/completeness.py` |
| **E6** | Core Web Vitals Thresholds | Performance | Phase 2 | `app/metrics/cwv.py` |
| **E7** | Lower-is-Better Metric Normalization | Normalization | Phase 2 | `app/metrics/normalization.py` |
| **E8** | Broken Internal Link Ratio (BLR) | Technical | Phase 1 | `app/metrics/links.py` |
| **E9** | Internal Link Health (ILH) | Technical | Phase 1 | `app/metrics/links.py` |
| **E10** | Image Alt Attribute Coverage (IAC) | Content / Assets | Phase 1 | `app/metrics/assets.py` |
| **E11** | Redirect Hop Count & Loop Detection | Crawlability | Phase 1 | `app/crawler/redirects.py` |
| **E12** | Sitemap URL Health (SH) | Crawlability | Phase 1 | `app/metrics/sitemap.py` |
| **E13** | Inspected Sample Indexation Rate (IR) | Search Console | Phase 6 | `app/integrations/gsc/metrics.py` |
| **E14** | JSON-LD Syntax Validity Ratio (JVR) | Structured Data | Phase 1 | `app/parsers/jsonld.py` |
| **E15** | Competitor Visibility Score (CV) | Competitor Intelligence| Phase 3 | `app/competitor/visibility.py` |
| **E16** | Weighted Content Coverage Gap ($G$) | Gap Analysis | Phase 3 | `app/gap_analysis/content.py` |
| **E17** | Keyword Opportunity Score (KO) | Gap Analysis | Phase 3 | `app/gap_analysis/keywords.py` |
| **E18** | Potential Click Opportunity (PCO) | Search Console / Gaps | Phase 3 | `app/gap_analysis/clicks.py` |
| **E19** | Content Section Placement Score ($L$) | Resolution Center | Phase 4 | `app/resolution/placement.py` |
| **E20** | Root-Cause Triage Composite (RC) | Resolution Center | Phase 4 | `app/resolution/triage.py` |
| **E21** | Resolution Priority (RICE-inspired) | Resolution Center | Phase 4 | `app/resolution/priority.py` |
| **E22** | Referring Domain Gap (RDG) | Authority / Backlinks | Phase 3 | `app/gap_analysis/backlinks.py` |
| **E23** | Link Opportunity Relevance (LO) | Authority / Outreach | Phase 3 | `app/gap_analysis/backlinks.py` |
| **E24** | Search Console Click-Through Rate (CTR) | Search Console | Phase 6 | `app/integrations/gsc/analytics.py` |
| **E25** | Impression Decline Rate ($D_I$) | Trend Analysis | Phase 6 | `app/metrics/trends.py` |
| **E26** | Click Decline Rate ($D_C$) | Trend Analysis | Phase 6 | `app/metrics/trends.py` |
| **E27** | Average Position Change ($\Delta P$) | Trend Analysis | Phase 6 | `app/metrics/trends.py` |
| **E28** | Potential Keyword Cannibalization ($K$)| Diagnostic | Phase 6 | `app/metrics/cannibalization.py`|
| **E29** | Scan Completion Rate (SCR) | Operational / Leads | Phase 2 | `app/metrics/operational.py` |
| **E30** | Lead Conversion Rate (LCR) | Operational / Leads | Phase 2 | `app/metrics/operational.py` |
| **E31** | Qualified Lead Rate (QLR) | Operational / CRM | Phase 2 | `app/metrics/operational.py` |
| **E32** | Client Conversion Rate (CCR) | Operational / Sales | Phase 2 | `app/metrics/operational.py` |
| **E33** | Issue Resolution Rate (IRR) | Verification | Phase 6 | `app/verification/resolution.py`|
| **E34** | Metric Performance Improvement ($PI_X$)| Verification | Phase 6 | `app/verification/performance.py`|
| **E35** | Audit Regression Rate (RR) | Verification | Phase 6 | `app/verification/regression.py` |
| **E36** | Difference-in-Differences (DiD) | Impact Evaluation | Phase 6 | `app/verification/did.py` |

---

## 2. Model Specifications (E1 through E36)

---

### E1. Deterministic SEO Check Values
- **Model ID**: `E1`
- **Domain**: Audit Outcome & Quality Mapping
- **Classification**: Direct Deterministic Observation Mapping
- **Implementation Phase**: Phase 1
- **Target Module**: `apps/api/app/rules/evaluator.py`

#### Mathematical Formulation
Every audit check $i$ evaluates to an outcome state $O_i \in \{\text{PASS}, \text{FAIL}, \text{UNKNOWN}, \text{NOT\_TESTED}, \text{NOT\_APPLICABLE}\}$:

$$q_i = \begin{cases} 
1.0 & \text{if } O_i = \text{PASS} \\ 
0.0 & \text{if } O_i = \text{FAIL} \\ 
p_i & \text{if } O_i = \text{PARTIAL (where } p_i \in [0.0, 1.0] \text{ is rule-defined)} \\ 
\text{NULL} & \text{if } O_i \in \{\text{UNKNOWN}, \text{NOT\_TESTED}, \text{NOT\_APPLICABLE}\} 
\end{cases}$$

#### Input Specifications
- $O_i$: 5-state categorical outcome from deterministic rule evaluator.
- $p_i$: Optional explicit partial credit scalar defined only in the rule registry (e.g. valid canonical present but non-matching protocol gives $p=0.5$).

#### Null and Boundary Rules
- `UNKNOWN`, `NOT_TESTED`, and `NOT_APPLICABLE` **must never** map to 0 or 1.
- If $O_i \in \{\text{UNKNOWN}, \text{NOT\_TESTED}, \text{NOT\_APPLICABLE}\}$, the check is excluded from the score denominator ($\sum w_i$).
- `UNKNOWN` and `NOT_TESTED` lower the Report Completeness Index ($E5$), but do not directly reduce the measured score.
- `NOT_APPLICABLE` is excluded from both the score and completeness denominators.

#### Output Meaning & Caveats
- $q_i$ represents the quality compliance scalar for rule $i$. It indicates deterministic compliance with web and search standards, not search ranking probability.

---

### E2. Category Weighted SEO Health Score
- **Model ID**: `E2`
- **Domain**: Category Scoring
- **Classification**: Internal Deterministic Composite
- **Implementation Phase**: Phase 1
- **Target Module**: `apps/api/app/scoring/category.py`

#### Mathematical Formulation
$$S_c = 100 \times \frac{\sum_{i \in \mathcal{E}_c} w_i q_i}{\sum_{i \in \mathcal{E}_c} w_i}$$

Where:
- $c$: Audit category (e.g., Crawlability, Indexability, On-Page, Performance, Structured Data).
- $\mathcal{E}_c$: Set of applicable and evaluated checks in category $c$ where $q_i \neq \text{NULL}$ (i.e. $O_i \in \{\text{PASS}, \text{FAIL}, \text{PARTIAL}\}$).
- $w_i$: Configured importance weight for check $i$ ($w_i \in [1, 10]$).
- $q_i$: Quality compliance score from $E1$ ($q_i \in [0.0, 1.0]$).

#### Input Specifications
- $\mathcal{E}_c$: List of evaluated checks for category $c$.
- $w_i$: Integer weight assigned in versioned rule configuration (`rules_v1.json`).

#### Null and Boundary Rules
- If $\sum_{i \in \mathcal{E}_c} w_i = 0$ (no applicable checks evaluated, e.g. all checks returned `UNKNOWN` or `NOT_APPLICABLE`):
  $$S_c = \text{NULL (Category Unavailable)}$$
- The function must **never** return 0 when no checks could be evaluated.
- Missing coverage must be reported via Category Completeness ($C_c$).

#### Output Meaning & Caveats
- $S_c \in [0.0, 100.0]$. A score of 100 indicates that all evaluated applicable checks in that category satisfied their compliance criteria. It does not mean the category is "flawless" if completeness is under 100%.

---

### E3. Overall SEO Health Score
- **Model ID**: `E3`
- **Domain**: Overall Site / Page Scoring
- **Classification**: Internal Deterministic Composite
- **Implementation Phase**: Phase 1
- **Target Module**: `apps/api/app/scoring/overall.py`

#### Mathematical Formulation
When all four canonical categories are available:
$$S = 0.35 I + 0.30 T + 0.20 P + 0.15 O$$

Where:
- $I$: Indexability Score ($S_{\text{indexability}}$).
- $T$: Technical / Crawlability Score ($S_{\text{technical}}$).
- $P$: Performance Score ($S_{\text{performance}}$).
- $O$: On-Page / Document Structure Score ($S_{\text{on\_page}}$).

When one or more categories are unavailable ($S_c = \text{NULL}$), calculate the normalized weighted mean across available categories $\mathcal{A}$:
$$S = \frac{\sum_{c \in \mathcal{A}} \alpha_c S_c}{\sum_{c \in \mathcal{A}} \alpha_c}$$

Where baseline category weights are $\alpha_I = 0.35$, $\alpha_T = 0.30$, $\alpha_P = 0.20$, $\alpha_O = 0.15$.

#### Null and Boundary Rules
- If $\mathcal{A} = \emptyset$ (no categories evaluated):
  $$S = \text{NULL (Report Unavailable)}$$
- Whenever any category is missing, the response payload must include `category_availability: Dict[str, bool]` and `report_completeness` ($E5$).
- Weights $\alpha_c$ must be versioned in `scoring_model_v1.json`. Weights must not be dynamically modified at runtime without recording `model_version`.

#### Output Meaning & Caveats
- $S \in [0.0, 100.0]$. Internal health indicator representing engineering and standards hygiene. **Strict Warning**: This score does not reflect or predict Google organic rankings, organic traffic volume, or search impressions.

---

### E4. Legacy Severity-Deduction Model (Calibration Only)
- **Model ID**: `E4`
- **Domain**: Benchmarking & Model Calibration
- **Classification**: Internal Deterministic Diagnostic Metric
- **Implementation Phase**: Phase 1
- **Target Module**: `apps/api/app/scoring/calibration.py`

#### Mathematical Formulation
$$S_d = \max\left(0, 100 - \sum_{i \in \text{Failures}} d(s_i)\right)$$

Where $d(s_i)$ is the severity deduction:
$$d(s_i) = \begin{cases}
25 & \text{if severity } s_i = \text{CRITICAL} \\
10 & \text{if severity } s_i = \text{WARNING} \\
4 & \text{if severity } s_i = \text{OPPORTUNITY} \\
0 & \text{if severity } s_i = \text{INFO}
\end{cases}$$

#### Null and Boundary Rules
- If no rules fail, $S_d = 100$.
- Floor at 0. Deductions beyond 100 do not create negative scores.
- Kept strictly as a secondary diagnostic / calibration baseline. Must **never** be blended with $E2$ or $E3$ to double-penalize an issue.

---

### E5. Report Completeness Index
- **Model ID**: `E5`
- **Domain**: Audit Coverage & Confidence
- **Classification**: Internal Deterministic Metric
- **Implementation Phase**: Phase 1
- **Target Module**: `apps/api/app/scoring/completeness.py`

#### Mathematical Formulation
$$C = 100 \times \frac{\sum_{i=1}^n w_i \cdot \mathbb{I}(O_i \in \{\text{PASS}, \text{FAIL}, \text{PARTIAL}\})}{\sum_{i=1}^n w_i \cdot \mathbb{I}(O_i \neq \text{NOT\_APPLICABLE})}$$

Where $\mathbb{I}(\cdot)$ is the indicator function.

#### Null and Boundary Rules
- Evaluated set: `PASS`, `FAIL`, rule-defined `PARTIAL`.
- Not evaluated: `UNKNOWN`, `NOT_TESTED`.
- Excluded from denominator: `NOT_APPLICABLE`.
- If the denominator is 0 (no checks applicable to the page), $C = \text{NULL}$.
- If $C < 100\%$, the report highlights unverified checks and operational causes (e.g., target connection timeout, SPA without client rendering).

---

### E6. Core Web Vitals Thresholds
- **Model ID**: `E6`
- **Domain**: Performance & Page Experience
- **Classification**: Official External Measurement (CrUX) & Lab Diagnostic (PSI)
- **Implementation Phase**: Phase 2
- **Target Module**: `apps/api/app/metrics/cwv.py`

#### Metric Threshold Classifications
| Metric | Good (Pass) | Needs Improvement | Poor | Measurement Unit | Scope |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **LCP** (Largest Contentful Paint) | $\le 2.50\text{ s}$ | $> 2.50\text{ s} \text{ and } \le 4.00\text{ s}$ | $> 4.00\text{ s}$ | Seconds | Field (CrUX 75th pctl) / Lab (PSI) |
| **INP** (Interaction to Next Paint) | $\le 200\text{ ms}$ | $> 200\text{ ms} \text{ and } \le 500\text{ ms}$ | $> 500\text{ ms}$ | Milliseconds | Field Only (CrUX 75th pctl) |
| **CLS** (Cumulative Layout Shift) | $\le 0.10$ | $> 0.10 \text{ and } \le 0.25$ | $> 0.25$ | Unitless scalar | Field (CrUX 75th pctl) / Lab (PSI) |

#### Lab Proxy Rule
- **INP is strictly a field metric**. Total Blocking Time (TBT) from Lighthouse lab runs may be presented as an uncoupled lab diagnostic proxy, but must **never** be renamed, substituted, or presented as INP.

#### Null and Provenance Rules
- If CrUX field data is unavailable (e.g. insufficient site traffic in 28-day collection window), report `status = UNAVAILABLE`. **Never infer failure or synthesize values.**
- Every CWV record must explicitly declare: `data_type` (`FIELD` vs `LAB`), `collection_period` (e.g. 28 days), `device` (`MOBILE` vs `DESKTOP`), and `scope` (`PAGE` vs `ORIGIN`).

---

### E7. Lower-is-Better Metric Normalization
- **Model ID**: `E7`
- **Domain**: Performance Sub-scoring
- **Classification**: Internal Deterministic Normalization
- **Implementation Phase**: Phase 2
- **Target Module**: `apps/api/app/metrics/normalization.py`

#### Mathematical Formulation
$$M(x) = \begin{cases} 
100.0 & \text{if } x \le g \\ 
100.0 \times \frac{p - x}{p - g} & \text{if } g < x < p \\ 
0.0 & \text{if } x \ge p 
\end{cases}$$

Where:
- $x$: Observed continuous metric value (e.g. LCP in seconds, CLS scalar).
- $g$: "Good" threshold value from standards.
- $p$: "Poor" threshold value from standards ($p > g$).

#### Null and Boundary Rules
- If $x$ is missing or `NULL`, $M(x) = \text{NULL}$.
- If $p \le g$, raise a `ConfigurationError` during initialization (invariant violation).
- Result is clamped to $[0.0, 100.0]$.
- Must never be used to blend lab and field metrics into an unlabeled composite.

---

### E8. Broken Internal Link Ratio (BLR)
- **Model ID**: `E8`
- **Domain**: Technical Link Integrity
- **Classification**: Direct Deterministic Observation
- **Implementation Phase**: Phase 1
- **Target Module**: `apps/api/app/metrics/links.py`

#### Mathematical Formulation
$$\text{BLR} = 100 \times \frac{|\mathcal{L}_{\text{broken\_verified}}|}{|\mathcal{L}_{\text{checked\_verified}}|}$$

Where:
- $\mathcal{L}_{\text{checked\_verified}}$: Set of internal unique link targets verified with definitive HTTP status (e.g. 200, 301, 404, 500).
- $\mathcal{L}_{\text{broken\_verified}}$: Set of verified internal links returning HTTP $4xx$ or $5xx$ status codes.

#### Null and Boundary Rules
- Transient network timeouts, socket aborts, or rate-limited responses (HTTP 429) must **not** be counted as broken; they are marked `INCONCLUSIVE` and excluded from both numerator and denominator.
- If $|\mathcal{L}_{\text{checked\_verified}}| = 0$ (e.g. page has no internal links), $\text{BLR} = \text{NULL}$ (disclose `links_checked = 0`).

---

### E9. Internal Link Health (ILH)
- **Model ID**: `E9`
- **Domain**: Technical Link Health
- **Classification**: Internal Deterministic Metric
- **Implementation Phase**: Phase 1
- **Target Module**: `apps/api/app/metrics/links.py`

#### Mathematical Formulation
$$\text{ILH} = 100.0 - \text{BLR}$$

#### Null and Boundary Rules
- If $\text{BLR} = \text{NULL}$, $\text{ILH} = \text{NULL}$.
- Must be displayed alongside sample size ($|\mathcal{L}_{\text{checked\_verified}}|$).
- This is a sample link integrity metric, not a domain-wide or algorithmic ranking score.

---

### E10. Image Alt Attribute Coverage (IAC)
- **Model ID**: `E10`
- **Domain**: Content Accessibility & On-Page SEO
- **Classification**: Direct Deterministic Observation
- **Implementation Phase**: Phase 1
- **Target Module**: `apps/api/app/metrics/assets.py`

#### Mathematical Formulation
$$\text{IAC} = 100 \times \frac{|\mathcal{I}_{\text{eligible\_with\_alt}}|}{|\mathcal{I}_{\text{eligible\_analysed}}|}$$

Where:
- $\mathcal{I}_{\text{eligible\_analysed}}$: Set of non-decorative, eligible meaningful images on the page.
- $\mathcal{I}_{\text{eligible\_with\_alt}}$: Subset of eligible images having a non-empty `alt` attribute string ($\text{len}(\text{trim}(\text{alt})) > 0$).

#### Null, Boundary & Decorative Image Rules
- **Decorative Images**: Images with `alt=""` or `role="presentation"` or `aria-hidden="true"` are classified as **decorative by intent** and must **not** be counted as failures. They are excluded from eligible meaningful images.
- Images must be classified into three distinct buckets in report telemetry:
  1. `MISSING_ALT`: Tag lacks the `alt` attribute entirely (Defect).
  2. `EMPTY_ALT`: Tag has `alt=""` (Permitted if decorative; defect if inside an anchor tag without text).
  3. `NON_EMPTY_ALT`: Tag has text (Meets syntax requirement).
- The scanner must not claim arbitrary text is "semantically descriptive" without separate NLP/vision evaluation.
- If $|\mathcal{I}_{\text{eligible\_analysed}}| = 0$, $\text{IAC} = \text{NULL}$ (flag `NO_ELIGIBLE_IMAGES`).

---

### E11. Redirect Hop Count & Loop Detection
- **Model ID**: `E11`
- **Domain**: Crawlability & Network Transport
- **Classification**: Direct Deterministic Observation
- **Implementation Phase**: Phase 1
- **Target Module**: `apps/api/app/crawler/redirects.py`

#### Operational Classification Model
Let $H$ be the count of actual HTTP $3xx$ redirect hops followed manually:
$$\text{Classification}(H) = \begin{cases}
\text{PASS (Optimal)} & \text{if } H \in \{0, 1\} \\
\text{WARNING (Sub-optimal)} & \text{if } H \in \{2, 3\} \\
\text{CRITICAL (Excessive Latency)} & \text{if } H \ge 4 \\
\text{CRITICAL (Redirect Loop)} & \text{if target URL seen previously in chain}
\end{cases}$$

#### Telemetry Requirements
- Store each hop's: `hop_index`, `status_code`, `request_url`, `response_headers['location']`, `resolved_ip`, and `rtt_ms`.
- Maximum redirect limit enforced by crawler: 5 hops. If exceeded, crawler terminates and flags `MAX_REDIRECTS_EXCEEDED`.

---

### E12. Sitemap URL Health (SH)
- **Model ID**: `E12`
- **Domain**: Crawlability & Indexing Infrastructure
- **Classification**: Direct Deterministic Observation
- **Implementation Phase**: Phase 1
- **Target Module**: `apps/api/app/metrics/sitemap.py`

#### Mathematical Formulation
$$\text{SH} = 100 \times \frac{|\mathcal{U}_{\text{valid}}|}{| \mathcal{U}_{\text{sampled}} |}$$

Where $\mathcal{U}_{\text{valid}}$ is the set of sampled sitemap URLs satisfying all four deterministic validation dimensions:
1. Valid absolute URL syntax matching the origin scheme and host.
2. Fetchable with HTTP 200 OK.
3. Canonical URL points self-referentially to itself (not canonicalized away).
4. Directives do not contain `noindex` in meta tag or `X-Robots-Tag`.

#### Null and Boundary Rules
- Disclose each dimension separately in evidence: `syntax_pass_rate`, `status_200_rate`, `canonical_aligned_rate`, `indexable_rate`.
- If no sitemap is referenced or found, $\text{SH} = \text{NULL}$ (flag `SITEMAP_NOT_FOUND`).
- Sampling size must be reported ($|\mathcal{U}_{\text{sampled}}|$, max 50 URLs in Phase 1 single-scan mode).
- Inclusion in a sitemap does not guarantee indexing by Google.

---

### E13. Inspected Sample Indexation Rate (IR)
- **Model ID**: `E13`
- **Domain**: Google Search Console Status
- **Classification**: Official External Measurement (GSC API)
- **Implementation Phase**: Phase 6
- **Target Module**: `apps/api/app/integrations/gsc/metrics.py`

#### Mathematical Formulation
$$\text{IR} = 100 \times \frac{|\mathcal{U}_{\text{inspected\_indexed}}|}{|\mathcal{U}_{\text{inspected\_eligible}}|}$$

Where:
- $\mathcal{U}_{\text{inspected\_eligible}}$: Set of submitted URLs for which GSC URL Inspection API returned a definitive response within quota limits.
- $\mathcal{U}_{\text{inspected\_indexed}}$: Subset where `coverageState` indicates indexed (e.g. `Submitted and indexed` or `Indexed, not submitted in sitemap`).

#### Null and Boundary Rules
- Must be labeled as **Inspected Sample Indexation Rate**, never whole-site indexation unless 100% of sitemap URLs were inspected.
- URLs that encountered API quota errors (HTTP 429) or timeouts are marked `UNKNOWN` and excluded from both numerator and denominator.
- URLs not inspected must **never** be assumed non-indexed.
- If $|\mathcal{U}_{\text{inspected\_eligible}}| = 0$, $\text{IR} = \text{NULL}$.

---

### E14. JSON-LD Syntax Validity Ratio (JVR)
- **Model ID**: `E14`
- **Domain**: Structured Data
- **Classification**: Direct Deterministic Observation
- **Implementation Phase**: Phase 1
- **Target Module**: `apps/api/app/parsers/jsonld.py`

#### Mathematical Formulation
$$\text{JVR} = 100 \times \frac{|\mathcal{J}_{\text{parsed\_valid}}|}{| \mathcal{J}_{\text{detected}} |}$$

Where:
- $\mathcal{J}_{\text{detected}}$: Set of all `<script type="application/ld+json">` elements present in the DOM.
- $\mathcal{J}_{\text{parsed\_valid}}$: Subset of detected elements whose text content parses as valid RFC 8259 JSON.

#### Distinctions & Caveats
- If $|\mathcal{J}_{\text{detected}}| = 0$, return $\text{JVR} = \text{NULL}$ with telemetry `NO_JSONLD_DETECTED`.
- **Strict Semantic Distinction**: $\text{JVR}$ measures JSON syntax validity only. It does **not** prove Schema.org semantic validity, required field presence, or Google Rich Results eligibility.
- Four distinct reporting states:
  1. `NONE_DETECTED`: 0 blocks found.
  2. `SYNTAX_INVALID`: One or more blocks failed JSON parsing.
  3. `SYNTAX_VALID`: All blocks parse as valid JSON.
  4. `RICH_RESULT_ELIGIBLE`: Evaluated by separate schema schema validator against Google guidelines.

---

### E15. Competitor Visibility Score (CV)
- **Model ID**: `E15`
- **Domain**: Competitor Intelligence
- **Classification**: Third-Party Licensed Estimate Composite
- **Implementation Phase**: Phase 3
- **Target Module**: `apps/api/app/competitor/visibility.py`

#### Mathematical Formulation
$$\text{CV}(d) = \sum_{q=1}^{m} \frac{w_q}{\log_2(1 + r_{d, q})}$$

Where:
- $d$: Competitor domain or page under analysis.
- $q$: Target keyword query ($q \in \{1, \dots, m\}$).
- $w_q$: Normalized importance weight of query $q$ ($\sum_{q} w_q = 1.0$).
- $r_{d, q}$: Observed organic SERP ranking position of domain $d$ for query $q$ ($r_{d, q} \in [1, K]$, where $K$ is the scraped SERP depth, typically 10 or 20).

#### Censoring & Boundary Handling
- **Censored SERP Depth**: If domain $d$ does not appear within the collected depth $K$ for query $q$, the observation is strictly **censored**.
- The model must **never** invent an arbitrary rank (e.g. rank 100). The query contribution is treated as 0:
  $$\frac{w_q}{\log_2(1 + r_{d, q})} = 0 \quad \text{if } d \notin \text{SERP}(q, K)$$
- Provenance requirements: Every SERP record must store provider name, retrieval timestamp, target country, city, language, device (`mobile` vs `desktop`), and depth $K$.
- This is an internal visibility index; it does not measure private traffic or impressions.

---

### E16. Weighted Content Coverage Gap ($G$)
- **Model ID**: `E16`
- **Domain**: Content Gap Analysis
- **Classification**: Deterministic Comparative Heuristic
- **Implementation Phase**: Phase 3
- **Target Module**: `apps/api/app/gap_analysis/content.py`

#### Mathematical Formulation
$$G = 100 \times \frac{\sum_{j=1}^{n} w_j \max\left(0, C_j - T_j\right)}{\sum_{j=1}^{n} w_j}$$

Where:
- $j$: Topic or entity sub-theme in the target taxonomy ($j \in \{1, \dots, n\}$).
- $w_j$: Importance weight of topic $j$ ($w_j > 0$).
- $C_j$: Representative competitor coverage for topic $j$ on a continuous normalized scale $[0.0, 1.0]$ (derived as the **median** coverage across top ranking competitor pages).
- $T_j$: Target site page's verified coverage for topic $j$ on the same $[0.0, 1.0]$ scale.

#### Null and Handling Rules
- If $\sum w_j = 0$ or no topics are defined for the target query, $G = \text{NULL}$.
- Max operator $\max(0, C_j - T_j)$ ensures that topics where the client outperforms competitors ($T_j > C_j$) do not offset or hide gaps in other topics.
- Disclose taxonomy source, extraction method (n-gram / entity frequency), and competitor sample size.
- **Strict Warning**: A gap indicates a difference in coverage; it does not imply copying competitor content or that adding words guarantees ranking increases.

---

### E17. Keyword Opportunity Score (KO)
- **Model ID**: `E17`
- **Domain**: Keyword Strategy
- **Classification**: Third-Party Licensed Estimate Composite
- **Implementation Phase**: Phase 3
- **Target Module**: `apps/api/app/gap_analysis/keywords.py`

#### Mathematical Formulation
$$\text{KO} = 100 \times \frac{D \times R \times B \times F}{\text{KD} + 1.0}$$

Where all inputs are normalized to the range $[0.0, 1.0]$ prior to computation:
- $D$: Normalized search demand / volume estimate ($D \in [0.0, 1.0]$) from a licensed keyword data provider.
- $R$: Business and query intent relevance ($R \in [0.0, 1.0]$).
- $B$: Competitor visibility gap / opportunity ($B \in [0.0, 1.0]$).
- $F$: Implementation feasibility ($F \in [0.0, 1.0]$).
- $\text{KD}$: Normalized keyword difficulty estimate ($\text{KD} \in [0.0, 1.0]$) from a licensed provider.

#### Null, Boundary & Integrity Rules
- If any required input ($D, R, B, F, \text{KD}$) is missing, return $\text{KO} = \text{NULL}$. **Never fabricate search volume or difficulty.**
- Normalization parameters (e.g. logarithmic scaling of raw search volume $V$: $D = \min(1.0, \frac{\log_{10}(V + 1)}{5})$) must be recorded in metadata.
- Third-party volume and difficulty are third-party statistical estimates, not exact Google internal numbers.

---

### E18. Potential Click Opportunity (PCO)
- **Model ID**: `E18`
- **Domain**: Opportunity Sizing
- **Classification**: Internal Deterministic Scenario Estimate
- **Implementation Phase**: Phase 3
- **Target Module**: `apps/api/app/gap_analysis/clicks.py`

#### Mathematical Formulation
$$\text{PCO} = I \times \max\left(0, \text{CTR}_{\text{benchmark}} - \text{CTR}_{\text{current}}\right)$$

Where:
- $I$: Observed impressions from Google Search Console for the query/page over a defined, comparable time window (e.g. 28 days).
- $\text{CTR}_{\text{current}}$: Observed Search Console CTR expressed as a decimal ($0.04$ for $4\%$).
- $\text{CTR}_{\text{benchmark}}$: Curated benchmark CTR for target position / SERP layout as a decimal ($0.12$ for $12\%$).

#### Null and Boundary Rules
- If $I = 0$ or $I = \text{NULL}$, $\text{PCO} = \text{NULL}$.
- If $\text{CTR}_{\text{current}} \ge \text{CTR}_{\text{benchmark}}$, $\text{PCO} = 0$.
- $\text{CTR}_{\text{benchmark}}$ must explicitly cite its dataset origin (e.g., industry study, device type, search feature context) or be labeled as an illustrative scenario.
- **Strict Warning**: This is an illustrative potential opportunity estimate, not a forecast, guarantee, or promise of future traffic.

---

### E19. Content Section Placement Score ($L$)
- **Model ID**: `E19`
- **Domain**: Remediation Engineering
- **Classification**: Internal Deterministic Heuristic
- **Implementation Phase**: Phase 4
- **Target Module**: `apps/api/app/resolution/placement.py`

#### Mathematical Formulation
$$L = 0.30 R + 0.25 S + 0.20 U + 0.15 V + 0.10 D$$

Where each input is a normalized score in $[0, 100]$:
- $R$: Topic relevance to candidate section.
- $S$: Structural suitability of candidate container element (e.g. `<article>`, `<section>`, heading depth alignment).
- $U$: User / search-intent suitability.
- $V$: Visual prominence and layout visibility suitability.
- $D$: Non-duplication suitability (penalizes existing semantically redundant sections).

#### Evidence Requirements
- $L$ is a heuristic prioritization score.
- The proposed placement **must** be accompanied by concrete DOM proof: target URL, preceding heading text, DOM selector path, and insertion anchor (`before`, `after`, `append`).
- Exact source code file and line numbers **cannot** be inferred from public HTML. Source code mapping is labeled `UNAVAILABLE` unless authorized repository / ZIP AST mapping is provided in Phase 5.

---

### E20. Root-Cause Triage Composite (RC)
- **Model ID**: `E20`
- **Domain**: Resolution Triage
- **Classification**: Internal Deterministic Triage Metric
- **Implementation Phase**: Phase 4
- **Target Module**: `apps/api/app/resolution/triage.py`

#### Mathematical Formulation
$$\text{RC} = 0.40 E + 0.25 P + 0.20 H + 0.15 S$$

Where all inputs are defined on $[0, 100]$:
- $E$: Direct evidence strength (e.g. 100 for raw HTTP header, 80 for DOM selector, 40 for indirect heuristic).
- $P$: Reproducibility across multiple test fetches.
- $H$: Historical consistency / persistence.
- $S$: Affected page scope / blast radius (share of site pages affected).

#### Critical Semantic Correction
- Because affected scope ($S$) measures impact/blast radius, $\text{RC}$ is a **triage prioritization composite**, **not a causal probability**. It must never be labeled or described to users as a "probability of causation".
- Direct deterministic findings (e.g. page responds with `X-Robots-Tag: noindex`) are already confirmed facts; they do not need $\text{RC}$ to become "verified".

---

### E21. Resolution Priority (RICE-Inspired)
- **Model ID**: `E21`
- **Domain**: Task Prioritization
- **Classification**: Internal Deterministic Prioritization Heuristic
- **Implementation Phase**: Phase 4
- **Target Module**: `apps/api/app/resolution/priority.py`

#### Mathematical Formulation
$$P_{\text{priority}} = \frac{R \times I \times C}{E}$$

Where:
- $R$: Reach (number of affected URLs or estimated search query volume, scaled $1–10$).
- $I$: Impact (technical severity / indexability blocker impact, scaled $1–5$).
- $C$: Evidence confidence factor ($0.5$ for low/indirect, $0.8$ for high, $1.0$ for direct verified proof).
- $E$: Estimated engineering effort in hours or complexity points ($\ge 1.0$).

#### Null and Denominator Guard
- Effort $E$ is constrained to $E \ge 1.0$ (floor) to mathematically prevent division by zero.
- Used strictly for ordering implementation tasks in the Admin Resolution Center.

---

### E22. Referring Domain Gap (RDG)
- **Model ID**: `E22`
- **Domain**: Backlink & Authority Intelligence
- **Classification**: Third-Party Licensed Estimate
- **Implementation Phase**: Phase 3
- **Target Module**: `apps/api/app/gap_analysis/backlinks.py`

#### Mathematical Formulation
$$\text{RDG} = \max\left(0, \text{RD}_{\text{competitor\_benchmark}} - \text{RD}_{\text{client}}\right)$$

Where:
- $\text{RD}_{\text{competitor\_benchmark}}$: Representative referring domain count (median across top organic competitors) from a licensed backlink data provider.
- $\text{RD}_{\text{client}}$: Verified unique referring domain count of the client domain from the same provider.

#### Boundary & Attribution Rules
- Must use data from the **same provider**, retrieved within the **same 7-day window**, and using the **same scope** (root domain vs subfolder).
- Never scrape public homepages to estimate backlink counts.
- Backlink metrics must declare provider name, snapshot date, and active index status.

---

### E23. Link Opportunity Relevance (LO)
- **Model ID**: `E23`
- **Domain**: Off-Page Opportunity Analysis
- **Classification**: Internal Deterministic Ratio
- **Implementation Phase**: Phase 3
- **Target Module**: `apps/api/app/gap_analysis/backlinks.py`

#### Mathematical Formulation
$$\text{LO} = 100 \times \frac{|\mathcal{O}_{\text{relevant\_verified}}|}{| \mathcal{O}_{\text{total\_verified}} |}$$

Where $\mathcal{O}$ represents the deduplicated set of researched linking opportunities.
- Describes the relevance quality of discovered link prospects. Does not represent probability of link acquisition.

---

### E24. Search Console Click-Through Rate (CTR)
- **Model ID**: `E24`
- **Domain**: Performance Analytics
- **Classification**: Official External Measurement (GSC API)
- **Implementation Phase**: Phase 6
- **Target Module**: `apps/api/app/integrations/gsc/analytics.py`

#### Mathematical Formulation
$$\text{CTR} = 100 \times \frac{\text{Clicks}}{\text{Impressions}}$$

#### Null and Zero Handling
- If $\text{Impressions} = 0$ or unavailable:
  $$\text{CTR} = \text{NULL (Unavailable, not 0)}$$
- Always store and disclose the exact GSC dimensions: date range, search type (`web`, `image`), country filter, and device filter.

---

### E25. Impression Decline Rate ($D_I$)
- **Model ID**: `E25`
- **Domain**: Trend Analysis
- **Classification**: Official External Measurement Comparison
- **Implementation Phase**: Phase 6
- **Target Module**: `apps/api/app/metrics/trends.py`

#### Mathematical Formulation
$$D_I = 100 \times \frac{I_{\text{previous}} - I_{\text{current}}}{I_{\text{previous}}}$$

#### Null and Boundary Rules
- If $I_{\text{previous}} = 0$:
  $$D_I = \text{NULL (Report absolute change: } I_{\text{current}} - I_{\text{previous}}\text{)}$$
- Requires identical time period lengths (e.g. 28 days vs previous 28 days), aligned day-of-week seasonality, and data freshness clearance (excluding the most recent 3 days of immature GSC data).

---

### E26. Click Decline Rate ($D_C$)
- **Model ID**: `E26`
- **Domain**: Trend Analysis
- **Classification**: Official External Measurement Comparison
- **Implementation Phase**: Phase 6
- **Target Module**: `apps/api/app/metrics/trends.py`

#### Mathematical Formulation
$$D_C = 100 \times \frac{C_{\text{previous}} - C_{\text{current}}}{C_{\text{previous}}}$$

#### Null and Boundary Rules
- If $C_{\text{previous}} = 0$, $D_C = \text{NULL}$ (report absolute change).
- A decline in clicks does not automatically prove a technical SEO defect; external factors (seasonality, demand shifts, competitor campaigns) must be reported as potential confounders.

---

### E27. Average Position Change ($\Delta P$)
- **Model ID**: `E27`
- **Domain**: Trend Analysis
- **Classification**: Official External Measurement Comparison
- **Implementation Phase**: Phase 6
- **Target Module**: `apps/api/app/metrics/trends.py`

#### Mathematical Formulation
$$\Delta P = P_{\text{previous}} - P_{\text{current}}$$

#### Directional Semantics
- In SERP ranking, a lower number is a better position (e.g. Position 1 is top).
- **Positive $\Delta P$** indicates an **improvement** (e.g. $P_{\text{prev}} = 8.4, P_{\text{curr}} = 4.2 \implies \Delta P = +4.2$).
- **Negative $\Delta P$** indicates a **deterioration** (e.g. $P_{\text{prev}} = 3.1, P_{\text{curr}} = 7.5 \implies \Delta P = -4.4$).
- Telemetry must clarify that GSC average position is an aggregate metric sensitive to changes in query impression mix.

---

### E28. Potential Keyword Cannibalization / URL Overlap ($K$)
- **Model ID**: `E28`
- **Domain**: Indexing & Intent Diagnostics
- **Classification**: Internal Deterministic Diagnostic Signal
- **Implementation Phase**: Phase 6
- **Target Module**: `apps/api/app/metrics/cannibalization.py`

#### Mathematical Formulation
$$K = 1.0 - \frac{\max(I_1, I_2, \dots, I_n)}{\sum_{i=1}^{n} I_i}$$

Where $I_i$ is the impression count for distinct URL $i$ ranking for the exact same query in the same period ($n \ge 2$).

#### Null and Boundary Rules
- If $n < 2$ (only one URL observed) or $\sum I_i = 0$:
  $$K = \text{NULL (No overlap)}$$
- If URL 1 has $99\%$ of impressions, $K \to 0.01$ (negligible overlap).
- If two URLs split impressions $50\% / 50\%$, $K = 0.50$ (high overlap).
- **Strict Warning**: $K$ is a mathematical signal of impression dispersion, **not definitive proof** of harmful cannibalization. Intent analysis, ranking volatility, and URL stability must be verified before recommending URL consolidation.

---

### E29. Scan Completion Rate (SCR)
- **Model ID**: `E29`
- **Domain**: Platform Operational Health
- **Classification**: Internal Deterministic Telemetry
- **Implementation Phase**: Phase 2
- **Target Module**: `apps/api/app/metrics/operational.py`

#### Mathematical Formulation
$$\text{SCR} = 100 \times \frac{\text{Scans}_{\text{completed}}}{\text{Scans}_{\text{initiated}}}$$

- Filtered by unique scan sessions within an attribution window. Excludes automated client retries.

---

### E30. Lead Conversion Rate (LCR)
- **Model ID**: `E30`
- **Domain**: Business Funnel Performance
- **Classification**: Internal Deterministic Business Metric
- **Implementation Phase**: Phase 2
- **Target Module**: `apps/api/app/metrics/operational.py`

#### Mathematical Formulation
$$\text{LCR} = 100 \times \frac{\text{Leads}_{\text{valid}}}{\text{Scans}_{\text{completed}}}$$

- $\text{Leads}_{\text{valid}}$ requires deduplicated, valid email and domain association. Excludes spam and test submissions.

---

### E31. Qualified Lead Rate (QLR)
- **Model ID**: `E31`
- **Domain**: Business Funnel Performance
- **Classification**: Internal Deterministic Business Metric
- **Implementation Phase**: Phase 2
- **Target Module**: `apps/api/app/metrics/operational.py`

#### Mathematical Formulation
$$\text{QLR} = 100 \times \frac{\text{Leads}_{\text{qualified}}}{\text{Leads}_{\text{valid}}}$$

- If $\text{Leads}_{\text{valid}} = 0$, $\text{QLR} = \text{NULL}$.
- Qualification criteria defined in CRM: verified site ownership, business email, confirmed technical blockers.

---

### E32. Client Conversion Rate (CCR)
- **Model ID**: `E32`
- **Domain**: Business Funnel Performance
- **Classification**: Internal Deterministic Business Metric
- **Implementation Phase**: Phase 2
- **Target Module**: `apps/api/app/metrics/operational.py`

#### Mathematical Formulation
$$\text{CCR} = 100 \times \frac{\text{Clients}_{\text{signed}}}{\text{Leads}_{\text{qualified}}}$$

- If $\text{Leads}_{\text{qualified}} = 0$, $\text{CCR} = \text{NULL}$.

---

### E33. Issue Resolution Rate (IRR)
- **Model ID**: `E33`
- **Domain**: Remediation Verification
- **Classification**: Internal Deterministic Verification Metric
- **Implementation Phase**: Phase 6
- **Target Module**: `apps/api/app/verification/resolution.py`

#### Mathematical Formulation
$$\text{IRR} = 100 \times \frac{|\mathcal{F}_{\text{verified\_resolved}}|}{| \mathcal{F}_{\text{attempted}} |}$$

Where:
- $\mathcal{F}_{\text{attempted}}$: Set of audit issues for which a code patch was approved, deployed, and re-tested.
- $\mathcal{F}_{\text{verified\_resolved}}$: Subset of attempted issues where post-deployment re-scan evaluates rule to `PASS`.

#### Integrity Guard
- Issues marked rejected, pending, or not attempted are strictly excluded from the denominator.
- Every resolved issue must store immutable before/after evidence snapshots.

---

### E34. Performance Improvement Rate ($PI_X$)
- **Model ID**: `E34`
- **Domain**: Verification & QA
- **Classification**: Comparative Measurement
- **Implementation Phase**: Phase 6
- **Target Module**: `apps/api/app/verification/performance.py`

#### Mathematical Formulation
For any lower-is-better metric $X$ (e.g. LCP, CLS, TTFB, TBT):
$$PI_X = 100 \times \frac{X_{\text{before}} - X_{\text{after}}}{X_{\text{before}}}$$

#### Null and Comparison Guards
- If $X_{\text{before}} = 0$ or unavailable, return absolute difference $\Delta X = X_{\text{before}} - X_{\text{after}}$.
- Must compare **identical measurement contexts**: same URL, same device, same network profile, and same source tier (field CrUX vs field CrUX, or lab vs lab). **Never compare lab before with field after.**

---

### E35. Audit Regression Rate (RR)
- **Model ID**: `E35`
- **Domain**: Verification & QA
- **Classification**: Internal Deterministic Verification Metric
- **Implementation Phase**: Phase 6
- **Target Module**: `apps/api/app/verification/regression.py`

#### Mathematical Formulation
$$\text{RR} = 100 \times \frac{|\mathcal{R}_{\text{previously\_pass\_now\_fail}}|}{| \mathcal{R}_{\text{previously\_pass\_retested}} |}$$

#### Guardrails
- Denominator includes **only** checks that previously evaluated to `PASS` and were successfully re-tested under identical conditions.
- Every newly introduced failure is surfaced individually with a diff of before/after evidence.

---

### E36. Difference-in-Differences (DiD) Evaluation
- **Model ID**: `E36`
- **Domain**: Causal Outcome Evaluation
- **Classification**: Statistical Evaluation Design
- **Implementation Phase**: Phase 6
- **Target Module**: `apps/api/app/verification/did.py`

#### Mathematical Formulation
$$\text{DiD} = \left(\bar{Y}_{\text{treated, post}} - \bar{Y}_{\text{treated, pre}}\right) - \left(\bar{Y}_{\text{control, post}} - \bar{Y}_{\text{control, pre}}\right)$$

Where:
- $\bar{Y}$: Mean observed outcome metric (e.g. organic clicks, impressions, or indexation rate).
- $\text{treated}$: Cohort of URLs that received code patches.
- $\text{control}$: Matched cohort of comparable URLs within the same domain that received no changes.
- $\text{pre}, \text{post}$: Pre- and post-intervention time windows of equal length.

#### Evaluation Safeguards & Anti-Hallucination
- Parallel trends assumption must be verified on pre-period data.
- **Strict Warning**: DiD is an econometric evaluation design to isolate treatment effects from sitewide seasonal trends. It does **not** provide mathematical proof of search algorithm causality. External shocks (Google core updates, brand promotions) must be documented.

---

## 3. Testing Strategy for Mathematical Models

### 3.1 Test Framework
All models must be verified using:
1. **Pytest**: Standard unit tests against fixed deterministic fixtures.
2. **Hypothesis**: Property-based testing generating pseudo-random edge-case inputs to verify invariants:
   - Invariant: Scores must remain strictly bounded in $[0.0, 100.0]$.
   - Invariant: Denominator zeros must always return `None` / `NULL`, never raise unhandled exceptions or return `inf` / `NaN`.
   - Invariant: If all applicable checks pass, category score must be exactly $100.0$.
   - Invariant: If all applicable checks fail, category score must be exactly $0.0$.

### 3.2 Mandatory Test Directory Structure
```
apps/api/tests/
├── unit/scoring/
│   ├── test_e1_check_mapping.py
│   ├── test_e2_category_score.py
│   ├── test_e3_overall_score.py
│   ├── test_e4_legacy_deduction.py
│   └── test_e5_completeness.py
├── unit/metrics/
│   ├── test_e6_e7_cwv_normalization.py
│   ├── test_e8_e9_internal_links.py
│   ├── test_e10_image_alt.py
│   └── test_e11_e12_e14_crawling_parsers.py
├── unit/gap_analysis/
│   ├── test_e15_competitor_visibility.py
│   ├── test_e16_content_gap.py
│   ├── test_e17_keyword_opportunity.py
│   └── test_e18_e22_e23_clicks_backlinks.py
├── unit/resolution/
│   ├── test_e19_placement.py
│   ├── test_e20_triage_composite.py
│   └── test_e21_rice_priority.py
├── unit/verification/
│   ├── test_e24_e28_gsc_trends.py
│   ├── test_e29_e32_operational.py
│   └── test_e33_e36_resolution_did.py
└── property/
    ├── test_scoring_invariants.py
    └── test_denominator_safety.py
```

