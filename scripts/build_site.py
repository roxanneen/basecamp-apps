#!/usr/bin/env python3
"""Write the catalogue's web page into docs/ from the listing.

    build_site.py <index.json> <icons dir>

Reads the generated index.json (what Basecamp reads), site.json (titles and
short descriptions written by hand) and logos-repo.json, and writes
docs/index.html plus docs/icons/. The page is static: no scripts are needed
to read it, nothing is loaded from another site, and nothing tracks a reader.
"""
import html
import json
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
index_path, icons_src = sys.argv[1], sys.argv[2]
index = json.load(open(index_path))
site = json.load(open(os.path.join(ROOT, "site.json")))
repo = json.load(open(os.path.join(ROOT, "logos-repo.json")))
REPO_URL = "https://raw.githubusercontent.com/roxanneen/basecamp-apps/main/logos-repo.json"
HOME = repo["homepage"]
DID = repo["trustedSigners"][0]["did"]
SIGNER = repo["trustedSigners"][0].get("name", "")
PLATFORMS = {"darwin-arm64": "macOS, Apple chip", "linux-amd64": "Linux x86_64", "linux-arm64": "Linux ARM64"}
e = html.escape

docs = os.path.join(ROOT, "docs")
icons_out = os.path.join(docs, "icons")
shutil.rmtree(icons_out, ignore_errors=True)
os.makedirs(icons_out)


def dep_name(d):
    return d["name"] if isinstance(d, dict) else d


def size_mb(n):
    return f"{n / 1_000_000:.1f} MB"


cards = []
order = list(site["apps"].keys())
packages = sorted(index["packages"], key=lambda p: order.index(p["name"]) if p["name"] in order else len(order))
for p in packages:
    v = p["versions"][-1]
    m = v["manifest"]
    info = site["apps"].get(p["name"], {})
    title = info.get("title") or m.get("display_name") or p["name"]
    blurb = info.get("blurb") or m.get("description", "")
    icon_html = '<div class="icon placeholder" aria-hidden="true"></div>'
    if v.get("icon"):
        shutil.copy(os.path.join(icons_src, v["icon"]["path"]), os.path.join(icons_out, v["icon"]["path"]))
        icon_html = f'<img class="icon" src="icons/{e(v["icon"]["path"])}" alt="" width="56" height="56">'
    runs = [PLATFORMS[k.split("/", 1)[1]] for k in sorted(m.get("hashes", {})) if k.startswith("variants/") and k.split("/", 1)[1] in PLATFORMS]
    needs = [dep_name(d) for d in (m.get("dependencies") or [])]
    optional = [dep_name(d) for d in (m.get("optional_dependencies") or [])]
    signed = v.get("signature", {}).get("did") == DID
    links = []
    if info.get("guide"):
        links.append(f'<a href="{e(info["guide"])}">Step-by-step guide</a>')
    if info.get("source"):
        links.append(f'<a href="{e(info["source"])}">Source</a>')
    links.append(f'<a href="{e(v["url"])}">Package file</a>')
    needs_html = ""
    if needs:
        needs_html += '<p class="meta"><span class="label">Needs</span> ' + " ".join(f"<code>{e(n)}</code>" for n in needs) + " <span class=\"hint\">from the official Logos catalogue; Basecamp fetches it for you</span></p>"
    else:
        needs_html += '<p class="meta"><span class="label">Needs</span> nothing else</p>'
    if optional:
        needs_html += '<p class="meta"><span class="label">Optional</span> ' + " ".join(f"<code>{e(n)}</code>" for n in optional) + "</p>"
    cards.append(f"""
      <article class="card" id="{e(p['name'])}">
        <header>
          {icon_html}
          <div>
            <h3>{e(title)}</h3>
            <p class="tags"><span class="tag">{e(m.get('category', 'app'))}</span>{'<span class="tag signed">signed by ' + e(SIGNER) + '</span>' if signed else '<span class="tag unsigned">not signed</span>'}</p>
          </div>
        </header>
        <p class="blurb">{e(blurb)}</p>
        {needs_html}
        <p class="meta"><span class="label">Runs on</span> {e(', '.join(runs))}</p>
        <footer>
          <span class="version"><code>{e(p['name'])}</code> · v{e(m['version'])} · {size_mb(v['size'])}</span>
          <span class="links">{' '.join(links)}</span>
        </footer>
      </article>""")

