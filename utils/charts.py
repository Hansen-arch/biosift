import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np


def chart_records_per_year(df):
    try:
        df_year = df[df["year"].notna()].copy()
        if df_year.empty:
            return None

        df_year["year"] = df_year["year"].astype(int)
        year_counts = (
            df_year.groupby("year").size().reset_index(name="count")
        )

        fig = go.Figure()

        fig.add_trace(go.Bar(
            x=year_counts["year"],
            y=year_counts["count"],
            name="Records",
            marker_color="#3FB950",
            opacity=0.8
        ))

        if len(year_counts) >= 3:
            z = np.polyfit(year_counts["year"], year_counts["count"], 1)
            p = np.poly1d(z)
            fig.add_trace(go.Scatter(
                x=year_counts["year"],
                y=p(year_counts["year"]),
                mode="lines",
                name="Trend",
                line=dict(color="#F0883E", width=2, dash="dash")
            ))

        fig.update_layout(
            title="Records per Year",
            xaxis_title="Year",
            yaxis_title="Records",
            plot_bgcolor="#161B22",
            paper_bgcolor="#161B22",
            font_color="#F0F6FC",
            legend=dict(bgcolor="#1C2128", bordercolor="#21262D")
        )
        return fig

    except Exception:
        return None


def chart_records_per_month(df):
    try:
        df_month = df[df["month"].notna()].copy()
        if df_month.empty:
            return None

        df_month["month"] = df_month["month"].astype(int)
        month_counts = (
            df_month.groupby("month").size().reset_index(name="count")
        )

        month_names = {
            1:"Jan",  2:"Feb",  3:"Mar",  4:"Apr",
            5:"May",  6:"Jun",  7:"Jul",  8:"Aug",
            9:"Sep", 10:"Oct", 11:"Nov", 12:"Dec"
        }
        month_counts["month_name"] = (
            month_counts["month"].map(month_names)
        )

        fig = px.bar(
            month_counts,
            x="month_name",
            y="count",
            title="Records per Month",
            labels={"month_name": "Month", "count": "Records"},
            color_discrete_sequence=["#58A6FF"],
            category_orders={"month_name": list(month_names.values())}
        )
        fig.update_layout(
            plot_bgcolor="#161B22",
            paper_bgcolor="#161B22",
            font_color="#F0F6FC"
        )
        return fig

    except Exception:
        return None


def chart_basis_of_record(df):
    try:
        if "basisOfRecord" not in df.columns:
            return None

        basis_counts = df["basisOfRecord"].value_counts().reset_index()
        basis_counts.columns = ["basis", "count"]

        fig = px.pie(
            basis_counts,
            names="basis",
            values="count",
            title="Basis of Record",
            color_discrete_sequence=px.colors.sequential.Greens_r
        )
        fig.update_layout(
            plot_bgcolor="#161B22",
            paper_bgcolor="#161B22",
            font_color="#F0F6FC"
        )
        return fig

    except Exception:
        return None


def chart_top_countries(df):
    try:
        if "country" not in df.columns:
            return None

        country_counts = (
            df["country"].value_counts().head(10).reset_index()
        )
        country_counts.columns = ["country", "count"]

        fig = px.bar(
            country_counts,
            x="count",
            y="country",
            orientation="h",
            title="Top 10 Countries",
            labels={"country": "Country", "count": "Records"},
            color_discrete_sequence=["#BC8CFF"]
        )
        fig.update_layout(
            yaxis={"categoryorder": "total ascending"},
            plot_bgcolor="#161B22",
            paper_bgcolor="#161B22",
            font_color="#F0F6FC"
        )
        return fig

    except Exception:
        return None


