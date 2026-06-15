import requests
import pandas as pd

GBIF_API = "https://api.gbif.org/v1"

def search_publisher(publisher_name):
    try:
        url = f"{GBIF_API}/organization"
        params = {"q": publisher_name, "limit": 5}
        r = requests.get(url, params=params, timeout=10)
        data = r.json()

        results = data.get("results", [])
        if not results:
            return None, "No publisher found with that name."

        return results, None

    except Exception as e:
        return None, str(e)


def get_publisher_datasets(publisher_key, limit=20):
    try:
        url = f"{GBIF_API}/dataset"
        params = {
            "publishingOrg": publisher_key,
            "limit"         : limit
        }
        r = requests.get(url, params=params, timeout=10)
        data = r.json()
        return data.get("results", []), None

    except Exception as e:
        return [], str(e)


def get_dataset_metrics(dataset_key):
    try:
        url = f"{GBIF_API}/occurrence/search"
        params = {
            "datasetKey"     : dataset_key,
            "limit"          : 0,
            "hasCoordinate"  : "true"
        }
        r = requests.get(url, params=params, timeout=10)
        data = r.json()
        count_with_coords = data.get("count", 0)

        url2 = f"{GBIF_API}/occurrence/search"
        params2 = {"datasetKey": dataset_key, "limit": 0}
        r2 = requests.get(url2, params=params2, timeout=10)
        data2 = r2.json()
        total = data2.get("count", 0)

        coord_pct = round(
            count_with_coords / total * 100, 1
        ) if total > 0 else 0

        return {
            "total"          : total,
            "with_coords"    : count_with_coords,
            "coord_pct"      : coord_pct,
        }

    except Exception:
        return None


def build_publisher_report(publisher_key, publisher_name, limit=10):
    datasets, error = get_publisher_datasets(publisher_key, limit)

    if error or not datasets:
        return None, error or "No datasets found."

    rows = []
    total_records = 0

    for ds in datasets:
        key     = ds.get("key", "")
        title   = ds.get("title", "Unknown")[:60]
        ds_type = ds.get("type", "N/A")
        created = ds.get("created", "N/A")[:10] if ds.get("created") else "N/A"
        modified = ds.get("modified", "N/A")[:10] if ds.get("modified") else "N/A"

        metrics = get_dataset_metrics(key)

        if metrics:
            total_records += metrics["total"]
            rows.append({
                "Dataset"             : title,
                "Type"                : ds_type,
                "Total Records"       : f"{metrics['total']:,}",
                "With Coordinates"    : f"{metrics['with_coords']:,}",
                "Coordinate Coverage" : f"{metrics['coord_pct']}%",
                "Created"             : created,
                "Last Modified"       : modified,
            })
        else:
            rows.append({
                "Dataset"             : title,
                "Type"                : ds_type,
                "Total Records"       : "N/A",
                "With Coordinates"    : "N/A",
                "Coordinate Coverage" : "N/A",
                "Created"             : created,
                "Last Modified"       : modified,
            })

    return {
        "publisher"     : publisher_name,
        "dataset_count" : len(rows),
        "total_records" : total_records,
        "datasets"      : pd.DataFrame(rows)
    }, None