"""PDF generator for Technical SEO Consultation Briefs using fpdf2."""

from typing import Any

from fpdf import FPDF
from fpdf.enums import XPos, YPos

from app.contracts.brief import ServiceBriefDTO


def sanitize_text(text: Any) -> str:
    """Sanitizes text for safe rendering with standard PDF fonts."""
    if text is None:
        return "N/A"
    s = str(text)
    # Replace unicode quotes, dashes, bullets with ASCII equivalents
    replacements = {
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2013": "-",
        "\u2014": "--",
        "\u2022": "*",
        "\u2026": "...",
        "\u00a0": " ",
        "→": "->",
        "✓": "[PASS]",
        "✗": "[FAIL]",
        "⚠️": "[WARN]",
    }
    for orig, rep in replacements.items():
        s = s.replace(orig, rep)
    # Encode to latin-1 safe representation, ignoring non-representable characters
    return s.encode("latin-1", "replace").decode("latin-1")


class ConsultationBriefPDF(FPDF):
    """Custom PDF document styling for Technical SEO Consultation Briefs."""

    def __init__(self, target_url: str, brief_id: str) -> None:
        super().__init__(orientation="P", unit="mm", format="A4")
        self.target_url = sanitize_text(target_url)
        self.brief_id = sanitize_text(brief_id)
        self.set_margins(10, 10, 10)
        self.set_auto_page_break(auto=True, margin=15)

    def header(self) -> None:
        # Top banner
        self.set_fill_color(15, 23, 42)  # slate-900
        self.rect(0, 0, 210, 18, "F")

        self.set_font("Helvetica", "B", 10)
        self.set_text_color(56, 189, 248)  # cyan-400
        self.set_xy(10, 5)
        self.cell(100, 8, "SEO OPTIMIZER | TECHNICAL CONSULTATION BRIEF", align="L")

        self.set_font("Helvetica", "", 8)
        self.set_text_color(148, 163, 184)  # slate-400
        self.set_xy(110, 5)
        self.cell(90, 8, f"ID: {self.brief_id[:16]}...", align="R")

        self.set_y(22)

    def footer(self) -> None:
        self.set_y(-12)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(100, 116, 139)  # slate-500
        self.cell(
            0,
            8,
            f"Confidential Client Advisory Brief  |  Target: {self.target_url[:40]}  |  Page {self.page_no()}/{{nb}}",
            align="C",
        )


