"""Synthetic HTML fixtures for testing deterministic SEO audit rules."""

VALID_PAGE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>Enterprise SEO Platform — Deterministic Audits & Remediation</title>
    <meta name="description" content="Discover technical search engine bottlenecks with 100% deterministic, evidence-backed proof and automated source-code remediation.">
    <link rel="canonical" href="https://example.com/platform">
    <meta name="robots" content="index, follow">
    <script type="application/ld+json">
    {
        "@context": "https://schema.org",
        "@type": "SoftwareApplication",
        "name": "SEO Optimizer",
        "operatingSystem": "All",
        "applicationCategory": "BusinessApplication"
    }
    </script>
</head>
<body>
    <header>
        <nav><a href="/about">About Us</a></nav>
    </header>
    <main>
        <h1>Deterministic SEO Diagnosis Platform</h1>
        <p>Welcome to our verifiable search optimization platform.</p>
        <img src="/assets/hero.webp" alt="SEO dashboard screenshot" width="1200" height="630">
        <h2>Key Capabilities</h2>
        <p>Comprehensive rule evaluations with full evidence.</p>
        <img src="/assets/decorative-shape.svg" alt="" role="presentation">
        <h3>SSRF Defense</h3>
        <p>Socket pinning and strict CIDR blocklists.</p>
    </main>
</body>
</html>
"""

NOINDEX_PAGE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <title>Staging Environment — Do Not Index</title>
    <meta name="robots" content="noindex, nofollow">
</head>
<body>
    <h1>Staging Portal</h1>
</body>
</html>
"""

MISSING_TAGS_HTML = """<!DOCTYPE html>
<html>
<head>
</head>
<body>
    <p>Page without headings, title, description, or canonical tag.</p>
    <img src="/banner.png">
    <script type="application/ld+json">
    {
        "broken": json missing closing brace
    </script>
</body>
</html>
"""

MULTIPLE_H1_HTML = """<!DOCTYPE html>
<html>
<head>
    <title>Multiple H1 Document Page</title>
</head>
<body>
    <h1>First Primary Heading</h1>
    <h1>Second Primary Heading</h1>
    <h4>Skipped Level Heading (H1 to H4)</h4>
    <h1>Third Primary Heading</h1>
</body>
</html>
"""

DECORATIVE_IMAGES_HTML = """<!DOCTYPE html>
<html>
<head><title>Image Test Page</title></head>
<body>
    <h1>Image Tests</h1>
    <img src="/img1.jpg" alt="Informative visual graph" width="400" height="300">
    <img src="/img2.jpg" alt="" role="presentation">
    <img src="/img3.svg" aria-hidden="true">
    <img src="/img4.jpg" alt="   "> <!-- Missing meaningful alt -->
</body>
</html>
"""

SPA_CONTAINER_HTML = """<!DOCTYPE html>
<html>
<head><title>SPA Client Application</title></head>
<body>
    <div id="root"></div>
    <script src="/bundle.js"></script>
</body>
</html>
"""

