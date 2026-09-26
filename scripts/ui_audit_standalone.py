"""
Standalone-app UI audit (raw CDP, reuses ui_audit harness).

Usage: venv/bin/python scripts/ui_audit_standalone.py [species]
Env:   BIOSIFT_URL (default http://localhost:8080)
       SA_PHASE=viewport  -> boot + controls + viewport matrix only
                            (skips the two ~90 s analysis runs)

Checks:
  1. boot: title, map loaded, basemap layers, zero page errors
  2. every control hit-testable (elementFromPoint catches overlays)
  3. Run Analysis x2 species: metrics, tables, map layers, EOO hull
  4. map colour agrees with the analysis (BDQ verdict, not GBIF issues)
  5. clusters render at world zoom; popup opens on a real point click
  6. basemap switch keeps data layers
  7. no clipped/truncated text (scrollWidth/Height probes) across a
     4-viewport matrix incl. the user's 1366x768 (1092x560 CSS)
  8. search form above the fold + bottom content reachable everywhere
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ui_audit  # noqa: E402  (harness: start_chrome, Tab)
from ui_audit import Tab, start_chrome  # noqa: E402

ui_audit.SHOTS = "/tmp/biosift_sa_shots"
os.makedirs(ui_audit.SHOTS, exist_ok=True)
APP = os.environ.get("BIOSIFT_URL", "http://localhost:8080")
SPECIES = sys.argv[1] if len(sys.argv) > 1 else "Panthera leo"
VIEWPORTS = [(1440, 900), (1092, 560), (820, 900), (390, 844)]

FAILS = []


def check(label, ok, detail=""):
    print(f"  [{'PASS' if ok else 'FAIL'}] {label}"
          + (f" — {detail}" if detail else ""))
    if not ok:
        FAILS.append(label)


def errs(tab):
    return tab.js("window.__errs || []")


def install_hooks(tab):
    tab.js("""
      window.__errs = [];
      window.addEventListener('error',
        e => window.__errs.push(String(e.message).slice(0,200)));
      window.addEventListener('unhandledrejection',
        e => window.__errs.push('promise: '
            + String(e.reason && e.reason.message || e.reason)
                  .slice(0,200)));
    """)
    tab.js("""
      (() => {
        const wire = () => {
          if (window.__map && !window.__map.__errHook) {
            window.__map.__errHook = true;
            window.__map.on('error',
              e => window.__errs.push('map: ' + String(
                (e && e.error && e.error.message) || e).slice(0,200)));
          }
        };
        wire(); setTimeout(wire, 2500);
      })()
    """)


def top_element(tab, selector):
    """Topmost element at the control's center (scrolls into view)."""
    return tab.js(f"""
      (() => {{
        const el = document.querySelector({json.dumps(selector)});
        if (!el) return 'missing';
        el.scrollIntoView({{block: 'center'}});
        const r = el.getBoundingClientRect();
        if (r.width < 2 || r.height < 2) return 'zero-size';
        const top = document.elementFromPoint(
            r.x + r.width / 2, r.y + r.height / 2);
        return top ? (top.tagName + (top === el ? ' (self)' : ''
            + ' (' + (top.id || top.className || '').toString()
                      .slice(0, 40) + ')')) : 'none';
      }})()
    """)


def top_element_no_scroll(tab, selector):
    """Hit-test WITHOUT scrollIntoView (document scroll untouched)."""
    return tab.js(f"""
      (() => {{
        const el = document.querySelector({json.dumps(selector)});
        if (!el) return 'missing';
        const r = el.getBoundingClientRect();
        if (r.width < 2 || r.height < 2) return 'zero-size';
        const top = document.elementFromPoint(
            r.x + r.width / 2, r.y + r.height / 2);
        return top ? (top.tagName + (top === el ? ' (self)' : ''
            + ' (' + (top.id || top.className || '').toString()
                      .slice(0, 40) + ')')) : 'none';
      }})()
    """)


def set_input(tab, sel, value):
    return tab.js(f"""
      (() => {{
        const el = document.querySelector({json.dumps(sel)});
        if (!el) return 'missing';
        const setter = Object.getOwnPropertyDescriptor(
            window.HTMLInputElement.prototype, 'value').set;
        el.focus(); setter.call(el, {json.dumps(value)});
        el.dispatchEvent(new Event('input', {{bubbles: true}}));
        el.dispatchEvent(new Event('change', {{bubbles: true}}));
        el.blur();
        return 'ok';
      }})()
    """)


