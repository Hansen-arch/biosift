import pandas as pd
import numpy as np
import plotly.graph_objects as go


def _count_decimals(val):
    """Float-noise safe decimal counter — local copy."""
    if pd.isna(val):
        return 0
    try:
        rounded = round(float(val), 10)
        text = f"{rounded:.10f}".rstrip("0").rstrip(".")
        if "." in text:
            return len(text.split(".")[-1])
        return 0
    except Exception:
        return 0


def get_dataset_quality_breakdown(df, flags):
    """
    Break down quality metrics per contributing GBIF dataset.

    Groups records by datasetName, computes per-dataset:
      - record count
      - health score
      - duplicate %
      - missing coord %
      - low precision %
      - country mismatch %
      - avg coordinate precision tier
      - overall quality grade (A–F)

    Returns (summary_df, chart_fig) or (None, None) on failure.
    """
    try:
        if "datasetName" not in df.columns:
            return None, None

        combined = df.copy()
        combined["_any_flag"] = flags["any_flag"].values
        combined["_duplicate"] = flags.get(
            "duplicate",
            pd.Series(False, index=df.index)
        ).values
        combined["_missing_coords"] = flags.get(
            "missing_coords",
            pd.Series(False, index=df.index)
        ).values
        combined["_low_precision"] = flags.get(
            "low_precision",
            pd.Series(False, index=df.index)
        ).values
        combined["_country_mismatch"] = flags.get(
            "country_mismatch",
            pd.Series(False, index=df.index)
        ).values

        def precision_tier(val):
            d = _count_decimals(val)
            if d >= 5 : return 5
            elif d == 4: return 4
            elif d == 3: return 3
            elif d == 2: return 2
            else        : return 1

        if "decimalLatitude" in combined.columns:
            combined["_prec_tier"] = combined[
                "decimalLatitude"
            ].apply(precision_tier)
        else:
            combined["_prec_tier"] = 1

        combined["datasetName"] = (
            combined["datasetName"]
            .fillna("Unknown Dataset")
            .replace("", "Unknown Dataset")
        )

        rows = []
        for ds_name, grp in combined.groupby("datasetName"):
            n      = len(grp)
            clean  = int((~grp["_any_flag"]).sum())
            health = round(clean / n * 100, 1)

            dup_pct  = round(grp["_duplicate"].mean()        * 100, 1)
            mc_pct   = round(grp["_missing_coords"].mean()   * 100, 1)
            lp_pct   = round(grp["_low_precision"].mean()    * 100, 1)
            cm_pct   = round(grp["_country_mismatch"].mean() * 100, 1)
            avg_prec = round(grp["_prec_tier"].mean(), 1)

            if   health >= 90: grade = "A"
            elif health >= 75: grade = "B"
            elif health >= 60: grade = "C"
            elif health >= 40: grade = "D"
            else             : grade = "F"

            rows.append({
                "Dataset"           : (
                    ds_name[:55] + "…"
                    if len(ds_name) > 55
                    else ds_name
                ),
                "Records"           : n,
                "Health Score"      : f"{health}%",
                "Grade"             : grade,
                "Duplicates"        : f"{dup_pct}%",
                "Missing Coords"    : f"{mc_pct}%",
                "Low Precision"     : f"{lp_pct}%",
                "Country Mismatch"  : f"{cm_pct}%",
                "Avg Precision Tier": avg_prec,
                "_health_val"       : health,
                "_n"                : n,
            })

        if not rows:
            return None, None

        summary_df = pd.DataFrame(rows).sort_values(
            "_health_val", ascending=False
        )

        # chart: top 15 datasets by record count
        chart_df = summary_df.nlargest(15, "_n").sort_values(
            "_health_val", ascending=True
        )

        colors = [
            "#3FB950" if h >= 80
            else "#E3B341" if h >= 50
            else "#F85149"
            for h in chart_df["_health_val"]
        ]

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=chart_df["_health_val"],
            y=chart_df["Dataset"],
            orientation="h",
            marker_color=colors,
            text=[
                f"{h}%  ({n:,} records)"
                for h, n in zip(
                    chart_df["_health_val"],
                    chart_df["_n"]
                )
            ],
            textposition="outside",
            textfont=dict(color="#8B949E", size=11),
            hovertemplate=(
                "<b>%{y}</b><br>"
                "Health: %{x:.1f}%<extra></extra>"
            )
        ))

        fig.update_layout(
            title="Dataset Health Scores (top 15 by record count)",
            xaxis_title="Health Score (%)",
            xaxis=dict(range=[0, 115], gridcolor="#21262D"),
            yaxis_title=None,
            plot_bgcolor="#161B22",
            paper_bgcolor="#161B22",
            font_color="#F0F6FC",
            margin=dict(l=10, r=120, t=50, b=40),
            height=max(350, len(chart_df) * 30 + 80)
        )

        display_df = summary_df.drop(columns=["_health_val", "_n"])

        return display_df, fig

    except Exception:
        return None, None