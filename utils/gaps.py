import folium
import pandas as pd
import numpy as np


def build_gap_map(df):
    try:
        clean = df[
            ["decimalLatitude", "decimalLongitude"]
        ].dropna()

        if clean.empty:
            return None

        lat_center = clean["decimalLatitude"].mean()
        lon_center = clean["decimalLongitude"].mean()

        m = folium.Map(
            location=[lat_center, lon_center],
            zoom_start=3,
            tiles="CartoDB dark_matter"
        )

        grid_size = 10
        lat_bins  = np.arange(-90,  91, grid_size)
        lon_bins  = np.arange(-180, 181, grid_size)

        clean = clean.copy()
        clean["lat_bin"] = pd.cut(
            clean["decimalLatitude"],
            bins=lat_bins,
            labels=lat_bins[:-1]
        )
        clean["lon_bin"] = pd.cut(
            clean["decimalLongitude"],
            bins=lon_bins,
            labels=lon_bins[:-1]
        )

        cell_counts = clean.groupby(
            ["lat_bin", "lon_bin"]
        ).size().reset_index(name="count")

        max_count = (
            cell_counts["count"].max()
            if not cell_counts.empty else 1
        )

        for _, row in cell_counts.iterrows():
            try:
                lat_s = float(row["lat_bin"])
                lon_w = float(row["lon_bin"])
                lat_n = lat_s + grid_size
                lon_e = lon_w + grid_size
                count = row["count"]

                ratio   = count / max_count
                color   = _gap_color(ratio)
                opacity = 0.3 + ratio * 0.5

                folium.Rectangle(
                    bounds=[[lat_s, lon_w], [lat_n, lon_e]],
                    color="#21262D",
                    weight=0.5,
                    fill=True,
                    fill_color=color,
                    fill_opacity=opacity,
                    popup=folium.Popup(
                        f"<b>{count} records</b><br>"
                        f"Lat: {lat_s}° to {lat_n}°<br>"
                        f"Lon: {lon_w}° to {lon_e}°",
                        max_width=150
                    )
                ).add_to(m)

            except Exception:
                continue

        return m

    except Exception:
        return None


def _gap_color(ratio):
    if ratio >= 0.75:
        return "#3FB950"
    elif ratio >= 0.4:
        return "#E3B341"
    elif ratio >= 0.1:
        return "#F0883E"
    else:
        return "#F85149"