def layer_ids(tab):
    return tab.js(
        "window.__map ? window.__map.getStyle().layers"
        ".map(l => l.id) : null")


def geo_count(tab):
    return tab.js(
        "(window.__lastGeo && window.__lastGeo.points"
        " && window.__lastGeo.points.features"
        " && window.__lastGeo.points.features.length) || 0")


def status_text(tab):
    return tab.js(
        "document.getElementById('status')"
        " ? document.getElementById('status').textContent : ''")


def clipped_text(tab):
    """Elements whose text is cut off by overflow (no ellipsis)."""
    return tab.js("""
      (() => {
        const bad = [];
        document.querySelectorAll('#panel *').forEach(el => {
          const cs = getComputedStyle(el);
          if (cs.display === 'none' || cs.visibility === 'hidden'
              || el.tagName === 'svg' || el.tagName === 'SVG') return;
          const hasText = [...el.childNodes].some(
            n => n.nodeType === 3 && n.textContent.trim());
          if (!hasText) return;
          if (el.scrollWidth > el.clientWidth + 3
              || el.scrollHeight > el.clientHeight + 4) {
            bad.push(el.tagName + '.'
              + String(el.className).slice(0, 26)
              + ' "' + el.textContent.trim().slice(0, 24) + '"');
          }
        });
        return bad.slice(0, 6);
      })()
    """) or []


def audit_controls(tab):
    print("== CONTROL HIT TESTS ==")
    for sel, name in [
        ("#species", "species input"),
        ("#yf", "year-from"),
        ("#yt", "year-to"),
        ("#limit", "max records"),
        ("#basis", "basis select"),
        ("#profile", "SDM profile select"),
        ("#run", "Run Analysis button"),
    ]:
        res = top_element(tab, sel)
        ok = res.split(" ")[0] in ("INPUT", "SELECT", "BUTTON")
        check(f"clickable: {name}", ok, res)
    bmsel = tab.js("""
      (() => {
        const el = document.querySelector('#mapwrap select');
        if (!el) return 'missing';
        const r = el.getBoundingClientRect();
        const top = document.elementFromPoint(
            r.x + r.width / 2, r.y + r.height / 2);
        return 'found top=' + (top ? top.tagName : 'none')
            + ' visible=' + (r.width > 10 && r.height > 10);
      })()
    """)
    check("clickable: basemap select", "top=SELECT" in str(bmsel), bmsel)


