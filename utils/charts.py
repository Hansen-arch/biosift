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
        year_counts = df_year.groupby("year").size().reset_index(name="count")

        fig = go.Figure()

        # bar chart
        fig.add_trace(go.Bar(
            x=year_counts["year"],
            y=year_counts["count"],
            name="Records",
            marker_color="#3FB950",
            opacity=0.8
        ))

        # trend line
        if len(year_counts) >= 3:
            z = np.polyfit(year_counts["year"], year_counts["count"], 1)
            p = np.poly1d(z)
            trend_y = p(year_counts["year"])

            fig.add_trace(go.Scatter(
                x=year_counts["year"],
                y=trend_y,
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
            legend=dict(
                bgcolor="#1C2128",
                bordercolor="#21262D"
            )
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
        month_counts = df_month.groupby("month").size().reset_index(name="count")

        month_names = {
            1:"Jan", 2:"Feb", 3:"Mar", 4:"Apr",
            5:"May", 6:"Jun", 7:"Jul", 8:"Aug",
            9:"Sep", 10:"Oct", 11:"Nov", 12:"Dec"
        }
        month_counts["month_name"] = month_counts["month"].map(month_names)

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

        country_counts = df["country"].value_counts().head(10).reset_index()
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


def chart_decade_breakdown(df):
    try:
        df_year = df[df["year"].notna()].copy()
        if df_year.empty:
            return None

        df_year["year"] = df_year["year"].astype(int)
        df_year["decade"] = (df_year["year"] // 10 * 10).astype(str) + "s"
        decade_counts = df_year.groupby("decade").size().reset_index(name="count")
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
        year_counts = df_year.groupby("year").size().reset_index(name="count")

        all_years = set(range(
            int(df_year["year"].min()),
            int(df_year["year"].max()) + 1
        ))
        recorded_years = set(df_year["year"].unique())
        gap_years = sorted(all_years - recorded_years)

        # consecutive gap ranges
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

        # trend direction
        if len(year_counts) >= 3:
            z = np.polyfit(year_counts["year"], year_counts["count"], 1)
            trend = "increasing" if z[0] > 0 else "decreasing"
        else:
            trend = "insufficient data"

        # citizen science surge (spike after 2008)
        pre  = df_year[df_year["year"] < 2008].shape[0]
        post = df_year[df_year["year"] >= 2008].shape[0]
        cs_surge = post > pre * 3

        # recent activity (last 5 years)
        current_year  = df_year["year"].max()
        recent_count  = df_year[df_year["year"] >= current_year - 5].shape[0]
        recent_pct    = round(recent_count / len(df_year) * 100, 1)

        return {
            "first_year"   : int(df_year["year"].min()),
            "last_year"    : int(df_year["year"].max()),
            "span_years"   : int(df_year["year"].max() - df_year["year"].min()),
            "gap_count"    : len(gap_years),
            "major_gaps"   : [(s, e) for s, e in gaps if e - s >= 4],
            "trend"        : trend,
            "cs_surge"     : cs_surge,
            "recent_pct"   : recent_pct,
            "peak_year"    : int(year_counts.loc[year_counts["count"].idxmax(), "year"]),
            "peak_count"   : int(year_counts["count"].max())
        }

    except Exception:
        return None


def get_recommendations(summary, temporal_stats, df):
    recs = []

    # quality based
    if summary.get("duplicate", {}).get("percent", 0) > 5:
        recs.append({
            "type"   : "warning",
            "title"  : "High Duplicate Rate",
            "message": f"{summary['duplicate']['percent']}% duplicate records detected. "
                       f"Consider deduplication before running species distribution models."
        })

    if summary.get("missing_coords", {}).get("percent", 0) > 10:
        recs.append({
            "type"   : "warning",
            "title"  : "Missing Coordinates",
            "message": f"{summary['missing_coords']['percent']}% of records lack coordinates. "
                       f"These cannot be used in spatial analyses."
        })

    if summary.get("low_precision", {}).get("percent", 0) > 20:
        recs.append({
            "type"   : "warning",
            "title"  : "Low Coordinate Precision",
            "message": f"{summary['low_precision']['percent']}% of records have low coordinate "
                       f"precision (less than 2 decimal places, ~1km accuracy). "
                       f"Use caution in fine-scale spatial analyses."
        })

    if summary.get("old_record", {}).get("percent", 0) > 10:
        recs.append({
            "type"   : "info",
            "title"  : "Historical Records Present",
            "message": f"{summary['old_record']['percent']}% of records predate 1900. "
                       f"Verify if historical data is appropriate for your analysis."
        })

    # temporal based
    if temporal_stats:
        if temporal_stats["gap_count"] > 10:
            recs.append({
                "type"   : "warning",
                "title"  : "Temporal Gaps Detected",
                "message": f"{temporal_stats['gap_count']} years with no recorded observations. "
                           f"Data may not reflect continuous population monitoring."
            })

        if temporal_stats["trend"] == "decreasing":
            recs.append({
                "type"   : "info",
                "title"  : "Decreasing Recording Trend",
                "message": "Data collection appears to be declining over time. "
                           "Recent records may be underrepresented."
            })

        if temporal_stats["cs_surge"]:
            recs.append({
                "type"   : "success",
                "title"  : "Citizen Science Contribution",
                "message": "Significant increase in records post-2008, likely reflecting "
                           "citizen science platforms like iNaturalist. "
                           "Consider basis of record when filtering."
            })

        if temporal_stats["recent_pct"] < 10:
            recs.append({
                "type"   : "warning",
                "title"  : "Low Recent Activity",
                "message": f"Only {temporal_stats['recent_pct']}% of records are from "
                           f"the last 5 years. Current distribution may differ from data."
            })

    # positive feedback
    clean_pct = 100 - summary.get("any_flag", {}).get("percent", 0)
    if clean_pct >= 90:
        recs.append({
            "type"   : "success",
            "title"  : "High Data Quality",
            "message": f"{clean_pct}% of records passed all quality checks. "
                       f"This dataset is suitable for most analyses."
        })

    if not recs:
        recs.append({
            "type"   : "success",
            "title"  : "Data Looks Good",
            "message": "No major issues detected. "
                       "Always verify data fitness for your specific use case."
        })

    return recs