# SEO Optimizer — Security Architecture & Threat Model

> **Version**: 2.0.0 (Foundation Alignment)  
> **Status**: Approved Security Specification  
> **Backend Implementation**: Python 3.x (`httpx` / `socket` / `ipaddress`)  
> **Core Policy**: Zero-Trust Network Egress | Zero Host Execution of Untrusted Code | AES-256-GCM Token Encryption

---

## 1. Security Context & Threat Landscape

SEO Optimizer is an internet-facing application that accepts arbitrary user-supplied URLs for public scanning and, in later phases, accepts client-supplied source-code archives (ZIP files) for automated technical remediation. By nature, these two capabilities expose the system to high-severity attack vectors:

1. **Server-Side Request Forgery (SSRF)**: Malicious or crafted URLs designed to probe internal cloud VPC infrastructure, localhost services, Kubernetes APIs, or cloud metadata endpoints (`169.254.169.254`).
2. **DNS Rebinding Attacks (TOCTOU)**: Exploiting Time-of-Check to Time-of-Use race conditions where an attacker's DNS server returns a benign public IP during pre-flight validation, but returns `127.0.0.1` or `169.254.169.254` during the actual HTTP connection handshake.
3. **Decompression & Resource Exhaustion (DoS)**: Gzip/Brotli HTTP compression bombs, slowloris streaming attacks, and Zip Bombs designed to exhaust memory or CPU.
4. **Directory Traversal (Zip Slip)**: Specially crafted archive files containing path traversal sequences (e.g. `../../etc/passwd`) designed to overwrite system files upon extraction.
5. **Arbitrary Code Execution (RCE)**: Malicious install scripts, build hooks, or dependency manifests within client codebases attempting to run arbitrary code on the API host.
6. **Credential & Token Leakage**: Exposure of client Google Search Console OAuth tokens or third-party API keys to the frontend browser or unprivileged processes.

To counter these threats, the system enforces a strict **Zero-Trust Security Perimeter**.

---

## 2. Server-Side Request Forgery (SSRF) Defense Architecture

The SSRF prevention subsystem (`apps/api/app/crawler/`) operates as an unbypassable gatekeeper between the Python crawler and the external internet.

```mermaid
flowchart TD
    UserURL["Inbound Scan URL\n(e.g., https://target.com/page)"] --> URLSanitizer["1. URL Sanitizer\n- Scheme: http/https only\n- Port: 80/443 only\n- Strip credentials (user:pass@)\n- Hostname normalization"]
    URLSanitizer --> DNSResolver["2. DNS Pre-Resolution\n- Resolve all A and AAAA records\n- Check for mixed public/private answers\n- Timeout: 3.0s"]
    DNSResolver --> CIDRFilter{"3. CIDR Denylist Check\nIs any resolved IP in\nforbidden CIDRs?"}
    CIDRFilter -- Yes --> Reject["REJECT REQUEST\nHTTP 400 'Target host not permitted'"]
    CIDRFilter -- No --> PinSocket["4. Socket Connection Pinning\n- Bind socket directly to pre-validated IP\n- Set HTTP 'Host' header to original domain\n- Set TLS SNI to original domain\n- Mathematically eliminates DNS Rebinding"]
    PinSocket --> StreamFetcher["5. Streaming Fetcher with Guardrails\n- Max body size: 10 MB\n- Socket timeout: 3s, Total timeout: 10s\n- Strict Content-Type check (text/html, application/xml)"]
    StreamFetcher --> RedirectCheck{"Redirect (3xx)?"}
    RedirectCheck -- Yes --> HopCheck{"Redirect Count < 5?"}
    HopCheck -- No --> AbortMaxRedir["REJECT: Max redirects exceeded (HTTP 400)"]
    HopCheck -- Yes --> URLSanitizer
    RedirectCheck -- No --> IngestStream["Pass verified stream to Parser"]
```

### 2.1 Critical Invariant: DNS Pre-Check Alone is NOT Sufficient
A naive implementation that resolves DNS, checks the IP, and subsequently calls `httpx.get(url)` is **critically vulnerable to DNS Rebinding**. Because the operating system or HTTP library re-resolves the domain during the subsequent TCP handshake, an attacker configuring a sub-second TTL DNS server can return `127.0.0.1` on the second resolution.

**Mandatory Mitigation**:
The crawler must either:
1. **Pin the Outbound Connection**: Connect the raw TCP/TLS socket directly to the pre-validated IP address, explicitly supplying the target domain name in the `Host` header and TLS Server Name Indication (SNI).
2. **Egress Proxy Enforcement**: Route all outbound scanning requests through an unbypassable network egress firewall/proxy (e.g., Envoy or Smokescreen) that enforces the CIDR blocklist at the packet/socket layer.

### 2.2 Comprehensive CIDR Denylist (IPv4 & IPv6)

Every resolved IP address (A and AAAA records) must be matched against the following forbidden ranges using Python's `ipaddress` module:

