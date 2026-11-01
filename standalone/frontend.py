"""
BioSift Standalone Frontend — single-file MapLibre GL JS app.

Design notes (light scholarly ledger, see DESIGN.md; antislop filter):
  - warm paper + ink + one deep-emerald accent, flat surfaces, radius 4,
    Georgia serif brand, system sans with tabular numerals
  - MapLibre GL JS (BSD-3, Mapbox GL v1 fork — no API key, no token)
  - key-free raster style built from verified XYZ endpoints (Esri Light
    Gray + World Imagery, OSM, OpenTopoMap — no CARTO, no API keys)
  - inspector layout: fixed left analysis panel, full-height map
  - no emoji, no gradient hero, no decorative icons — monochrome
    SVG line icons only, same visual family as utils/icons.py
  - system font stack (no webfont fetch), tabular numerals for metrics

UX rules applied (from MapLibre docs + dashboard-UX guides):
  - points cluster at low zooms (official clustering pattern), click
    for a popup (official popup pattern)
  - point colour comes from the BioSift BDQ verdict (biosift_flag),
    never GBIF's benign `issues` string
  - every text container breaks long words; tables never force
    horizontal scroll (readability without zoom)
  - panel width is fluid; the search form is always above the fold
"""

PAGE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>BioSift: Biodiversity Data Quality</title>
<script src="https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.js"></script>
<link href="https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.css" rel="stylesheet"/>
<style>
:root{
  --bg:#F4F1E8; --panel:#EDE9DC; --card:#FBF9F2; --line:#D6CFBC;
  --line-strong:#B9B09A;
  --text:#232019; --dim:#5C5647; --faint:#6E6653;
  --acc:#136F4E; --red:#A2382B; --amber:#75530F; --blue:#1D5FA8;
}
*{box-sizing:border-box;margin:0;padding:0}
html,body{height:100%}
body{
  font:14px/1.5 -apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  background:var(--bg);color:var(--text);
}
#app{display:grid;grid-template-columns:clamp(320px,29vw,420px) 1fr;
  height:100vh}
/* ── panel ── */
#panel{
  background:var(--panel);border-right:1px solid var(--line);
  display:flex;flex-direction:column;overflow:hidden;min-width:0;
}
#panel header{
  padding:18px 20px 14px;border-bottom:1px solid var(--line);
}
.brand{display:flex;align-items:baseline;gap:10px}
.brand h1{font-family:Georgia,"Times New Roman",serif;
  font-size:20px;font-weight:700;letter-spacing:-.3px}
.brand span{font-size:10px;letter-spacing:1.6px;color:var(--faint);
  text-transform:uppercase}
/* gaia-style capability strip (below the search form, inside .scroll;
   shown at boot, hidden once results render) */
#capabilities{display:none;padding:18px 0 10px}
#capabilities .capgrid{display:grid;grid-template-columns:1fr;gap:8px}
.cap{display:flex;gap:12px;align-items:flex-start;background:var(--card);
  border:1px solid var(--line);border-radius:4px;padding:12px 14px}
.cap .n{font-family:ui-monospace,Menlo,Consolas,monospace;
  font-size:11px;font-weight:700;color:var(--dim);
  border:1px solid var(--line-strong);border-radius:3px;
  min-width:22px;height:22px;display:flex;align-items:center;
  justify-content:center;margin-top:1px}
.cap .t{font-size:13px;font-weight:600}
.cap .d{font-size:11px;color:var(--dim);margin-top:1px;line-height:1.45}
#audience{display:none;padding:8px 0 20px}
#audience .aud{display:flex;flex-wrap:wrap;gap:6px}
#audience .chip{font-size:10.5px}
#panel .scroll{
  overflow-y:auto;padding:16px 20px 32px;flex:1;min-height:0;
}
.field{margin-bottom:14px}
.field label{
  display:block;font-size:10px;font-weight:600;letter-spacing:1.2px;
  text-transform:uppercase;color:var(--faint);margin-bottom:5px;
}
.field input,.field select{
  width:100%;background:var(--card);border:1px solid var(--line);
  color:var(--text);border-radius:4px;padding:9px 11px;font-size:13px;
  outline:none;
}
.field input:focus,.field select:focus{border-color:var(--acc)}
.row{display:grid;grid-template-columns:1fr 1fr;gap:10px}
button#run, #run-byod{
  width:100%;background:var(--acc);color:#F4F1E8;border:none;
  border-radius:4px;padding:11px;font-weight:700;font-size:13px;
  cursor:pointer;margin-top:4px;
}
button#run:disabled{opacity:.55;cursor:wait}
button#run:hover:not(:disabled){background:#106144}
/* segmented mode switch (joined control, not loose buttons) */
.modes{display:flex;gap:2px;margin-top:12px;background:var(--card);
  border:1px solid var(--line);border-radius:4px;padding:2px}
.modebtn{flex:1;background:transparent;border:none;color:var(--dim);
  border-radius:3px;padding:7px 10px;font-size:11.5px;font-weight:700;
  cursor:pointer;letter-spacing:.3px}
.modebtn.active{color:#F4F1E8;background:var(--acc)}
/* profile summary box */
#profbox{background:var(--card);border:1px solid var(--line);
  border-left:3px solid var(--acc);border-radius:10px;
  padding:10px 12px;margin:4px 0 14px;font-size:12px;line-height:1.5;
  overflow-wrap:anywhere}
#profbox b{font-weight:700}
.countchip{display:none;font-size:9px;margin-left:2px}
#t-mapping select{
  width:100%;background:var(--card);border:1px solid var(--line);
  color:var(--text);border-radius:4px;padding:5px 7px;font-size:11.5px;
  outline:none;max-width:100%;}
#t-mapping select:focus{border-color:var(--acc)}
/* metrics */
.metrics{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin:4px 0 14px}
.metric{background:var(--card);border:1px solid var(--line);
  border-radius:4px;padding:10px 12px;min-width:0}
.metric .k{font-size:9.5px;font-weight:600;letter-spacing:1.1px;
  text-transform:uppercase;color:var(--faint)}
.metric .v{font-size:20px;font-weight:700;margin-top:2px;
  font-variant-numeric:tabular-nums;overflow-wrap:anywhere}
.metric .n{font-size:10.5px;color:var(--dim);margin-top:1px}
.good{color:var(--acc)} .fair{color:var(--amber)} .poor{color:var(--red)}
.bar{height:6px;background:var(--panel);border:1px solid var(--line);
  border-radius:2px;overflow:hidden;margin-top:6px}
.bar i{display:block;height:100%;background:var(--acc)}
/* sections */
h2.sec{
  font-size:10.5px;font-weight:700;letter-spacing:1.6px;color:var(--faint);
  text-transform:uppercase;margin:18px 0 8px;display:flex;gap:8px;
  align-items:center;
}
h2.sec::after{content:"";flex:1;height:1px;background:var(--line-strong)}
table{width:100%;border-collapse:collapse;font-size:12px;
  table-layout:fixed}
table col.c-wide{width:auto}
table col.c-num{width:84px}
table col.c-bdq{width:118px}
td,th{padding:6px 4px;border-bottom:1px solid var(--line);text-align:left;
  vertical-align:top;overflow-wrap:anywhere}
th{color:var(--faint);font-weight:600;font-size:10px;
  letter-spacing:.8px;text-transform:uppercase}
td.num{text-align:right;font-variant-numeric:tabular-nums;color:var(--dim)}
.mono{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:10.5px;
  color:var(--faint);overflow-wrap:anywhere}
.chip{display:inline-block;font-size:9.5px;font-weight:700;
  padding:2px 7px;border-radius:99px;border:1px solid var(--line);
  color:var(--dim);margin:1px 2px 1px 0}
.chip.ok{color:var(--acc);border-color:var(--acc);background:#DCEBE0}
.chip.bad{color:var(--red);border-color:var(--red);background:#F1DAD3}
.chip.warn{color:var(--amber);border-color:var(--amber);background:#F3E7C8}
.note{font-size:11px;color:var(--dim);line-height:1.5;margin-top:6px;
  overflow-wrap:anywhere}
.cite{font-size:10px;color:var(--faint);line-height:1.5;margin-top:6px}
.status{font-size:12px;color:var(--dim);padding:10px 0;overflow-wrap:anywhere}
.status.err{color:var(--red)}
/* sparkline (records per year) */
.spark{width:100%;height:56px;display:block;margin-top:4px}
.spark .axis{stroke:var(--line);stroke-width:1}
.spark path{fill:rgba(30,122,84,.15);stroke:var(--acc);stroke-width:1.5}
.gaps{margin-top:6px}
/* charts — dependency-free SVG heatmaps + CSS bars */
.chart{display:block;width:100%;height:auto;margin-top:2px}
.chart .ax{font-size:9.5px;fill:var(--faint)}
.chart .celltx{font-size:8.5px;fill:var(--text);
  font-variant-numeric:tabular-nums}
.chartlegend{display:flex;gap:12px;align-items:center;font-size:10px;
  color:var(--faint);margin-top:5px}
.chartlegend i{display:inline-block;width:10px;height:10px;border-radius:2px;
  vertical-align:-1px;margin-right:4px}
.bars{margin-top:3px}
.barrow{display:grid;grid-template-columns:44px 1fr 78px;gap:8px;
  align-items:center;padding:2px 0}
.barrow .bl{font-size:10px;color:var(--dim);overflow-wrap:anywhere;
  font-variant-numeric:tabular-nums}
.barrow .bv{font-size:10px;color:var(--faint);text-align:right;
  font-variant-numeric:tabular-nums}
.btrack{position:relative;height:12px;background:var(--panel);
  border:1px solid var(--line);border-radius:2px;overflow:hidden}
.btrack i{position:absolute;left:0;top:0;bottom:0;background:#CFC7B2}
.btrack i.acc{background:var(--acc);opacity:.85}
.btrack b{position:absolute;left:0;top:0;bottom:0;background:var(--amber);
  opacity:.9}
/* seasonality columns */
.months{display:flex;gap:4px;align-items:flex-end;height:92px;
  margin-top:6px}
.mb{flex:1;display:flex;flex-direction:column;justify-content:flex-end;
  align-items:center;height:100%;min-width:0}
.mb i{display:block;width:100%;background:var(--acc);opacity:.8}
.mb span{font-size:9px;color:var(--faint);margin-top:3px}
/* trend / envelope line charts */
.trend{display:block;width:100%;height:auto;margin-top:6px}
.trend .base{stroke:var(--line-strong);stroke-dasharray:4 3;fill:none}
.trend .line{fill:none;stroke:var(--blue);stroke-width:1.6}
.trend .ax{font-size:9.5px;fill:var(--faint)}
/* compact inline buttons (map overlay, scripts) */
.sbtn{background:var(--card);border:1px solid var(--line-strong);
  color:var(--text);border-radius:4px;padding:7px 12px;font-size:11.5px;
  font-weight:600;cursor:pointer;margin:10px 6px 0 0}
.sbtn:hover{border-color:var(--acc);color:var(--acc)}
/* export row */
#exports{display:none;margin-top:16px}
#exports .exp{display:flex;gap:8px;flex-wrap:wrap}
#exports button{
  background:var(--card);border:1px solid var(--line-strong);color:var(--text);
  border-radius:4px;padding:7px 12px;font-size:11.5px;font-weight:600;
  cursor:pointer;
}
#exports button:hover{border-color:var(--acc);color:var(--acc)}
/* ── map column ── */
#mapwrap{position:relative;min-width:0}
#map{position:absolute;inset:0}
#legend{
  position:absolute;left:12px;bottom:24px;z-index:5;
  background:rgba(251,249,242,.95);border:1px solid var(--line-strong);
  border-radius:4px;padding:10px 12px;font-size:11px;color:var(--dim);
}
#legend .dot{display:inline-block;width:9px;height:9px;border-radius:50%;
  margin-right:6px;vertical-align:middle}
#speciesbar{
  position:absolute;top:12px;left:12px;z-index:5;max-width:60%;
  background:rgba(251,249,242,.95);border:1px solid var(--line-strong);
  border-radius:4px;padding:9px 14px;font-size:13px;display:none;
}
#speciesbar b{font-style:italic;overflow-wrap:anywhere}
#speciesbar .chip{margin-left:8px}
.maplibregl-ctrl-group{
  background:var(--card)!important;border:1px solid var(--line)!important;
}
.maplibregl-ctrl-group button+button{border-top:1px solid var(--line)!important}
.maplibregl-ctrl-attrib{
  background:rgba(251,249,242,.85)!important;color:var(--faint)!important;
  font-size:10px!important;
}
.maplibregl-ctrl-attrib a{color:var(--dim)!important}
/* popups (MapLibre popup pattern) */
.maplibregl-popup-content{
  background:var(--card)!important;color:var(--text)!important;
  border:1px solid var(--line)!important;border-radius:4px!important;
  padding:12px 14px!important;font-size:12px;line-height:1.5;
  min-width:220px;max-width:290px;box-shadow:0 2px 12px rgba(35,32,25,.22);
}
.maplibregl-popup-tip{border-top-color:var(--card)!important;
  border-bottom-color:var(--card)!important}