page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(site['title'])}</title>
<meta name="description" content="{e(site['tagline'])}">
<meta name="referrer" content="no-referrer">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='7' fill='%2315171b'/%3E%3Cpath d='M6 22h20v2H6zM10 21c0-7 2-11 6-11s6 4 6 11z' fill='%23e0a04a'/%3E%3C/svg%3E">
<style>
  :root {{
    --bg: #111317; --surface: #1a1d23; --surface-2: #20242b; --line: #2c313a;
    --text: #ece8dc; --muted: #a39f94; --faint: #7c796f;
    --accent: #e0a04a; --accent-ink: #1a1408; --ok: #7fc48b; --warn: #e0a04a;
    --mono: ui-monospace, "SF Mono", "JetBrains Mono", Menlo, Consolas, monospace;
    --sans: system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  }}
  @media (prefers-color-scheme: light) {{
    :root {{
      --bg: #f6f3ec; --surface: #ffffff; --surface-2: #f1ede3; --line: #ddd7c9;
      --text: #1d1c19; --muted: #5d5a52; --faint: #86827a;
      --accent: #a8661a; --accent-ink: #ffffff; --ok: #2f7d3f; --warn: #a8661a;
    }}
  }}
  * {{ box-sizing: border-box; }}
  html {{ -webkit-text-size-adjust: 100%; }}
  body {{ margin: 0; background: var(--bg); color: var(--text); font: 16px/1.55 var(--sans); }}
  a {{ color: var(--accent); text-decoration: none; }}
  a:hover, a:focus-visible {{ text-decoration: underline; }}
  code, .mono {{ font-family: var(--mono); font-size: 0.875em; }}
  main {{ max-width: 1040px; margin: 0 auto; padding: 40px 20px 64px; }}
  .masthead {{ display: flex; gap: 16px; align-items: center; margin-bottom: 10px; }}
  .mark {{ flex: none; width: 52px; height: 52px; border-radius: 12px; background: var(--surface); border: 1px solid var(--line); display: grid; place-items: center; }}
  .mark svg {{ width: 30px; height: 30px; }}
  h1 {{ font-size: clamp(1.6rem, 4vw, 2.1rem); line-height: 1.15; margin: 0; letter-spacing: -0.01em; }}
  .tagline {{ color: var(--muted); font-size: 1.05rem; max-width: 62ch; margin: 8px 0 0; }}
  .notice {{ margin: 22px 0 0; padding: 12px 16px; border: 1px solid var(--line); border-left: 3px solid var(--warn); border-radius: 8px; background: var(--surface); color: var(--muted); font-size: 0.95rem; }}
  .notice strong {{ color: var(--text); }}
  h2 {{ font-size: 1.15rem; margin: 40px 0 12px; letter-spacing: 0.01em; }}
  .add {{ background: var(--surface); border: 1px solid var(--line); border-radius: 12px; padding: 20px; }}
  .address {{ display: flex; gap: 10px; align-items: stretch; flex-wrap: wrap; }}
  .address code {{ flex: 1 1 320px; min-width: 0; padding: 12px 14px; background: var(--bg); border: 1px solid var(--line); border-radius: 8px; overflow-wrap: anywhere; user-select: all; font-size: 0.9rem; }}
  button.copy {{ flex: none; font: 600 0.95rem var(--sans); padding: 0 18px; min-height: 44px; border-radius: 8px; border: 1px solid var(--accent); background: var(--accent); color: var(--accent-ink); cursor: pointer; }}
  button.copy.ghost {{ background: transparent; color: var(--accent); }}
  button.copy:focus-visible, a:focus-visible {{ outline: 2px solid var(--accent); outline-offset: 2px; }}
  ol.steps {{ margin: 16px 0 0; padding-left: 1.3em; color: var(--muted); }}
  ol.steps li {{ margin: 6px 0; }}
  ol.steps strong {{ color: var(--text); }}
  .platforms {{ margin: 14px 0 0; color: var(--muted); font-size: 0.95rem; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(min(100%, 440px), 1fr)); gap: 16px; }}
  .card {{ background: var(--surface); border: 1px solid var(--line); border-radius: 12px; padding: 18px; display: flex; flex-direction: column; }}
  .card header {{ display: flex; gap: 14px; align-items: center; }}
  .icon {{ width: 56px; height: 56px; border-radius: 12px; flex: none; background: var(--surface-2); object-fit: cover; }}
  .card h3 {{ margin: 0; font-size: 1.15rem; }}
  .tags {{ margin: 4px 0 0; display: flex; gap: 6px; flex-wrap: wrap; }}
  .tag {{ font-size: 0.75rem; padding: 2px 8px; border-radius: 999px; border: 1px solid var(--line); color: var(--muted); text-transform: capitalize; }}
  .tag.signed {{ color: var(--ok); border-color: color-mix(in srgb, var(--ok) 45%, var(--line)); text-transform: none; }}
  .tag.unsigned {{ color: var(--warn); text-transform: none; }}
  .blurb {{ margin: 14px 0 10px; }}
  .meta {{ margin: 4px 0; color: var(--muted); font-size: 0.9rem; }}
  .label {{ display: inline-block; min-width: 4.6em; color: var(--faint); }}
  .hint {{ color: var(--faint); }}
  .card footer {{ margin-top: auto; padding-top: 14px; display: flex; justify-content: space-between; gap: 10px 16px; flex-wrap: wrap; font-size: 0.9rem; color: var(--muted); border-top: 1px solid var(--line); }}
  .card footer {{ margin-top: 14px; }}
  .links {{ display: flex; gap: 14px; flex-wrap: wrap; }}
  .trust {{ color: var(--muted); }}
  .trust li {{ margin: 6px 0; }}
  .trust strong {{ color: var(--text); }}
  .key {{ display: block; margin-top: 8px; padding: 10px 12px; background: var(--surface); border: 1px solid var(--line); border-radius: 8px; overflow-wrap: anywhere; user-select: all; }}
  .foot {{ margin-top: 48px; padding-top: 18px; border-top: 1px solid var(--line); color: var(--faint); font-size: 0.9rem; }}
  .sr {{ position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); }}
