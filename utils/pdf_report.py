"""
PDF Quality Report
──────────────────
A polished, branded PDF summary of any BioSift analysis — designed to be
attached to grant applications, theses and data management plans.
"""

import datetime
from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)

from utils.bdq import bdq_meta, citation_note
from utils.theme import C


def _hex(h):
    return colors.HexColor(h)


def _title_fs():
    return ParagraphStyle(
        "T", fontName="Helvetica-Bold", fontSize=22, leading=26,
        textColor=_hex(C["text"]), spaceAfter=2,
    )


def build_pdf_report(
    species, score, df, clean_df, summary, benchmark=None,
    reliability=None, completeness=None, species_info=None,
    filters=None,
):
    """Return (bytes, None) or (None, error)."""
    try:
        buf = BytesIO()
        doc = SimpleDocTemplate(
            buf, pagesize=A4,
            leftMargin=1.8 * cm, rightMargin=1.8 * cm,
            topMargin=1.6 * cm, bottomMargin=1.6 * cm,
            title=f"BioSift Data Quality Report — {species}",
            author="BioSift",
        )
        el = []

        accent = _hex(C["accent"])
        dim = _hex(C["text_dim"])
        faint = _hex(C["text_faint"])

        # palette for tables
        line = _hex(C["line"])
        card = _hex(C["card"])

        # ── header ─────────────────────────────────────────
        el.append(Paragraph("BioSift", _title_fs()))
        el.append(Paragraph(
            "Biodiversity Data Quality Report · aligned with TDWG BDQ",
            ParagraphStyle(
                "S", fontName="Helvetica", fontSize=9.5, leading=12,
                textColor=dim, spaceAfter=8,
            ),
        ))
        el.append(HRFlowable(width="100%", thickness=0.8, color=line))

        # ── score banner ───────────────────────────────────
        cls = "Good" if score >= 80 else ("Fair" if score >= 50 else "Poor")
        score_color = accent if score >= 80 else (
            _hex(C["amber"]) if score >= 50 else _hex(C["red"])
        )
        el.append(Spacer(1, 10))
        score_tbl = Table(
            [[
                Paragraph(
                    f"<font size=26 color=#{score_color.hexval()[2:]}><b>"
                    f"{score}%</b></font>",
                    ParagraphStyle("sv", fontName="Helvetica-Bold",
                                   fontSize=26, leading=30),
                ),
                Paragraph(
                    f"<font size=15><b>{species}</b></font><br/>"
                    f"<font size=9 color=#{dim.hexval()[2:]}>"
                    f"{len(df):,} records analysed · {len(clean_df):,} clean · "
                    f"{cls} data health</font>",
                    ParagraphStyle("sd", fontName="Helvetica", fontSize=10,
                                   leading=14),
                ),
            ]],
            colWidths=[3.2 * cm, None],
        )
        score_tbl.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
        ]))
        el.append(score_tbl)
        el.append(Spacer(1, 6))

        # ── meta block ─────────────────────────────────────
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M UTC")
        meta_rows = [
            ["Generated", now],
            ["GBIF total matching", f"{(filters or {}).get('gbif_total', 0):,}"],
            ["Year range", (filters or {}).get("year_range", "all years")],
            ["Basis of record", (filters or {}).get("basis", "All")],
            ["Standard", "TDWG BDQ TG2 core tests · Darwin Core"],
        ]
        meta_tbl = Table(meta_rows, colWidths=[4.2 * cm, None])
        meta_tbl.setStyle(TableStyle([
            ("FONT", (0, 0), (0, -1), "Helvetica-Bold", 8.5),
            ("FONT", (1, 0), (1, -1), "Helvetica", 8.5),
            ("TEXTCOLOR", (0, 0), (0, -1), faint),
            ("TEXTCOLOR", (1, 0), (1, -1), dim),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ]))
        el.append(meta_tbl)
        parameters = Spacer(1, 10)
        el.append(parameters)

        # ── quality checks table ───────────────────────────
        el.append(Paragraph(
            "Quality checks (TDWG BDQ aligned)",
            ParagraphStyle("H", fontName="Helvetica-Bold", fontSize=12,
                           leading=15, textColor=_hex(C["text"]),
                           spaceAfter=4),
        ))
        check_rows = [["Check", "BDQ test", "Flagged", "%"]]
        for k, stats in summary.items():
            if k in ("any_flag", "has_issues"):
                continue
            name = bdq_meta(k)[1]
            bdq = bdq_meta(k)[0]
            check_rows.append([
                name, bdq,
                f"{stats['count']:,}",
                f"{stats['percent']}%",
            ])
        checks_tbl = Table(check_rows, colWidths=[4.6 * cm, 8.2 * cm, 2.2 * cm, 1.6 * cm], repeatRows=1)
        checks_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), card),
            ("TEXTCOLOR", (0, 0), (-1, 0), faint),
            ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 8),
            ("FONT", (0, 1), (-1, -1), "Helvetica", 7.5),
            ("TEXTCOLOR", (0, 1), (-1, -1), dim),
            ("GRID", (0, 0), (-1, -1), 0.4, line),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        el.append(checks_tbl)
        el.append(Spacer(1, 10))

        # ── benchmark section ──────────────────────────────
        if benchmark:
            el.append(Paragraph(
                "Benchmark vs GBIF-wide population (same filters)",
                ParagraphStyle("H2", fontName="Helvetica-Bold", fontSize=12,
                               leading=15, textColor=_hex(C["text"]),
                               spaceAfter=4),
            ))
            b_rows = [["Metric", "This sample", "GBIF-wide", "Δ"]]
            for b in benchmark:
                b_rows.append([
                    b["label"],
                    f"{b['sample_pct']}%",
                    f"{b['population_pct']}%",
                    f"{b['delta']:+.1f} pp",
                ])
            b_tbl = Table(b_rows, colWidths=[6.8 * cm, 2.9 * cm, 2.9 * cm, 2.2 * cm], repeatRows=1)
            b_tbl.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), card),
                ("TEXTCOLOR", (0, 0), (-1, 0), faint),
                ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 8),
                ("FONT", (0, 1), (-1, -1), "Helvetica", 8),
                ("TEXTCOLOR", (0, 1), (-1, -1), dim),
                ("GRID", (0, 0), (-1, -1), 0.4, line),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]))
            el.append(b_tbl)
            el.append(Spacer(1, 10))

        # ── reliability / completeness strip ───────────────
        strips = []
        if reliability is not None:
            strips.append([
                "Mean reliability",
                f"{round(float(reliability.mean()), 1)}/100",
            ])
        if completeness:
            strips.append([
                "Mean completeness",
                f"{completeness.get('avg_score')}%",
            ])
        if strips:
            s_tbl = Table([["Metric", "Value"]] + strips,
                          colWidths=[6.8 * cm, 2.9 * cm])
            s_tbl.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), card),
                ("TEXTCOLOR", (0, 0), (-1, 0), faint),
                ("FONT", (0, 0), (-
1, 0), "Helvetica-Bold", 8),
                ("FONT", (0, 1), (-1, -1), "Helvetica", 8),
                ("TEXTCOLOR", (0, 1), (-1, -1), dim),
                ("GRID", (0, 0), (-1, -1), 0.4, line),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]))
            el.append(s_tbl)
            el.append(Spacer(1, 10))

        # ── methods paragraph ──────────────────────────────
        from utils.reliability import generate_methods_text
        methods = generate_methods_text(
            species, df, clean_df, summary, score
        )
        el.append(Paragraph(
            "Methods paragraph",
            ParagraphStyle("H3", fontName="Helvetica-Bold", fontSize=12,
                           leading=15, textColor=_hex(C["text"]),
                           spaceAfter=4),
        ))
        el.append(Paragraph(methods, ParagraphStyle(
            "M", fontName="Helvetica", fontSize=8.5, leading=12,
            textColor=dim,
        )))

        # ── footer note ────────────────────────────────────
        el.append(Spacer(1, 12))
        el.append(HRFlowable(width="100%", thickness=0.8, color=line))
        el.append(Paragraph(
            "Data: GBIF.org (CC-BY). Quality assertions follow the TDWG BDQ "
            "TG2 core test vocabulary. Generated by BioSift — "
            "biosift-gbif.streamlit.app",
            ParagraphStyle("F", fontName="Helvetica", fontSize=7.5,
                           leading=10, textColor=faint),
        ))

        doc.build(el)
        return buf.getvalue(), None

    except Exception as e:
        return None, str(e)
