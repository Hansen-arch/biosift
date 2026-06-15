import numpy as np
import pandas as pd
import folium
from scipy.stats import gaussian_kde

def build_sdm_map(df):
    try:
        clean = df[["decimalLatitude", "decimalLongitude"]].dropna()

        if len(clean) < 10:
            return None, "Not enough records for SDM (minimum 10 needed)"

        lat = clean["decimalLatitude"].values
        lon = clean["decimalLongitude"].values

        lat_center = lat.mean()
        lon_center = lon.mean()

        # build KDE
        coords = np.vstack([lat, lon])
        kde    = gaussian_kde(coords, bw_method=0.3)

        # grid over bounding box
        lat_min = max(lat.min() - 5, -90)
        lat_max = min(lat.max() + 5,  90)
        lon_min = max(lon.min() - 5, -180)
        lon_max = min(lon.max() + 5,  180)

        grid_lat = np.linspace(lat_min, lat_max, 60)
        grid_lon = np.linspace(lon_min, lon_max, 60)

        ll_lat, ll_lon = np.meshgrid(grid_lat, grid_lon)
        positions = np.vstack([ll_lat.ravel(), ll_lon.ravel()])
        density   = kde(positions).reshape(ll_lat.shape)

        # normalize 0-1
        density = (density - density.min()) / (density.max() - density.min())

        # build map
        m = folium.Map(
            location=[lat_center, lon_center],
            zoom_start=4,
            tiles="CartoDB dark_matter"
        )

        # add actual occurrence dots
        for la, lo in zip(lat, lon):
            folium.CircleMarker(
                location=[la, lo],
                radius=2,
                color="#3FB950",
                fill=True,
                fill_opacity=0.5
            ).add_to(m)

        # add density rectangles
        cell_lat = (lat_max - lat_min) / 60
        cell_lon = (lon_max - lon_min) / 60

        for i in range(len(grid_lon)):
            for j in range(len(grid_lat)):
                d = density[i, j]
                if d < 0.05:
                    continue

                opacity = float(d) * 0.6
                color   = _density_color(float(d))

                folium.Rectangle(
                    bounds=[
                        [grid_lat[j],              grid_lon[i]],
                        [grid_lat[j] + cell_lat,   grid_lon[i] + cell_lon]
                    ],
                    color=None,
                    fill=True,
                    fill_color=color,
                    fill_opacity=opacity
                ).add_to(m)

        return m, None

    except Exception as e:
        return None, str(e)


def _density_color(d):
    if d >= 0.75:
        return "#F85149"
    elif d >= 0.5:
        return "#F0883E"
    elif d >= 0.25:
        return "#E3B341"
    else:
        return "#3FB950"