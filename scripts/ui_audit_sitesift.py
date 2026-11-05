"""SiteSift UI audit (raw CDP, reuses the ui_audit harness).

Usage: venv/bin/python scripts/ui_audit_sitesift.py
Env:   SITESIFT_URL (default http://localhost:8090)

Checks:
  1. boot: title, map canvas, basemap switcher, zero page errors
  2. real mouse clicks on the map add vertices; Screen enables at three
  3. screening a drawn polygon fills every results section
  4. the map carries record points and a legend after screening
  5. R and Python exports render and quote the screened polygon
  6. switching basemap keeps the data layers
  7. no horizontal overflow at desktop and phone widths
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ui_audit  # noqa: E402
from ui_audit import Tab, start_chrome  # noqa: E402

ui_audit.SHOTS = "/tmp/sitesift_shots"
os.makedirs(ui_audit.SHOTS, exist_ok=True)
APP = os.environ.get("SITESIFT_URL", "http://localhost:8090")

FAILS = []


def check(label, ok, detail=""):
    print(f"  [{'PASS' if ok else 'FAIL'}] {label}"
          + (f" — {detail}" if detail else ""))
    if not ok:
        FAILS.append(label)


def click_xy(tab, x, y):
    tab.send("Input.dispatchMouseEvent", type="mousePressed", x=x, y=y,
             button="left", clickCount=1)
    tab.send("Input.dispatchMouseEvent", type="mouseReleased", x=x, y=y,
             button="left", clickCount=1)


def main():
    proc = start_chrome()
    try:
        tab = Tab(APP)
        tab.send("Emulation.setDeviceMetricsOverride", width=1440, height=900,
                 deviceScaleFactor=1, mobile=False)
        time.sleep(4.5)
        tab.js("""
          window.__errs = [];
          window.addEventListener('error',
            e => window.__errs.push(String(e.message).slice(0,200)));
          window.addEventListener('unhandledrejection',
            e => window.__errs.push('promise: '
                + String(e.reason && e.reason.message || e.reason)
                      .slice(0,200)));
        """)

        print("\n1. boot")
        check("title", "SiteSift" in tab.js("document.title"))
        check("map canvas present", bool(tab.js(
            "!!document.querySelector('#map canvas')")))
        check("basemap switcher has 3 choices", tab.js(
            "document.querySelectorAll('#basemaps button').length") == 3)
        check("results hidden before any screen", tab.js(
            "document.getElementById('results').style.display") == "none")
        check("Screen disabled at zero vertices", tab.js(
            "document.getElementById('btnScreen').disabled") is True)

        print("\n2. drawing by real clicks")
        # zoom to a city first: at world zoom a three-click triangle spans
        # continents and the server (correctly) rejects it as too coarse
        # void: jumpTo returns the map, which CDP cannot serialise
        tab.js("void map.jumpTo({center:[-0.1,51.5], zoom:12})")
        time.sleep(2.0)
        for x, y in ((700, 300), (950, 340), (820, 560)):
            click_xy(tab, x, y)
            time.sleep(0.4)
        n = tab.js("vertices.length")
        check("three vertices placed by clicking", n == 3, f"got {n}")
        check("Screen enabled after three vertices", tab.js(
            "document.getElementById('btnScreen').disabled") is False)
        check("draft polygon drawn on map", tab.js(
            "map.getSource('site')._data.features.length") >= 1)

        print("\n3. screening")
        tab.js("document.getElementById('label').value = 'Audit site'")
        tab.click_text("Screen site")
        ok = False
        for _ in range(120):
            if tab.js("document.querySelectorAll('#tiles .tile').length") == 4:
                ok = True
                break
            time.sleep(0.5)
        check("results rendered", ok)
        recs = tab.js("bundle && bundle.summary.records")
        check("records found in a London polygon", bool(recs) and recs > 0,
              f"{recs:,} records" if recs else "none")
        area = tab.js("bundle && bundle.site.area_km2")
        check("site area is site-sized, not continental",
              bool(area) and 0 < area < 5000, f"{area} km²")

        for sec, label in (("tiles", "summary tiles"), ("threat", "species of concern"),
                           ("iucn", "IUCN bars"), ("establish", "native/introduced"),
                           ("species", "species table"), ("temporal", "effort over time"),
                           ("months", "seasonality"), ("issues", "record quality"),
                           ("datasets", "dataset attribution"),
                           ("caveats", "caveats")):
            txt = tab.js(f"(document.getElementById('{sec}')||{{}}).innerText || ''")
            check(f"{label} has content", bool(txt and len(txt.strip()) > 20),
                  (txt or "")[:60].replace("\n", " "))

        print("\n4. map after screening")
        pts = tab.js(
            "(() => {const s=map.getSource('records');"
            "return s && s._data ? s._data.features.length : 0})()")
        check("record points on map", pts > 0, f"{pts} points")
        check("legend shown", tab.js(
            "document.getElementById('legend').classList.contains('on')"))
        check("site polygon still on map", tab.js(
            "map.getSource('site')._data.features.length") >= 1)

        print("\n5. exports")
        tab.click_text("R script")
        time.sleep(0.6)
        r = tab.js("document.getElementById('scriptcode').textContent")
        check("R script rendered", "occ_search" in r and "geometry" in r)
        check("R script quotes the screened WKT", "POLYGON((" in r)
        tab.click_text("Python script")
        time.sleep(0.6)
        p = tab.js("document.getElementById('scriptcode').textContent")
        check("Python script rendered", "requests.get" in p)
        check("Python script warns about IUCN comma list",
              "no comma list" in p)
        check("JSON export wired", tab.js(
            "typeof document.getElementById('btnJson').onclick") == "function")

        print("\n6. basemap switch keeps data")
        tab.click_text("Satellite")
        time.sleep(3.5)
        check("records source survives restyle", bool(tab.js(
            "!!map.getSource('records')")))
        check("site source survives restyle", bool(tab.js(
            "!!map.getSource('site')")))

        print("\n7. viewports")
        for w, h in ((1440, 900), (390, 844)):
            tab.send("Emulation.setDeviceMetricsOverride", width=w, height=h,
                     deviceScaleFactor=1, mobile=(w < 500))
            time.sleep(1.2)
            over = tab.js(
                "document.documentElement.scrollWidth - "
                "document.documentElement.clientWidth")
            check(f"no horizontal overflow at {w}x{h}", over <= 1, f"{over}px")

        errs = tab.js("window.__errs || []")
        check("zero page errors", not errs, str(errs)[:220])
    finally:
        proc.terminate()

    print("\n" + ("RESULT: ALL CHECKS PASSED" if not FAILS
                  else f"RESULT: {len(FAILS)} FAILED — {FAILS}"))
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