def chart_country_density(df):
    """
    Observation Density Chart — country contribution as % of total.
    Shows top 15 countries as a horizontal bar chart with
    percentage labels. Better than raw counts for comparing
    relative contributions.
    """
    try:
        if "country" not in df.columns:
            return None

        total  = len(df)
        counts = df["country"].value_counts().head(15)

        if counts.empty:
            return None

        pct    = (counts / total * 100).round(1)
        chart_df = pd.DataFrame({
            "country": counts.index,
            "records": counts.values,
            "pct"    : pct.values
        })

        # color gradient from most to least records
        chart_df = chart_df.sort_values("pct", ascending=True)

        fig = go.Figure()

        fig.add_trace(go.Bar(
            x=chart_df["pct"],
            y=chart_df["country"],
            orientation="h",
            marker=dict(
                color=chart_df["pct"],
                colorscale=[
                    [0.0, "#1F4D2F"],
                    [0.5, "#2EA043"],
                    [1.0, "#3FB950"]
                ],
                showscale=False
            ),
            text=[
                f"{p}%  ({r:,} records)"
                for p, r in zip(chart_df["pct"], chart_df["records"])
            ],
            textposition="outside",
            textfont=dict(color="#8B949E", size=11),
            hovertemplate=(
                "<b>%{y}</b><br>"
                "Records: %{customdata:,}<br>"
                "Share: %{x:.1f}%<extra></extra>"
            ),
            customdata=chart_df["records"]
        ))

        fig.update_layout(
            title="Observation Density by Country (% of Total)",
            xaxis_title="% of Total Records",
            yaxis_title=None,
            plot_bgcolor="#161B22",
            paper_bgcolor="#161B22",
            font_color="#F0F6FC",
            xaxis=dict(
                range=[0, chart_df["pct"].max() * 1.3],
                gridcolor="#21262D"
            ),
            margin=dict(l=10, r=120, t=50, b=40),
            height=max(350, len(chart_df) * 28 + 80)
        )

        return fig

    except Exception:
        return None