| Network Category | IPv4 CIDR Range | IPv6 CIDR Range | Security Threat Mitigated |
| :--- | :--- | :--- | :--- |
| **Loopback** | `127.0.0.0/8` | `::1/128` | Localhost services (Postgres, Redis, local APIs) |
| **Private Networks (RFC 1918)** | `10.0.0.0/8`<br>`172.16.0.0/12`<br>`192.168.0.0/16` | `fc00::/7` (ULA) | Internal VPC instances, microservices, internal routers |
| **Link-Local & Cloud Metadata** | `169.254.0.0/16` | `fe80::/10` | AWS/GCP/Azure Instance Metadata Service (`169.254.169.254`) |
| **Carrier-Grade NAT (RFC 6598)** | `100.64.0.0/10` | — | Internal ISP & cloud provider infrastructure |
| **Current Network ("This" Host)**| `0.0.0.0/8` | `::/128` | Local host interface binding attacks |
| **Broadcast & Multicast** | `224.0.0.0/4`<br>`240.0.0.0/4`<br>`255.255.255.255/32` | `ff00::/8` | Multicast amplification and broadcast spoofing |
| **Documentation & Test Nets** | `192.0.2.0/24`<br>`198.51.100.0/24`<br>`203.0.113.0/24` | `2001:db8::/32` | Non-routable documentation subnets |
| **IPv4-Mapped IPv6** | — | `::ffff:0:0/96` | IPv4 embedded in IPv6 (e.g. `::ffff:127.0.0.1`) |

*Rule*: If a DNS query returns multiple IP records and **any** single record matches the denylist, or if the answer set mixes public and private IPs, the entire request is rejected immediately.

### 2.3 Protocol & Port Constraints
- **Permitted Schemes**: Strictly `http:` and `https:`. All other schemes (`file:`, `ftp:`, `gopher:`, `dict:`, `data:`, `javascript:`, `ws:`) are rejected during URL parsing.
- **Permitted Destination Ports**: Strictly `80` (HTTP) and `443` (HTTPS). Non-standard ports (e.g. `:8080`, `:8443`, `:22`, `:5432`) are rejected.
- **URL Credentials**: URLs containing user credentials (e.g. `https://admin:password@target.com`) are rejected before resolution.

### 2.4 Manual Redirect Interception
- Automatic redirects in `httpx` (`follow_redirects=True`) are **strictly disabled**.
- Every HTTP 301, 302, 303, 307, or 308 response is intercepted hop-by-hop.
- The `Location` header is parsed into an absolute URL and passed back through the full SSRF validation pipeline (Scheme check $\to$ Port check $\to$ DNS resolution $\to$ CIDR filter $\to$ Socket pinning).
- **Hop Limit**: Maximum **5 hops**. Exceeding 5 hops terminates the scan with a `FAIL` status for the redirect chain rule.
- **Loop Detection**: Any URL already visited in the active chain triggers an immediate `REDIRECT_LOOP_DETECTED` failure.

### 2.5 Resource Bounds & Decompression Safety
- **Max Response Size**: Hard streaming ceiling of **10 MB** (`10,485,760` bytes). Stream ingestion terminates immediately if the byte count exceeds this limit.
- **Decompression Guard**: Decompression (gzip, deflate, brotli) is performed with a streaming chunk counter on the *uncompressed* output stream to prevent decompression bombs.
- **Timeouts**:
  - DNS Resolution: 3.0 seconds.
  - Socket Connect: 3.0 seconds.
  - Stream Read: 5.0 seconds.
  - Overall Scan Deadline: 10.0 seconds.
- **Content-Type Filter**: Outbound crawling rejects non-text/html responses (e.g. large binary video, ISO images) once headers are read.

---

## 3. Browser Worker Security Architecture (Later Phase)

When headless browser rendering (Playwright) is introduced in subsequent phases for SPA analysis:

1. **Dedicated Container Isolation**:
   - The browser process runs inside an isolated, containerized worker separate from the FastAPI server.
   - Read-only root filesystem (`read_only: true`).
   - Non-root execution (`user: 10001:10001`).
   - Linux capabilities dropped: `ALL` (no `NET_ADMIN`, no `SYS_PTRACE`).
   - `seccomp` and `AppArmor` security profiles enforced.
2. **Network Egress Confinement**:
   - The Playwright worker has **no direct route to the internet**.
   - All browser traffic routes exclusively through an internal egress proxy that enforces the `ssrf-guard` policy.
3. **Browser Context Hardening**:
   - WebSockets (`wss://`), WebRTC, Service Workers, Geolocation, Notifications, and Local File Access (`file://`) are explicitly disabled.
   - Strict resource limits: max 1 active page per context, 512 MB RAM ceiling, 15-second navigation timeout.
4. **Secret Isolation**:
   - Application secrets, database credentials, and API keys are **never mounted** in the browser worker environment.

---

## 4. Source Code Archive (ZIP) & Sandbox Security (Phase 5)

Client code remediation in Phase 5 involves accepting ZIP archives of client repositories. Under no circumstances is untrusted code executed on the main application server.

