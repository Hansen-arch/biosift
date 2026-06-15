import folium
import pandas as pd

def build_map(df, flags):
    try:
        lat_center = df["decimalLatitude"].dropna().mean()
        lon_center = df["decimalLongitude"].dropna().mean()

        if pd.isna(lat_center) or pd.isna(lon_center):
            lat_center, lon_center = 0, 0

    except Exception:
        lat_center, lon_center = 0, 0

    m = folium.Map(location=[lat_center, lon_center], zoom_start=4)

    for idx, row in df.iterrows():
        try:
            lat = row.get("decimalLatitude")
            lon = row.get("decimalLongitude")

            if pd.isna(lat) or pd.isna(lon):
                continue

            is_flagged = flags.loc[idx, "any_flag"]
            color = "red" if is_flagged else "green"

            popup_text = f"""
            <b>{row.get('species', 'Unknown')}</b><br>
            Country: {row.get('country', 'N/A')}<br>
            Year: {row.get('year', 'N/A')}<br>
            Basis: {row.get('basisOfRecord', 'N/A')}
            """

            folium.CircleMarker(
                location=[lat, lon],
                radius=4,
                color=color,
                fill=True,
                fill_opacity=0.7,
                popup=folium.Popup(popup_text, max_width=200)
            ).add_to(m)

        except Exception:
            continue

    return m