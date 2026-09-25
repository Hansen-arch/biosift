"""
BioSift Icon System
───────────────────
Single-stroke, geometric SVG icons (Lucide via iconify CDN data-URI, then
inlined static paths for zero-network rendering). Professional
monochrome line icons — no emoji anywhere in the product.

Usage:
    from utils.icons import icon
    st.markdown(icon("microscope", 18), unsafe_allow_html=True)
    # or inside card HTML:
    f'<span class="ic">{icon("dna", 20)}</span>'
"""

SVG = {
    "home": '<path d="M3 10.5 12 3l9 7.5"/><path d="M5 9.5V21h14V9.5"/>',
    "microscope": (
        '<path d="M6 18h8"/><path d="M3 22h18"/>'
        '<path d="M14 22a7 7 0 1 0 0-14h-1"/><path d="M9 14h2"/>'
        '<path d="M9 12a2 2 0 0 1-2-2V6a2 2 0 0 1 4 0v4a2 2 0 0 1-2 2Z"/>'
    ),
    "scale": (
        '<path d="M12 3v18"/><path d="M5 7h14"/>'
        '<path d="m5 7-3 6h6l-3-6Z"/><path d="m19 7-3 6h6l-3-6Z"/>'
    ),
    "building": (
        '<path d="M6 22V4a1 1 0 0 1 1-1h10a1 1 0 0 1 1 1v18"/>'
        '<path d="M3 22h18"/><path d="M10 6h4M10 10h4M10 14h4M10 18h4"/>'
    ),
    "ruler": (
        '<path d="M21.3 8.7 8.7 21.3a1 1 0 0 1-1.4 0L2.7 16.7a1 1 0 0 1 0-1.4L15.3 2.7a1 1 0 0 1 1.4 0l4.6 4.6a1 1 0 0 1 0 1.4Z"/>'
        '<path d="m7.5 10.5 2 2"/><path d="m10.5 7.5 2 2"/>'
        '<path d="m13.5 4.5 2 2"/>'
    ),
    "dna": (
        '<path d="M4 2c0 4 3.6 4.9 6 6.5 2.6 1.7 4 3.5 4 6.5"/>'
        '<path d="M20 2c0 4-3.6 4.9-6 6.5C11.4 10.2 10 12 10 15"/>'
        '<path d="M20 22c0-4-3.6-4.9-6-6.5-2.6-1.7-4-3.5-4-6.5"/>'
        '<path d="M4 22c0-4 3.6-4.9 6-6.5 2.6-1.7 4-3.5 4-6.5"/>'
    ),
    "link": (
        '<path d="M10 13a5 5 0 0 0 7.5.5l3-3a5 5 0 0 0-7-7l-1.7 1.7"/>'
        '<path d="M14 11a5 5 0 0 0-7.5-.5l-3 3a5 5 0 0 0 7 7l1.7-1.7"/>'
    ),
    "layers": (
        '<path d="m12 2 9 4.9-9 4.9-9-4.9L12 2Z"/>'
        '<path d="m3 11.9 9 4.9 9-4.9"/><path d="m3 16.9 9 4.9 9-4.9"/>'
    ),
    "pulse": (
        '<path d="M22 12h-4l-3 9L9 3l-3 9H2"/>'
    ),
    "map": (
        '<path d="M9 3 3 5v16l6-2 6 2 6-2V3l-6 2-6-2Z"/>'
        '<path d="M9 3v16"/><path d="M15 5v16"/>'
    ),
    "shield": (
        '<path d="M12 22s8-3.5 8-10V5l-8-3-8 3v7c0 6.5 8 10 8 10Z"/>'
        '<path d="m9 11.5 2 2 4-4.5"/>'
    ),
    "download": (
        '<path d="M12 3v12"/><path d="m7 10 5 5 5-5"/>'
        '<path d="M4 21h16"/>'
    ),
    "database": (
        '<ellipse cx="12" cy="5" rx="9" ry="3"/>'
        '<path d="M3 5v14c0 1.7 4 3 9 3s9-1.3 9-3V5"/>'
        '<path d="M3 12c0 1.7 4 3 9 3s9-1.3 9-3"/>'
    ),
    "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 3"/>',
    "chart": (
        '<path d="M3 3v18h18"/><path d="M8 17V9"/><path d="M13 17V5"/>'
        '<path d="M18 17v-6"/>'
    ),
    "target": (
        '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/>'
        '<circle cx="12" cy="12" r="1"/>'
    ),
    "arrow": '<path d="M5 12h14"/><path d="m13 6 6 6-6 6"/>',
    "check": '<path d="M20 6 9 17l-5-5"/>',
    "warn": (
        '<path d="M12 3 2 20h20L12 3Z"/><path d="M12 10v4"/>'
        '<path d="M12 17.5h.01"/>'
    ),
    "info": (
        '<circle cx="12" cy="12" r="9"/><path d="M12 11v5"/>'
        '<path d="M12 8h.01"/>'
    ),
    "book": (
        '<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20V4H6.5A2.5 2.5 0 0 0 4 6.5v13Z"/>'
        '<path d="M4 19.5A2.5 2.5 0 0 0 6.5 22H20v-5"/>'
    ),
    "globe": (
        '<circle cx="12" cy="12" r="9"/>'
        '<path d="M3 12h18"/><path d="M12 3a15 15 0 0 1 0 18 15 15 0 0 1 0-18Z"/>'
    ),
    "spark": (
        '<path d="M12 3v3M12 18v3M3 12h3M18 12h3M5.6 5.6l2.1 2.1M16.3 16.3l2.1 2.1M5.6 18.4l2.1-2.1M16.3 7.7l2.1-2.1"/>'
    ),
}


def icon(name: str, size: int = 18, stroke: float = 1.8) -> str:
    """Return inline SVG markup for the given icon name."""
    path = SVG.get(name, SVG["info"])
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" '
        f'fill="none" stroke="currentColor" stroke-width="{stroke}" '
        f'stroke-linecap="round" stroke-linejoin="round" '
        f'style="vertical-align:-0.15em">{path}</svg>'
    )
