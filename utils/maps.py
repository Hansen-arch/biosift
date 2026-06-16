import folium
import pandas as pd
from folium.plugins import HeatMap

def build_map(df, flags, map_type="points"):
    try:
        lat_center = df["decimalLatitude"].dropna().mean()
        lon_center = df["decimalLongitude"].dropna().mean()
        if pd.isna(lat_center) or pd.isna(lon_center):
            lat_center, lon_center = 0, 0
    except Exception:
        lat_center, lon_center = 0, 0

    m = folium.Map(
        location=[lat_center, lon_center],
        zoom_start=4,
        tiles="CartoDB dark_matter"
    )

    if map_type == "heatmap":
        heat_data = []
        for _, row in df.iterrows():
            try:
                lat = row.get("decimalLatitude")
                lon = row.get("decimalLongitude")
                if not pd.isna(lat) and not pd.isna(lon):
                    heat_data.append([lat, lon])
            except Exception:
                continue

        if heat_data:
            HeatMap(
                heat_data,
                radius=12,
                blur=15,
                min_opacity=0.4
            ).add_to(m)

    else:
        for idx, row in df.iterrows():
            try:
                lat = row.get("decimalLatitude")
                lon = row.get("decimalLongitude")
                if pd.isna(lat) or pd.isna(lon):
                    continue

                is_flagged = flags.loc[idx, "any_flag"]
                color      = "#F85149" if is_flagged else "#3FB950"
                status     = "Flagged" if is_flagged else "Clean"

                popup_text = f"""
                <div style="font-family:sans-serif;font-size:12px;
                            min-width:150px">
                    <b>{row.get('species', 'Unknown')}</b><br>
                    <span style="color:#888">Country:</span>
                    {row.get('country', 'N/A')}<br>
                    <span style="color:#888">Year:</span>
                    {row.get('year', 'N/A')}<br>
                    <span style="color:#888">Basis:</span>
                    {row.get('basisOfRecord', 'N/A')}<br>
                    <span style="color:#888">Status:</span>
                    {status}
                </div>
                """

                folium.CircleMarker(
                    location=[lat, lon],
                    radius=4,
                    color=color,
                    fill=True,
                    fill_color=color,
                    fill_opacity=0.7,
                    popup=folium.Popup(popup_text, max_width=220)
                ).add_to(m)

            except Exception:
                continue

    return m