def run_analysis(tab, species):
    print(f"== RUN ANALYSIS: {species} ==")
    check("set species", set_input(tab, "#species", species) == "ok")
    tab.js("""
      document.getElementById('species').dispatchEvent(
        new KeyboardEvent('keydown', {key: 'Enter', bubbles: true}));
    """)
    time.sleep(2)
    st = status_text(tab)
    check("click triggered fetch", "Fetching" in st or "Error" in st,
          f"status='{st[:60]}'")
    deadline = time.time() + 180
    final = ""
    while time.time() < deadline:
        final = status_text(tab)
        if "Analysis complete" in final or final.startswith("Error"):
            break
        time.sleep(2)
    check("analysis completed", "Analysis complete" in final, final[:100])
    check("no page errors after run", len(errs(tab)) == 0,
          json.dumps(errs(tab))[:200])

    visible = tab.js(
        "document.getElementById('results').style.display !== 'none'")
    check("results panel visible", bool(visible))
    metrics = tab.js("""
      ['m-total','m-analysed','m-health','m-sdm'].map(id =>
        document.getElementById(id).textContent).join(' | ')
    """)
    check("metrics filled", "—" not in metrics, metrics[:80])

    nrows = tab.js("document.querySelectorAll('#t-checks tr').length")
    check("quality-check rows", (nrows or 0) >= 5, f"{nrows} rows")

    # colour agreement: map colours come from OUR BDQ verdict.
    # The server embeds only the first 200 analysed rows, so compare
    # the map against the EMBEDDED records (exact) and require that
    # embedded flagged <= overall flagged from the score frame.
    agree = tab.js("""
      (() => {
        const recs = (window.__bundle.records
            && window.__bundle.records.analysed) || [];
        return JSON.stringify({
          served: recs.filter(r => r.biosift_flag === true).length,
          overall: window.__bundle.scores.records_analysed
                 - window.__bundle.scores.records_clean,
          map: window.__flaggedSeen || 0});
      })()
    """)
    d = json.loads(agree)
    check("map color = BDQ verdict (not GBIF issues)",
          d["served"] == d["map"] and d["served"] <= d["overall"],
          f"embedded_flagged={d['served']} on_map={d['map']}"
          f" overall_flagged={d['overall']} (embedded sample of"
          f" first 200 rows)")

    # new sections actually render
    temporal = tab.js(
        "document.getElementById('temporal').innerText.slice(0,60)")
    check("temporal section rendered",
          bool(temporal and ("Span" in temporal or "—" in temporal
                             or "No dated" in temporal)),
          (temporal or "")[:50])
    sdm_txt = tab.js(
        "document.getElementById('sdm').innerText.slice(0,80)")
    check("SDM gate table rendered",
          bool(sdm_txt and ("gate" in sdm_txt.lower()
                            or "profile" in sdm_txt.lower())),
          (sdm_txt or "")[:50])

    kba_txt = tab.js(
        "document.getElementById('kba').innerText.slice(0,120)")
    check("KBA section rendered", bool(kba_txt and
          ("EOO" in kba_txt or "Extent" in kba_txt
           or "Not enough" in kba_txt)), (kba_txt or "")[:80])

    bar = tab.js("""(() => {
        const b = document.getElementById('speciesbar');
        return b.style.display + ' name=' + document
            .getElementById('sb-name').textContent;
      })()""")
    check("species bar shown", "block" in str(bar), str(bar))
    lids = layer_ids(tab)
    check("map data layers pushed",
          bool(lids) and "occ-pt-fill" in lids, json.dumps(lids))
    n = geo_count(tab)
    check("points in geojson", (n or 0) > 0, f"{n} features")
    hull = tab.js("!!(window.__lastGeo && window.__lastGeo.hull)")
    check("EOO hull present", bool(hull))
    tab.shot("results")


def basemap_after_results(tab):
    print("== BASEMAP SWITCH AFTER RESULTS ==")
    tab.js("""
      (() => {
        const s = document.querySelector('#mapwrap select');
        s.value = 'satellite';
        s.dispatchEvent(new Event('change', {bubbles: true}));
      })()
    """)
    time.sleep(3)
    lids = layer_ids(tab)
    check("data layers survive style swap",
          bool(lids) and "occ-pt-fill" in lids and "base" in lids,
          json.dumps(lids))
    check("points still in geojson", geo_count(tab) > 0)
    tab.js("""
      (() => {
        const s = document.querySelector('#mapwrap select');
        s.value = 'light';
        s.dispatchEvent(new Event('change', {bubbles: true}));
      })()
    """)
    time.sleep(2)


