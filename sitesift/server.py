"""SiteSift API, site-level screening over open GBIF data.

Run from the repository root:

    uvicorn sitesift.server:app --port 8090
"""
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

from sitesift import frontend, screening

app = FastAPI(
    title="SiteSift",
    version="1.0",
    description=(
        "Site-level biodiversity screening from open GBIF occurrence data. "
        "Screens a drawn polygon for species of concern, native/introduced "
        "status, survey effort and record quality. Does not include "
        "protected-area or KBA boundaries, which are licensed datasets."
    ),
)


class ScreenRequest(BaseModel):
    geometry: dict = Field(..., description="GeoJSON Polygon/MultiPolygon, "
                                            "or Point with radius_km")
    label: str = ""
    year_from: int | None = None
    year_to: int | None = None
    basis: str = "All"
    country: str | None = Field(
        None, description="ISO 3166-1 alpha-2 code, e.g. 'GB'. Limits the "
                          "screen to records attributed to that country.")
    include_points: bool = True


@app.get("/", response_class=HTMLResponse)
async def index():
    return frontend.HTML


@app.get("/api/health")
async def health():
    return {"status": "ok", "app": "sitesift", "version": "1.0",
            "upstream": "api.gbif.org"}


@app.post("/api/screen")
async def screen_site(req: ScreenRequest):
    if req.year_from and req.year_to and req.year_from > req.year_to:
        raise HTTPException(422, "year_from must not be after year_to")
    try:
        return JSONResponse(screening.screen(
            req.geometry, label=req.label,
            year_from=req.year_from, year_to=req.year_to,
            basis=req.basis, country=req.country,
            include_points=req.include_points))
    except ValueError as e:
        raise HTTPException(422, str(e))
    except RuntimeError as e:
        raise HTTPException(502, str(e))
