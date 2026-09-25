"""
BioSift UI audit driver (raw CDP over Chrome DevTools protocol).
Walks pages, clicks through the analysis flow, screenshots + DOM audit.

Usage: venv/bin/python scripts/ui_audit.py <phase>
  phase: "pages" | "analysis"
"""
import json
import base64
import time
import sys
import http.client
import urllib.request
import urllib.parse
from websocket import create_connection  # websocket-client

import os
APP = os.environ.get("BIOSIFT_URL", "http://localhost:8622")
SHOTS = "/tmp/biosift_shots"
PORT = 9333


def http_json(method, path):
    conn = http.client.HTTPConnection("127.0.0.1", PORT, timeout=10)
    conn.request(method, path)
    resp = conn.getresponse()
    data = resp.read()
    conn.close()
    return json.loads(data.decode("utf-8"))


def start_chrome():
    import subprocess
    proc = subprocess.Popen(
        ["google-chrome", "--headless=new", "--no-sandbox",
         "--disable-gpu", "--remote-debugging-port=9333",
         "--remote-allow-origins=*",
         "--window-size=1500,1000", "--hide-scrollbars",
         "about:blank"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    for _ in range(40):
        try:
            http_json("GET", "/json/version")
            return proc
        except Exception:
            time.sleep(0.5)
    raise RuntimeError("chrome did not start")


class Tab:
    def __init__(self, url):
        self.ws_url = self._new_tab(url)
        self.ws = create_connection(self.ws_url, timeout=60)
        self.id = 0

    @staticmethod
    def _new_tab(url):
        encoded = urllib.parse.quote(url, safe="")
        data = http_json("PUT", f"/json/new?{encoded}")
        return data["webSocketDebuggerUrl"]

    def send(self, method, **params):
        self.id += 1
        self.ws.send(json.dumps(
            {"id": self.id, "method": method, "params": params}
        ))
        deadline = time.time() + 60
        while time.time() < deadline:
            msg = json.loads(self.ws.recv())
            if msg.get("id") == self.id:
                if "error" in msg:
                    raise RuntimeError(f"{method}: {msg['error']}")
                return msg.get("result", {})
        raise TimeoutError(method)

    def wait_event(self, method, timeout=30):
        self.ws.settimeout(timeout)
        try:
            while True:
                msg = json.loads(self.ws.recv())
                if msg.get("method") == method:
                    return msg
        except Exception:
            return None
        finally:
            self.ws.settimeout(60)

    def js(self, expr):
        res = self.send(
            "Runtime.evaluate",
            expression=expr, returnByValue=True, awaitPromise=True,
        )
        exc = res.get("exceptionDetails")
        if exc:
            raise RuntimeError("JS error: " + json.dumps(exc)[:500])
        return res.get("result", {}).get("value")

    def shot(self, name):
        res = self.send("Page.captureScreenshot", format="png")
        with open(f"{SHOTS}/{name}.png", "wb") as f:
            f.write(base64.b64decode(res["data"]))
        print(f"  [shot] {name}.png")

    def goto(self, url):
        self.send("Page.navigate", url=url)
        time.sleep(3)

    def wait_text(self, text, timeout=40):
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self.js(
                f"document.body.innerText.includes({json.dumps(text)})"
            ):
                return True
            time.sleep(1)
        return False

    def wait_gone(self, text, timeout=30):
        deadline = time.time() + timeout
        while time.time() < deadline:
            if not self.js(
                f"document.body.innerText.includes({json.dumps(text)})"
            ): 
                return True
            time.sleep(1)
        return False

    def click_text(self, text, tag="button"):
        """Real CDP mouse click on the element matching text.
        Falls back to a, button, [role=tab], label, div.
        Self-contained JS — survives Streamlit soft reloads."""
        selectors = [tag, "a", "button", '[role="tab"]', "label", "div"]
        for sel in selectors:
            rect = self.js(f"""
                ((tag, text) => {{
                  const els = [...document.querySelectorAll(tag)];
                  const el = els.find(e => e.innerText.trim() === text)
                          || els.find(e =>
                              e.innerText.trim().includes(text));
                  if (!el) return null;
                  el.scrollIntoView({{block: 'center'}});
                  const r = el.getBoundingClientRect();
                  return JSON.stringify({{x: r.x + r.width / 2,
                                         y: r.y + r.height / 2}});
                }})({json.dumps(sel)}, {json.dumps(text)})
            """)
            if rect:
                pos = json.loads(rect)
                self.send("Input.dispatchMouseEvent",
                          type="mousePressed", x=pos["x"], y=pos["y"],
                          button="left", clickCount=1)
                self.send("Input.dispatchMouseEvent",
                          type="mouseReleased", x=pos["x"], y=pos["y"],
                          button="left", clickCount=1)
                return True
        return False

    def set_text(self, label, value):
        """Set a Streamlit text input by label, self-contained."""
        return self.js(f"""
            ((label, value) => {{
              const lbl = [...document.querySelectorAll('label')].find(
                  l => l.innerText.toLowerCase()
                          .includes(label.toLowerCase()));
              let input = null;
              if (lbl) {{
                const holder =
                    lbl.closest('[data-testid="stWidgetLabel"]')
                    || lbl.parentElement;
                input = (holder.parentElement || document)
                    .querySelector('input, textarea');
              }}
              if (!input) input = document.querySelector(
                  '[data-testid="stTextInputRootElement"] input');
              if (!input) return 'no-input';
              const setter = Object.getOwnPropertyDescriptor(
                  window.HTMLInputElement.prototype, 'value').set;
              input.focus();
              setter.call(input, value);
              input.dispatchEvent(new Event('input', {{bubbles: true}}));
              input.dispatchEvent(new Event('change', {{bubbles: true}}));
              input.dispatchEvent(new KeyboardEvent('keydown',
                  {{key: 'Enter', bubbles: true}}));
              input.blur();
              return 'ok:' + value;
            }})({json.dumps(label)}, {json.dumps(value)})
        """)

    def audit(self):
        return self.js("""
            (() => {
              const inScroller = (el) => {
                let a = el.parentElement;
                while (a && a !== document.body) {
                  const s = getComputedStyle(a);
                  if (/(auto|scroll)/.test(s.overflowX)
                      && a.scrollWidth > a.clientWidth + 4) {
                    return true;
                  }
                  a = a.parentElement;
                }
                return false;
              };
              const issues = [];
              const vw = window.innerWidth;
              document.querySelectorAll('body *').forEach(el => {
                const r = el.getBoundingClientRect();
                const cs = getComputedStyle(el);
                if (r.width > 5 && r.height > 5
                    && r.right > vw + 12
                    && cs.position !== 'fixed'
                    && cs.position !== 'sticky'
                    && !inScroller(el)
                    && !el.closest('[data-testid="stSidebar"]')
                    && !el.closest('iframe')) {
                  issues.push({type: 'h-overflow', tag: el.tagName,
                               snippet: (el.outerHTML || '')
                                    .slice(0, 90),
                               right: Math.round(r.right)});
                }
              });
              const errors = [...document.querySelectorAll(
                  '[data-testid="stException"], .stException')].map(
                  e => e.innerText.slice(0, 300));
              const running = !!document.querySelector(
                  '[data-testid="stStatusWidget"],'
                  + ' [data-testid="stSpinner"]');
              return {
                issues: issues.slice(0, 8),
                exceptions: errors,
                running: running,
                pageScrollsX: (document.documentElement.scrollWidth
                               > window.innerWidth + 8),
              };
            })()
        """)

    def active_tab_text(self, n=900):
        """Visible text of the currently selected st.tabs panel."""
        return self.js(f"""
            (() => {{
              const panels = [...document.querySelectorAll(
                  '[data-baseweb="tab-panel"]')];
              const vis = panels.find(p =>
                  p.getBoundingClientRect().height > 40);
              return (vis || {{innerText: 'NO-PANEL'}})
                  .innerText.slice(0, {int(n)});
            }})()
        """) or ""

    def count_download_buttons(self):
        return self.js(
            "document.querySelectorAll("
            "'[data-testid=\"stDownloadButton\"] button').length"
        ) or 0

    def body_text(self, n=1200):
        return self.js(
            f"document.body.innerText.slice(0, {int(n)})"
        ) or ""

    def close(self):
        try:
            self.ws.close()
        except Exception:
            pass


BOOT = """
window.clickByText = function(tag, text) {
  const els = [...document.querySelectorAll(tag)];
  const el = els.find(e => e.innerText.trim() === text)
          || els.find(e => e.innerText.trim().includes(text));
  if (!el) return false;
  el.scrollIntoView({block: 'center'});
  el.click();
  return true;
};
window.setStreamlitText = function(label, value) {
  let input = null;
  const lbl = [...document.querySelectorAll('label')].find(
      l => l.innerText.toLowerCase().includes(label.toLowerCase()));
  if (lbl) {
    const holder = lbl.closest('[data-testid="stWidgetLabel"]')
                   ? lbl.closest('[data-testid="stWidgetLabel"]')
                        .nextElementSibling
                   : lbl.nextElementSibling;
    input = (holder || document).querySelector('input, textarea');
  }
  if (!input) {
    input = document.querySelector(
        '[data-testid="stTextInput"] input');
  }
  if (!input) return 'no-input';
  const proto = input.tagName === 'TEXTAREA'
      ? window.HTMLTextAreaElement.prototype
      : window.HTMLInputElement.prototype;
  const setter = Object.getOwnPropertyDescriptor(proto, 'value').set;
  input.focus();
  setter.call(input, value);
  input.dispatchEvent(new Event('input', {bubbles: true}));
  input.dispatchEvent(new Event('change', {bubbles: true}));
  input.dispatchEvent(new KeyboardEvent('keydown',
      {key: 'Enter', code: 'Enter', bubbles: true}));
  input.dispatchEvent(new KeyboardEvent('keyup',
      {key: 'Enter', code: 'Enter', bubbles: true}));
  input.blur();
  return 'ok:' + value;
};
window.bodyText = function(n) {
  return document.body.innerText.slice(0, n || 1200);
};
window.rectOf = function(tag, text) {
  const els = [...document.querySelectorAll(tag)];
  const el = els.find(e => e.innerText.trim() === text)
          || els.find(e => e.innerText.trim().includes(text));
  if (!el) return null;
  el.scrollIntoView({block: 'center'});
  const r = el.getBoundingClientRect();
  return JSON.stringify({x: r.x + r.width / 2, y: r.y + r.height / 2,
                         found: true, txt: el.innerText.slice(0, 40)});
};
window.probeInputs = function() {
  const out = [];
  document.querySelectorAll('input, textarea').forEach(el => {
    let tid = '';
    let anc = el;
    while (anc && anc !== document.body) {
      if (anc.getAttribute && anc.getAttribute('data-testid')) {
        tid = anc.getAttribute('data-testid');
        break;
      }
      anc = anc.parentElement;
    }
    out.push({tag: el.tagName, testid: tid,
              ph: el.getAttribute('placeholder') || '',
              type: el.getAttribute('type') || ''});
  });
  return JSON.stringify(out);
};
window.audit = function() {
  const issues = [];
  const vw = window.innerWidth;
  document.querySelectorAll('body *').forEach(el => {
    const r = el.getBoundingClientRect();
    const cs = getComputedStyle(el);
    if (r.width > 5 && r.height > 5) {
      if (r.right > vw + 12 && cs.position !== 'fixed'
          && cs.position !== 'sticky'
          && !el.closest('[data-testid="stSidebar"]')
          && !el.closest('iframe')) {
        issues.push({type: 'h-overflow',
                     tag: el.tagName, cls: (el.className || '')
                     .toString().slice(0, 40),
                     right: Math.round(r.right)});
      }
      if (cs.color && (cs.color === 'rgb(34, 34, 34)'
          || cs.color === 'rgb(17, 17, 17)')) {
        const bg = cs.backgroundColor;
        if (bg === 'rgb(255, 255, 255)'
            || bg === 'rgba(0, 0, 0, 0)') {
          issues.push({type: 'dark-on-dark?',
                       tag: el.tagName,
                       txt: (el.innerText || '').slice(0, 30)});
        }
      }
    }
  });
  const errors = [...document.querySelectorAll(
      '[data-testid="stException"], .stException')].map(
      e => e.innerText.slice(0, 300));
  const spin = !!document.querySelector('[data-testid="stSpinner"],'
      + ' [data-testid="stStatusWidget"]');
  return {issues: issues.slice(0, 12), exceptions: errors,
          running: spin, overflowCount: issues.filter(
              i => i.type === 'h-overflow').length};
};
"""


def main():
    phase = sys.argv[1] if len(sys.argv) > 1 else "pages"
    proc = start_chrome()
    try:
        tab = Tab(APP)
        tab.send("Page.enable")
        tab.send("Runtime.enable")
        time.sleep(4)
        # initial render can take a moment; wait for app chrome
        tab.wait_text("BioSift", timeout=40)

        if phase == "pages":
            audit_pages(tab)
        else:
            audit_analysis(tab)
        tab.close()
    finally:
        proc.terminate()


def audit_pages(tab):
    print("== HOME ==")
    time.sleep(3)
    print(" audit:", json.dumps(tab.audit())[:300])
    tab.shot("01_home")

    for title, shot in [
        ("Species Analysis", "02_analysis_inputs"),
        ("Batch Comparison", "03_batch"),
        ("Publisher Report", "04_publisher"),
        ("Methods & Standards", "05_methods"),
    ]:
        print(f"== NAV: {title} ==")
        ok = tab.click_text(title, "a")
        time.sleep(4)
        url = tab.js("location.pathname")
        print(" clicked:", ok, "| url:", url)
        print(" audit:", json.dumps(tab.audit())[:300])
        tab.shot(shot)


def audit_analysis(tab):
    print("== ANALYSIS FLOW ==")
    ok = tab.click_text("Species Analysis", "a")
    print(" click nav:", ok, "| url:", tab.js("location.pathname"))
    time.sleep(4)

    print(" set:", tab.set_text("Scientific name", "Panthera leo"))
    time.sleep(1.5)
    tab.shot("06_analysis_filled")

    print(" click Run Analysis:", tab.click_text("Run Analysis", "button"))
    tab.shot("07_progress")
    appeared = tab.wait_text("GBIF records matching", timeout=120)
    print(" results appeared:", appeared)
    if not appeared:
        print(" audit:", json.dumps(tab.audit())[:500])
        print(" page:", tab.body_text(1000).replace("\n", " | "))
        tab.shot("07b_stuck")
        return

    time.sleep(6)  # let heavy widgets settle
    audit = tab.audit()
    print(" audit:", json.dumps(audit)[:600])
    tab.shot("08_results_top")

    for i, name in enumerate([
        "Overview", "Occurrence Map", "Temporal", "Charts",
        "Gap Analysis", "Data & Export",
    ], start=9):
        print(f" tab: {name}")
        clicked = tab.click_text(name, "button")
        time.sleep(8 if name in ("Occurrence Map", "Gap Analysis")
                   else 4)
        res = tab.audit()
        print("  clicked:", clicked,
              "| scrollsX:", res.get("pageScrollsX"),
              "| exceptions:", len(res.get("exceptions", [])),
              "| real overflows:", len(res.get("issues", [])))
        if res.get("issues"):
            for iss in res["issues"][:4]:
                print("    ~", iss.get("snippet", "")[:80])
        if res.get("exceptions"):
            print("    !! ", res["exceptions"][0][:200])
        safe = (name.lower().replace(" ", "_").replace("&", "")
                .replace("__", "_"))
        tab.shot(f"{i:02d}_tab_{safe}")

    # export affordances — check the visible panel + actual buttons
    time.sleep(2)
    panel = tab.active_tab_text(600)
    print(" export panel mentions pack/pdf/cube:",
          "pack" in panel.lower(), "pdf" in panel.lower(),
          "cube" in panel.lower())
    print(" download buttons rendered:",
          tab.count_download_buttons())
    tab.shot("15_exports")


if __name__ == "__main__":
    main()
