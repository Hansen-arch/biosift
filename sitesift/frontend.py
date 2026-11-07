"""SiteSift frontend, one page, no build step, no API keys."""

HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>SiteSift, site biodiversity screening</title>
<script src="https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.js"></script>
<link href="https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.css" rel="stylesheet"/>
<style>
:root{
  --bg:#F4F1E8; --panel:#EDE9DC; --card:#FBF9F2; --line:#D6CFBC;
  --line-strong:#B9B09A; --text:#232019; --dim:#5C5647; --faint:#6E6653;
  --acc:#136F4E; --red:#A2382B; --amber:#75530F; --blue:#1D5FA8;
  --cr:#A2382B; --en:#B4551F; --vu:#75530F; --nt:#5C6B24; --lc:#136F4E;
}
*{box-sizing:border-box;margin:0;padding:0}
html,body{height:100%}
body{font:14px/1.5 -apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  background:var(--bg);color:var(--text);-webkit-font-smoothing:antialiased}
#app{display:grid;grid-template-columns:clamp(360px,32vw,460px) 1fr;
  height:100vh}
#panel{background:var(--panel);border-right:1px solid var(--line);
  overflow-y:auto;padding:18px 18px 60px}
#mapwrap{position:relative;min-width:0}
#map{position:absolute;inset:0}

h1{font-size:17px;letter-spacing:-.01em;display:flex;align-items:baseline;gap:8px}
h1 em{font-style:normal;color:var(--acc);font-weight:700}
.tagline{color:var(--dim);font-size:12.5px;margin:4px 0 16px;max-width:40ch}
h2{font-size:12px;text-transform:uppercase;letter-spacing:.09em;
  color:var(--faint);font-weight:700;margin:22px 0 8px;
  border-top:1px solid var(--line);padding-top:12px}
h2:first-of-type{border-top:none;padding-top:0}

.card{background:var(--card);border:1px solid var(--line);border-radius:8px;
  padding:12px 13px;margin-bottom:10px}
label.f{display:block;font-size:11.5px;text-transform:uppercase;
  letter-spacing:.06em;color:var(--faint);font-weight:700;margin-bottom:4px}
input[type=text],select{width:100%;padding:7px 9px;font:inherit;font-size:13px;
  color:var(--text);background:#fff;border:1px solid var(--line-strong);
  border-radius:6px}
input[type=text]:focus,select:focus{outline:2px solid var(--acc);outline-offset:-1px}
.row{display:flex;gap:8px}.row>*{flex:1}

button{font:inherit;font-size:13px;font-weight:600;cursor:pointer;
  border-radius:6px;border:1px solid var(--line-strong);background:#fff;
  color:var(--text);padding:8px 12px;transition:.14s}
