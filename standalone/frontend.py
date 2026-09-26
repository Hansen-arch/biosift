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
#app{display:grid;grid-template-columns:380px 1fr;height:100vh}
/* ── panel ── */
#panel{
  background:var(--panel);border-right:1px solid var(--line);
  display:flex;flex-direction:column;overflow:hidden;
}
#panel header{
  padding:18px 20px 14px;border-bottom:1px solid var(--line);
}
.brand{display:flex;align-items:baseline;gap:10px}
.brand h1{font-size:19px;font-weight:700;letter-spacing:-.3px}
.brand span{font-size:10px;letter-spacing:1.6px;color:var(--faint);
  text-transform:uppercase}
/* gaia-style capability strip on landing */
#capabilities{display:none;padding:26px 20px 10px}
#capabilities .capgrid{display:grid;grid-template-columns:1fr;gap:8px}
.cap{display:flex;gap:12px;align-items:flex-start;background:var(--card);
  border:1px solid var(--line);border-radius:12px;padding:12px 14px}
.cap .n{font-size:11px;font-weight:700;color:var(--acc);
  border:1px solid rgba(34,197,139,.4);border-radius:8px;
  min-width:22px;height:22px;display:flex;align-items:center;
  justify-content:center;margin-top:1px}
.cap .t{font-size:13px;font-weight:600}
.cap .d{font-size:11px;color:var(--dim);margin-top:1px;line-height:1.45}
#audience{display:none;padding:8px 20px 20px}
#audience .aud{display:flex;flex-wrap:wrap;gap:6px}
#audience .chip{font-size:10.5px}
#panel .scroll{
  overflow-y:auto;padding:16px 20px 32px;flex:1;
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
  border-radius:10px;padding:10px 12px}
.metric .k{font-size:9.5px;font-weight:600;letter-spacing:1.1px;
  text-transform:uppercase;color:var(--faint)}
.metric .v{font-size:20px;font-weight:700;margin-top:2px;
  font-variant-numeric:tabular-nums}
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
table{width:100%;border-collapse:collapse;font-size:12px}
td,th{padding:6px 4px;border-bottom:1px solid var(--line);text-align:left;
  vertical-align:top}
th{color:var(--faint);font-weight:600;font-size:10px;
  letter-spacing:.8px;text-transform:uppercase}
td.num{text-align:right;font-variant-numeric:tabular-nums;color:var(--dim)}
.mono{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:10.5px;
  color:var(--faint)}
.chip{display:inline-block;font-size:9.5px;font-weight:700;
  padding:2px 7px;border-radius:99px;border:1px solid var(--line);
  color:var(--dim);margin:1px 2px 1px 0}
.chip.ok{color:var(--acc);border-color:rgba(34,197,139,.45)}
.chip.bad{color:var(--red);border-color:rgba(242,85,90,.45)}
.chip.warn{color:var(--amber);border-color:rgba(232,179,57,.45)}
.note{font-size:11px;color:var(--dim);line-height:1.5;margin-top:6px}
.cite{font-size:10px;color:var(--faint);line-height:1.5;margin-top:6px}
.status{font-size:12px;color:var(--dim);padding:10px 0}
.status.err{color:var(--red)}
/* ── map column ── */
#mapwrap{position:relative}
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
  position:absolute;top:12px;left:12px;z-index:5;
  background:rgba(15,21,28,.92);border:1px solid var(--line);
  border-radius:10px;padding:9px 14px;font-size:13px;
  backdrop-filter:blur(4px);display:none;
}
#speciesbar b{font-style:italic}
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
@media(max-width:860px){
  #app{grid-template-columns:1fr;grid-template-rows:auto 1fr}
  #panel{max-height:46vh;border-right:none;
    border-bottom:1px solid var(--line)}
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
    <div id="capabilities">
      <div class="capgrid">
        <div class="cap"><div class="n">1</div><div>
          <div class="t">Audit occurrence data on demand</div>
          <div class="d">Ten automated checks mapped to the official TDWG BDQ test vocabulary.</div></div></div>
        <div class="cap"><div class="n">2</div><div>
          <div class="t">Benchmark against the world</div>
          <div class="d">Defect rates compared live against the full GBIF population.</div></div></div>
        <div class="cap"><div class="n">3</div><div>
          <div class="t">Relationships & communities</div>
          <div class="d">GloBI interactions plus congeneric co-occurrence (Jaccard).</div></div></div>
        <div class="cap"><div class="n">4</div><div>
          <div class="t">Predict distribution & carbon</div>
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
            <div class="n">live sample</div>
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
        <table id="t-checks"></table>

        <h2 class="sec">Benchmark vs GBIF-wide</h2>
        <div id="benchmark" class="note">—</div>

        <h2 class="sec">Distribution & KBA Criterion B</h2>
        <div id="kba"></div>

        <h2 class="sec">Ecological community</h2>
        <div id="community"></div>

        <h2 class="sec">Carbon (plants only)</h2>
        <div id="carbon"></div>

        <div class="cite" id="cites"></div>
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
        Basemap switcher: top-right · Esri satellite · OSM · Topo
      </span>
    </div>
  </div>