</style>
</head>
<body>
<main>
  <div class="masthead">
    <div class="mark" aria-hidden="true">
      <svg viewBox="0 0 32 32"><path d="M4 23h24v2.4H4zM9.5 22c0-8.5 2.4-13 6.5-13s6.5 4.500 6.5 13z" fill="var(--accent)"/></svg>
    </div>
    <h1>{e(site['title'])}</h1>
  </div>
  <p class="tagline">{e(site['tagline'])}</p>

  <p class="notice"><strong>Not official.</strong> These are personal, experimental hobby projects. They are not Logos products, they have not been audited, and they come with no warranty. They are not affiliated with or endorsed by Logos or Basecamp.</p>

  <h2 id="add">Add the catalogue to Basecamp</h2>
  <section class="add" aria-labelledby="add">
    <div class="address">
      <code id="repo-url">{e(REPO_URL)}</code>
      <button class="copy" type="button" data-copy="repo-url">Copy address</button>
    </div>
    <ol class="steps">
      <li>In Basecamp, open <strong>Package Manager</strong>, then <strong>Manage Repositories</strong>.</li>
      <li>Paste the address into <strong>Add a repository</strong> and add it.</li>
      <li>Go back to Package Manager. The apps below appear in the list. Pick one and install it.</li>
    </ol>
    <p class="platforms">Works with Basecamp 0.3.2 or newer on macOS with an Apple chip and on 64-bit Linux desktops. Not on Windows, Intel Macs, phones or tablets. New to Basecamp? <a href="https://github.com/roxanneen/Manifesto-app/blob/main/docs/INSTALL.md">Follow the step-by-step guide</a>, or <a href="https://github.com/logos-co/logos-basecamp/releases/latest">download Basecamp</a>.</p>
  </section>

  <h2 id="apps">The apps</h2>
  <section class="grid" aria-labelledby="apps">{''.join(cards)}
  </section>

  <h2 id="trust">What adding it means</h2>
  <ul class="trust">
    <li><strong>You are trusting the publisher.</strong> Every Basecamp app runs inside your Basecamp session with no sandbox. Adding a catalogue means trusting whoever signs its packages.</li>
    <li><strong>The packages are signed.</strong> Each one carries a signature made with the publisher key below. Basecamp checks it, and the file's hash, before installing.</li>
    <li><strong>The signature says who published the file.</strong> It does not say the app is safe or reviewed. Each app's code is in its own repository, linked on its card.</li>
    <li><strong>This catalogue lists only these apps.</strong> It never lists a package from the official Logos catalogue.</li>
  </ul>
  <p class="trust">Publisher key of <strong>{e(SIGNER)}</strong>:
    <code class="key" id="did">{e(DID)}</code>
  </p>
  <p><button class="copy ghost" type="button" data-copy="did">Copy key</button></p>

  <p class="foot">Catalogue source and scripts: <a href="{e(HOME)}">{e(HOME.replace('https://', ''))}</a>. This page loads nothing from other sites and does not track you.</p>
</main>
<script>
  // Copy buttons. The page reads fully without this script.
  document.querySelectorAll('button[data-copy]').forEach(function (b) {{
    var label = b.textContent;
    var flash = function (text) {{ b.textContent = text; setTimeout(function () {{ b.textContent = label; }}, 2200); }};
    var select = function (el) {{
      var r = document.createRange(); r.selectNodeContents(el);
      var s = getSelection(); s.removeAllRanges(); s.addRange(r);
    }};
    b.addEventListener('click', function () {{
      var el = document.getElementById(b.dataset.copy);
      var text = el.textContent.trim();
      // If the browser refuses to copy, leave the text selected so one
      // keypress copies it.
      var fallback = function () {{
        select(el);
        var ok = false;
        try {{ ok = document.execCommand('copy'); }} catch (err) {{}}
        flash(ok ? 'Copied' : 'Selected. Press Ctrl+C or Cmd+C');
      }};
      if (navigator.clipboard && navigator.clipboard.writeText)
        navigator.clipboard.writeText(text).then(function () {{ flash('Copied'); }}, fallback);
      else fallback();
    }});
  }});
</script>
</body>
</html>
"""
os.makedirs(docs, exist_ok=True)
open(os.path.join(docs, "index.html"), "w", encoding="utf-8").write(page)
open(os.path.join(docs, ".nojekyll"), "w").write("")
print(f"wrote docs/index.html ({len(packages)} apps)")
