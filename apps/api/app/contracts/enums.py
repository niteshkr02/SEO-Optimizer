"""Canonical enumeration types for SEO Optimizer domain."""

from enum import Enum


class RuleState(str, Enum):
    """The 5-state audit rule outcome model."""

    PASS = "PASS"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"
    NOT_TESTED = "NOT_TESTED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class IssueSeverity(str, Enum):
    """Impact severity rating for audit findings."""

    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


class RuleCategory(str, Enum):
    """Taxonomic category of an audit rule."""

    CRAWLABILITY = "CRAWLABILITY"
    INDEXABILITY = "INDEXABILITY"
    DOCUMENT = "DOCUMENT"
    CONTENT = "CONTENT"
    STRUCTURED = "STRUCTURED"
    SECURITY = "SECURITY"


class ProvenanceCategory(str, Enum):
    """Data provenance classification taxonomy."""

    DIRECT_OBSERVATION = "DIRECT_OBSERVATION"
    EXTERNAL_MEASUREMENT = "EXTERNAL_MEASUREMENT"
    LICENSED_ESTIMATE = "LICENSED_ESTIMATE"
    INTERNAL_COMPOSITE = "INTERNAL_COMPOSITE"
    USER_INPUT = "USER_INPUT"
    AI_ASSISTED_DRAFT = "AI_ASSISTED_DRAFT"


class ScanStatus(str, Enum):
    """Operational lifecycle state of a scan run."""

    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class LeadStatus(str, Enum):
    """Lifecycle stages for consulting service leads."""

    NEW = "NEW"
    CONTACTED = "CONTACTED"
    SCOPED = "SCOPED"
    CONTRACTED = "CONTRACTED"
    CLOSED = "CLOSED"


class LeadUrgency(str, Enum):
    """Urgency level specified by client inquiry."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class RequestedService(str, Enum):
    """SEO consulting service categories."""

    TECHNICAL_AUDIT = "TECHNICAL_AUDIT"
    PERFORMANCE_OPTIMIZATION = "PERFORMANCE_OPTIMIZATION"
    MIGRATION_ARCHITECTURE = "MIGRATION_ARCHITECTURE"
    COMPETITOR_GAP_RESOLUTION = "COMPETITOR_GAP_RESOLUTION"
    FULL_CODE_REMEDIATION = "FULL_CODE_REMEDIATION"
    OTHER = "OTHER"

