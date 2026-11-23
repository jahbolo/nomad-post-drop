"""Render every .cv canvas of a Nomad post HTML file to PNGs at exact size.

Usage: python3 render.py <post.html> <out_dir> <name_prefix>
Needs: npm packages @calcom/cal-sans-ui@1.3.0 and html-to-image@1.11.11 in ./node_modules
(next to where you run it), playwright for python, and google-chrome.
jsDelivr may be blocked, so the font and script URLs are rewritten to local copies.
"""
import base64, http.server, os, shutil, sys, threading, tempfile
from playwright.sync_api import sync_playwright

src, out_dir, prefix = sys.argv[1], sys.argv[2], sys.argv[3]
nm = os.path.abspath("node_modules")
work = tempfile.mkdtemp()
shutil.copytree(os.path.join(nm, "@calcom/cal-sans-ui/dist/fonts"), os.path.join(work, "fonts"))
shutil.copy(os.path.join(nm, "html-to-image/dist/html-to-image.js"), work)
html = open(src, encoding="utf-8").read()
html = html.replace("https://cdn.jsdelivr.net/npm/html-to-image@1.11.11/dist/html-to-image.js", "/html-to-image.js")
html = html.replace("https://cdn.jsdelivr.net/npm/@calcom/cal-sans-ui@1.3.0/dist/fonts/", "/fonts/")
open(os.path.join(work, "index.html"), "w", encoding="utf-8").write(html)

class H(http.server.SimpleHTTPRequestHandler):
    def __init__(s, *a, **k): super().__init__(*a, directory=work, **k)
    def log_message(s, *a): pass
srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
threading.Thread(target=srv.serve_forever, daemon=True).start()
os.makedirs(out_dir, exist_ok=True)

with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
    pg = b.new_page(viewport={"width": 1400, "height": 1600})
    pg.goto(f"http://127.0.0.1:{srv.server_port}/index.html")
    pg.wait_for_function("document.querySelector('#fontstatus') && /loaded|did not/.test(document.querySelector('#fontstatus').textContent)", timeout=30000)
    if "did not" in pg.inner_text("#fontstatus"):
        sys.exit("Cal Sans UI failed to load; not exporting.")
    urls = pg.evaluate("""async()=>{const out=[];for(const cv of document.querySelectorAll('.cv')){
      document.body.classList.add('exporting');const w=+cv.dataset.w,h=+cv.dataset.h;
      out.push(await htmlToImage.toPng(cv,{width:w,height:h,canvasWidth:w,canvasHeight:h,pixelRatio:1,fontEmbedCSS:fontCSS,skipAutoScale:true,style:{transform:'none',left:'0',top:'0'}}));}
      return out;}""")
    b.close()
for i, u in enumerate(urls, 1):
    path = os.path.join(out_dir, f"{prefix}-{i:02d}.png")
    open(path, "wb").write(base64.b64decode(u.split(",", 1)[1]))
    print(path, os.path.getsize(path))