def popup_and_cluster(tab):
    print("== CLUSTER & POPUP ==")

    def goto(center, zoom):
        # IIFE: jumpTo returns the map object, which CDP cannot
        # serialise ("Object reference chain is too long")
        tab.js(f"(() => {{ window.__map.jumpTo("
               f"{{center:[{center[0]},{center[1]}], zoom:{zoom}}}); }})()")
        # wait for render idle (tiles + cluster index rebuilt)
        tab.js("""
          window.__idle = new Promise(res => {
            let done = false;
            const fin = () => { if(!done){ done = true; res(1); } };
            window.__map.once('idle', fin);
            setTimeout(fin, 5000);
          });
        """)
        time.sleep(0.5)
        tab.js("window.__idle")  # resolve promise via awaitPromise

    goto([20, 5], 1.6)
    cl = tab.js("window.__idle.then(() => JSON.stringify("\
        "window.__map.queryRenderedFeatures(undefined, "\
        "{layers:['clusters']}).map(f => f.properties.cluster)))")
    n_cl = len(json.loads(cl or "[]"))
    check("clusters render at world zoom", n_cl > 0, f"{n_cl} clusters")

    # pick a REAL leaf coordinate from the embedded data (sparse
    # datasets: a cluster centroid at z9 can be empty — jumping to an
    # actual point location always lands on the leaf)
    coord = tab.js("""
      (() => {
        const fs = (window.__lastGeo && window.__lastGeo.points
            && window.__lastGeo.points.features) || [];
        if (!fs.length) return 'null';
        const f = fs.find(f => f.properties.biosift_flag === true)
                  || fs[0];
        window.__pt = f.geometry.coordinates.slice();
        return JSON.stringify(window.__pt);
      })()
    """)
    check("leaf point located for popup", coord != "null", coord)
    if coord == "null":
        return
    tab.js("""
      window.__idle3 = new Promise(res => {
        let done = false;
        const fin = () => { if(!done){ done = true; res(1); } };
        window.__map.once('idle', fin);
        setTimeout(fin, 5000);
      });
      (() => { window.__map.jumpTo(
          {center: window.__pt, zoom: 9}); })();
    """)
    time.sleep(0.5)
    tab.js("window.__idle3")
    time.sleep(1)
    # project to CONTAINER pixels, then add the container's window
    # offset — CDP clicks use window coordinates, map.project does not
    xy = tab.js("window.__idle3.then(() => { const p = window.__map"
                ".project(window.__pt); const r = document"
                ".getElementById('map').getBoundingClientRect(); "
                "return JSON.stringify({x: Math.round(r.left + p.x), "
                "y: Math.round(r.top + p.y)}); })")
    p = json.loads(xy)
    for t in ("mousePressed", "mouseReleased"):
        tab.send("Input.dispatchMouseEvent", type=t, x=p["x"],
                 y=p["y"], button="left", clickCount=1)
    time.sleep(1)
    pop = tab.js(
        "!!document.querySelector('.maplibregl-popup-content')")
    check("popup opens on point click", bool(pop))
    if pop:
        content = tab.js(
            "document.querySelector('.maplibregl-popup-content')"
            ".innerText")
        ok = ("Passes all" in content) or ("Flag" in content) \
            or ("Coordinate" in content) or ("Uncertainty" in content)
        check("popup shows BDQ verdict + fields", ok,
              content.replace("\n", " | ")[:90])
        tab.shot("popup")


def exports_smoke(tab):
    print("== EXPORTS ==")
    ok = tab.js("""
      (() => {
        const csv = document.getElementById('exp-csv');
        csv.click();
        return 'clicked';
      })()
    """)
    check("CSV export clickable", ok == "clicked")
    # JSON round-trip: bundle must be serialisable (numpy-safe check
    # already proven server-side; here just confirm presence)
    has = tab.js("!!window.__bundle && !!window.__bundle.scores")
    check("bundle cached for JSON export", bool(has))