button:hover:not(:disabled){border-color:var(--acc);color:var(--acc)}
button:disabled{opacity:.45;cursor:not-allowed}
button.primary{background:var(--acc);border-color:var(--acc);color:#fff}
button.primary:hover:not(:disabled){background:#0E5A3F;color:#fff}
button.ghost{background:transparent;border-color:var(--line-strong)}
.btns{display:flex;gap:8px;margin-top:10px;flex-wrap:wrap}
.btns button{flex:1;min-width:88px}

.tiles{display:grid;grid-template-columns:1fr 1fr;gap:8px}
.tile{background:var(--card);border:1px solid var(--line);border-radius:8px;
  padding:10px 12px}
.tile .n{font-size:20px;font-weight:700;letter-spacing:-.02em;
  font-variant-numeric:tabular-nums}
.tile .k{font-size:11px;color:var(--faint);text-transform:uppercase;
  letter-spacing:.05em;font-weight:600}
.tile.warn .n{color:var(--red)}

.bar{height:7px;border-radius:4px;background:#E2DCCB;overflow:hidden;
  display:flex;gap:2px}
.bar i{display:block;height:100%}
.rowline{display:flex;align-items:center;gap:8px;margin:5px 0;font-size:13px}
.rowline .lab{flex:0 0 96px;color:var(--dim)}
.rowline .val{flex:0 0 62px;text-align:right;font-variant-numeric:tabular-nums;
  font-weight:600;font-size:12.5px}
.rowline .bwrap{flex:1;height:7px;background:#E2DCCB;border-radius:4px;
  overflow:hidden}
.rowline .bwrap i{display:block;height:100%;background:var(--acc)}

table{width:100%;border-collapse:collapse;font-size:12.5px}
th{text-align:left;font-size:10.5px;text-transform:uppercase;
  letter-spacing:.06em;color:var(--faint);padding-bottom:4px;font-weight:700}
td{padding:4px 0;border-top:1px solid var(--line);vertical-align:top}
td.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
i.sci{font-style:italic}

.cat{margin-bottom:12px}
.cat .head{display:flex;align-items:center;gap:7px;margin-bottom:5px}
.dot{width:9px;height:9px;border-radius:50%;flex:0 0 auto}
.cat .head b{font-size:12.5px}
.cat .head span{color:var(--faint);font-size:11.5px;margin-left:auto;
  font-variant-numeric:tabular-nums}
.chip{display:inline-block;font-size:10.5px;font-weight:700;padding:1px 6px;
  border-radius:4px;color:#fff;letter-spacing:.03em}
.sp{font-size:12.5px;padding:2px 0;display:flex;gap:8px}
.sp b{font-weight:400;font-style:italic;flex:1;overflow-wrap:anywhere}
.sp span{color:var(--faint);font-variant-numeric:tabular-nums}

.note{font-size:12px;color:var(--dim);line-height:1.5}
ul.cav{list-style:none;font-size:12px;color:var(--dim)}
ul.cav li{padding:5px 0 5px 14px;position:relative;border-top:1px solid var(--line)}
ul.cav li:first-child{border-top:none}
ul.cav li:before{content:"-";position:absolute;left:0;color:var(--faint)}

#status{position:absolute;left:50%;top:18px;transform:translateX(-50%);
  background:var(--card);border:1px solid var(--line-strong);border-radius:8px;
  padding:9px 16px;font-size:13px;font-weight:600;box-shadow:0 4px 16px #0002;
  z-index:5;display:none;max-width:80%}
#status.on{display:block}
#status.err{background:#FBEDEA;border-color:var(--red);color:var(--red)}

#hint{position:absolute;left:16px;bottom:16px;background:var(--card);
  border:1px solid var(--line);border-radius:7px;padding:8px 12px;
  font-size:12.5px;color:var(--dim);max-width:320px;z-index:4;
  box-shadow:0 2px 10px #0001}
#hint b{color:var(--text)}

#basemaps{position:absolute;right:12px;top:12px;z-index:4;display:flex;gap:6px;
  background:var(--card);border:1px solid var(--line);border-radius:7px;
  padding:4px}
#basemaps button{font-size:11.5px;padding:4px 9px;border:none;background:none;
  font-weight:600;color:var(--dim)}
#basemaps button.on{background:var(--acc);color:#fff;border-radius:4px}

#legend{position:absolute;right:12px;bottom:28px;z-index:4;background:var(--card);
  border:1px solid var(--line);border-radius:7px;padding:9px 11px;font-size:11.5px;
  display:none}
#legend.on{display:block}
#legend div{display:flex;align-items:center;gap:6px;margin:2px 0}
#legend .sw{width:9px;height:9px;border-radius:50%}

.toggle{display:flex;align-items:center;gap:8px;font-size:12.5px;
  color:var(--dim);margin:8px 0 0}
.toggle input{accent-color:var(--acc);width:15px;height:15px}

.scriptbox{margin-top:8px;display:none}
.scriptbox.on{display:block}
pre{background:#232019;color:#E8E4D8;border-radius:7px;padding:11px;
  font:11.5px/1.55 ui-monospace,SFMono-Regular,Menlo,monospace;
  overflow:auto;max-height:260px;white-space:pre-wrap;overflow-wrap:anywhere}
.mono{font:11.5px ui-monospace,Menlo,monospace;color:var(--faint);
  overflow-wrap:anywhere}