def get_gap_stats(df):
    try:
        clean = df[
            ["decimalLatitude", "decimalLongitude", "country"]
        ].dropna(
            subset=["decimalLatitude", "decimalLongitude"]
        )

        total_cells = (180 // 10) * (360 // 10)

        lat_bins = np.arange(-90,  91, 10)
        lon_bins = np.arange(-180, 181, 10)

        clean = clean.copy()
        clean["lat_bin"] = pd.cut(
            clean["decimalLatitude"],
            bins=lat_bins,
            labels=lat_bins[:-1]
        )
        clean["lon_bin"] = pd.cut(
            clean["decimalLongitude"],
            bins=lon_bins,
            labels=lon_bins[:-1]
        )

        cells_with_data = clean.groupby(
            ["lat_bin", "lon_bin"]
        ).size().reset_index()

        covered = len(cells_with_data)
        gap_pct = round((1 - covered / total_cells) * 100, 1)
        cov_pct = round(covered / total_cells * 100, 1)

        return {
            "total_cells": total_cells,
            "covered"    : covered,
            "gap_pct"    : gap_pct,
            "cov_pct"    : cov_pct,
            "countries"  : clean["country"].nunique()
                           if "country" in clean.columns else 0
        }

    except Exception:
        return None


def get_gap_alerts(df):
    """
    Analyse spatial coverage and return actionable alerts.

    Alerts cover:
      - Heavily concentrated records (single cell dominance)
      - Sparse isolated cells (potential georef errors)
      - Continental coverage gaps
      - Hemisphere imbalance

    Returns list of alert dicts:
      { type: warning|info|success, title: str, message: str }
    """
    try:
        alerts = []

        clean = df[
            ["decimalLatitude", "decimalLongitude"]
        ].dropna()

        if len(clean) < 5:
            return []

        lat_bins = np.arange(-90,  91, 10)
        lon_bins = np.arange(-180, 181, 10)

        c = clean.copy()
        c["lat_bin"] = pd.cut(
            c["decimalLatitude"],
            bins=lat_bins,
            labels=lat_bins[:-1]
        )
        c["lon_bin"] = pd.cut(
            c["decimalLongitude"],
            bins=lon_bins,
            labels=lon_bins[:-1]
        )

        cell_counts = c.groupby(
            ["lat_bin", "lon_bin"]
        ).size().reset_index(name="count")

        total      = len(clean)
        n_cells    = len(cell_counts)
        max_count  = cell_counts["count"].max()
        max_pct    = round(max_count / total * 100, 1)

        # ── alert: single cell dominance ─────────────────
        if max_pct > 60:
            top_cell = cell_counts.loc[
                cell_counts["count"].idxmax()
            ]
            alerts.append({
                "type"   : "warning",
                "title"  : "Spatial Concentration Alert",
                "message": (
                    f"{max_pct}% of all records fall within a single "
                    f"10° grid cell "
                    f"(lat {float(top_cell['lat_bin']):.0f}° to "
                    f"{float(top_cell['lat_bin'])+10:.0f}°, "
                    f"lon {float(top_cell['lon_bin']):.0f}° to "
                    f"{float(top_cell['lon_bin'])+10:.0f}°). "
                    f"Distribution data may be biased toward "
                    f"well-sampled regions."
                )
            })

        # ── alert: isolated singleton cells ───────────────
        singletons = int((cell_counts["count"] == 1).sum())
        if singletons > 0 and singletons / n_cells > 0.3:
            alerts.append({
                "type"   : "warning",
                "title"  : "Isolated Records Detected",
                "message": (
                    f"{singletons} grid cells contain only a single "
                    f"record. Isolated points may indicate "
                    f"georeferencing errors or vagrant observations "
                    f"outside the core range. Review with DBSCAN "
                    f"outlier detection."
                )
            })

        # ── alert: hemisphere imbalance ───────────────────
        n_north = int((clean["decimalLatitude"] >= 0).sum())
        n_south = int((clean["decimalLatitude"] <  0).sum())

        if total > 20:
            north_pct = round(n_north / total * 100, 1)
            south_pct = round(n_south / total * 100, 1)
            if north_pct > 95:
                alerts.append({
                    "type"   : "info",
                    "title"  : "Northern Hemisphere Bias",
                    "message": (
                        f"{north_pct}% of records are from the northern "
                        f"hemisphere. Southern hemisphere distribution "
                        f"may be underrepresented in GBIF for this "
                        f"species."
                    )
                })
            elif south_pct > 95:
                alerts.append({
                    "type"   : "info",
                    "title"  : "Southern Hemisphere Bias",
                    "message": (
                        f"{south_pct}% of records are from the southern "
                        f"hemisphere."
                    )
                })

        # ── alert: low overall grid coverage ─────────────
        if n_cells == 1:
            alerts.append({
                "type"   : "warning",
                "title"  : "Extremely Limited Spatial Coverage",
                "message": (
                    "All records fall within a single 10° grid cell. "
                    "This dataset cannot support range-wide analyses."
                )
            })
        elif n_cells <= 3:
            alerts.append({
                "type"   : "warning",
                "title"  : "Very Limited Spatial Coverage",
                "message": (
                    f"Records span only {n_cells} grid cells. "
                    f"Distribution models will have very low "
                    f"geographic resolution."
                )
            })

        # ── alert: good coverage ──────────────────────────
        if n_cells >= 10 and max_pct < 40:
            alerts.append({
                "type"   : "success",
                "title"  : "Good Spatial Coverage",
                "message": (
                    f"Records span {n_cells} grid cells with no "
                    f"single cell dominating more than {max_pct}% "
                    f"of records. Spatial coverage is suitable for "
                    f"distribution modelling."
                )
            })

        return alerts

    except Exception:
        return []