def viewports(tab):
    print("== VIEWPORT MATRIX ==")
    for w, h in VIEWPORTS:
        print(f"-- {w}x{h} --")
        tab.send("Emulation.setDeviceMetricsOverride", width=w,
                 height=h, deviceScaleFactor=1, mobile=(w < 500))
        time.sleep(2)
        tab.js("(() => { window.scrollTo(0,0); const s = document"
               ".querySelector('#panel .scroll');"
               "if(s) s.scrollTop=0; })()")
        time.sleep(1)
        # fresh-load fold measurement FIRST (nothing scrolled yet)
        pos = tab.js("""
          (() => {
            const el = document.querySelector('#species');
            if (!el) return JSON.stringify({form_top: -999});
            const r = el.getBoundingClientRect();
            return JSON.stringify({
              form_top: Math.round(r.top),
              viewport_h: window.innerHeight,
              win_scroll_y: Math.round(window.scrollY)});
          })()
        """)
        d = json.loads(pos)
        check(f"search form above fold ({w}x{h})",
              0 <= d.get("form_top", -999) < d.get("viewport_h", 0),
              f"form_top={d.get('form_top')}"
              f" viewport_h={d.get('viewport_h')}"
              f" win_scroll_y={d.get('win_scroll_y')}")
        # then reachability: directly, or after an in-panel scroll on
        # mobile/short screens (panel capped at 46vh — standard
        # stacked-dashboard behaviour)
        res = top_element_no_scroll(tab, "#run")
        if res.split(" ")[0] == "BUTTON":
            check(f"Run button reachable ({w}x{h})", True,
                  "directly (above fold)")
        else:
            tab.js("(() => { document.querySelector('#run')"
                   ".scrollIntoView({block: 'center'}); })()")
            time.sleep(1)
            res2 = top_element_no_scroll(tab, "#run")
            check(f"Run button reachable ({w}x{h})",
                  res2.split(" ")[0] == "BUTTON",
                  f"after panel scroll: {res2}")
        # bottom-most VISIBLE content reachable after scrolling panel
        tab.js("(() => { const s = document"
               ".querySelector('#panel .scroll');"
               "if(s) s.scrollTo(0, 999999); })()")
        time.sleep(1)
        last = tab.js("""
          (() => {
            const kids = document
                .querySelector('#panel .scroll').children;
            for (let i = kids.length - 1; i >= 0; i--) {
              const r = kids[i].getBoundingClientRect();
              if (r.width > 2 && r.height > 2) {
                const cy = Math.max(
                    2, Math.min(r.y + r.height / 2,
                                window.innerHeight - 2));
                const cx = Math.max(
                    2, Math.min(r.x + r.width / 2,
                                window.innerWidth - 2));
                const top = document.elementFromPoint(cx, cy);
                return JSON.stringify({hit: top ? top.tagName : 'none',
                                       id: kids[i].id
                                          || kids[i].className});
              }
            }
            return JSON.stringify({hit: 'none', id: 'all-hidden'});
          })()
        """)
        dl = json.loads(last)
        check(f"bottom content reachable ({w}x{h})",
              dl["hit"] != "none", f"last={dl['id']} hit={dl['hit']}")
        clips = clipped_text(tab)
        check(f"no clipped text ({w}x{h})", len(clips) == 0,
              json.dumps(clips)[:160])
        tab.shot(f"vp_{w}x{h}")
    tab.send("Emulation.clearDeviceMetricsOverride")
    time.sleep(1)


def main():
    proc = start_chrome()
    try:
        tab = Tab(APP)
        tab.send("Page.enable")
        tab.send("Runtime.enable")
        install_hooks(tab)
        deadline = time.time() + 30
        booted = False
        while time.time() < deadline:
            try:
                if tab.js("!!document.getElementById('run')"):
                    booted = True
                    break
            except Exception:
                pass
            time.sleep(1)
        check("app booted (Run button present)", booted)
        if not booted:
            print("BODY:", tab.js("document.body.innerText.slice(0,400)"))
            return

        time.sleep(3)
        check("page title", tab.js("document.title")
              .startswith("BioSift"))
        check("map object exists", tab.js("!!window.__map"))
        loaded = False
        dl = time.time() + 25
        while time.time() < dl:
            if tab.js("window.__map && window.__map.loaded()") is True:
                loaded = True
                break
            time.sleep(2)
        check("map loaded", loaded)
        lids = layer_ids(tab)
        check("basemap layers [bg, base]",
              lids == ["bg", "base"], json.dumps(lids))
        check("zero errors at boot", len(errs(tab)) == 0,
              json.dumps(errs(tab))[:200])
        caps = tab.js(
            "document.getElementById('capabilities').style.display")
        check("capability strip shown at boot", caps == "block", caps)
        tab.shot("01_landing")

        audit_controls(tab)

        if os.environ.get("SA_PHASE") == "viewport":
            viewports(tab)
            tab.close()
        else:
            run_analysis(tab, SPECIES)
            basemap_after_results(tab)
            popup_and_cluster(tab)
            exports_smoke(tab)

            run_analysis(tab, "Quercus robur")
            carbon_txt = tab.js(
                "document.getElementById('carbon').innerText"
                ".slice(0,80)")
            check("oak carbon rendered", bool(carbon_txt), carbon_txt or "")

            viewports(tab)
            tab.close()
    finally:
        proc.terminate()

    print()
    if FAILS:
        print(f"RESULT: {len(FAILS)} FAILURE(S): {FAILS}")
        sys.exit(1)
    print("RESULT: ALL CHECKS PASSED")


if __name__ == "__main__":
    main()