@media(max-width:840px){
  #app{grid-template-columns:1fr;grid-template-rows:minmax(300px,42vh) 1fr}
  #mapwrap{grid-row:1}#panel{grid-row:2;border-right:none;
    border-top:1px solid var(--line)}
}
</style>
</head>
<body>
<div id="app">
  <aside id="panel">
    <h1>Site<em>Sift</em></h1>
    <p class="tagline">Draw a site. See which species are recorded there,
      which are of conservation concern, and how trustworthy those records are.</p>

    <h2>Site</h2>
    <div class="card">
      <label class="f" for="label">Site name</label>
      <input id="label" type="text" placeholder="e.g. Warehouse plot A"
             value=""/>
      <div class="row" style="margin-top:10px">
        <div><label class="f" for="yfrom">From year</label>
          <input id="yfrom" type="text" inputmode="numeric" placeholder="any"/></div>
        <div><label class="f" for="yto">To year</label>
          <input id="yto" type="text" inputmode="numeric" placeholder="any"/></div>
      </div>
      <div style="margin-top:10px">
        <label class="f" for="basis">Record type</label>
        <select id="basis">
          <option value="All">All records</option>
          <option value="HUMAN_OBSERVATION">Human observation</option>
          <option value="PRESERVED_SPECIMEN">Preserved specimen</option>
          <option value="MATERIAL_SAMPLE">Material sample</option>
          <option value="OCCURRENCE">Occurrence</option>
        </select>
      </div>
      <div class="btns">
        <button id="btnScreen" class="primary" disabled>Screen site</button>
        <button id="btnUndo" class="ghost" title="Remove last vertex">Undo</button>
        <button id="btnClear" class="ghost">Clear</button>
      </div>
      <div class="note" id="drawinfo" style="margin-top:9px">
        Click the map to place vertices; three or more closes a site.
      </div>
      <div class="btns">
        <button id="btnView" class="ghost">Use current map view</button>
      </div>
    </div>

    <div id="results" style="display:none">
      <h2>Summary</h2>
      <div class="tiles" id="tiles"></div>
      <div class="note" id="siteline" style="margin-top:8px"></div>

      <h2>Species of concern</h2>
      <div id="threat"></div>

      <h2>IUCN categories recorded</h2>
      <div class="card" id="iucn"></div>

      <h2>Native or introduced</h2>
      <div class="card" id="establish"></div>

      <h2>Most recorded species</h2>
      <div class="card" id="species"></div>

      <h2>Survey effort over time</h2>
      <div class="card" id="temporal"></div>

      <h2>Seasonality</h2>
      <div class="card" id="months"></div>

      <h2>Record quality</h2>
      <div class="card" id="issues"></div>

      <h2>Which datasets</h2>
      <div class="card" id="datasets"></div>

      <h2>Read before you cite</h2>
      <div class="card"><ul class="cav" id="caveats"></ul></div>

      <h2>Take it with you</h2>
      <div class="btns">
        <button id="btnJson">Download JSON</button>
        <button id="btnR">R script</button>
        <button id="btnPy">Python script</button>
      </div>
      <div class="scriptbox" id="scriptbox">
        <pre id="scriptcode"></pre>
        <div class="btns">
          <button id="btnCopy">Copy</button>
          <button id="btnDlScript" class="ghost">Download</button>
        </div>
      </div>
    </div>
  </aside>

  <main id="mapwrap">
    <div id="map"></div>
    <div id="basemaps"></div>
    <div id="status"></div>
    <div id="hint"><b>Click</b> to place vertices. <b>Backspace</b> undoes,
      <b>Esc</b> clears.</div>
    <div id="legend"></div>
  </main>
</div>