def chart_decade_breakdown(df):
    try:
        df_year = df[df["year"].notna()].copy()
        if df_year.empty:
            return None

        df_year["year"]   = df_year["year"].astype(int)
        df_year["decade"] = (
            (df_year["year"] // 10 * 10).astype(str) + "s"
        )
        decade_counts = (
            df_year.groupby("decade").size().reset_index(name="count")
        )
        decade_counts = decade_counts.sort_values("decade")

        fig = px.bar(
            decade_counts,
            x="decade",
            y="count",
            title="Records by Decade",
            labels={"decade": "Decade", "count": "Records"},
            color_discrete_sequence=["#F0883E"]
        )
        fig.update_layout(
            plot_bgcolor="#161B22",
            paper_bgcolor="#161B22",
            font_color="#F0F6FC"
        )
        return fig

    except Exception:
        return None


def get_temporal_stats(df):
    try:
        df_year = df[df["year"].notna()].copy()
        if df_year.empty:
            return None

        df_year["year"] = df_year["year"].astype(int)
        year_counts = (
            df_year.groupby("year").size().reset_index(name="count")
        )

        all_years = set(range(
            int(df_year["year"].min()),
            int(df_year["year"].max()) + 1
        ))
        recorded_years = set(df_year["year"].unique())
        gap_years      = sorted(all_years - recorded_years)

        gaps = []
        if gap_years:
            start = gap_years[0]
            end   = gap_years[0]
            for y in gap_years[1:]:
                if y == end + 1:
                    end = y
                else:
                    gaps.append((start, end))
                    start = y
                    end   = y
            gaps.append((start, end))

        if len(year_counts) >= 3:
            z     = np.polyfit(year_counts["year"], year_counts["count"], 1)
            trend = "increasing" if z[0] > 0 else "decreasing"
        else:
            trend = "insufficient data"

        pre      = df_year[df_year["year"] <  2008].shape[0]
        post     = df_year[df_year["year"] >= 2008].shape[0]
        cs_surge = post > pre * 3

        current_year = df_year["year"].max()
        recent_count = df_year[df_year["year"] >= current_year - 5].shape[0]
        recent_pct   = round(recent_count / len(df_year) * 100, 1)

        return {
            "first_year" : int(df_year["year"].min()),
            "last_year"  : int(df_year["year"].max()),
            "span_years" : int(
                df_year["year"].max() - df_year["year"].min()
            ),
            "gap_count"  : len(gap_years),
            "major_gaps" : [(s, e) for s, e in gaps if e - s >= 4],
            "trend"      : trend,
            "cs_surge"   : cs_surge,
            "recent_pct" : recent_pct,
            "peak_year"  : int(
                year_counts.loc[year_counts["count"].idxmax(), "year"]
            ),
            "peak_count" : int(year_counts["count"].max())
        }

    except Exception:
        return None


def get_recommendations(summary, temporal_stats, df):
    recs = []

    if summary.get("duplicate", {}).get("percent", 0) > 5:
        recs.append({
            "type"   : "warning",
            "title"  : "High Duplicate Rate",
            "message": (
                f"{summary['duplicate']['percent']}% duplicate records "
                f"detected. Consider deduplication before running "
                f"species distribution models."
            )
        })

    if summary.get("missing_coords", {}).get("percent", 0) > 10:
        recs.append({
            "type"   : "warning",
            "title"  : "Missing Coordinates",
            "message": (
                f"{summary['missing_coords']['percent']}% of records "
                f"lack coordinates. These cannot be used in spatial "
                f"analyses."
            )
        })

    if summary.get("low_precision", {}).get("percent", 0) > 20:
        recs.append({
            "type"   : "warning",
            "title"  : "Low Coordinate Precision",
            "message": (
                f"{summary['low_precision']['percent']}% of records have "
                f"low coordinate precision (less than 2 decimal places, "
                f"~1km accuracy). Use caution in fine-scale spatial "
                f"analyses."
            )
        })

    if summary.get("country_mismatch", {}).get("percent", 0) > 2:
        recs.append({
            "type"   : "warning",
            "title"  : "Country Coordinate Mismatch",
            "message": (
                f"{summary['country_mismatch']['percent']}% of records "
                f"have coordinates that fall outside the stated country "
                f"boundary. These may indicate georeferencing errors or "
                f"transposed coordinates."
            )
        })

    if summary.get("old_record", {}).get("percent", 0) > 10:
        recs.append({
            "type"   : "info",
            "title"  : "Historical Records Present",
            "message": (
                f"{summary['old_record']['percent']}% of records predate "
                f"1900. Verify if historical data is appropriate for "
                f"your analysis."
            )
        })

    if temporal_stats:
        if temporal_stats["gap_count"] > 10:
            recs.append({
                "type"   : "warning",
                "title"  : "Temporal Gaps Detected",
                "message": (
                    f"{temporal_stats['gap_count']} years with no recorded "
                    f"observations. Data may not reflect continuous "
                    f"population monitoring."
                )
            })

        if temporal_stats["trend"] == "decreasing":
            recs.append({
                "type"   : "info",
                "title"  : "Decreasing Recording Trend",
                "message": (
                    "Data collection appears to be declining over time. "
                    "Recent records may be underrepresented."
                )
            })

        if temporal_stats["cs_surge"]:
            recs.append({
                "type"   : "success",
                "title"  : "Citizen Science Contribution",
                "message": (
                    "Significant increase in records post-2008, likely "
                    "reflecting citizen science platforms like iNaturalist. "
                    "Consider basis of record when filtering."
                )
            })

        if temporal_stats["recent_pct"] < 10:
            recs.append({
                "type"   : "warning",
                "title"  : "Low Recent Activity",
                "message": (
                    f"Only {temporal_stats['recent_pct']}% of records are "
                    f"from the last 5 years. Current distribution may "
                    f"differ from data."
                )
            })

    clean_pct = 100 - summary.get("any_flag", {}).get("percent", 0)
    if clean_pct >= 90:
        recs.append({
            "type"   : "success",
            "title"  : "High Data Quality",
            "message": (
                f"{clean_pct}% of records passed all quality checks. "
                f"This dataset is suitable for most analyses."
            )
        })

    if not recs:
        recs.append({
            "type"   : "success",
            "title"  : "Data Looks Good",
            "message": (
                "No major issues detected. Always verify data fitness "
                "for your specific use case."
            )
        })

    return recs