"""Visual suite: screenshots compared with saved images, plus layout checks.
Baselines: tests/baselines/*.png. They depend on this sandbox's fonts and software GPU, so they are only valid here.
Look changed on purpose?  python3 tests/run.py visual --update   (then LOOK at the new PNGs and commit them).
On a mismatch the new image and a diff image are written to /tmp/visual_fail/."""
import os, sys, io
from PIL import Image, ImageChops
HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.join(HERE, "baselines")
FAIL = "/tmp/visual_fail"
UPDATE = "--update" in sys.argv
PIX_THR = 40        # per-pixel colour distance (sum of r,g,b) that counts as "changed"
MAX_CHANGED = 0.0002 # allowed share of changed pixels (0.02%; renders here are identical run to run)
from harness import open_page

def compare(t, name, png):
    """Check one screenshot against its baseline."""
    os.makedirs(BASE, exist_ok=True)
    path = os.path.join(BASE, name + ".png")
    if UPDATE or not os.path.exists(path):
        open(path, "wb").write(png)
        t.ok("baseline saved: " + name, True, "(new)" if not UPDATE else "(updated)")
        return
    a = Image.open(path).convert("RGB"); b = Image.open(io.BytesIO(png)).convert("RGB")
    if a.size != b.size:
        t.ok("look: " + name, False, "size %s vs baseline %s" % (b.size, a.size)); return
    d = ImageChops.difference(a, b).convert("RGB")
    px = d.load(); w, h = d.size; n = 0
    for y in range(h):
        for x in range(w):
            r, g, bl = px[x, y]
            if r + g + bl > PIX_THR: n += 1
    share = n / float(w * h)
    good = share <= MAX_CHANGED
    if not good:
        os.makedirs(FAIL, exist_ok=True)
        b.save(os.path.join(FAIL, name + "_new.png"))
        ImageChops.difference(a, b).point(lambda v: min(255, v * 6)).save(os.path.join(FAIL, name + "_diff.png"))
    t.ok("look: %s (%.3f%% changed, limit %.2f%%)" % (name, share * 100, MAX_CHANGED * 100), good,
         "" if good else "see " + FAIL + "/" + name + "_diff.png")

async def no_overflow(t, label):
    r = await t.ev("({sw:document.documentElement.scrollWidth,iw:window.innerWidth,bw:document.body.scrollWidth})")
    t.ok("no sideways scroll: " + label, r["sw"] <= r["iw"] and r["bw"] <= r["iw"], r)

async def inside(t, sel, label):
    r = await t.ev("(function(){var e=document.querySelector(%r);if(!e)return null;var b=e.getBoundingClientRect();return {l:b.left,t:b.top,r:b.right,b:b.bottom,w:innerWidth,h:innerHeight}})()" % sel)
    t.ok("on screen: " + label, bool(r) and r["l"] >= 0 and r["t"] >= 0 and r["r"] <= r["w"] and r["b"] <= r["h"] and (r["r"] - r["l"]) > 0, r)

async def desktop(br, site, fx):
    t = await open_page(br, site, "visual-desktop", w=1440, h=900)
    await t.wait(1500); compare(t, "home", await t.pg.screenshot(mask=[t.pg.locator("#ver")]))  # the version label changes every release
    await no_overflow(t, "home")
    await t.new_project(); await t.add_ply(fx["tilt"])
    await t.ev("addCamera();leaveThru();addLight('sun');addLight('spot')"); await t.wait(500)
    await t.ev("openTool('lightobj')"); await t.wait(800)
    await t.ev("setStatus('')"); compare(t, "editor_light", await t.pg.screenshot())
    await no_overflow(t, "editor")
    await inside(t, "#tlBtn", "timeline button")
    await t.pg.click("#tlBtn"); await t.wait(800)
    await t.ev("setStatus('')"); compare(t, "editor_timeline", await t.pg.screenshot())
    # the timeline toolbar must stay as two compact rows, nothing wrapped
    rows = await t.ev("(function(){var o=[];[].forEach.call(document.querySelectorAll('#tld .tlh'),function(h){var tops=[].filter.call(h.children,function(c){return getComputedStyle(c).position!=='absolute'}).map(function(c){var b=c.getBoundingClientRect();return Math.round(b.top+b.height/2)});var mn=Math.min.apply(null,tops),mx=Math.max.apply(null,tops);o.push({h:Math.round(h.getBoundingClientRect().height),spread:mx-mn})});return o})()")
    t.ok("timeline toolbar: two rows", len(rows) == 2, rows)
    t.ok("timeline toolbar: rows not wrapped (<=48px tall, items level)", all(r["h"] <= 48 and r["spread"] <= 6 for r in rows), rows)
    await inside(t, '#tld [data-tla="close"]', "timeline close button")
    await no_overflow(t, "editor + timeline")
    return t.finish()

async def phone(br, site, fx):
    t = await open_page(br, site, "visual-phone", w=390, h=844)
    await t.new_project(); await t.add_ply(fx["tilt"])
    await t.ev("addLight('point')"); await t.ev("openTool('lightobj')"); await t.wait(900)
    await t.ev("setStatus('')"); compare(t, "phone_light", await t.pg.screenshot())
    await no_overflow(t, "phone light sheet")
    return t.finish()

async def run(br, site, fx):
    return (await desktop(br, site, fx)) + (await phone(br, site, fx))