```mermaid
flowchart TD
    ClientUpload["Client Uploads source.zip\n(Signed Pre-Signed URL)"] --> Quarantine["Quarantine Storage Bucket\n(Isolated from Application Server)"]
    Quarantine --> ArchiveCheck["Archive Pre-Verification\n- Max compressed: 50 MB\n- Inspect central directory headers"]
    ArchiveCheck --> BombCheck{"Uncompressed size < 250 MB\nAND File count < 10,000\nAND Ratio < 100:1?"}
    BombCheck -- No --> AbortBomb["REJECT: Archive exceeds safety quotas"]
    BombCheck -- Yes --> SlipCheck{"Zip Slip Check:\nAny entry contains '..'\nor absolute path\nor symlinks/hardlinks?"}
    SlipCheck -- Yes --> AbortSlip["REJECT: Path traversal / symlink detected"]
    SlipCheck -- No --> StaticInspect["Static AST Inspection on Host\n- Framework detection\n- Read-only AST parsing\n- Zero npm install / Zero pip run"]
    StaticInspect --> EphemeralSandbox["Spawn Ephemeral MicroVM (gVisor/Firecracker)\nDefault-Deny Network Egress"]

    subgraph SandboxBoundary ["Ephemeral Micro-Sandbox (Zero Network)"]
        ExtractRAM["Extract to In-Memory RAM Disk"]
        RunBuildTest["Execute sandboxed build/test verification"]
        GenerateDiff["Produce Git Unified Diff (.patch)"]
    end

    EphemeralSandbox --> SandboxBoundary
    SandboxBoundary --> StoreDiff["Store Diff in DB for Human Review & Approval"]
    SandboxBoundary --> Terminate["Destroy MicroVM & Scrub Memory"]
```

### 4.1 Zip Slip Defense
- Every archive entry path is validated before extraction:
  $$\text{target\_path} = \text{os.path.abspath}(\text{os.path.join}(\text{base\_dir}, \text{entry.filename}))$$
- If `target_path` does not start with `base_dir + os.sep`, the archive is rejected as a malicious path traversal attempt.
- Symbolic links and hard links are strictly forbidden and cause immediate archive rejection.

### 4.2 Zip Bomb & Archive Bounds
- **Max Compressed Archive Size**: 50 MB.
- **Max Uncompressed Size**: 250 MB.
- **Max File Count**: 10,000 files.
- **Max Compression Ratio**: Any individual file with a compression ratio $> 100:1$ is rejected.
- **Nested Archives**: Recursive unpacking of archives (ZIP inside ZIP) is strictly disabled.

### 4.3 Zero Host Execution Guarantee
- Untrusted client code is **never compiled, bundled, or executed on the API server**.
- Commands such as `npm install`, `pnpm install`, `yarn`, `pip install`, or `composer` are **strictly forbidden** on the host.
- Static transformations operate via read-only Abstract Syntax Tree (AST) parsers.
- Build and test verifications (Phase 5) run exclusively in isolated, ephemeral microVMs (gVisor / Firecracker) with zero network egress.

---

## 5. Persistence, Multi-Tenancy & Credential Security

### 5.1 Row-Level Security (RLS)
- Supabase PostgreSQL enforces Row-Level Security across all application tables.
- Public scans are identified by a cryptographic `scan_token` (`UUIDv4` or `nanoid(24)`). Anonymous clients can only read the scan matching their token.
- Administrative tables (`resolution_tasks`, `code_patches`, `approvals`, `leads`) require authenticated JWT tokens with `admin` or `engineer` role claims.

### 5.2 Encryption of OAuth Tokens at Rest
- Google Search Console OAuth tokens (`access_token`, `refresh_token`) are encrypted at rest in the database using **AES-256-GCM**.
- Cryptographic keys are supplied via environment secrets (`GSC_ENCRYPTION_KEY`), never stored in database tables or logs.
- Decryption occurs strictly server-side within the Python backend immediately prior to dispatching authenticated Google API requests.
- **Zero Client Exposure**: Decrypted tokens and client secrets are **never** transmitted to the frontend browser.

### 5.3 SQL Injection Prevention
- All database queries are executed via parameterized statements using SQLAlchemy ORM or the Supabase client.
- Raw string concatenation in SQL queries is strictly prohibited.

---

## 6. Rate Limiting & Abuse Prevention

| Tier | Rate Limit Threshold | Target Identifier | Action on Exceeded |
| :--- | :--- | :--- | :--- |
| **Public Instant Scan** | 5 scans per minute / 20 scans per hour | Client IP Address | HTTP 429 Too Many Requests |
| **Target Host Scan** | Max 1 concurrent scan per target root domain | Target FQDN | HTTP 429 "Domain scan already in progress" |
| **Lead Submission** | 3 submissions per 10 minutes | Client IP + Domain | HTTP 429 Rate Limit Exceeded |
| **Admin API** | 120 requests per minute | Admin Session JWT | HTTP 429 Rate Limit Exceeded |
| **GSC API Client** | Quota-aware rate limiter with exponential backoff | GSC Property | Queue request / Return cached status |