def generate_brief_pdf(brief: ServiceBriefDTO) -> bytes:
    """Compiles a complete consultation brief into a PDF byte stream."""
    pdf = ConsultationBriefPDF(
        target_url=brief.client_details.website_url,
        brief_id=brief.brief_id,
    )
    pdf.alias_nb_pages()
    pdf.add_page()

    # 1. Title & Executive Summary Header
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 9, "Technical SEO Consultation Brief", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(
        0,
        5,
        f"Generated: {brief.generated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}  |  Scope: Deterministic Technical & Code Diagnostic",
        new_x=XPos.LMARGIN,
        new_y=YPos.NEXT,
    )
    pdf.ln(3)

    # 2. Key Metrics Overview Grid
    pdf.set_fill_color(248, 250, 252)  # slate-50
    pdf.set_draw_color(226, 232, 240)  # slate-200
    pdf.rect(10, pdf.get_y(), 190, 22, "FD")

    curr_y = pdf.get_y() + 2.5
    # Health Score
    pdf.set_xy(14, curr_y)
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(71, 85, 105)
    pdf.cell(42, 4, "HEALTH SCORE (E3)")
    pdf.set_xy(14, curr_y + 4.5)
    pdf.set_font("Helvetica", "B", 13)
    if brief.audit_scope.overall_health_score is not None:
        pdf.set_text_color(16, 185, 129)  # emerald-500
        score_val = f"{brief.audit_scope.overall_health_score:.1f}/100"
    else:
        pdf.set_text_color(100, 116, 139)
        score_val = "UNMEASURED"
    pdf.cell(42, 7, score_val)

    # Completeness
    pdf.set_xy(60, curr_y)
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(71, 85, 105)
    pdf.cell(42, 4, "COMPLETENESS (E5)")
    pdf.set_xy(60, curr_y + 4.5)
    pdf.set_font("Helvetica", "B", 13)
    if brief.audit_scope.completeness_score is not None:
        pdf.set_text_color(6, 182, 212)  # cyan-500
        comp_val = f"{brief.audit_scope.completeness_score:.1f}%"
    else:
        pdf.set_text_color(100, 116, 139)
        comp_val = "N/A"
    pdf.cell(42, 7, comp_val)

    # Critical Issues
    pdf.set_xy(106, curr_y)
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(71, 85, 105)
    pdf.cell(42, 4, "CRITICAL/HIGH ISSUES")
    pdf.set_xy(106, curr_y + 4.5)
    pdf.set_font("Helvetica", "B", 13)
    crit_count = len(brief.critical_issues)
    if crit_count > 0:
        pdf.set_text_color(225, 29, 72)  # rose-600
    else:
        pdf.set_text_color(16, 185, 129)
    pdf.cell(42, 7, f"{crit_count} Issues")

    # Client Urgency
    pdf.set_xy(152, curr_y)
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(71, 85, 105)
    pdf.cell(42, 4, "CLIENT URGENCY")
    pdf.set_xy(152, curr_y + 4.5)
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(217, 119, 6)  # amber-600
    pdf.cell(42, 7, sanitize_text(brief.client_details.urgency))

    pdf.set_y(curr_y + 23)

    # 3. Client & Target Information Table
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 6, "1. Client & Target Domain Specifications", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    info_data = [
        ("Client Contact:", brief.client_details.customer_name, "Business Email:", brief.client_details.business_email),
        ("Target Website:", brief.client_details.website_url, "Phone Number:", brief.client_details.phone_number),
        ("Business Vertical:", brief.client_details.business_category, "Target City:", brief.client_details.target_city),
        ("Service Requested:", brief.client_details.requested_service, "Urgency:", brief.client_details.urgency),
    ]

    pdf.set_draw_color(226, 232, 240)
    for row in info_data:
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_text_color(71, 85, 105)
        pdf.cell(32, 5.5, sanitize_text(row[0]), border=1)
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(15, 23, 42)
        pdf.cell(63, 5.5, sanitize_text(row[1]), border=1)

        pdf.set_font("Helvetica", "B", 8)
        pdf.set_text_color(71, 85, 105)
        pdf.cell(32, 5.5, sanitize_text(row[2]), border=1)
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(15, 23, 42)
        pdf.cell(63, 5.5, sanitize_text(row[3]), border=1, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # Problem Description block
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(71, 85, 105)
    pdf.cell(0, 5, "Client Problem Statement:", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(15, 23, 42)
    pdf.multi_cell(0, 4.5, sanitize_text(brief.client_details.problem_description), border=1, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(3)

    # 4. Verified Critical Issues (Section 2)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 6, "2. Verified Critical Findings & Technical Evidence", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    if not brief.critical_issues:
        pdf.set_font("Helvetica", "I", 8)
        pdf.set_text_color(100, 116, 139)
        pdf.cell(0, 5, "No CRITICAL or HIGH severity issues identified in this audit.", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    else:
        for idx, issue in enumerate(brief.critical_issues, 1):
            if pdf.get_y() > 240:
                pdf.add_page()

            # Issue header box
            pdf.set_fill_color(255, 241, 242) if issue.severity == "CRITICAL" else pdf.set_fill_color(255, 247, 237)
            pdf.set_draw_color(253, 164, 175) if issue.severity == "CRITICAL" else pdf.set_draw_color(253, 186, 116)
            pdf.set_font("Helvetica", "B", 8.5)
            pdf.set_text_color(159, 18, 57) if issue.severity == "CRITICAL" else pdf.set_text_color(154, 52, 18)
            pdf.cell(
                0,
                5.5,
                f"[{sanitize_text(issue.severity)}] {idx}. {sanitize_text(issue.title)} ({sanitize_text(issue.rule_id)})",
                border=1,
                fill=True,
                new_x=XPos.LMARGIN,
                new_y=YPos.NEXT,
            )

            pdf.set_font("Helvetica", "", 8)
            pdf.set_text_color(51, 65, 85)
            pdf.multi_cell(0, 4, f"Observed Value: {sanitize_text(issue.observed_value)}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            if issue.raw_snippet:
                pdf.set_font("Courier", "", 7)
                pdf.set_text_color(100, 116, 139)
                pdf.multi_cell(0, 3.5, f"Snippet: {sanitize_text(issue.raw_snippet[:200])}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_font("Helvetica", "I", 8)
            pdf.set_text_color(15, 23, 42)
            pdf.multi_cell(0, 4, f"Guidance: {sanitize_text(issue.remediation_guidance)}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.ln(1.5)

    # 5. Proposed Engineering Solutions & Priorities (Section 3)
    if pdf.get_y() > 230:
        pdf.add_page()

    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 6, "3. Prioritized Engineering Action Plan (Model E21)", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    if not brief.implementation_priorities:
        pdf.set_font("Helvetica", "I", 8)
        pdf.set_text_color(100, 116, 139)
        pdf.cell(0, 5, "No pending resolution tasks generated.", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    else:
        for p_idx, task in enumerate(brief.implementation_priorities[:5], 1):
            if pdf.get_y() > 245:
                pdf.add_page()

            pdf.set_font("Helvetica", "B", 8)
            pdf.set_text_color(15, 23, 42)
            pdf.cell(
                0,
                5,
                f"Step {p_idx}: {sanitize_text(task.title)}  |  RICE Priority: {task.priorityScore:.1f}  |  Action: {sanitize_text(task.actionType.value if hasattr(task.actionType, 'value') else task.actionType)}",
                new_x=XPos.LMARGIN,
                new_y=YPos.NEXT,
            )
            pdf.set_font("Helvetica", "", 8)
            pdf.set_text_color(71, 85, 105)
            pdf.multi_cell(0, 4, f"Proposed Change: {sanitize_text(task.proposedChange)}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.multi_cell(0, 4, f"Rollback: {sanitize_text(task.rollbackInstructions)}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.ln(1)

    # 6. Disclosures & Legal Ranking Non-Guarantee (Section 4)
    if pdf.get_y() > 220:
        pdf.add_page()

    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 5.5, "4. Scope Disclosures & Statutory Non-Guarantee Statement", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_font("Helvetica", "", 7.5)
    pdf.set_text_color(100, 116, 139)
    for disc in brief.unknown_and_unavailable_disclosures:
        pdf.multi_cell(0, 3.5, f"- {sanitize_text(disc)}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.ln(2)
    # Prominent Disclaimer Callout
    pdf.set_fill_color(254, 242, 242)
    pdf.set_draw_color(248, 113, 113)
    pdf.set_font("Helvetica", "B", 7.5)
    pdf.set_text_color(185, 28, 28)
    pdf.multi_cell(
        0,
        4,
        f"STATUTORY DISCLAIMER:\n{sanitize_text(brief.ranking_disclaimer)}",
        border=1,
        fill=True,
        new_x=XPos.LMARGIN,
        new_y=YPos.NEXT,
    )

    return bytes(pdf.output())