</div>

<script>
const ACC='#22C58B', RED='#F2555A';
let map, mapReady=false;

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
  window.__map = map;  // audit hook
}

function pushGeo({points, hull}){
  window.__lastGeo = {points, hull};
  if(!mapReady) return;
  // MapLibre v4 removeLayer/removeSource return void (not Promises) —
  // guard with getLayer/getSource, never .catch()
  ['occ-heat','occ-hull-fill','occ-hull-line','occ-pt-fill','occ-pt-stroke']
    .forEach(id=>{ try{ if(map.getLayer(id)) map.removeLayer(id); }catch(e){} });
  if(map.getSource('occ')){ try{ map.removeSource('occ'); }catch(e){} }
  if(map.getSource('hull')){ try{ map.removeSource('hull'); }catch(e){} }
  map.addSource('occ', {type:'geojson', data:points});
  map.addLayer({
    id:'occ-pt-stroke', type:'circle', source:'occ', paint:{
      'circle-radius':6.5,'circle-color':'#000','circle-opacity':0.18},
  });
  map.addLayer({
    id:'occ-pt-fill', type:'circle', source:'occ', paint:{
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

function render(d){
  document.getElementById('results').style.display='block';
  document.getElementById('capabilities').style.display='none';
  document.getElementById('audience').style.display='none';
  const s=d.scores;
  document.getElementById('m-total').textContent=s.gbif_total_matching.toLocaleString();
  document.getElementById('m-analysed').textContent=s.records_analysed.toLocaleString();
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
    <div style="display:flex;justify-content:space-between;padding:4px 0;border-bottom:1px solid var(--line)">
      <span>${b.label}</span>
      <span class="mono">${b.sample_pct}% vs ${b.population_pct}% (Δ${b.delta>0?'+':''}${b.delta} pp) — ${b.verdict}</span>
    </div>`).join('')
    : 'Baseline unavailable for this query.';

  // KBA
  const k=d.distribution_kba;
  if(k){
    const kb=k.kba;
    const chipsHtml =
      (kb.b1_meets?'<span class="chip ok">B1 met</span>':'<span class="chip">B1 no</span>')
      + (kb.b2_meets?'<span class="chip ok">B2 met</span>':'<span class="chip">B2 no</span>');
    document.getElementById('kba').innerHTML = `
      <table>
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
      <table><tr><th>Congener</th><th style="text-align:right">Overlap</th></tr>`
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
        <tr><th>Metric</th><th style="text-align:right">Value</th></tr>
        <tr><td>Standing-stock CO₂e</td><td class="num">${t.co2e_t.toLocaleString()} t</td></tr>
        <tr><td>Total carbon</td><td class="num">${t.carbon_t.toLocaleString()} t C</td></tr>
        <tr><td>Annual sequestration</td><td class="num">${t.annual_sequestration_co2e_t.toLocaleString()} t/yr</td></tr>
        <tr><td>Car-travel equivalent</td><td class="num">${e.car_km.toLocaleString()} km</td></tr>
      </table>
      <div class="note">${cb.scenario_note||''}</div>`;
  }

  document.getElementById('cites').innerHTML =
    'Method: '+d.standards.quality_tests;

  // map data
  const recs=(d.records&&d.records.analysed)||[];
  const feats=recs
    .filter(r=>r.decimalLatitude!=null&&r.decimalLongitude!=null)
    .map(r=>({
      type:'Feature',
      geometry:{type:'Point',
        coordinates:[r.decimalLongitude,r.decimalLatitude]},
      properties:{
        color:(r.issues&&String(r.issues).length>2)?RED:ACC,
        species:r.species, year:r.year, country:r.country,
      },
    }));
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
