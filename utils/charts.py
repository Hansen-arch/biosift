import plotly.express as px
import pandas as pd

def chart_records_per_year(df):
    df_year = df[df["year"].notna()].copy()
    df_year["year"] = df_year["year"].astype(int)
    year_counts = df_year.groupby("year").size().reset_index(name="count")

    fig = px.bar(
        year_counts,
        x="year",
        y="count",
        title="Records per Year",
        labels={"year": "Year", "count": "Number of Records"},
        color_discrete_sequence=["#2ecc71"]
    )
    fig.update_layout(bargap=0.1)
    return fig


def chart_records_per_month(df):
    df_month = df[df["month"].notna()].copy()
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
        title="Records per Month (Seasonal Pattern)",
        labels={"month_name": "Month", "count": "Number of Records"},
        color_discrete_sequence=["#3498db"],
        category_orders={"month_name": list(month_names.values())}
    )
    return fig


def chart_basis_of_record(df):
    if "basisOfRecord" not in df.columns:
        return None

    basis_counts = df["basisOfRecord"].value_counts().reset_index()
    basis_counts.columns = ["basis", "count"]

    fig = px.pie(
        basis_counts,
        names="basis",
        values="count",
        title="Basis of Record"
    )
    return fig


def chart_top_countries(df):
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
        labels={"country": "Country", "count": "Number of Records"},
        color_discrete_sequence=["#9b59b6"]
    )
    fig.update_layout(yaxis={"categoryorder": "total ascending"})
    return fig