<script>
const BASEMAPS = {
  light: {title:'Light', tiles:['https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}'],
    attribution:'Esri, HERE, Garmin, FAO, NOAA, USGS'},
  osm: {title:'OSM', tiles:['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
    attribution:'&copy; OpenStreetMap contributors'},
  sat: {title:'Satellite', tiles:['https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'],
    attribution:'Esri, Maxar, Earthstar Geographics'},
};
const IUCN_COLOR = {EX:'#1A1A1A', EW:'#4D4D4D', CR:'#A2382B', EN:'#B4551F',
  VU:'#75530F', NT:'#5C6B24', LC:'#136F4E', DD:'#8A8474'};
const IUCN_CHIP = {CR:'#A2382B', EN:'#B4551F', VU:'#75530F'};

let map, vertices = [], drawn = false, bundle = null, scriptKind = 'r';
let markerLayer = {site:null, pts:null};

function rasterStyle(key){
  const b = BASEMAPS[key];
  return {version:8, glyphs:'https://demotiles.maplibre.org/font/{fontstack}/{range}.pbf',
    sources:{base:{type:'raster', tiles:b.tiles, tileSize:256, attribution:b.attribution, maxzoom:18}},
    layers:[{id:'bg', type:'background', paint:{'background-color':'#F4F1E8'}},
            {id:'base', type:'raster', source:'base'}]};
}

function initMap(){
  map = new maplibregl.Map({container:'map', style:rasterStyle('light'),
    center:[12,20], zoom:1.4, attributionControl:{compact:true}});
  map.addControl(new maplibregl.NavigationControl(), 'top-left');
  map.addControl(new maplibregl.ScaleControl({maxWidth:110, unit:'metric'}), 'bottom-left');
  map.on('load', () => {
    map.addSource('site', {type:'geojson', data:emptyFC()});
    map.addLayer({id:'site-fill', type:'fill', source:'site',
      paint:{'fill-color':'#136F4E','fill-opacity':0.14}});
    map.addLayer({id:'site-line', type:'line', source:'site',
      paint:{'line-color':'#136F4E','line-width':2}});
    map.addSource('vtx', {type:'geojson', data:emptyFC()});
    map.addLayer({id:'vtx-dot', type:'circle', source:'vtx',
      paint:{'circle-radius':4.5,'circle-color':'#136F4E',
             'circle-stroke-color':'#fff','circle-stroke-width':1.5}});
    map.addSource('records', {type:'geojson', data:emptyFC()});
    map.addLayer({id:'rec-dot', type:'circle', source:'records',
      paint:{'circle-radius':['interpolate',['linear'],['zoom'],1,2.5,10,5],
             'circle-color':['get','color'],'circle-opacity':0.82,
             'circle-stroke-color':'#fff','circle-stroke-width':0.6}});
  });
  map.on('click', e => {
    if (drawn) return;
    vertices.push([round6(e.lngLat.lng), round6(e.lngLat.lat)]);
    renderDraft();
  });
  for (const k of Object.keys(BASEMAPS)){
    const b = document.createElement('button');
    b.textContent = BASEMAPS[k].title; b.dataset.k = k;
    if (k === 'light') b.classList.add('on');
    b.onclick = () => {
      document.querySelectorAll('#basemaps button').forEach(x => x.classList.remove('on'));
      b.classList.add('on'); map.setStyle(rasterStyle(k));
      map.once('styledata', () => { addLayersAfterStyle(); });
    };
    document.getElementById('basemaps').appendChild(b);
  }
}

// setStyle drops sources/layers; re-add them once the new style is ready
function addLayersAfterStyle(){
  if (!map.getSource('site')){
    map.addSource('site', {type:'geojson', data:emptyFC()});
    map.addLayer({id:'site-fill', type:'fill', source:'site',
      paint:{'fill-color':'#136F4E','fill-opacity':0.14}});
    map.addLayer({id:'site-line', type:'line', source:'site',
      paint:{'line-color':'#136F4E','line-width':2}});
    map.addSource('vtx', {type:'geojson', data:emptyFC()});
    map.addLayer({id:'vtx-dot', type:'circle', source:'vtx',
      paint:{'circle-radius':4.5,'circle-color':'#136F4E',
             'circle-stroke-color':'#fff','circle-stroke-width':1.5}});
    map.addSource('records', {type:'geojson', data:emptyFC()});
    map.addLayer({id:'rec-dot', type:'circle', source:'records',
      paint:{'circle-radius':['interpolate',['linear'],['zoom'],1,2.5,10,5],
             'circle-color':['get','color'],'circle-opacity':0.82,
             'circle-stroke-color':'#fff','circle-stroke-width':0.6}});
    renderDraft(); if (bundle) renderPoints(bundle);
  }
}

const round6 = n => Math.round(n * 1e6) / 1e6;
const emptyFC = () => ({type:'FeatureCollection', features:[]});

function draftFC(){
  const f = [];
  if (vertices.length >= 3){
    const ring = vertices.concat([vertices[0]]);
    f.push({type:'Feature', properties:{}, geometry:{type:'Polygon', coordinates:[ring]}});
  } else if (vertices.length === 2){
    f.push({type:'Feature', properties:{}, geometry:{type:'LineString', coordinates:vertices}});
  }
  return {type:'FeatureCollection', features:f};
}

function renderDraft(){
  const src = map.getSource('site'); if (!src) return;
  src.setData(draftFC());
  map.getSource('vtx').setData({type:'FeatureCollection', features:
    vertices.map(v => ({type:'Feature', properties:{}, geometry:{type:'Point', coordinates:v}}))});
  const n = vertices.length;
  document.getElementById('drawinfo').innerHTML = drawn
    ? 'Site closed, press <b>Screen site</b>, or <b>Clear</b> to redraw.'
    : (n === 0 ? 'Click the map to place vertices; three or more closes a site.'
               : `${n} vertex${n > 1 ? 'es' : ''} placed. Click again to add, or screen once you have three.`);
  document.getElementById('btnScreen').disabled = n < 3;
  document.getElementById('btnUndo').disabled = n === 0 || drawn;
}

function clearAll(){
  vertices = []; drawn = false; bundle = null;
  document.getElementById('results').style.display = 'none';
  document.getElementById('legend').classList.remove('on');
  if (map.getSource('records')) map.getSource('records').setData(emptyFC());
  renderDraft();
}

function useView(){
  const b = map.getBounds();
  vertices = [[b.getWest(), b.getSouth()], [b.getEast(), b.getSouth()],
              [b.getEast(), b.getNorth()], [b.getWest(), b.getNorth()]];
  drawn = false; renderDraft();
}

function status(msg, isErr){
  const el = document.getElementById('status');
  el.textContent = msg;
  el.className = 'on' + (isErr ? ' err' : '');
  if (!msg) el.className = '';
}

async function screenSite(){
  if (vertices.length < 3) return;
  drawn = true; renderDraft();
  const label = document.getElementById('label').value.trim();
  const yf = document.getElementById('yfrom').value.trim();
  const yt = document.getElementById('yto').value.trim();
  const basis = document.getElementById('basis').value;
  const body = {geometry:{type:'Polygon', coordinates:[vertices.concat([vertices[0]])]},
    label, basis, year_from: yf ? parseInt(yf, 10) : null,
    year_to: yt ? parseInt(yt, 10) : null};
  status('Screening the site against GBIF…');
  document.getElementById('btnScreen').disabled = true;
  try{
    const r = await fetch('/api/screen', {method:'POST',
      headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)});
    const js = await r.json();
    if (!r.ok) throw new Error(js.detail || 'screening failed');
    bundle = js;
    render(js);
    status(`Screened in ${js.elapsed_s}s${js.cached ? ' (cached)' : ''}, ${js.summary.records.toLocaleString()} records`);
    setTimeout(() => status(''), 3600);
    if (js.site.bbox){
      map.fitBounds([[js.site.bbox[0], js.site.bbox[1]],
                     [js.site.bbox[2], js.site.bbox[3]]], {padding:60, duration:600});
    }
  }catch(e){
    status('Screening failed: ' + e.message, true);
    drawn = false; renderDraft();
  }finally{
    document.getElementById('btnScreen').disabled = vertices.length < 3;
  }
}

