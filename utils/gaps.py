import folium
import pandas as pd
import numpy as np

def build_gap_map(df):
    try:
        clean = df[["decimalLatitude", "decimalLongitude"]].dropna()

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

        lat_bins = np.arange(-90,  91, grid_size)
        lon_bins = np.arange(-180, 181, grid_size)

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

        max_count = cell_counts["count"].max() if not cell_counts.empty else 1

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
        clean = df[["decimalLatitude", "decimalLongitude",
                    "country"]].dropna(
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

        covered  = len(cells_with_data)
        gap_pct  = round((1 - covered / total_cells) * 100, 1)
        cov_pct  = round(covered / total_cells * 100, 1)

        return {
            "total_cells" : total_cells,
            "covered"     : covered,
            "gap_pct"     : gap_pct,
            "cov_pct"     : cov_pct,
            "countries"   : clean["country"].nunique()
                            if "country" in clean.columns else 0
        }

    except Exception:
        return None