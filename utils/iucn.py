import requests

IUCN_CATEGORIES = {
    "EX": ("Extinct", "🖤"),
    "EW": ("Extinct in the Wild", "🖤"),
    "CR": ("Critically Endangered", "🔴"),
    "EN": ("Endangered", "🟠"),
    "VU": ("Vulnerable", "🟡"),
    "NT": ("Near Threatened", "🟢"),
    "LC": ("Least Concern", "✅"),
    "DD": ("Data Deficient", "⚪"),
    "NE": ("Not Evaluated", "⚪")
}

def get_iucn_status(species_name, api_key):
    if not api_key:
        return None

    try:
        url = f"https://apiv3.iucnredlist.org/api/v3/species/{species_name}?token={api_key}"
        response = requests.get(url, timeout=10)
        data = response.json()

        if not data.get("result"):
            return None

        result = data["result"][0]
        category = result.get("category", "NE")
        label, emoji = IUCN_CATEGORIES.get(category, ("Unknown", "⚪"))

        return {
            "category": category,
            "label": label,
            "emoji": emoji,
            "scientific_name": result.get("scientific_name", species_name),
            "published_year": result.get("published_year", "N/A")
        }

    except Exception:
        return None