const esc = s => String(s == null ? '' : s).replace(/[&<>"']/g,
  c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const num = n => (n == null ? '-' : Number(n).toLocaleString());

function render(b){
  document.getElementById('results').style.display = 'block';
  const s = b.summary, site = b.site;
  document.getElementById('tiles').innerHTML = [
    tile(num(s.records), 'records inside'),
    tile(num(s.species_observed) + (s.species_truncated ? '+' : ''), 'species recorded'),
    tile(num(s.threatened_records), 'from threatened species', s.threatened_records > 0),
    tile(num(s.datasets) + (s.datasets_truncated ? '+' : ''), 'datasets'),
  ].join('');
  document.getElementById('siteline').innerHTML =
    `<b>${esc(site.label)}</b> · ${num(site.area_km2)} km² · ` +
    `${s.records_per_km2} records/km²`;
  renderThreat(b); renderIucn(b); renderEstablish(b); renderSpecies(b);
  renderTemporal(b); renderMonths(b); renderIssues(b); renderDatasets(b);
  document.getElementById('caveats').innerHTML =
    b.caveats.map(c => `<li>${esc(c)}</li>`).join('');
  renderPoints(b);
  if (b.points.length){
    document.getElementById('legend').classList.add('on');
    document.getElementById('legend').innerHTML =
      ['CR','EN','VU','NT','LC','DD'].filter(k => b.points.some(p => p.iucn === k))
        .map(k => `<div><span class="sw" style="background:${IUCN_COLOR[k]}"></span>${k}</div>`).join('')
      + `<div><span class="sw" style="background:#B9B09A"></span>unassessed</div>`;
  }
}

const tile = (n, k, warn) => `<div class="tile${warn ? ' warn' : ''}">
  <div class="n">${n}</div><div class="k">${k}</div></div>`;

function renderThreat(b){
  const el = document.getElementById('threat');
  const cats = b.threatened.categories.filter(c => (c.species || []).length);
  if (!cats.length){
    el.innerHTML = `<div class="card"><div class="note">No threatened
      (CR / EN / VU) species are recorded inside this site. That is a real
      finding only if surveying has been adequate, check the effort panel below.</div></div>`;
    return;
  }
  el.innerHTML = `<div class="card">` + cats.map(c => `
    <div class="cat">
      <div class="head">
        <span class="dot" style="background:${IUCN_CHIP[c.code]}"></span>
        <b>${esc(c.label)}</b>
        <span>${num(c.records)} records</span>
      </div>
      ${c.species.slice(0, 8).map(sp => `<div class="sp"><b>${esc(sp.name)}</b>
        <span>${num(sp.records)}</span></div>`).join('')}
      ${c.species.length > 8 ? `<div class="note">+${c.species.length - 8} more</div>` : ''}
    </div>`).join('') +
    `<div class="note" style="margin-top:8px">${esc(b.threatened.note)}</div></div>`;
}

function renderIucn(b){
  const el = document.getElementById('iucn');
  if (!b.iucn.length){ el.innerHTML = '<div class="note">No IUCN category is recorded on these records.</div>'; return; }
  const max = Math.max(...b.iucn.map(c => c.records));
  el.innerHTML = b.iucn.map(c => `<div class="rowline">
    <span class="lab"><span class="chip" style="background:${IUCN_COLOR[c.code] || '#8A8474'}">${c.code}</span></span>
    <span class="bwrap"><i style="width:${max ? (c.records / max * 100) : 0}%;background:${IUCN_COLOR[c.code] || '#8A8474'}"></i></span>
    <span class="val">${num(c.records)}</span></div>`).join('');
}

function renderEstablish(b){
  const e = b.establishment;
  const el = document.getElementById('establish');
  if (!e.recorded){
    el.innerHTML = `<div class="note">No record here carries
      <span class="mono">establishmentMeans</span>, so native and introduced
      cannot be separated for this site.</div>`;
    return;
  }
  const total = e.recorded;
  el.innerHTML = `<div class="bar">
      <i style="width:${e.native / total * 100}%;background:#136F4E"></i>
      <i style="width:${e.introduced / total * 100}%;background:#A2382B"></i>
      <i style="width:${e.uncertain / total * 100}%;background:#B9B09A"></i>
    </div>
    <div class="rowline"><span class="lab">Native</span>
      <span class="bwrap"><i style="width:${e.native / total * 100}%;background:#136F4E"></i></span>
      <span class="val">${num(e.native)}</span></div>
    <div class="rowline"><span class="lab">Introduced</span>
      <span class="bwrap"><i style="width:${e.introduced / total * 100}%;background:#A2382B"></i></span>
      <span class="val">${num(e.introduced)}</span></div>
    <div class="rowline"><span class="lab">Uncertain</span>
      <span class="bwrap"><i style="width:${e.uncertain / total * 100}%;background:#B9B09A"></i></span>
      <span class="val">${num(e.uncertain)}</span></div>
    <div class="note" style="margin-top:8px">Recorded on
      <b>${e.coverage_pct}%</b> of the site's records. It is shown as
      coverage rather than used to filter, because filtering would discard
      the ${100 - e.coverage_pct > 0 ? (100 - e.coverage_pct).toFixed(1) : 0}%
      that carry no value, including planted and escaped species.</div>`;
}

function renderSpecies(b){
  const el = document.getElementById('species');
  if (!b.species.length){ el.innerHTML = '<div class="note">No species-level records inside this site.</div>'; return; }
  el.innerHTML = `<table><thead><tr><th>Species</th><th style="text-align:right">Records</th></tr></thead><tbody>
    ${b.species.slice(0, 15).map(s => `<tr><td><i class="sci">${esc(s.name)}</i></td>
      <td class="num">${num(s.records)}</td></tr>`).join('')}</tbody></table>
    ${b.summary.species_truncated ? `<div class="note" style="margin-top:6px">Showing the 30 most recorded; the facet caps at 300 names.</div>` : ''}`;
}

function renderTemporal(b){
  const t = b.temporal, el = document.getElementById('temporal');
  if (!t.decades.length){ el.innerHTML = '<div class="note">No dated records.</div>'; return; }
  const max = Math.max(...t.decades.map(d => d.records));
  el.innerHTML = `<div style="display:flex;align-items:flex-end;gap:2px;height:64px;margin-bottom:6px">
    ${t.decades.map(d => `<div title="${d.decade}s: ${num(d.records)}" style="flex:1;
      background:var(--acc);border-radius:2px 2px 0 0;opacity:${0.35 + 0.65 * d.records / max};
      height:${Math.max(2, d.records / max * 100)}%"></div>`).join('')}
    </div>
    <div class="mono" style="display:flex;justify-content:space-between">
      <span>${t.decades[0].decade}s</span><span>${t.decades[t.decades.length - 1].decade}s</span></div>
    <div class="note" style="margin-top:8px">${t.years_with_records} years with records
      (${t.first_year}–${t.last_year}) · ${t.recent_pct}% since 2000 ·
      ${t.pre_1950_pct}% before 1950. Recent records reflect survey activity as
      much as the species.</div>`;
}

function renderMonths(b){
  const el = document.getElementById('months');
  const max = Math.max(1, ...b.months.map(m => m.records));
  if (!b.months.some(m => m.records)){ el.innerHTML = '<div class="note">No dated records.</div>'; return; }
  const names = ['J','F','M','A','M','J','J','A','S','O','N','D'];
  el.innerHTML = `<div style="display:flex;align-items:flex-end;gap:3px;height:56px">
    ${b.months.map((m, i) => `<div title="${names[i]}: ${num(m.records)}" style="flex:1;
      background:var(--blue);border-radius:2px 2px 0 0;opacity:${0.3 + 0.7 * m.records / max};
      height:${Math.max(2, m.records / max * 100)}%"></div>`).join('')}</div>
    <div class="mono" style="display:flex;justify-content:space-between;margin-top:4px">
      ${names.map(n => `<span>${n}</span>`).join('')}</div>`;
}

function renderIssues(b){
  const el = document.getElementById('issues');
  const shown = b.issues.filter(i => i.material).slice(0, 8);
  if (!shown.length){ el.innerHTML = '<div class="note">GBIF flagged no substantive issues on these records.</div>'; return; }
  el.innerHTML = `<table><thead><tr><th>GBIF issue</th><th style="text-align:right">Records</th><th style="text-align:right">%</th></tr></thead><tbody>
    ${shown.map(i => `<tr><td>${esc(i.label)}</td>
      <td class="num">${num(i.records)}</td>
      <td class="num" style="color:${i.severity === 'serious' ? 'var(--red)' : 'var(--dim)'}">${i.pct}%</td></tr>`).join('')}
    </tbody></table>
    <div class="note" style="margin-top:8px">A record can carry several
      issues, so these percentages do not sum to 100.` +
    (b.other_flag_count ? ` A further ${b.other_flag_count} technical flags
      (collection and institution matching and similar) are in the JSON
      export.` : '') + `</div>`;
}

function renderDatasets(b){
  const el = document.getElementById('datasets');
  if (!b.datasets.length){ el.innerHTML = '<div class="note">No datasets.</div>'; return; }
  el.innerHTML = `<table><thead><tr><th>Dataset</th><th style="text-align:right">Records</th></tr></thead><tbody>
    ${b.datasets.map(d => `<tr><td><a href="${esc(d.url)}" target="_blank" rel="noopener"
      style="color:var(--blue);text-decoration:none">${esc(d.title)}</a></td>
      <td class="num">${num(d.records)} <span style="color:var(--faint)">${d.pct}%</span></td></tr>`).join('')}
    </tbody></table>`;
}

function renderPoints(b){
  if (!b.points.length || !map.getSource('records')) return;
  map.getSource('records').setData({type:'FeatureCollection', features:
    b.points.map(p => ({type:'Feature',
      properties:{color: IUCN_COLOR[p.iucn] || '#B9B09A', name:p.species, year:p.year, iucn:p.iucn},
      geometry:{type:'Point', coordinates:[p.lon, p.lat]}}))});
  const src = map.getSource('site');
  if (src && b.site.wkt){
    // redraw the screened polygon exactly as the server measured it
    src.setData({type:'FeatureCollection', features:[{type:'Feature', properties:{},
      geometry:{type:'Polygon', coordinates:[vertices.concat([vertices[0]])]}}]});
  }
}

// ── exports
function rScript(){
  const label = document.getElementById('label').value.trim() || 'site';
  const yf = document.getElementById('yfrom').value.trim();
  const yt = document.getElementById('yto').value.trim();
  const basis = document.getElementById('basis').value;
  const wkt = bundle.site.wkt;
  const filters = [
    yf && yt ? `,\n  year = "${yf},${yt}"` : '',
    basis !== 'All' ? `,\n  basisOfRecord = "${basis}"` : '',
  ].join('');
  return `# SiteSift, reproducible screen of ${label.replace(/"/g, '')}
# ${bundle.site.area_km2} km² · screened ${new Date().toISOString().slice(0, 10)}
library(rgbif)

wkt <- "${wkt}"

occ <- occ_search(
  geometry = wkt,
  hasCoordinate = TRUE,
  occurrenceStatus = "PRESENT",${filters}
  limit = 5000,
  fields = c("scientificName", "decimalLatitude", "decimalLongitude",
             "year", "basisOfRecord", "iucnRedListCategory",
             "establishmentMeans", "datasetKey", "issue")
)

occ$data
rgbif::occ_count(geometry = wkt, hasCoordinate = TRUE, occurrenceStatus = "PRESENT")
`;
}

function pyScript(){
  const label = document.getElementById('label').value.trim() || 'site';
  const yf = document.getElementById('yfrom').value.trim();
  const yt = document.getElementById('yto').value.trim();
  const basis = document.getElementById('basis').value;
  const wkt = bundle.site.wkt;
  return `'''SiteSift, reproducible screen of ${label.replace(/"/g, '')}
${bundle.site.area_km2} km² · screened ${new Date().toISOString().slice(0, 10)}
'''
import requests

GBIF = "https://api.gbif.org/v1/occurrence/search"
WKT = "${wkt}"

params = [
    ("geometry", WKT),
    ("hasCoordinate", "true"),
    ("occurrenceStatus", "PRESENT"),${yf && yt ? `
    ("year", "${yf},${yt}"),` : ''}${basis !== 'All' ? `
    ("basisOfRecord", "${basis}"),` : ''}
    ("limit", 300),
]

records = requests.get(GBIF, params=params, timeout=60).json()

# note: iucnRedListCategory takes no comma list, one request per category
for cat in ("CR", "EN", "VU"):
    r = requests.get(GBIF, params=params[:4] + [
        ("iucnRedListCategory", cat), ("limit", 0),
        ("facet", "scientificName"), ("facetLimit", 100)], timeout=60).json()
    print(cat, r["count"], [c["name"] for c in r["facets"][0]["counts"]])
`;
}

function showScript(kind){
  scriptKind = kind;
  const box = document.getElementById('scriptbox');
  document.getElementById('scriptcode').textContent = kind === 'r' ? rScript() : pyScript();
  box.classList.add('on');
  box.scrollIntoView({behavior:'smooth', block:'nearest'});
}

function download(name, text, type){
  const blob = new Blob([text], {type: type});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob); a.download = name; a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 4000);
}

// ── wiring
initMap();
document.getElementById('btnScreen').onclick = screenSite;
document.getElementById('btnClear').onclick = clearAll;
document.getElementById('btnView').onclick = useView;
document.getElementById('btnUndo').onclick = () => { vertices.pop(); renderDraft(); };
document.addEventListener('keydown', e => {
  if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT') return;
  if (e.key === 'Backspace'){ e.preventDefault(); vertices.pop(); renderDraft(); }
  if (e.key === 'Escape') clearAll();
  if (e.key === 'Enter' && vertices.length >= 3 && !drawn) screenSite();
});
document.getElementById('btnJson').onclick = () =>
  download('sitesift-' + (bundle.site.label || 'site').replace(/\W+/g, '-').toLowerCase() + '.json',
    JSON.stringify(bundle, null, 2), 'application/json');
document.getElementById('btnR').onclick = () => showScript('r');
document.getElementById('btnPy').onclick = () => showScript('py');
document.getElementById('btnCopy').onclick = () => {
  navigator.clipboard.writeText(document.getElementById('scriptcode').textContent);
  document.getElementById('btnCopy').textContent = 'Copied';
  setTimeout(() => document.getElementById('btnCopy').textContent = 'Copy', 1500);
};
document.getElementById('btnDlScript').onclick = () =>
  download(scriptKind === 'r' ? 'sitesift-screen.R' : 'sitesift-screen.py',
    document.getElementById('scriptcode').textContent, 'text/plain');
renderDraft();
</script>
</body>
</html>
"""