.maplibregl-popup-close-button{
  color:var(--dim)!important;font-size:15px;padding:2px 7px!important;
}
.pop-t{font-weight:700;font-style:italic;margin-bottom:4px;
  overflow-wrap:anywhere}
.pop-r{display:flex;justify-content:space-between;gap:14px}
.pop-r span:first-child{color:var(--faint)}
.pop-r span:last-child{text-align:right;overflow-wrap:anywhere}
.pop-f{margin-top:6px}
@media(max-width:860px){
  #app{grid-template-columns:1fr;grid-template-rows:auto 1fr}
  #panel{max-height:46vh;border-right:none;
    border-bottom:1px solid var(--line)}
  #speciesbar{max-width:80%}
}
</style>
</head>
<body>
<div id="app">
  <div id="panel">
    <header>
      <div class="brand">
        <h1>BioSift</h1>
        <span>Professional Biodiversity Studio</span>
      </div>
      <div class="note" style="margin-top:4px" id="subtitle">
        GBIF data-quality analysis · TDWG BDQ aligned
      </div>
      <div class="modes">
        <button class="modebtn active" id="mode-gbif">GBIF species</button>
        <button class="modebtn" id="mode-byod">Your data</button>
      </div>
    </header>
    <div class="scroll">
      <!-- GBIF mode inputs -->
      <div id="gbif-inputs">
      <div class="field">
        <label for="species">Scientific name</label>
        <input id="species" value="Panthera leo" spellcheck="false"/>
      </div>
      <div class="row">
        <div class="field">
          <label for="yf">Year from</label>
          <input id="yf" type="number" value="1900" min="1000" max="2026"/>
        </div>
        <div class="field">
          <label for="yt">Year to</label>
          <input id="yt" type="number" value="2026" min="1000" max="2026"/>
        </div>
      </div>
      <div class="row">
        <div class="field">
          <label for="limit">Max records</label>
          <input id="limit" type="number" value="500" min="50" max="5000"
                 step="50"/>
        </div>
        <div class="field">
          <label for="basis">Basis</label>
          <select id="basis">
            <option>All</option>
            <option>HUMAN_OBSERVATION</option>
            <option>PRESERVED_SPECIMEN</option>
            <option>MACHINE_OBSERVATION</option>
            <option>LIVING_SPECIMEN</option>
            <option>LITERATURE</option>
            <option>FOSSIL_SPECIMEN</option>
          </select>
        </div>
      </div>
      <div class="field">
        <label for="profile">SDM strictness profile</label>
        <select id="profile">
          <option>Standard (≤10 km, Zizka et al. 2020)</option>
          <option>Strict (≤1 km, publication-grade)</option>
        </select>
      </div>
      <button id="run">Run Analysis</button>
      </div><!-- /gbif-inputs -->

      <!-- Your-data mode inputs -->
      <div id="byod-inputs" style="display:none">
        <div class="field">
          <label for="file">Dataset file (CSV, TSV, Excel or DwC-A zip)</label>
          <input id="file" type="file"
                 accept=".csv,.tsv,.txt,.xlsx,.xls,.zip,.dwca"/>
          <div class="note">Everything is processed locally in this
            session. The file is not stored. Column names are matched
            automatically (Darwin Core terms, common aliases) and you
            can adjust the mapping before running.</div>
        </div>
        <div class="field">
          <label for="byod-profile">Fit-for-use profile</label>
          <select id="byod-profile">
            <option>General</option>
            <option>SDM (Zizka et al. 2020)</option>
            <option>Report only (nothing excluded)</option>
          </select>
        </div>
        <button id="inspect" style="width:100%;background:var(--card);
          color:var(--text);border:1px solid var(--line-strong);border-radius:4px;
          padding:10px;font-weight:700;font-size:12.5px;cursor:pointer">
          Inspect file</button>
        <div id="mapping" style="display:none">
          <h2 class="sec">Column mapping</h2>
          <table id="t-mapping"></table>
          <div class="note" id="map-note"></div>
          <div id="preview" style="display:none;margin-top:10px">
            <table id="t-preview"></table>
          </div>
          <button id="run-byod" style="width:100%;margin-top:10px">
            Run Analysis</button>
        </div>
      </div>

      <div id="status" class="status">Search a species to begin.</div>

      <!-- gaia-style pitch: lives BELOW the form so the search is
           always above the fold on short screens (1366x768) -->
      <div id="capabilities">
        <h2 class="sec">Capabilities</h2>
        <div class="capgrid">
          <div class="cap"><div class="n">1</div><div>
            <div class="t">Audit GBIF data, or your own</div>
            <div class="d">17 automated checks mapped to the official TDWG BDQ vocabulary. Bring a CSV, TSV, Excel file or DwC-A archive, or fetch any species live.</div></div></div>
          <div class="cap"><div class="n">2</div><div>
            <div class="t">Benchmark against the world</div>
            <div class="d">Defect rates compared live against the full GBIF population.</div></div></div>
          <div class="cap"><div class="n">3</div><div>
            <div class="t">Relationships &amp; communities</div>
            <div class="d">GloBI interactions plus congeneric co-occurrence (Jaccard).</div></div></div>
          <div class="cap"><div class="n">4</div><div>
            <div class="t">Clean and export, not just report</div>
            <div class="d">Fit-for-use profiles keep or exclude records; download your data back with verdict columns, or as GeoJSON.</div></div></div>
          <div class="cap"><div class="n">5</div><div>
            <div class="t">Model-ready or nothing</div>
            <div class="d">SDM readiness gates cite Zizka 2020 and Marcer 2022; EOO/AOO with KBA Criterion B screening for both modes.</div></div></div>
        </div>
      </div>
      <div id="audience">
        <div class="aud">
          <span class="chip ok">Researchers</span>
          <span class="chip">Data managers</span>
          <span class="chip">Node staff</span>
          <span class="chip">Policy analysts</span>
        </div>
      </div>

      <div id="results" style="display:none">
        <div class="metrics">
          <div class="metric">
            <div class="k" id="m-total-k">GBIF records</div>
            <div class="v" id="m-total">n/a</div>
            <div class="n" id="m-total-n">matching filters</div>
          </div>
          <div class="metric">
            <div class="k">Analysed</div>
            <div class="v" id="m-analysed">n/a</div>
            <div class="n" id="m-completeness"></div>
          </div>
          <div class="metric">
            <div class="k">Health score</div>
            <div class="v" id="m-health">n/a</div>
            <div class="bar"><i id="m-healthbar" style="width:0%"></i></div>
          </div>
          <div class="metric">
            <div class="k">SDM-ready</div>
            <div class="v" id="m-sdm">n/a</div>
            <div class="n" id="m-sdmnote"></div>
          </div>
          <div class="metric byod-only" style="display:none">
            <div class="k">Profile retention</div>
            <div class="v" id="m-keep">n/a</div>
            <div class="n" id="m-keepnote"></div>
          </div>
          <div class="metric byod-only" style="display:none">
            <div class="k">Flagged</div>
            <div class="v" id="m-flag">n/a</div>
            <div class="n">any check triggered</div>
          </div>
        </div>

        <div id="profbox" class="byod-only" style="display:none"></div>

        <h2 class="sec gbif-only">Species factsheet
          <span class="chip countchip" id="cnt-fact"></span></h2>
        <div id="factsheet" class="gbif-only"></div>

        <h2 class="sec">Quality checks, TDWG BDQ <span class="chip countchip" id="cnt-checks"></span></h2>
        <table id="t-checks">
          <colgroup><col class="c-wide"/><col class="c-bdq"/>
            <col class="c-num"/><col class="c-num"/></colgroup>
        </table>

        <h2 class="sec gbif-only">Benchmark vs GBIF-wide</h2>
        <div id="benchmark" class="note gbif-only">n/a</div>

        <h2 class="sec">Temporal coverage</h2>
        <div id="temporal"></div>

        <h2 class="sec">Seasonality
          <span class="chip countchip" id="cnt-phen"></span></h2>
        <div id="phenology"></div>

        <h2 class="sec">Change over time
          <span class="chip countchip" id="cnt-shift"></span></h2>
        <div id="rangeshift"></div>

        <h2 class="sec">Reporting trend, effort-aware
          <span class="chip countchip" id="cnt-trend"></span></h2>
        <div id="trend"></div>

        <h2 class="sec">Patterns &amp; correlations
          <span class="chip countchip" id="cnt-patterns"></span></h2>
        <div id="patterns"></div>

        <h2 class="sec">Climate envelope
          <span class="chip countchip" id="cnt-env"></span></h2>
        <div id="envelope"></div>

        <h2 class="sec">Distribution &amp; KBA Criterion B</h2>
        <div id="kba"></div>

        <h2 class="sec gbif-only">Ecological community</h2>
        <div id="community" class="gbif-only"></div>

        <h2 class="sec gbif-only">Carbon (plants only)</h2>
        <div id="carbon" class="gbif-only"></div>

        <h2 class="sec">SDM readiness, gate detail</h2>
        <div id="sdm"></div>

        <h2 class="sec byod-only" style="display:none">Species breakdown <span class="chip countchip" id="cnt-species"></span></h2>
        <div id="speciesbrk" class="byod-only" style="display:none"></div>

        <h2 class="sec byod-only" style="display:none">Dataset profile <span class="chip countchip" id="cnt-dsprof"></span></h2>
        <div id="dsprofile" class="byod-only" style="display:none"></div>

        <h2 class="sec byod-only" style="display:none">Spatial outliers, DBSCAN <span class="chip countchip" id="cnt-outliers"></span></h2>
        <div id="outliers" class="byod-only" style="display:none"></div>

        <h2 class="sec byod-only" style="display:none">Taxon verification, GBIF backbone <span class="chip countchip" id="cnt-names"></span></h2>
        <div id="namecheck" class="byod-only" style="display:none"></div>

        <h2 class="sec byod-only" style="display:none">Flagged records, first 20 <span class="chip countchip" id="cnt-flagged"></span></h2>
        <div id="flagged" class="byod-only" style="display:none"></div>

        <h2 class="sec byod-only" style="display:none">Recommended actions <span class="chip countchip" id="cnt-recs"></span></h2>
        <div id="recs" class="byod-only" style="display:none"></div>

        <div class="cite" id="cites"></div>

        <div id="exports">
          <h2 class="sec">Export</h2>
          <div class="exp">
            <button id="exp-json">JSON bundle</button>
            <button id="exp-csv">Records CSV</button>
            <button id="exp-geo" class="byod-only" style="display:none">GeoJSON</button>
            <button id="exp-flagged" class="byod-only" style="display:none">Flagged CSV</button>
            <button id="exp-clean" class="byod-only" style="display:none">Clean CSV (profile)</button>
            <button id="exp-r" class="gbif-only">R recipe</button>
            <button id="exp-py" class="gbif-only">Python recipe</button>
          </div>
        </div>
      </div>
    </div>
  </div>

  <div id="mapwrap">
    <div id="map"></div>
    <div id="speciesbar">
      <b id="sb-name">No species yet</b>
      <span id="sb-chips"></span>
    </div>
    <div id="legend">
      <span class="dot" style="background:#1E7A54"></span>Clean
      &nbsp; <span class="dot" style="background:#C9922B"></span>Flagged
      &nbsp; <span class="dot" style="background:#C2402F"></span>Excluded
      <br/>
      <span style="font-size:9.5px;color:var(--faint)">
        Click a point for details · Basemap: top-right
      </span>
    </div>
  </div>
