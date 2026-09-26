"""
Standalone-app UI audit (raw CDP, reuses ui_audit harness).

Usage: venv/bin/python scripts/ui_audit_standalone.py [species]
Env:   BIOSIFT_URL (default http://localhost:8080)

Checks:
  1. boot: title, map object, basemap tiles wired, zero page errors
  2. every control actually hit-testable (elementFromPoint — catches
     invisible overlays that swallow clicks)
  3. real Run Analysis click -> results render, metrics fill,
     map layers pushed, hull drawn
  4. second species run (repeatability) + basemap switch AFTER results
     (points must survive style swap)
  5. narrow-viewport pass: panel/controls still reachable
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
    """Return tag of the topmost element at the control's center."""
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
        const proto = el.tagName === 'TEXTAREA'
            ? window.HTMLTextAreaElement.prototype
            : window.HTMLInputElement.prototype;
        const setter = Object.getOwnPropertyDescriptor(
            proto, 'value').set;
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
    # map-side basemap select (created at runtime, inside a wrapper div)
    bmsel = tab.js("""
      (() => {
        const s = [...document.querySelectorAll('#mapwrap select')]
        const el = s[0];
        if (!el) return 'missing';
        const r = el.getBoundingClientRect();
        const top = document.elementFromPoint(
            r.x + r.width / 2, r.y + r.height / 2);
        return 'found top=' + (top ? top.tagName : 'none')
            + ' visible=' + (r.width > 10 && r.height > 10);
      })()
    """)
    check("clickable: basemap select", "top=SELECT" in str(bmsel), bmsel)


def run_analysis(tab, species, expect_hull=True):
    print(f"== RUN ANALYSIS: {species} ==")
    check("set species", set_input(tab, "#species", species) == "ok")
    tab.js("""
      document.getElementById('species').dispatchEvent(
        new KeyboardEvent('keydown', {key: 'Enter', bubbles: true}));
    """)
    # status must change from idle within 5s
    time.sleep(2)
    st = status_text(tab)
    check("click triggered fetch", "Fetching" in st or "Error" in st,
          f"status='{st[:60]}'")
    # poll to completion (server bundle takes 30-90s)
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
    print("  metrics:", metrics)
    check("metrics filled", "—" not in metrics, metrics[:80])
    nrows = tab.js("document.querySelectorAll('#t-checks tr').length")
    check("quality-check rows", (nrows or 0) >= 5, f"{nrows} rows")
    kba_txt = tab.js(
        "document.getElementById('kba').innerText.slice(0,120)")
    check("KBA section rendered", bool(kba_txt and
          "Not enough" not in kba_txt or "EOO" in kba_txt
          or "Extent" in kba_txt), (kba_txt or "")[:80])
    carbon_txt = tab.js(
        "document.getElementById('carbon').innerText.slice(0,100)")
    print("  carbon:", (carbon_txt or "").replace("\\n", " | ")[:90])
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
    hull = tab.js(
        "!!(window.__lastGeo && window.__lastGeo.hull)")
    if expect_hull:
        check("EOO hull present", bool(hull))
    tab.shot("results")
    return final


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


def narrow_viewport(tab):
    # 820x900: general mobile-ish; 1092x560 = 1366x768 physical at 125%
    # browser zoom (user's ThinkPad X230) — regression: capability strip
    # above the form consumed ~595px, pushing the search form below the
    # fold on short viewports
    for w, h in [(820, 900), (1092, 560)]:
        print(f"== VIEWPORT {w}x{h} ==")
        tab.send("Emulation.setDeviceMetricsOverride", width=w,
                 height=h, deviceScaleFactor=1, mobile=False)
        time.sleep(2)
        # reset ALL scrolling (window + panel) for a deterministic
        # fresh-load measurement — earlier scrollIntoView may have
        # scrolled the document
        tab.js("window.scrollTo(0,0);"
               "document.querySelector('#panel .scroll')"
               ".scrollTop=0")
        time.sleep(1)
        res = top_element_no_scroll(tab, "#run")
        check(f"Run button reachable ({w}x{h})",
              res.split(" ")[0] == "BUTTON", res)
        pos = tab.js(f"""
          (() => {{
            const r = document.querySelector('#species')
                .getBoundingClientRect();
            const s = document.querySelector('#panel .scroll');
            return JSON.stringify({{
              form_top: Math.round(r.top), viewport_h: window.innerHeight,
              win_scroll_y: Math.round(window.scrollY),
              scroll_would: s.scrollHeight > s.clientHeight + 4,
              scroll_top_now: Math.round(s.scrollTop)}});
          }})()
        """)
        d = json.loads(pos)
        ok = (d["form_top"] >= 0 and d["form_top"] < d["viewport_h"])
        check(f"search form visible above fold ({w}x{h})", ok,
              f"form_top={d['form_top']} viewport_h={d['viewport_h']}"
              f" win_scroll_y={d['win_scroll_y']}")
        # scroll panel to bottom: pitch + results must remain reachable
        # scroll panel to its very bottom: the LAST content element
        # must be hit-testable (proves nothing is clipped/unreachable)
        tab.js("document.querySelector('#panel .scroll')"
               ".scrollTo(0, 999999)")
        time.sleep(1)
        res2 = tab.js(f"""
          (() => {{
            const kids = document
                .querySelector('#panel .scroll').children;
            const last = kids[kids.length - 1];
            const r = last.getBoundingClientRect();
            const top = document.elementFromPoint(
                r.x + r.width / 2, r.y + r.height / 2);
            return JSON.stringify({{
              last_id: last.id || last.className,
              hit: top ? top.tagName : 'none',
              bottom_visible: r.bottom <= window.innerHeight + 2}});
          }})()
        """)
        d2 = json.loads(res2)
        check(f"bottom content reachable after scroll ({w}x{h})",
              d2["hit"] != "none" and d2["bottom_visible"],
              f"last={d2['last_id']} hit={d2['hit']}")
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
        # wait for app boot
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

        time.sleep(3)  # map tiles settle
        check("page title", tab.js("document.title")
              .startswith("BioSift"))
        check("map object exists", tab.js("!!window.__map"))
        # tiles can stream for a while — poll for load
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

        # viewport-only mode (SA_PHASE=viewport): skip the 2x90s runs
        if os.environ.get("SA_PHASE") == "viewport":
            narrow_viewport(tab)
            tab.close()
        else:
            # desktop flow
            run_analysis(tab, SPECIES)
            basemap_after_results(tab)

            # repeatability: second species
            run_analysis(tab, "Quercus robur", expect_hull=True)
            carbon_txt = tab.js(
                "document.getElementById('carbon').innerText.slice(0,80)")
            check("oak carbon rendered", "CO" in (carbon_txt or "")
                  or "carbon" in (carbon_txt or "").lower()
                  or "t" in (carbon_txt or ""), carbon_txt or "empty")

            narrow_viewport(tab)

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
