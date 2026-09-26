"""
BioSift Standalone Frontend — single-file MapLibre GL JS app.

Design notes (professional, non-AI-look):
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
<title>BioSift — Biodiversity Data Quality</title>
<script src="https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.js"></script>
<link href="https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.css" rel="stylesheet"/>
<style>
:root{
  --bg:#0B0F14; --panel:#0F151C; --card:#111823; --line:#1F2A38;
  --text:#E9EFF6; --dim:#8A97A8; --faint:#5C6879;
  --acc:#22C58B; --red:#F2555A; --amber:#E8B339; --blue:#4DA3FF;
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
.brand h1{font-size:19px;font-weight:700;letter-spacing:-.3px}
.brand span{font-size:10px;letter-spacing:1.6px;color:var(--faint);
  text-transform:uppercase}
/* gaia-style capability strip (below the search form, inside .scroll;
   shown at boot, hidden once results render) */
#capabilities{display:none;padding:18px 0 10px}
#capabilities .capgrid{display:grid;grid-template-columns:1fr;gap:8px}
.cap{display:flex;gap:12px;align-items:flex-start;background:var(--card);
  border:1px solid var(--line);border-radius:12px;padding:12px 14px}
.cap .n{font-size:11px;font-weight:700;color:var(--acc);
  border:1px solid rgba(34,197,139,.4);border-radius:8px;
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
  color:var(--text);border-radius:8px;padding:9px 11px;font-size:13px;
  outline:none;
}
.field input:focus,.field select:focus{border-color:var(--acc)}
.row{display:grid;grid-template-columns:1fr 1fr;gap:10px}
button#run{
  width:100%;background:var(--acc);color:#04140D;border:none;
  border-radius:9px;padding:11px;font-weight:700;font-size:13px;
  cursor:pointer;margin-top:4px;
}
button#run:disabled{opacity:.55;cursor:wait}
button#run:hover:not(:disabled){filter:brightness(1.08)}
/* metrics */
.metrics{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin:4px 0 14px}
.metric{background:var(--card);border:1px solid var(--line);
  border-radius:10px;padding:10px 12px;min-width:0}
.metric .k{font-size:9.5px;font-weight:600;letter-spacing:1.1px;
  text-transform:uppercase;color:var(--faint)}
.metric .v{font-size:20px;font-weight:700;margin-top:2px;
  font-variant-numeric:tabular-nums;overflow-wrap:anywhere}
.metric .n{font-size:10.5px;color:var(--dim);margin-top:1px}
.good{color:var(--acc)} .fair{color:var(--amber)} .poor{color:var(--red)}
.bar{height:6px;background:var(--line);border-radius:99px;overflow:hidden;
  margin-top:6px}
.bar i{display:block;height:100%;border-radius:99px;
  background:linear-gradient(90deg,#0E7A57,var(--acc))}
/* sections */
h2.sec{
  font-size:10.5px;font-weight:700;letter-spacing:1.6px;color:var(--faint);
  text-transform:uppercase;margin:18px 0 8px;display:flex;gap:8px;
  align-items:center;
}
h2.sec::after{content:"";flex:1;height:1px;background:var(--line)}
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
.chip.ok{color:var(--acc);border-color:rgba(34,197,139,.45)}
.chip.bad{color:var(--red);border-color:rgba(242,85,90,.45)}
.chip.warn{color:var(--amber);border-color:rgba(232,179,57,.45)}
.note{font-size:11px;color:var(--dim);line-height:1.5;margin-top:6px;
  overflow-wrap:anywhere}
.cite{font-size:10px;color:var(--faint);line-height:1.5;margin-top:6px}
.status{font-size:12px;color:var(--dim);padding:10px 0;overflow-wrap:anywhere}
.status.err{color:var(--red)}
/* sparkline (records per year) */
.spark{width:100%;height:56px;display:block;margin-top:4px}
.spark .axis{stroke:var(--line);stroke-width:1}
.spark path{fill:rgba(34,197,139,.15);stroke:var(--acc);stroke-width:1.5}
.gaps{margin-top:6px}
/* export row */
#exports{display:none;margin-top:16px}
#exports .exp{display:flex;gap:8px;flex-wrap:wrap}
#exports button{
  background:var(--card);border:1px solid var(--line);color:var(--text);
  border-radius:8px;padding:7px 12px;font-size:11.5px;font-weight:600;
  cursor:pointer;
}
#exports button:hover{border-color:var(--acc);color:var(--acc)}
/* ── map column ── */
#mapwrap{position:relative;min-width:0}
#map{position:absolute;inset:0}
#legend{
  position:absolute;left:12px;bottom:24px;z-index:5;
  background:rgba(15,21,28,.92);border:1px solid var(--line);
  border-radius:10px;padding:10px 12px;font-size:11px;color:var(--dim);
  backdrop-filter:blur(4px);
}
#legend .dot{display:inline-block;width:9px;height:9px;border-radius:50%;
  margin-right:6px;vertical-align:middle}
#speciesbar{
  position:absolute;top:12px;left:12px;z-index:5;max-width:60%;
  background:rgba(15,21,28,.92);border:1px solid var(--line);
  border-radius:10px;padding:9px 14px;font-size:13px;
  backdrop-filter:blur(4px);display:none;
}
#speciesbar b{font-style:italic;overflow-wrap:anywhere}
#speciesbar .chip{margin-left:8px}
.maplibregl-ctrl-group{
  background:var(--card)!important;border:1px solid var(--line)!important;
}
.maplibregl-ctrl-group button+button{border-top:1px solid var(--line)!important}
.maplibregl-ctrl-attrib{
  background:rgba(15,21,28,.8)!important;color:var(--faint)!important;
  font-size:10px!important;
}
.maplibregl-ctrl-attrib a{color:var(--dim)!important}
/* popups (MapLibre popup pattern) */
.maplibregl-popup-content{
  background:var(--card)!important;color:var(--text)!important;
  border:1px solid var(--line)!important;border-radius:10px!important;
  padding:12px 14px!important;font-size:12px;line-height:1.5;
  min-width:220px;max-width:290px;box-shadow:0 8px 28px rgba(0,0,0,.5);
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
      <div class="note" style="margin-top:4px">
        GBIF data-quality analysis · TDWG BDQ aligned
      </div>
    </header>
    <div class="scroll">
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
      <div id="status" class="status">Search a species to begin.</div>

      <!-- gaia-style pitch: lives BELOW the form so the search is
           always above the fold on short screens (1366x768) -->
      <div id="capabilities">
        <h2 class="sec">Capabilities</h2>
        <div class="capgrid">
          <div class="cap"><div class="n">1</div><div>
            <div class="t">Audit occurrence data on demand</div>
            <div class="d">Ten automated checks mapped to the official TDWG BDQ test vocabulary.</div></div></div>
          <div class="cap"><div class="n">2</div><div>
            <div class="t">Benchmark against the world</div>
            <div class="d">Defect rates compared live against the full GBIF population.</div></div></div>
          <div class="cap"><div class="n">3</div><div>
            <div class="t">Relationships &amp; communities</div>
            <div class="d">GloBI interactions plus congeneric co-occurrence (Jaccard).</div></div></div>
          <div class="cap"><div class="n">4</div><div>
            <div class="t">Predict distribution &amp; carbon</div>
            <div class="d">EOO/AOO with KBA Criterion B screening; Chave 2014 carbon scenarios for plants.</div></div></div>
          <div class="cap"><div class="n">5</div><div>
            <div class="t">Model-ready or nothing</div>
            <div class="d">SDM readiness gates cite Zizka 2020 and Marcer 2022 — strictness disclosed.</div></div></div>
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
            <div class="k">GBIF records</div>
            <div class="v" id="m-total">—</div>
            <div class="n">matching filters</div>
          </div>
          <div class="metric">
            <div class="k">Analysed</div>
            <div class="v" id="m-analysed">—</div>
            <div class="n" id="m-completeness"></div>
          </div>
          <div class="metric">
            <div class="k">Health score</div>
            <div class="v" id="m-health">—</div>
            <div class="bar"><i id="m-healthbar" style="width:0%"></i></div>
          </div>
          <div class="metric">
            <div class="k">SDM-ready</div>
            <div class="v" id="m-sdm">—</div>
            <div class="n" id="m-sdmnote"></div>
          </div>
        </div>

        <h2 class="sec">Quality checks — TDWG BDQ</h2>
        <table id="t-checks">
          <colgroup><col class="c-wide"/><col class="c-bdq"/>
            <col class="c-num"/><col class="c-num"/></colgroup>
        </table>

        <h2 class="sec">Benchmark vs GBIF-wide</h2>
        <div id="benchmark" class="note">—</div>

        <h2 class="sec">Temporal coverage</h2>
        <div id="temporal"></div>

        <h2 class="sec">Distribution &amp; KBA Criterion B</h2>
        <div id="kba"></div>

        <h2 class="sec">Ecological community</h2>
        <div id="community"></div>

        <h2 class="sec">Carbon (plants only)</h2>
        <div id="carbon"></div>

        <h2 class="sec">SDM readiness — gate detail</h2>
        <div id="sdm"></div>

        <div class="cite" id="cites"></div>

        <div id="exports">
          <h2 class="sec">Export</h2>
          <div class="exp">
            <button id="exp-json">JSON bundle</button>
            <button id="exp-csv">Records CSV</button>
          </div>
        </div>
      </div>
    </div>
  </div>

  <div id="mapwrap">
    <div id="map"></div>
    <div id="speciesbar">
      <b id="sb-name">—</b>
      <span id="sb-chips"></span>
    </div>
    <div id="legend">
      <span class="dot" style="background:var(--acc)"></span>Clean record
      &nbsp; <span class="dot" style="background:var(--red)"></span>Flagged
      <br/>
      <span style="font-size:9.5px;color:var(--faint)">
        Click a point for details · Basemap: top-right
      </span>
    </div>
  </div>
</div>

<script>
const ACC='#22C58B', RED='#F2555A';
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
        'background-color': base==='dark' ? '#0B0F14' : '#0F151C'}},
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
  sel.style.cssText = 'margin:10px 12px 0 0;padding:5px 8px;border-radius:7px;'
    + 'background:#111823;color:#E9EFF6;border:1px solid #1F2A38;'
    + 'font-size:11px;outline:none;float:right;';
  Object.entries(BASEMAPS).forEach(([k,v])=>{
    const o=document.createElement('option'); o.value=k;
    o.textContent=v.title; sel.appendChild(o);
  });
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

function esc(s){
  return String(s==null?'':s)
    .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

function popupHTML(p){
  const flagged = p.biosift_flag===true || p.biosift_flag==='true';
  const rows = [
    ['Species', '<i>'+esc(p.species)+'</i>'],
    ['Year', esc(p.year!=null?p.year:'—')],
    ['Country', esc(p.country||'—')],
    ['Basis', esc(String(p.basisOfRecord||'—').replace(/_/g,' '))],
    ['Dataset', esc(p.datasetName||'—')],
  ];
  if(p.coordinateUncertaintyInMeters!=null){
    rows.push(['Coord. uncertainty',
      Math.round(p.coordinateUncertaintyInMeters).toLocaleString()+' m']);
  }
  let html = '<div class="pop-t">'+esc(p.species)+'</div>'
    + rows.map(r=>'<div class="pop-r"><span>'+r[0]
      +'</span><span>'+r[1]+'</span></div>').join('');
  const flags = (()=>{
    try{ return JSON.parse(p.biosift_flags||'[]'); }catch(e){ return []; }
  })();
  if(flags.length){
    html += '<div class="pop-f">'
      + flags.map(f=>'<span class="chip bad">'+esc(prettyFlag(f))
        +'</span>').join('')
      + '</div>';
  }else{
    html += '<div class="pop-f"><span class="chip ok">Passes all BDQ checks</span></div>';
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
        '#5A2A2E',
        '#16302A'],
      'circle-radius':15,'circle-opacity':0.85,
      'circle-stroke-width':1,'circle-stroke-color':'rgba(233,239,246,.35)',
    },
  });
  map.addLayer({
    id:'cluster-count', type:'symbol', source:'occ',
    filter:['has','point_count'],
    layout:{
      'text-field':['get','point_count_abbreviated'],
      'text-font':['Noto Sans Regular'],'text-size':11,
    },
    paint:{'text-color':'#E9EFF6'},
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
    status.textContent='Analysis complete — '
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
    +'<div class="note mono">'+y0+' — '+y1+' · peak '
    +nMax+' in '+ys[ns.indexOf(nMax)]+'</div>';
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
  sv.textContent=fit? fit.ready_records.toLocaleString() : '—';
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
      <span class="mono" style="text-align:right">${b.sample_pct}% vs ${b.population_pct}% (Δ${b.delta>0?'+':''}${b.delta} pp) — ${b.verdict}</span>
    </div>`).join('')
    : 'Baseline unavailable for this query.';

  // temporal
  const t=d.temporal;
  const tEl=document.getElementById('temporal');
  if(t){
    const gapChips=(t.major_gaps||[]).slice(0,6).map(g=>
      `<span class="chip warn">gap ${g[0]}–${g[1]}</span>`).join('');
    tEl.innerHTML =
      sparkline(d.year_counts)
      + `<table><colgroup/><tr><th>Indicator</th><th style="text-align:right">Value</th></tr>
        <tr><td>Span</td><td class="num">${t.first_year}–${t.last_year} (${t.span_years} yr)</td></tr>
        <tr><td>Gap years</td><td class="num">${t.gap_count}</td></tr>
        <tr><td>Trend</td><td class="num">${esc(t.trend)}</td></tr>
        <tr><td>Recent 5-yr share</td><td class="num">${t.recent_pct}%</td></tr>
        <tr><td>Citizen-science surge</td><td class="num">${t.cs_surge?'yes':'no'}</td></tr></table>`
      + (gapChips? `<div class="gaps">${gapChips}</div>` : '');
  }else{
    tEl.innerHTML='<div class="note">No dated records in this sample.</div>';
  }

  // KBA
  const k=d.distribution_kba;
  if(k){
    const kb=k.kba;
    const chipsHtml =
      (kb.b1_meets?'<span class="chip ok">B1 met</span>':'<span class="chip">B1 no</span>')
      + (kb.b2_meets?'<span class="chip ok">B2 met</span>':'<span class="chip">B2 no</span>');
    document.getElementById('kba').innerHTML = `
      <table>
        <colgroup/>
        <tr><th>Metric</th><th style="text-align:right">Value</th></tr>
        <tr><td>Extent of Occurrence</td><td class="num">${k.eoo_km2.toLocaleString(undefined,{maximumFractionDigits:0})} km²</td></tr>
        <tr><td>Area of Occupancy</td><td class="num">${k.aoo_km2.toLocaleString()} km² (${k.aoo_cells} cells)</td></tr>
      </table>
      <div style="margin-top:6px">${chipsHtml}</div>
      <div class="note">${k.caveat}</div>
      ${(k.hull_warnings||[]).map(w=>`<div class="note poor">Caution: ${w}</div>`).join('')}`;
  }else{
    document.getElementById('kba').innerHTML='<div class="note">Not enough georeferenced records.</div>';
  }

  // community
  const com=document.getElementById('community');
  const inter=d.interactions||{total:0,by_type:[]};
  const coo=d.cooccurrence;
  let html='';
  if(inter.by_type && inter.by_type.length){
    html += '<div class="note" style="margin-bottom:6px"><b>GloBI interactions</b> — '
      + inter.by_type.slice(0,6).map(t=>`${t.label}: ${t.count}`).join(' · ')
      + ` (n=${inter.total})</div>`;
  }else{
    html += '<div class="note">No GloBI interaction records.</div>';
  }
  if(coo && coo.partners && coo.partners.length){
    html += `<div class="note"><b>Congeneric co-occurrence</b> (Jaccard, 1° grid) — genus <i>${coo.genus}</i> (${coo.assemblage_size} species):</div>
      <table><colgroup/><tr><th>Congener</th><th style="text-align:right">Overlap</th></tr>`
      + coo.partners.slice(0,6).map(p=>`
        <tr><td style="font-style:italic">${p.species}</td>
        <td class="num">${p.overlap} <span class="chip ${p.overlap>=0.4?'ok':(p.overlap>=0.15?'warn':'')}">${p.jaccard_label}</span></td></tr>`).join('')
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

  // SDM gate detail
  const sd=document.getElementById('sdm');
  if(fit && fit.gates && fit.gates.length){
    sd.innerHTML =
      '<div class="note" style="margin-bottom:4px">Profile: '
      + esc(fit.profile) + '</div>'
      + '<table><colgroup/><tr><th>Gate</th><th style="text-align:right">Pass</th>'
      + '<th style="text-align:right">Fail</th></tr>'
      + fit.gates.map(g=>`
        <tr>
          <td>${esc(g.gate)}${g.critical?'':' <span class="chip">soft</span>'}</td>
          <td class="num good">${g.pass.toLocaleString()}</td>
          <td class="num ${g.fail>0?'poor':''}">${g.fail.toLocaleString()}</td>
        </tr>`).join('')
      + '</table>'
      + '<div class="cite">'
      + (()=>{ const c=fit.citations;   // dict | array | string
          if(Array.isArray(c)) return c.map(x=>esc(x)).join(' · ');
          if(c && typeof c==='object')
            return Object.values(c).map(x=>esc(x)).join(' · ');
          return c?esc(c):''; })()
      + '</div>';
  }else{
    sd.innerHTML='<div class="note">Not available for this sample.</div>';
  }

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
document.getElementById('exp-json').addEventListener('click', ()=>{
  if(!window.__bundle) return;
  const sp=document.getElementById('species').value.trim()
    .replace(/\s+/g,'_');
  download('biosift_'+sp+'.json','application/json',
    JSON.stringify(window.__bundle, null, 2));
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
  const sp=document.getElementById('species').value.trim()
    .replace(/\s+/g,'_');
  download('biosift_'+sp+'.csv','text/csv', csv);
});

document.getElementById('run').addEventListener('click', run);
document.getElementById('species').addEventListener('keydown',
  e=>{ if(e.key==='Enter') run(); });
document.getElementById('capabilities').style.display='block';
document.getElementById('audience').style.display='block';
initMap();
</script>
</body>
</html>
"""