</div>

<script>
const ACC='#1E7A54', RED='#C2402F';
let map, mapReady=false, popup=null;

const BASEMAPS = {
  light: {
    title:'Light Gray (Esri)',
    tiles:['https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}'],
    attribution:'Esri, HERE, Garmin, FAO, NOAA, USGS',
  },
  osm: {
    title:'OpenStreetMap',
    tiles:['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
    attribution:'© OpenStreetMap contributors',
  },
  satellite: {
    title:'Satellite (Esri)',
    tiles:['https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'],
    attribution:'Esri, Maxar, Earthstar Geographics',
  },
  topo: {
    title:'Topographic (OpenTopoMap)',
    tiles:['https://a.tile.opentopomap.org/{z}/{x}/{y}.png'],
    attribution:'© OpenTopoMap (CC-BY-SA)',
  },
  dark: {
    title:'Dark (Esri)',
    tiles:['https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}'],
    attribution:'Esri, HERE, Garmin, FAO, NOAA, USGS',
  },
};

function rasterStyle(base){
  const b = BASEMAPS[base];
  return {
    version:8,
    glyphs:'https://demotiles.maplibre.org/font/{fontstack}/{range}.pbf',
    sources:{
      base:{
        type:'raster',
        tiles:b.tiles,
        tileSize:256,
        attribution:b.attribution,
        maxzoom:18,
      },
    },
    layers:[
      {id:'bg', type:'background', paint:{
        'background-color': base==='dark' ? '#14171A' : '#F4F1E8'}},
      {id:'base', type:'raster', source:'base'},
    ],
  };
}

function initMap(){
  map = new maplibregl.Map({
    container:'map',
    style:rasterStyle('light'),
    center:[20,5], zoom:1.6,
    attributionControl:{compact:true},
  });
  map.addControl(new maplibregl.NavigationControl(), 'top-right');
  map.addControl(new maplibregl.ScaleControl(), 'bottom-right');
  popup = new maplibregl.Popup({closeButton:true, maxWidth:'300px'});

  // basemap switcher (native select, professional styling)
  const sel = document.createElement('select');
  sel.style.cssText = 'margin:10px 12px 0 0;padding:5px 8px;border-radius:4px;'
    + 'background:#FBF9F2;color:#232019;border:1px solid #B9B09A;'
    + 'font-size:11px;outline:none;float:right;';
  Object.entries(BASEMAPS).forEach(([k,v])=>{
    const o=document.createElement('option'); o.value=k;
    o.textContent=v.title; sel.appendChild(o);
  });
  sel.addEventListener('focus', ()=>{ sel.style.borderColor='#136F4E'; });
  sel.addEventListener('blur', ()=>{ sel.style.borderColor='#B9B09A'; });
  sel.addEventListener('change', ()=>{
    map.setStyle(rasterStyle(sel.value), {diff:false});
    map.once('styledata', ()=>{ if(window.__lastGeo) pushGeo(window.__lastGeo); });
  });
  const wrap=document.createElement('div');
  wrap.appendChild(sel);
  document.getElementById('mapwrap').appendChild(wrap);
  wrap.style.cssText='position:absolute;top:8px;right:8px;z-index:6';
  map.on('load', ()=>{ mapReady=true; });
  // point popup — official MapLibre click pattern; layers are filtered
  // to whatever actually exists in the current style
  map.on('click', (e)=>{
    const ids = ['occ-pt-fill','clusters']
      .filter(id=>{ try{return map.getLayer(id);}catch(err){return false;} });
    if(!ids.length) return;
    const feats = map.queryRenderedFeatures(e.point, {layers:ids});
    if(!feats.length){ popup.remove(); return; }
    const f = feats[0];
    if(f.properties && f.properties.cluster){
      const src = map.getSource('occ');
      src.getClusterExpansionZoom(f.properties.cluster_id).then(z=>{
        map.easeTo({center:f.geometry.coordinates, zoom:z});
      });
      popup.setLngLat(f.geometry.coordinates).setHTML(
        '<div class="pop-t">'+f.properties.cluster+' records'
        +'</div><div class="note">Zoom in to separate points.</div>')
        .addTo(map);
      return;
    }
    popup.setLngLat(f.geometry.coordinates)
      .setHTML(popupHTML(f.properties)).addTo(map);
  });
  map.on('mouseenter', 'occ-pt-fill', ()=>{ map.getCanvas().style.cursor='pointer'; });
  map.on('mouseleave', 'occ-pt-fill', ()=>{ map.getCanvas().style.cursor=''; });
  window.__map = map;  // audit hook
}

function prettyFlag(s){
  return String(s).toLowerCase().split('_')
    .map(w=>w.charAt(0).toUpperCase()+w.slice(1)).join(' ');
}

const AMBER='#C9922B';
const BYOD_FIELDS=['species','decimalLatitude','decimalLongitude','year',
  'eventDate','basisOfRecord','country','countryCode','stateProvince',
  'locality','coordinateUncertaintyInMeters','datasetName',
  'institutionCode','occurrenceID','catalogNumber','recordedBy',
  'family','genus','kingdom','individualCount','month','day','depth',
  'elevation'];
const BYOD_CORE=['species','decimalLatitude','decimalLongitude','year'];

function setCount(id, text){
  const el=document.getElementById(id);
  if(el){ el.textContent=text; el.style.display='inline-block'; }
}

function temporalHTML(d){
  const t=d.temporal;
  if(!t) return '<div class="note">No dated records in this sample.</div>';
  const gapChips=(t.major_gaps||[]).slice(0,6).map(g=>
    '<span class="chip warn">gap '+g[0]+'–'+g[1]+'</span>').join('');
  return sparkline(d.year_counts)
    + '<table><colgroup/><tr><th>Indicator</th><th style="text-align:right">Value</th></tr>'
    + '<tr><td>Span</td><td class="num">'+t.first_year+'–'+t.last_year
    +' ('+t.span_years+' yr)</td></tr>'
    + '<tr><td>Gap years</td><td class="num">'+t.gap_count+'</td></tr>'
    + '<tr><td>Trend</td><td class="num">'+esc(t.trend)+'</td></tr>'
    + '<tr><td>Recent 5-yr share</td><td class="num">'+t.recent_pct+'%</td></tr>'
    + '<tr><td>Citizen-science surge</td><td class="num">'
    +(t.cs_surge?'yes':'no')+'</td></tr></table>'
    + (gapChips? '<div class="gaps">'+gapChips+'</div>' : '');
}

function kbaHTML(d){
  const k=d.distribution_kba;
  if(!k) return '<div class="note">Not enough georeferenced records.</div>';
  const kb=k.kba;
  const chipsHtml =
    (kb.b1_meets?'<span class="chip ok">B1 met</span>':'<span class="chip">B1 no</span>')
    + (kb.b2_meets?'<span class="chip ok">B2 met</span>':'<span class="chip">B2 no</span>');
  return '<table><colgroup/><tr><th>Metric</th><th style="text-align:right">Value</th></tr>'
    + '<tr><td>Extent of Occurrence</td><td class="num">'
    +k.eoo_km2.toLocaleString(undefined,{maximumFractionDigits:0})+' km²</td></tr>'
    + '<tr><td>Area of Occupancy</td><td class="num">'
    +k.aoo_km2.toLocaleString()+' km² ('+k.aoo_cells+' cells)</td></tr>'
    + '</table><div style="margin-top:6px">'+chipsHtml+'</div>'
    + '<div class="note">'+esc(k.caveat||'')+'</div>'
    + (k.hull_warnings||[]).map(w=>
      '<div class="note poor">Caution: '+esc(w)+'</div>').join('');
}

function sdmHTML(fit){
  if(!(fit && fit.gates && fit.gates.length))
    return '<div class="note">Not available for this sample.</div>';
  return '<div class="note" style="margin-bottom:4px">Profile: '
    + esc(fit.profile) + '</div>'
    + '<table><colgroup/><tr><th>Gate</th><th style="text-align:right">Pass</th>'
    + '<th style="text-align:right">Fail</th></tr>'
    + fit.gates.map(g=>'<tr><td>'+esc(g.gate)
      +(g.critical?'':' <span class="chip">soft</span>')+'</td>'
      +'<td class="num good">'+Number(g.pass).toLocaleString()+'</td>'
      +'<td class="num '+(g.fail>0?'poor':'')+'">'
      +Number(g.fail).toLocaleString()+'</td></tr>').join('')
    + '</table><div class="cite">'
    + (()=>{ const c=fit.citations;   // dict | array | string
        if(Array.isArray(c)) return c.map(x=>esc(x)).join(' · ');
        if(c && typeof c==='object')
          return Object.values(c).map(x=>esc(x)).join(' · ');
        return c?esc(c):''; })()
    + '</div>';
}

function esc(s){
  return String(s==null?'':s)
    .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

function popupHTML(p){
  const flagged = p.biosift_flag===true || p.biosift_flag==='true';
  const rows = [
    ['Species', '<i>'+esc(p.species)+'</i>'],
    ['Year', esc(p.year!=null?p.year:'n/a')],
    ['Country', esc(p.country||'n/a')],
    ['Basis', esc(String(p.basisOfRecord||'n/a').replace(/_/g,' '))],
    ['Dataset', esc(p.datasetName||'n/a')],
  ];
  if(p.coordinateUncertaintyInMeters!=null){
    rows.push(['Coord. uncertainty',
      Math.round(p.coordinateUncertaintyInMeters).toLocaleString()+' m']);
  }
  let html = '<div class="pop-t">'+esc(p.species)+'</div>'
    + rows.map(r=>'<div class="pop-r"><span>'+r[0]
      +'</span><span>'+r[1]+'</span></div>').join('');
  const flags = Array.isArray(p.biosift_flags) ? p.biosift_flags
    : (()=>{ try{ return JSON.parse(p.biosift_flags||'[]'); }
             catch(e){ return []; } })();
  if(flags.length){
    html += '<div class="pop-f">'
      + flags.map(f=>'<span class="chip bad">'+esc(prettyFlag(f))
        +'</span>').join('')
      + '</div>';
  }else{
    html += '<div class="pop-f"><span class="chip ok">Passes all BDQ checks</span></div>';
  }
  if(p.ex===true || p.ex===1 || p.ex==='1'){
    html += '<div class="pop-f"><span class="chip bad">Excluded by '
      +'profile</span></div>';
  }
  if(p.occurrenceID){
    html += '<div class="pop-f"><a href="'+esc(p.occurrenceID)
      +'" target="_blank" rel="noopener" style="color:var(--blue);'
      +'font-size:11px">Open source record</a></div>';
  }
  return html;
}

function pushGeo({points, hull}){
  window.__lastGeo = {points, hull};
  if(!mapReady) return;
  // a popup tied to the previous dataset is stale — drop it
  try{ popup.remove(); }catch(e){}
  // a period overlay belongs to the previous dataset — drop it too
  clearPeriodLayers();
  const pb=document.getElementById('btn-periods');
  if(pb) pb.textContent='Overlay periods on map';
  // MapLibre v4 removeLayer/removeSource return void (not Promises) —
  // guard with getLayer/getSource, never .catch()
  ['occ-heat','occ-hull-fill','occ-hull-line','occ-pt-fill',
   'occ-pt-stroke','clusters','cluster-count']
    .forEach(id=>{ try{ if(map.getLayer(id)) map.removeLayer(id); }catch(e){} });
  if(map.getSource('occ')){ try{ map.removeSource('occ'); }catch(e){} }
  if(map.getSource('hull')){ try{ map.removeSource('hull'); }catch(e){} }

  // cluster source — official MapLibre clustering pattern; leaves
  // carry the per-record properties used by the popup. clusterProperties
  // sums each leaf's fl (flagged 1/0) into `flagged` for cluster tint.
  map.addSource('occ', {
    type:'geojson', data:points,
    cluster:true, clusterRadius:40, clusterMaxZoom:8,
    clusterProperties:{flagged:['+',['get','fl']]},
  });
  map.addLayer({
    id:'clusters', type:'circle', source:'occ',
    filter:['has','point_count'],
    paint:{
      'circle-color':['case',
        ['>', ['/', ['coalesce',['get','flagged'],0],
               ['max',['get','point_count'],1]], 0.34],
        '#B23A2E',
        '#1E7A54'],
      'circle-radius':15,'circle-opacity':0.85,
      'circle-stroke-width':1,'circle-stroke-color':'rgba(255,255,255,.7)',
    },
  });
  map.addLayer({
    id:'cluster-count', type:'symbol', source:'occ',
    filter:['has','point_count'],
    layout:{
      'text-field':['get','point_count_abbreviated'],
      'text-font':['Noto Sans Regular'],'text-size':11,
    },
    paint:{'text-color':'#FFFFFF'},
  });
  map.addLayer({
    id:'occ-pt-stroke', type:'circle', source:'occ',
    filter:['!',['has','point_count']], paint:{
      'circle-radius':6.5,'circle-color':'#000','circle-opacity':0.18},
  });
  map.addLayer({
    id:'occ-pt-fill', type:'circle', source:'occ',
    filter:['!',['has','point_count']], paint:{
      'circle-radius':4.5,
      'circle-color':['get','color'],
      'circle-opacity':0.85,
      'circle-stroke-width':0.8,
      'circle-stroke-color':'rgba(0,0,0,0.5)',
    },
  });
  if(hull){
    map.addSource('hull', {type:'geojson', data:hull});
    map.addLayer({
      id:'occ-hull-fill', type:'fill', source:'hull', paint:{
        'fill-color':ACC,'fill-opacity':0.07},
    });
    map.addLayer({
      id:'occ-hull-line', type:'line', source:'hull', paint:{
        'line-color':ACC,'line-width':1.4,'line-dasharray':[3,2],
        'line-opacity':0.9},
    });
  }
}

async function run(){
  const btn=document.getElementById('run');
  const status=document.getElementById('status');
  const species=document.getElementById('species').value.trim();
  if(!species){ status.textContent='Enter a scientific name.'; return; }
  btn.disabled=true;
  status.className='status';
  let secs=0;
  const tick=setInterval(()=>{
    secs+=1;
    if(status.textContent.startsWith('Fetching'))
      status.textContent='Fetching from GBIF and running checks… ('
        + secs + 's)';
  },1000);
  status.textContent='Fetching from GBIF and running checks… (0s)';

  const q=new URLSearchParams({
    limit: document.getElementById('limit').value,
    year_from: document.getElementById('yf').value,
    year_to: document.getElementById('yt').value,
    basis: document.getElementById('basis').value,
    fitness_profile: document.getElementById('profile').value,
    include_records: 'true',
  });

  try{
    const r=await fetch(`/api/analysis/${encodeURIComponent(species)}?${q}`);
    if(!r.ok){
      const e=await r.json().catch(()=>({detail:r.statusText}));
      throw new Error(typeof e.detail==='string'?e.detail:'analysis failed');
    }
    const d=await r.json();
    window.__bundle=d;
    render(d);
    status.textContent='Analysis complete: '
      + d.scores.records_analysed.toLocaleString()+' records, '
      + new Date(d.generated_utc).toLocaleTimeString();
  }catch(e){
    status.className='status err'; status.textContent='Error: '+e.message;
  }finally{
    clearInterval(tick);
    btn.disabled=false;
  }
}

function pctClass(p){ return p>=80?'good':(p>=50?'fair':'poor'); }

function sparkline(counts){
  if(!counts || counts.length<2) return '';
  const W=340, H=54, P=4;
  const ys=counts.map(c=>c.year), ns=counts.map(c=>c.count);
  const y0=ys[0], y1=ys[ys.length-1];
  const nMax=Math.max.apply(null, ns);
  const x=i=>P+(W-2*P)*(y1===y0?0.5:(ys[i]-y0)/(y1-y0));
  const y=v=>H-P-(H-2*P)*(nMax?v/nMax:0);
  let d='M '+x(0).toFixed(1)+' '+y(ns[0]).toFixed(1);
  for(let i=1;i<ys.length;i++) d+=' L '+x(i).toFixed(1)+' '+y(ns[i]).toFixed(1);
  d+=' L '+x(ys.length-1).toFixed(1)+' '+(H-P)+' L '+x(0).toFixed(1)
    +' '+(H-P)+' Z';
  const mid=ys[Math.floor(ys.length/2)];
  return '<svg class="spark" viewBox="0 0 '+W+' '+H
    +'" preserveAspectRatio="none">'
    +'<line class="axis" x1="0" x2="'+W+'" y1="'+(H-P)+'" y2="'+(H-P)+'"/>'
    +'<path d="'+d+'"/>'
    +'</svg>'
    +'<div class="note mono">'+y0+' to '+y1+' · peak '
    +nMax+' in '+ys[ns.indexOf(nMax)]+'</div>';
}

/* ── charts ────────────────────────────────────────────────────
   Server sends the numbers; these render them as SVG / CSS bars
   so the figures inherit the app's palette and fonts. */
function heatmapHTML(vars, cells, o){
  o=o||{};
  const n=vars.length, left=o.left||88, top=o.top||64, cell=o.cell||26;
  // right margin leaves room for the rotated column labels
  const W=left+n*cell+46, H=top+n*cell+6;
  let s='<svg class="chart" viewBox="0 0 '+W+' '+H+'" role="img">';
  vars.forEach((v,i)=>{
    const x=left+i*cell+cell/2;
    s+='<text class="ax" x="'+x+'" y="'+(top-10)
      +'" transform="rotate(-55 '+x+' '+(top-10)+')" text-anchor="start">'
      +esc(v.short||v.label)+'</text>';
  });
  vars.forEach((v,i)=>{
    s+='<text class="ax" x="'+(left-6)+'" y="'
      +(top+i*cell+cell/2+3)+'" text-anchor="end">'
      +esc(v.short||v.label)+'</text>';
    vars.forEach((w,j)=>{
      const val=(cells[i]||[])[j];
      const x=left+j*cell, y=top+i*cell;
      let fill='#EDE9DC';
      if(val!=null){
        const a=(0.10+0.75*Math.min(1,Math.abs(val))).toFixed(2);
        fill=(val>=0?'rgba(19,111,78,':'rgba(29,95,168,')+a+')';
      }
      s+='<rect x="'+x+'" y="'+y+'" width="'+(cell-2)+'" height="'+(cell-2)
        +'" rx="1.5" fill="'+fill+'" stroke="#D6CFBC" stroke-width=".5">'
        +'<title>'+esc(v.label+' / '+w.label+': '
          +(val!=null?val.toFixed(2):'too few pairs'))+'</title></rect>';
      if(val!=null){
        s+='<text class="celltx" x="'+(x+cell/2-1)+'" y="'+(y+cell/2+3)
          +'" text-anchor="middle"'
          +(Math.abs(val)>0.62?' fill="#FBF9F2"':'')+'>'
          +val.toFixed(2)+'</text>';
      }
    });
  });
  return s+'</svg>';
}

function flagBars(rows, note){
  const max=Math.max.apply(null, rows.map(r=>r.records).concat([1]));
  return '<div class="bars">'
    + rows.map(r=>{
        const w=Math.max(1,Math.round(r.records/max*100));
        const fw=Math.round(w*(r.flag_pct||0)/100);
        return '<div class="barrow"><span class="bl">'+esc(r.label)
          +'</span><span class="btrack"><i style="width:'+w+'%"></i>'
          +'<b style="width:'+fw+'%"></b></span><span class="bv">'
          +Number(r.records).toLocaleString()
          +(r.flag_pct!=null?' · '+r.flag_pct+'%':'')+'</span></div>';
      }).join('')
    + '</div>'
    + (note?'<div class="cite">'+esc(note)+'</div>':'');
}

function distBars(rows, note){
  const max=Math.max.apply(null, rows.map(r=>r.count).concat([1]));
  return '<div class="bars">'
    + rows.map(r=>{
        const w=r.count?Math.max(1,Math.round(r.count/max*100)):0;
        return '<div class="barrow"><span class="bl">'+esc(r.label)
          +'</span><span class="btrack"><i class="acc" style="width:'+w
          +'%"></i></span><span class="bv">'
          +Number(r.count).toLocaleString()+'</span></div>';
      }).join('')
    + '</div>'
    + (note?'<div class="cite">'+esc(note)+'</div>':'');
}

function patternsHTML(p){
  if(!p) return '<div class="note">No chart data for this dataset.</div>';
  let h='';
  const c=p.correlation;
  if(c && c.variables && c.variables.length>=2 && c.cells){
    h+='<div class="note" style="margin-bottom:2px"><b>Attributes that '
      +'move together</b></div>'
      + heatmapHTML(c.variables, c.cells, {left:88, top:64, cell:26})
      + '<div class="chartlegend">'
      + '<span><i style="background:#136F4E"></i>positive</span>'
      + '<span><i style="background:#1D5FA8"></i>negative</span>'
      + '<span>Pearson r</span></div>'
      + '<div class="cite">'+esc(c.method||'')+'</div>';
  }
  const co=p.cooccurrence;
  if(co && co.checks && co.checks.length>=2 && co.cells){
    h+='<div class="note" style="margin:12px 0 2px"><b>Checks that fire '
      +'together</b></div>'
      + heatmapHTML(co.checks, co.cells, {left:88, top:64, cell:26})
      + '<div class="chartlegend">'
      + '<span><i style="background:#136F4E"></i>Jaccard overlap</span>'
      + '</div><div class="cite">'+esc(co.method||'')+'</div>';
  }
  const dec=p.decades||[];
  if(dec.length>=2){
    h+='<div class="note" style="margin:12px 0 2px"><b>Flag rate by decade</b>'
      +'</div>'+flagBars(dec,
        'Bar length = records; amber share = flagged records.');
  }
  const cd=p.completeness_dist||[];
  if(cd.length){
    h+='<div class="note" style="margin:12px 0 2px"><b>Record completeness</b>'
      +'</div>'+distBars(cd,
        'Share of ten scored Darwin Core fields present, per record.');
  }
  const cat=p.categorical||{};
  if(cat.by_country && cat.by_country.length>=2){
    h+='<div class="note" style="margin:12px 0 2px"><b>Flag rate by '
      +'country</b></div>'+flagBars(cat.by_country,
        'Amber share = flagged records in that country.');
  }
  if(cat.by_basis && cat.by_basis.length>=2){
    h+='<div class="note" style="margin:12px 0 2px"><b>Basis of record</b>'
      +'</div>'+flagBars(cat.by_basis,
        'Amber share = flagged records for that basis.');
  }
  return h || '<div class="note">Not enough records for charts.</div>';
}

/* ── species analysis: factsheet, seasonality, range shift,
   effort-aware trend, climate envelope ─────────────────────── */
const MONTHNAMES=['January','February','March','April','May','June',
  'July','August','September','October','November','December'];

function factsheetHTML(f){
  if(!f || !f.available)
    return '<div class="note">Taxonomy unavailable: '
      + esc((f && f.reason) || 'no data') + '</div>';
  const tax=(f.taxonomy||[]).map(r=>
    '<tr><td style="color:var(--faint);text-transform:capitalize">'
    + esc(r.rank) + '</td><td'
    + (r.rank==='species' ? ' style="font-style:italic"' : '')
    + '>' + esc(r.name) + '</td></tr>').join('');
  let h='<table><colgroup/>' + tax + '</table>';
  h+='<div class="note">' + esc(f.scientific_name)
    + (f.authorship ? ' <span class="mono">' + esc(f.authorship) + '</span>' : '')
    + (f.taxonomic_status ? ' <span class="chip ok">' + esc(f.taxonomic_status) + '</span>' : '')
    + (f.rank ? ' <span class="chip">' + esc(f.rank) + '</span>' : '')
    + (f.extinct ? ' <span class="chip bad">extinct</span>' : '') + '</div>';
  const line=(label, items, cls)=>{
    if(!items || !items.length) return '';
    return '<div class="note" style="margin-top:6px"><b>' + label
      + '</b>: ' + items.map(x=>'<span class="chip'
        + (cls ? ' ' + cls : '') + '">' + esc(x) + '</span>').join('')
      + '</div>';
  };
  h += line('Synonyms in backbone (' + (f.synonyms_total||0) + ')', f.synonyms);
  h += line('Common names', f.common_names);
  h += line('Habitat', f.habitats, 'ok');
  h += line('Threat status', f.threat_status, 'warn');
  if(f.source_dataset || f.gbif_url){
    h+='<div class="cite">Backbone: ' + esc(f.source_dataset || 'GBIF')
      + (f.gbif_url ? ' · <a href="' + esc(f.gbif_url)
        + '" target="_blank" rel="noopener" style="color:var(--blue)">'
        + 'Open on GBIF</a>' : '') + '</div>';
  }
  return h;
}

function phenologyHTML(p){
  if(!p || !p.counts || !p.total)
    return '<div class="note">Not enough dated records for a '
      + 'seasonality profile.</div>';
  const max=Math.max.apply(null, p.counts) || 1;
  const L=['J','F','M','A','M','J','J','A','S','O','N','D'];
  const bars=p.counts.map((c,i)=>
    '<span class="mb" title="' + MONTHNAMES[i] + ': ' + c + ' records ('
    + (c/p.total*100).toFixed(1) + '%)"><i style="height:'
    + Math.round(c/max*100) + '%"></i><span>' + L[i] + '</span></span>').join('');
  return '<div class="months">' + bars + '</div>'
    + '<div class="note mono">peak ' + MONTHNAMES[p.peak_month-1] + ' · '
    + p.peak_pct + '% of ' + p.total.toLocaleString() + ' dated records</div>'
    + '<div class="cite">' + esc(p.method) + '</div>';
}

function trendHTML(t){
  if(!t || !t.series || t.series.length<4)
    return '<div class="note">Not enough year-on-year coverage for an '
      + 'effort-aware index.</div>';
  const s=t.series, W=340, H=84, P=10;
  const xs=s.map(r=>r.year);
  const ys=s.map(r=>Math.min(r.index, 250));
  const x0=xs[0], x1=xs[xs.length-1];
  const ymax=Math.max(150, Math.max.apply(null, ys)) * 1.05;
  const X=i=>P+(W-2*P)*(x1===x0 ? 0.5 : (xs[i]-x0)/(x1-x0));
  const Y=v=>H-P-(H-2*P)*(v/ymax);
  let d='M ' + X(0).toFixed(1) + ' ' + Y(ys[0]).toFixed(1);
  for(let i=1;i<xs.length;i++)
    d+=' L ' + X(i).toFixed(1) + ' ' + Y(ys[i]).toFixed(1);
  const base=Y(100).toFixed(1);
  return '<svg class="trend" viewBox="0 0 ' + W + ' ' + H + '" role="img">'
    + '<line class="base" x1="' + P + '" x2="' + (W-P) + '" y1="' + base
    + '" y2="' + base + '"/>'
    + '<path class="line" d="' + d + '"/>'
    + '<text class="ax" x="' + P + '" y="' + (H-2) + '">' + x0 + '</text>'
    + '<text class="ax" x="' + (W-P) + '" y="' + (H-2)
    + '" text-anchor="end">' + x1 + '</text>'
    + '</svg>'
    + '<div class="note mono">dashed line = long-term median (100) · '
    + 'latest ' + s[s.length-1].index + '</div>'
    + (t.targeted ? '<div class="note mono">'
        + esc(t.targeted.span || '') + ' · '
        + t.targeted.years_sampled + ' years probed</div>' : '')
    + '<div class="cite">' + esc(t.method) + '</div>'
    + '<div class="cite">' + esc(t.caveat) + '</div>';
}

function rangeShiftHTML(rs){
  if(!rs || !rs.available)
    return '<div class="note">Change-over-time comparison unavailable: '
      + esc((rs && rs.reason) || 'not enough dated records') + '</div>';
  const A=rs.period_a, B=rs.period_b, s=rs.shift, t=rs.turnover;
  const row=(k,v)=>'<tr><td>' + k + '</td><td class="num">' + v + '</td></tr>';
  return '<table><colgroup/>'
    + '<tr><th>Measure</th><th style="text-align:right">Value</th></tr>'
    + row('Period A, early (' + A.year_median + ' median)',
        A.records.toLocaleString() + ' rec · ' + A.year_min + '–' + A.year_max)
    + row('Period B, late (' + B.year_median + ' median)',
        B.records.toLocaleString() + ' rec · ' + B.year_min + '–' + B.year_max)
    + row('Centroid shift', '<b>' + s.centroid_km.toLocaleString() + ' km</b>')
    + row('North / south component', (s.north_km>0?'+':'') + s.north_km
        + ' km · ' + esc(s.direction))
    + row('East / west component', (s.east_km>0?'+':'') + s.east_km + ' km')
    + row('Lat. extent A → B', A.lat_extent + '° → ' + B.lat_extent + '° ('
        + (s.lat_extent_delta>0?'+':'') + s.lat_extent_delta + '°)')
    + row('1° cells shared / A only / B only',
        t.shared + ' / ' + t.only_a + ' / ' + t.only_b
        + ' (Jaccard ' + t.jaccard + ')')
    + '</table>'
    + '<button class="sbtn" id="btn-periods">Overlay periods on map</button>'
    + '<div class="note mono">blue = period A, ochre = period B; '
    + 'verdict points hide while the overlay is on</div>'
    + '<div class="cite">' + esc(rs.method) + '</div>'
    + (rs.targeted ? '<div class="cite">Probed early: '
        + esc((rs.targeted.early_years||[]).join(', ')) + ' · late: '
        + esc((rs.targeted.late_years||[]).join(', ')) + '. '
        + esc(rs.targeted.note || '') + '</div>' : '')
    + '<div class="cite" style="color:var(--amber)">' + esc(rs.caveat) + '</div>';
}

function envChart(temp, prec, months){
  const W=340, H=92, P=10;
  const good=v=>v!=null && isFinite(v);
  const tv=temp.filter(good), pv=prec.filter(good);
  if(!tv.length) return '';
  const tmax=Math.max.apply(null, tv)+2, tmin=Math.min.apply(null, tv)-2;
  const span=Math.max(1, tmax-tmin);
  const pmax=Math.max.apply(null, pv.concat([1]));
  const X=i=>P+(W-2*P)*(i/11);
  const YT=v=>H-P-(H-2*P)*((v-tmin)/span);
  let path='';
  temp.forEach((v,i)=>{ if(!good(v)) return;
    path+=(path?' L ':'M ')+X(i).toFixed(1)+' '+YT(v).toFixed(1); });
  let bars='';
  prec.forEach((v,i)=>{ if(!good(v)) return;
    const h=Math.max(1, Math.round((H-2*P)*(v/pmax)));
    bars+='<rect x="'+(X(i)-5)+'" y="'+(H-P-h)+'" width="10" height="'+h
      +'" fill="rgba(29,95,168,.26)"><title>' + months[i] + ': ' + v
      +' mm</title></rect>'; });
  return '<svg class="trend" viewBox="0 0 ' + W + ' ' + H + '" role="img">'
    + bars
    + '<line class="base" x1="'+P+'" x2="'+(W-P)+'" y1="'+(H-P)
    +'" y2="'+(H-P)+'"/>'
    + '<path class="line" d="'+path+'"/></svg>'
    + '<div class="chartlegend"><span class="mono">blue bars: monthly '
    + 'precipitation (mm) · line: temperature (°C)</span></div>';
}

function envelopeHTML(e){
  if(!e || !e.available)
    return '<div class="note">Climate envelope unavailable: '
      + esc((e && e.reason) || 'no data') + '</div>';
  const rng=(v,u)=> v ? v.min + '–' + v.max + ' ' + u + ' (median '
      + v.median + ')' : 'n/a';
  let h='<table><colgroup/>'
    + '<tr><th>Variable</th><th style="text-align:right">Across records</th></tr>'
    + '<tr><td>Mean annual temperature</td><td class="num">'
    + rng(e.temp_annual_c, '°C') + '</td></tr>'
    + '<tr><td>Annual precipitation</td><td class="num">'
    + rng(e.precip_annual_mm, 'mm') + '</td></tr>'
    + '<tr><td>Elevation</td><td class="num">'
    + rng(e.elevation_m, 'm') + '</td></tr></table>';
  if(e.monthly_temp_c && e.monthly_temp_c.length && e.months)
    h+=envChart(e.monthly_temp_c, e.monthly_precip_mm || [], e.months);
  h+='<div class="note mono">sampled ' + e.points_sampled
    + ' record locations</div>'
    + '<div class="cite">' + esc(e.method) + '</div>'
    + '<div class="cite">' + esc(e.note) + '</div>';
  return h;
}

function renderNewSections(d, withFactsheet){
  if(withFactsheet){
    document.getElementById('factsheet').innerHTML = factsheetHTML(d.factsheet);
    setCount('cnt-fact', d.factsheet && d.factsheet.available
      ? (d.factsheet.synonyms_total || 0) + ' backbone synonyms'
      : 'n/a');
  }
  const p=d.patterns || {};
  document.getElementById('phenology').innerHTML = phenologyHTML(p.phenology);
  setCount('cnt-phen', p.phenology
    ? MONTHNAMES[p.phenology.peak_month-1] + ' peak' : 'n/a');
  window.__rangeShift = d.rangeshift || null;
  document.getElementById('rangeshift').innerHTML = rangeShiftHTML(d.rangeshift);
  setCount('cnt-shift', d.rangeshift && d.rangeshift.available
    ? d.rangeshift.shift.centroid_km.toLocaleString() + ' km shift'
    : 'n/a');
  document.getElementById('trend').innerHTML = trendHTML(p.trend);
  setCount('cnt-trend', p.trend ? p.trend.series.length + ' years' : 'n/a');
  document.getElementById('envelope').innerHTML = envelopeHTML(d.envelope);
  setCount('cnt-env', d.envelope && d.envelope.available
    ? d.envelope.points_sampled + ' points' : 'n/a');
}

function clearPeriodLayers(){
  ['per-a','per-b'].forEach(id=>{
    try{ if(map.getLayer(id)) map.removeLayer(id); }catch(e){}
    try{ if(map.getSource(id)) map.removeSource(id); }catch(e){}
  });
  ['occ-pt-fill','occ-pt-stroke','clusters','cluster-count'].forEach(id=>{
    try{ if(map.getLayer(id)) map.setLayoutProperty(id,'visibility','visible'); }
    catch(e){}
  });
}

function coordsOk(c){
  const lon=Number(c[0]), lat=Number(c[1]);
  return isFinite(lat) && isFinite(lon)
    && Math.abs(lat)<=90 && Math.abs(lon)<=180;
}

function point(c, col){
  return {type:'Feature',
    geometry:{type:'Point', coordinates:[Number(c[0]), Number(c[1])]},
    properties:{color: col}};
}

function togglePeriodOverlay(){
  if(!mapReady || !window.__rangeShift || !window.__rangeShift.available) return;
  const btn=document.getElementById('btn-periods');
  if(map.getLayer && map.getLayer('per-a')){
    clearPeriodLayers();
    if(btn) btn.textContent='Overlay periods on map';
    return;
  }
  const rs=window.__rangeShift;
  // prefer the exact coordinates the shift was computed from — the map
  // sample is newest-first and may hold no records in either period
  const feats=[];
  const pts=rs.points || null;
  if(pts && ((pts.a||[]).length || (pts.b||[]).length)){
    (pts.a||[]).forEach(c=>{
      if(coordsOk(c)) feats.push(point(c,'#1D5FA8'));
    });
    (pts.b||[]).forEach(c=>{
      if(coordsOk(c)) feats.push(point(c,'#75530F'));
    });
  }else{
    const gj=(window.__bundle && window.__bundle.geojson
              && window.__bundle.geojson.features) || null;
    const recs=(window.__bundle && window.__bundle.records
                && window.__bundle.records.analysed) || null;
    const src = gj || (recs||[]).map(r=>({
      geometry:{type:'Point', coordinates:[r.decimalLongitude, r.decimalLatitude]},
      properties:{year:r.year}
    }));
    src.forEach(f=>{
      const g=f.geometry;
      if(!g || !g.coordinates) return;
      if(!coordsOk(g.coordinates)) return;
      const y=(f.properties && f.properties.year!=null)
        ? Number(f.properties.year) : null;
      if(y==null) return;
      const inB = y>=rs.period_b.year_min && y<=rs.period_b.year_max;
      const inA = y>=rs.period_a.year_min && y<=rs.period_a.year_max;
      if(!inA && !inB) return;
      feats.push(point(g.coordinates, inB ? '#75530F' : '#1D5FA8'));
    });
  }
  if(!feats.length) return;
  clearPeriodLayers();
  ['occ-pt-fill','occ-pt-stroke','clusters','cluster-count'].forEach(id=>{
    try{ if(map.getLayer(id)) map.setLayoutProperty(id,'visibility','none'); }
    catch(e){}
  });
  ['per-a','per-b'].forEach((id, idx)=>{
    const col = idx===0 ? '#1D5FA8' : '#75530F';
    const data={type:'FeatureCollection',
      features:feats.filter(f=>f.properties.color===col)};
    if(!data.features.length) return;
    try{ if(map.getLayer(id)) map.removeLayer(id); }catch(e){}
    try{ if(map.getSource(id)) map.removeSource(id); }catch(e){}
    map.addSource(id, {type:'geojson', data:data});
    map.addLayer({id:id, type:'circle', source:id, paint:{
      'circle-radius':6.5, 'circle-color':col, 'circle-opacity':0.9,
      'circle-stroke-width':1, 'circle-stroke-color':'rgba(255,255,255,.85)'
    }});
  });
  if(btn) btn.textContent='Show BDQ verdict points';
}

function recipeSlug(){
  return (document.getElementById('species').value.trim()
    .replace(/\s+/g, '_') || 'analysis');
}

function qStr(v){
  return "'" + String(v==null ? '' : v)
    .replace(/\\/g, '\\\\').replace(/'/g, "\\'") + "'";
}

function buildScript(lang){
  const b=window.__bundle || {};
  const q=b.query || {};
  const sp=q.species || document.getElementById('species').value.trim();
  const yr=qStr((q.year_from || 1900) + ',' + (q.year_to || 2026));
  const lim=q.limit || 500;
  const basis=(q.basis && q.basis!=='All')
    ? '  basisOfRecord = ' + qStr(q.basis) + ',' : '';
  const head=[
    '# BioSift recipe — regenerate the analysis for ' + sp,
    '# ' + (b.scores ? b.scores.records_analysed : '') + ' records, years '
      + (q.year_from || '') + '-' + (q.year_to || '') + ', basis '
      + (q.basis || 'All'),
    '# Generated ' + (b.generated_utc || new Date().toISOString())
      + ' from the BioSift analysis bundle.', ''
  ];
  if(lang==='r'){
    return head.concat([
      'library(rgbif)',
      '',
      'occ <- occ_search(',
      '  scientificName = ' + qStr(sp) + ',',
      '  year = ' + yr + ',',
      basis,
      '  limit = ' + lim + ',',
      '  hasCoordinate = TRUE',
      ')',
      '',
      '# Quality: rerun the checks BioSift reported (TDWG BDQ vocabulary',
      '# plus CoordinateCleaner-style geography, Zizka et al. 2019):',
      '# install.packages("CoordinateCleaner")',
      '# cc <- clean_coordinates(occ$data, lon = "decimalLongitude",',
      '#   lat = "decimalLatitude", species = "species",',
      '#   country = "countryCode")',
      '',
      '# Citation: GBIF data must be cited with a download DOI.',
      '# Register once at https://www.gbif.org, then:',
      '#   key <- occ_download(...)',
      '#   gbif_citation(occ_download_meta(key))'
    ]).filter(l=>l!==undefined).join('\n');
  }
  return head.concat([
    '# BioSift recipe (pygbif): pip install pygbif pandas',
    'from pygbif import occurrences as occ',
    '',
    'data = occ.search(',
    '    scientificName=' + qStr(sp) + ',',
    '    year=' + yr + ',',
    basis ? '    basisOfRecord=' + qStr(q.basis) + ',' : '',
    '    limit=' + lim + ',',
    '    hasCoordinate=True,',
    ')',
    'df = occ.gbif_to_df(data)',
    '',
    '# Quality: the checks BioSift reported (TDWG BDQ +',
    '# CoordinateCleaner-style geography, Zizka et al. 2019).',
    '# Cite the data with a GBIF download DOI (gbif.org → download).'
  ]).filter(l=>l!==undefined).join('\n');
}

function render(d){
  document.getElementById('results').style.display='block';
  document.getElementById('exports').style.display='block';
  document.getElementById('capabilities').style.display='none';
  document.getElementById('audience').style.display='none';
  const s=d.scores;
  document.getElementById('m-total').textContent=s.gbif_total_matching.toLocaleString();
  document.getElementById('m-analysed').textContent=s.records_analysed.toLocaleString();
  document.getElementById('m-completeness').textContent=
    s.completeness_pct!=null ? 'completeness '+s.completeness_pct+'%' : 'live sample';
  const hv=document.getElementById('m-health');
  hv.textContent=s.health_pct+'%';
  hv.className='v '+pctClass(s.health_pct);
  document.getElementById('m-healthbar').style.width=Math.min(s.health_pct,100)+'%';
  const fit=d.sdm_readiness;
  const sv=document.getElementById('m-sdm');
  sv.textContent=fit? fit.ready_records.toLocaleString() : 'n/a';
  sv.className='v '+ (fit&&fit.verdict==='READY'?'good':(fit&&fit.verdict==='CONDITIONAL'?'fair':'poor'));
  document.getElementById('m-sdmnote').textContent= fit?
    `${fit.retention_pct}% retention · ${fit.verdict}` : '';

  // species bar
  const bar=document.getElementById('speciesbar');
  bar.style.display='block';
  document.getElementById('sb-name').textContent=d.species.scientific_name;
  const chips=[];
  if(d.species.iucn_category){
    chips.push(`<span class="chip warn">IUCN ${d.species.iucn_category.replace(/_/g,' ')}</span>`);
  }
  chips.push(`<span class="chip">${s.records_clean.toLocaleString()} clean</span>`);
  document.getElementById('sb-chips').innerHTML=chips.join('');

  // checks table
  document.getElementById('t-checks').innerHTML =
    '<tr><th>Check</th><th>BDQ test</th><th style="text-align:right">Flagged</th><th style="text-align:right">%</th></tr>'
    + d.quality_checks.map(c=>`
      <tr>
        <td>${c.label}</td>
        <td class="mono" style="font-size:9px">${c.bdq_test.split(' · ')[0]}</td>
        <td class="num">${c.flagged.toLocaleString()}</td>
        <td class="num ${c.percent>10?'poor':(c.percent>0?'warn':'good')}">${c.percent}%</td>
      </tr>`).join('');

  // benchmark
  const bm=d.benchmark||[];
  document.getElementById('benchmark').innerHTML = bm.length? bm.map(b=>`
    <div style="display:flex;justify-content:space-between;gap:12px;padding:4px 0;border-bottom:1px solid var(--line)">
      <span>${b.label}</span>
      <span class="mono" style="text-align:right">${b.sample_pct}% vs ${b.population_pct}% (Δ${b.delta>0?'+':''}${b.delta} pp): ${b.verdict}</span>
    </div>`).join('')
    : 'Baseline unavailable for this query.';

  document.getElementById('temporal').innerHTML = temporalHTML(d);

  document.getElementById('patterns').innerHTML = patternsHTML(d.patterns);
  const figs=document.querySelectorAll('#patterns svg, #patterns .bars').length;
  setCount('cnt-patterns', figs? figs+' figures' : 'none');
  renderNewSections(d, true);

  document.getElementById('kba').innerHTML = kbaHTML(d);

  // community (GBIF mode only — element hidden in BYOD mode)
  const com=document.getElementById('community');
  const inter=d.interactions||{total:0,by_type:[]};
  const coo=d.cooccurrence;
  let html='';
  if(inter.by_type && inter.by_type.length){
    html += '<div class="note" style="margin-bottom:6px"><b>GloBI interactions</b>: '
      + inter.by_type.slice(0,6).map(t=>`${t.label}: ${t.count}`).join(' · ')
      + ` (n=${inter.total})</div>`;
  }else{
    html += '<div class="note">No GloBI interaction records.</div>';
  }
  if(coo && coo.partners && coo.partners.length){
    html += `<div class="note"><b>Congeneric co-occurrence</b> (Jaccard, 1° grid), genus <i>${coo.genus}</i> (${coo.assemblage_size} species):</div>
      <table><colgroup/><tr><th>Congener</th><th style="text-align:right">Overlap</th></tr>`
      + coo.partners.slice(0,6).map(p=>`
        <tr><td style="font-style:italic">${p.species}</td>
        <td class="num">${p.overlap==null?'n/a':p.overlap} <span class="chip ${p.overlap==null?'':(p.overlap>=0.4?'ok':(p.overlap>=0.15?'warn':''))}">${p.jaccard_label}</span></td></tr>`).join('')
      + '</table>';
  }
  com.innerHTML=html || '<div class="note">No community data.</div>';

  // carbon (plants only)
  const cb=d.carbon;
  const cel=document.getElementById('carbon');
  if(!cb){
    cel.innerHTML='<div class="note">No data.</div>';
  }else if(!cb.applicable){
    cel.innerHTML='<div class="note">'+(cb.note||'Not applicable for this taxon.')+'</div>';
  }else{
    const t=cb.sample_totals, e=cb.equivalences;
    cel.innerHTML=`
      <table>
        <colgroup/>
        <tr><th>Metric</th><th style="text-align:right">Value</th></tr>
        <tr><td>Standing-stock CO₂e</td><td class="num">${t.co2e_t.toLocaleString()} t</td></tr>
        <tr><td>Total carbon</td><td class="num">${t.carbon_t.toLocaleString()} t C</td></tr>
        <tr><td>Annual sequestration</td><td class="num">${t.annual_sequestration_co2e_t.toLocaleString()} t/yr</td></tr>
        <tr><td>Car-travel equivalent</td><td class="num">${e.car_km.toLocaleString()} km</td></tr>
      </table>
      <div class="note">${cb.scenario_note||''}</div>`;
  }

  document.getElementById('sdm').innerHTML = sdmHTML(fit);

  document.getElementById('cites').innerHTML =
    'Method: '+d.standards.quality_tests;

  // map data — colour comes from OUR BDQ verdict, not GBIF issues
  const recs=(d.records&&d.records.analysed)||[];
  const feats=recs
    .filter(r=>r.decimalLatitude!=null&&r.decimalLongitude!=null)
    .map(r=>{
      const flagged=r.biosift_flag===true;
      return {
        type:'Feature',
        geometry:{type:'Point',
          coordinates:[r.decimalLongitude,r.decimalLatitude]},
        properties:{
          color:flagged?RED:ACC,
          fl:flagged?1:0,
          species:r.species, year:r.year, country:r.country,
          basisOfRecord:r.basisOfRecord, datasetName:r.datasetName,
          occurrenceID:r.occurrenceID,
          coordinateUncertaintyInMeters:r.coordinateUncertaintyInMeters,
          biosift_flag:flagged,
          biosift_flags:JSON.stringify(r.biosift_flags||[]),
        },
      };
    });
  window.__flaggedSeen=feats.filter(f=>f.properties.biosift_flag).length;
  const points={type:'FeatureCollection',features:feats};

  let hull=null;
  if(d.distribution_kba && d.distribution_kba.hull_geojson){
    hull=d.distribution_kba.hull_geojson;
  }
  pushGeo({points, hull});
  if(feats.length){
    const bounds=feats.reduce((b,f)=>{
      b.extend(f.geometry.coordinates); return b;
    }, new maplibregl.LngLatBounds());
    map.fitBounds(bounds, {padding:70, maxZoom:9, duration:800});
  }
}

// ── exports ──
function download(name, mime, text){
  const a=document.createElement('a');
  a.href=URL.createObjectURL(new Blob([text], {type:mime}));
  a.download=name; a.click();
  setTimeout(()=>URL.revokeObjectURL(a.href), 4000);
}

// ══ byod mode ══
let byodFile=null;

function setMode(m){
  const byod = m==='byod';
  document.getElementById('gbif-inputs').style.display= byod?'none':'block';
  document.getElementById('byod-inputs').style.display= byod?'block':'none';
  document.getElementById('mode-gbif').classList.toggle('active', !byod);
  document.getElementById('mode-byod').classList.toggle('active', byod);
  document.getElementById('subtitle').textContent = byod
    ? 'Audit your own dataset · TDWG BDQ + CoordinateCleaner'
    : 'GBIF data-quality analysis · TDWG BDQ aligned';
  document.querySelectorAll('.byod-only').forEach(el=>{
    el.style.display = byod?'block':'none';
  });
  document.querySelectorAll('.gbif-only').forEach(el=>{
    el.style.display = byod?'none':'';
  });
  ['exp-geo','exp-flagged','exp-clean'].forEach(id=>{
    document.getElementById(id).style.display =
      byod?'inline-block':'none';
  });
  document.getElementById('m-total-k').textContent =
    byod?'Rows uploaded':'GBIF records';
  document.getElementById('m-total-n').textContent =
    byod?'in source file':'matching filters';
  if(byod){
    document.getElementById('results').style.display='none';
    document.getElementById('exports').style.display='none';
    document.getElementById('capabilities').style.display='block';
    document.getElementById('audience').style.display='block';
    const st=document.getElementById('status');
    st.className='status';
    st.textContent='Choose a CSV, TSV, Excel or DwC-A file to begin.';
  }
}
document.getElementById('mode-gbif').addEventListener('click',
  ()=>setMode('gbif'));
document.getElementById('mode-byod').addEventListener('click',
  ()=>setMode('byod'));

function fileBase(){
  return ((window.__bundle && window.__bundle.dataset)||'dataset')
    .replace(/\.[^.]+$/,'').replace(/[^\w.-]+/g,'_') || 'dataset';
}

document.getElementById('exp-json').addEventListener('click', ()=>{
  if(!window.__bundle) return;
  const d=window.__bundle;
  const stem = d.schema==='biosift.byod/1.0'
    ? fileBase() : (document.getElementById('species').value.trim()
      .replace(/\s+/g,'_')||'analysis');
  download('biosift_'+stem+'.json','application/json',
    JSON.stringify(d, null, 2));
});

document.getElementById('exp-csv').addEventListener('click', ()=>{
  const recs=window.__bundle && window.__bundle.records
    && window.__bundle.records.analysed;
  if(!recs || !recs.length) return;
  const cols=['species','decimalLatitude','decimalLongitude','year',
    'month','country','basisOfRecord','datasetName',
    'coordinateUncertaintyInMeters','biosift_flag','biosift_flags',
    'occurrenceID'];
  const q=v=>v==null?'':'"'+String(v).replace(/"/g,'""')+'"';
  const csv=[cols.join(',')]
    .concat(recs.map(r=>cols.map(c=>{
      const v=r[c];
      return Array.isArray(v)?q(v.join(';')):q(v);
    }).join(','))).join('\n');
  const stem=(document.getElementById('species').value.trim()
    .replace(/\s+/g,'_'))||'analysis';
  download('biosift_'+stem+'.csv','text/csv', csv);
});

document.getElementById('exp-geo').addEventListener('click', ()=>{
  const b=window.__bundle;
  if(!b || !b.geojson || !b.geojson.features
     || !b.geojson.features.length) return;
  download('biosift_'+fileBase()+'.geojson','application/geo+json',
    JSON.stringify(b.geojson, null, 2));
});

async function byodExport(mode){
  if(!byodFile) return;
  const fd=new FormData();
  fd.append('file', byodFile, byodFile.name);
  if(window.__byodMapping)
    fd.append('mapping', JSON.stringify(window.__byodMapping));
  const prof=document.getElementById('byod-profile');
  fd.append('profile', prof ? prof.value : 'General');
  fd.append('mode', mode);
  const st=document.getElementById('status');
  st.className='status';
  st.textContent = mode==='clean'
    ? 'Preparing clean export…' : 'Preparing flagged export…';
  try{
    const r=await fetch('/api/upload/export', {method:'POST', body:fd});
    if(!r.ok){
      const e=await r.json().catch(()=>({detail:r.statusText}));
      throw new Error(typeof e.detail==='string'?e.detail:'export failed');
    }
    const j=await r.json();
    download(j.filename,'text/csv', j.csv);
    st.textContent='Export ready: '+j.filename;
  }catch(e){
    st.className='status err'; st.textContent='Export failed: '+e.message;
  }
}
document.getElementById('exp-flagged').addEventListener('click',
  ()=>byodExport('flagged'));
document.getElementById('exp-clean').addEventListener('click',
  ()=>byodExport('clean'));

document.getElementById('exp-r').addEventListener('click', ()=>{
  if(!window.__bundle) return;
  download('biosift_recipe_'+recipeSlug()+'.R', 'text/plain',
    buildScript('r'));
});
document.getElementById('exp-py').addEventListener('click', ()=>{
  if(!window.__bundle) return;
  download('biosift_recipe_'+recipeSlug()+'.py', 'text/plain',
    buildScript('py'));
});
// the overlay button is re-rendered inside #rangeshift, so delegate
// from the stable container instead of the button itself
document.getElementById('rangeshift').addEventListener('click', e=>{
  if(e.target && e.target.id==='btn-periods') togglePeriodOverlay();
});

async function inspectFile(){
  if(!byodFile){
    const st=document.getElementById('status');
    st.className='status err';
    st.textContent='Choose a file first.';
    return;
  }
  const st=document.getElementById('status');
  const btn=document.getElementById('inspect');
  btn.disabled=true;
  st.className='status';
  st.textContent='Reading '+byodFile.name+'…';
  try{
    const fd=new FormData();
    fd.append('file', byodFile, byodFile.name);
    const r=await fetch('/api/upload/inspect', {method:'POST', body:fd});
    if(!r.ok){
      const e=await r.json().catch(()=>({detail:r.statusText}));
      throw new Error(typeof e.detail==='string'?e.detail:'inspect failed');
    }
    const j=await r.json();
    window.__inspect=j;
    renderMapping(j);
    st.textContent=j.rows.toLocaleString()+' rows · '+j.columns.length
      +' columns · '+j.core_present.length+' core fields detected.'
      +(j.needs_mapping
        ?' Review the mapping below.'
        :' Mapping looks good. Ready to run.');
  }catch(e){
    st.className='status err'; st.textContent='Inspect failed: '+e.message;
  }finally{
    btn.disabled=false;
  }
}
document.getElementById('file').addEventListener('change', e=>{
  const f=e.target.files && e.target.files[0];
  if(!f) return;
  byodFile=f;
  inspectFile();
});
document.getElementById('inspect').addEventListener('click', inspectFile);

function renderMapping(insp){
  const wrap=document.getElementById('mapping');
  const tbl=document.getElementById('t-mapping');
  const note=document.getElementById('map-note');
  const cols=insp.columns||[];
  const ropt=cols.map(c=>
    '<option value="'+esc(c)+'">'+esc(String(c))+'</option>').join('');
  let rows='<tr><th>Canonical field</th><th>Your column</th><th>Filled</th></tr>';
  for(const canon of BYOD_FIELDS){
    const core=BYOD_CORE.includes(canon);
    rows+='<tr><td>'+esc(canon)
      +(core?' <span class="chip bad">core</span>':'')
      +'</td>'
      +'<td><select data-canon="'+esc(canon)+'">'
      +'<option value="">Not mapped</option>'
      +ropt+'</select></td>'
      +'<td class="mono" style="font-size:9.5px">n/a</td></tr>';
  }
  tbl.innerHTML=rows;
  tbl.querySelectorAll('select').forEach(sel=>{
    const canon=sel.getAttribute('data-canon');
    sel.value=(insp.proposed_mapping||{})[canon]||'';
    sel.addEventListener('change', collectMapping);
  });
  collectMapping();
  const missing=(insp.core_missing||[]);
  note.innerHTML = missing.length
    ? 'Core fields not detected: '
      +missing.map(m=>'<b>'+esc(m)+'</b>').join(', ')
      +'. Map them above for spatial and temporal analysis.'
    : 'All core fields mapped.';
  fillPreview(insp);
  wrap.style.display='block';
}

function collectMapping(){
  const m={};
  document.querySelectorAll('#t-mapping select').forEach(sel=>{
    const canon=sel.getAttribute('data-canon');
    if(sel.value) m[canon]=sel.value;
  });
  window.__byodMapping=m;
}

function fillPreview(insp){
  const stats=insp.col_stats||{};
  document.querySelectorAll('#t-mapping tr').forEach(tr=>{
    const sel=tr.querySelector('select[data-canon]');
    if(!sel) return;
    const cell=tr.querySelectorAll('td')[2];
    const src=sel.value;
    if(cell && src && stats[src]){
      cell.textContent=stats[src].filled_pct+'% · '
        +stats[src].distinct+' distinct';
    }else if(cell){
      cell.textContent='n/a';
    }
  });
  const pv=document.getElementById('preview');
  const pt=document.getElementById('t-preview');
  const srs=insp.sample_rows||[];
  const cols=insp.columns||[];
  if(!srs.length || !cols.length){ pv.style.display='none'; return; }
  pt.innerHTML='<tr><th>'+cols.map(c=>esc(c)).join('</th><th>')
    +'</th></tr>'
    + srs.map(r=>'<tr><td>'+cols.map(c=>{
        const v=r[c];
        return v==null
          ?'<span style="color:var(--faint)">null</span>'
          :esc(String(v));
      }).join('</td><td>')+'</td></tr>').join('');
  pv.style.display='block';
}

async function runByod(){
  if(!byodFile) return;
  collectMapping();
  const btn=document.getElementById('run-byod');
  const st=document.getElementById('status');
  btn.disabled=true;
  st.className='status';
  let secs=0;
  const tick=setInterval(()=>{
    secs+=1;
    if(st.textContent.startsWith('Analysing'))
      st.textContent='Analysing '+byodFile.name+'… ('+secs+'s)';
  },1000);
  st.textContent='Analysing '+byodFile.name+'… (0s)';
  try{
    const fd=new FormData();
    fd.append('file', byodFile, byodFile.name);
    fd.append('mapping', JSON.stringify(window.__byodMapping||{}));
    const prof=document.getElementById('byod-profile');
    fd.append('profile', prof ? prof.value : 'General');
    fd.append('dataset_name', byodFile.name);
    const r=await fetch('/api/upload/analyze', {method:'POST', body:fd});
    if(!r.ok){
      const e=await r.json().catch(()=>({detail:r.statusText}));
      throw new Error(typeof e.detail==='string'?e.detail:'analysis failed');
    }
    const d=await r.json();
    window.__bundle=d;
    renderByod(d);
    const p=d.profile||{};
    st.textContent='Analysis complete: '+d.rows.toLocaleString()+' rows · '
      +(p.records_kept!=null?p.records_kept.toLocaleString()+' kept by '
        +(p.profile||'General')+' profile · ':'')
      +new Date(d.generated_utc||Date.now()).toLocaleTimeString();
  }catch(e){
    st.className='status err'; st.textContent='Error: '+e.message;
  }finally{
    clearInterval(tick);
    btn.disabled=false;
  }
}
document.getElementById('run-byod').addEventListener('click', runByod);

function renderByod(d){
  document.getElementById('results').style.display='block';
  document.getElementById('exports').style.display='block';
  document.getElementById('capabilities').style.display='none';
  document.getElementById('audience').style.display='none';

  const s=d.scores;
  document.getElementById('m-total').textContent=d.rows.toLocaleString();
  document.getElementById('m-analysed').textContent=
    s.records_analysed.toLocaleString();
  document.getElementById('m-completeness').textContent=
    s.completeness_pct!=null ? 'completeness '+s.completeness_pct+'%' : '';
  const hv=document.getElementById('m-health');
  hv.textContent=s.health_pct+'%';
  hv.className='v '+pctClass(s.health_pct);
  document.getElementById('m-healthbar').style.width=
    Math.min(s.health_pct,100)+'%';
  const fv=document.getElementById('m-flag');
  fv.textContent=(s.records_analysed-s.records_clean).toLocaleString();
  const p=d.profile||{};
  const kv=document.getElementById('m-keep');
  kv.textContent=(p.retention_pct!=null?p.retention_pct+'%':'n/a');
  kv.className='v '+pctClass(p.retention_pct!=null?p.retention_pct:0);
  document.getElementById('m-keepnote').textContent=
    (p.records_kept!=null? p.records_kept.toLocaleString()+' rows kept':'');
  const fit=d.sdm_readiness;
  const sv=document.getElementById('m-sdm');
  sv.textContent=fit? fit.ready_records.toLocaleString() : 'n/a';
  sv.className='v '+ (fit&&fit.verdict==='READY'?'good':
    (fit&&fit.verdict==='CONDITIONAL'?'fair':'poor'));
  document.getElementById('m-sdmnote').textContent= fit?
    fit.retention_pct+'% retention · '+fit.verdict : 'no coordinates';

  const pb=document.getElementById('profbox');
  if(p.profile){
    pb.innerHTML='<b>'+esc(p.profile)+'</b> profile, kept <b>'
      +Number(p.records_kept).toLocaleString()+'</b> of '
      +Number(p.records_kept+p.records_excluded).toLocaleString()
      +' rows ('+p.retention_pct+'% retention). '+esc(p.note||'');
    pb.style.display='block';
  }else{ pb.style.display='none'; }

  const bad=d.quality_checks.filter(c=>c.flagged>0);
  document.getElementById('t-checks').innerHTML =
    '<tr><th>Check</th><th>BDQ test</th><th style="text-align:right">Flagged</th><th style="text-align:right">%</th></tr>'
    + d.quality_checks.map(c=>`
      <tr>
        <td>${c.label}</td>
        <td class="mono" style="font-size:9px">${c.bdq_test.split(' · ')[0]}</td>
        <td class="num">${c.flagged.toLocaleString()}</td>
        <td class="num ${c.percent>10?'poor':(c.percent>0?'warn':'good')}">${c.percent}%</td>
      </tr>`).join('');
  setCount('cnt-checks', bad.length+' of '+d.quality_checks.length
    +' triggered');

  const sb=d.species_table;
  const sbEl=document.getElementById('speciesbrk');
  if(sb && sb.length){
    sbEl.innerHTML='<table><colgroup/><tr><th>Species</th>'
      +'<th style="text-align:right">Records</th>'
      +'<th style="text-align:right">Flagged</th>'
      +'<th style="text-align:right">Kept</th></tr>'
      + sb.map(r=>'<tr><td style="font-style:italic">'+esc(r.species)
        +'</td><td class="num">'+Number(r.records).toLocaleString()
        +'</td><td class="num '+(r.flag_pct>25?'poor':(r.flag_pct>0?'warn':'good'))
        +'">'+Number(r.flagged).toLocaleString()
        +'</td><td class="num">'
        +Number(r.records-r.excluded).toLocaleString()
        +'</td></tr>').join('')+'</table>';
    sbEl.style.display='block';
    setCount('cnt-species', sb.length+' taxa');
  }

  const cp=d.column_profile;
  const cpEl=document.getElementById('dsprofile');
  if(cp && cp.length){
    cpEl.innerHTML='<table><colgroup/><tr><th>Column</th><th>Kind</th>'
      +'<th style="text-align:right">Filled</th>'
      +'<th style="text-align:right">Distinct</th></tr>'
      + cp.map(c=>'<tr><td class="mono" style="font-size:10px">'
        +esc(c.column)+'</td><td>'+c.kind+'</td>'
        +'<td class="num '+(c.filled_pct<50?'poor':(c.filled_pct<90?'warn':'good'))
        +'">'+c.filled_pct+'%</td><td class="num">'
        +Number(c.distinct).toLocaleString()+'</td></tr>').join('')
      + '</table>'
      + (d.rounded_stats && d.rounded_stats.diagnosis
        ? '<div class="note" style="color:var(--amber)">Dataset-level: '
          +esc(d.rounded_stats.diagnosis)+' ('
          +Math.round(d.rounded_stats.share_on_grid*100)
          +'% of coordinates).</div>' : '');
    cpEl.style.display='block';
    setCount('cnt-dsprof', cp.length+' columns');
  }

  const o=d.outliers;
  const oEl=document.getElementById('outliers');
  if(o){
    oEl.innerHTML='<div class="note">'+o.flagged+' spatial outlier'
      +(o.flagged===1?'':'s')+' ('+o.percent
      +'%). DBSCAN (eps 0.5, min 5) on scaled coordinates; '
      +'candidates for manual review before mapping or modelling.</div>';
    oEl.style.display='block';
    setCount('cnt-outliers', o.flagged+' found');
  }

  const nv=d.name_verification;
  const nvEl=document.getElementById('namecheck');
  if(nv && nv.results && nv.results.length){
    const exact=nv.results.filter(r=>r.matchType==='EXACT').length;
    const none=nv.results.filter(
      r=>r.matchType==='NONE'||r.matchType==='ERROR').length;
    nvEl.innerHTML='<table><colgroup/><tr><th>Submitted name</th>'
      +'<th>Backbone match</th>'
      +'<th style="text-align:right">Confidence</th></tr>'
      + nv.results.map(r=>
        '<tr><td style="font-style:italic">'+esc(r.name)+'</td><td>'
        +(r.scientificName
          ?('<i>'+esc(r.scientificName)+'</i>'
            +(r.status?' <span class="chip">'+esc(r.status)+'</span>':''))
          :'<span class="chip bad">no match</span>')
        +'</td><td class="num">'
        +(r.confidence!=null?r.confidence:'n/a')+'</td></tr>').join('')
      + '</table><div class="note">'+exact+' exact, '
      +(nv.checked-exact-none)+' fuzzy, '+none+' unmatched of '
      +nv.checked+' unique names (max 200; GBIF backbone).</div>';
    nvEl.style.display='block';
    setCount('cnt-names', none? none+' unmatched':'all matched');
  }

  const fl=d.flagged_sample||[];
  const flEl=document.getElementById('flagged');
  if(fl.length){
    flEl.innerHTML='<table><colgroup/><tr><th>Row</th><th>Species</th>'
      +'<th>Coordinates</th><th>Reasons</th></tr>'
      + fl.map(r=>'<tr><td class="mono">'+r.row+'</td>'
        +'<td style="font-style:italic">'+esc(r.species||'n/a')+'</td>'
        +'<td class="mono" style="font-size:10px">'
        +esc(r.decimalLatitude!=null
          ?(r.decimalLatitude+', '+r.decimalLongitude):'n/a')+'</td>'
        +'<td>'+(r.reasons||[]).map(x=>
          '<span class="chip bad">'+esc(prettyFlag(x))+'</span>')
          .join('')+'</td></tr>').join('')
      + '</table>';
    flEl.style.display='block';
    setCount('cnt-flagged', fl.length+' shown');
  }

  const rc=d.recommendations||[];
  const rcEl=document.getElementById('recs');
  if(rc.length){
    rcEl.innerHTML=rc.map(r=>
      '<div class="note" style="margin-bottom:8px"><b>'+esc(r.title)
      +'</b>: '+esc(r.message)+'</div>').join('');
    rcEl.style.display='block';
    setCount('cnt-recs', rc.length+' actions');
  }

  document.getElementById('patterns').innerHTML = patternsHTML(d.patterns);
  const figs=document.querySelectorAll('#patterns svg, #patterns .bars').length;
  setCount('cnt-patterns', figs? figs+' figures' : 'none');
  renderNewSections(d, false);

  document.getElementById('cites').innerHTML =
    'Method: '+d.standards.quality_tests;

  const feats=((d.geojson&&d.geojson.features)||[])
    .filter(f=>f.geometry && Array.isArray(f.geometry.coordinates)
      && Math.abs(f.geometry.coordinates[1])<=90
      && Math.abs(f.geometry.coordinates[0])<=180);
  const colored=feats.map(f=>{
    const pr=f.properties||{};
    const flagged=!!pr.biosift_flag;
    const excluded=pr.ex===1||pr.ex===true||pr.ex==='1';
    return {
      type:'Feature',
      geometry:f.geometry,
      properties:Object.assign({}, pr, {
        color: excluded?RED:(flagged?AMBER:ACC),
        fl: flagged?1:0,
        ex: excluded?1:0,
        basisOfRecord: pr.basisOfRecord||'',
        datasetName: pr.datasetName||'',
        occurrenceID: pr.occurrenceID||'',
        biosift_flags: Array.isArray(pr.biosift_flags)
          ? pr.biosift_flags : [],
      }),
    };
  });
  window.__flaggedSeen=colored.filter(
    f=>f.properties.biosift_flag).length;
  window.__excludedSeen=colored.filter(
    f=>f.properties.ex===1).length;
  const points={type:'FeatureCollection',features:colored};
  pushGeo({points, hull:null});
  if(colored.length){
    const bounds=colored.reduce((b,f)=>{
      b.extend(f.geometry.coordinates); return b;
    }, new maplibregl.LngLatBounds());
    map.fitBounds(bounds, {padding:70, maxZoom:9, duration:800});
  }
}

document.getElementById('species').addEventListener('keydown',
  e=>{ if(e.key==='Enter') run(); });
document.getElementById('capabilities').style.display='block';
document.getElementById('audience').style.display='block';
initMap();
</script>
</body>
</html>
"""
