"""desktop screenshots: home, editor with a light, editor with the timeline. Run: python3 tools/shot.py  ->  PNGs in /tmp/shots/ (view them with the Read tool)."""
import sys,asyncio,os
os.makedirs("/tmp/shots",exist_ok=True)
sys.path.insert(0,os.path.join(os.path.dirname(os.path.abspath(__file__)),"..","tests"))
from harness import *
async def run(br,site,fx):
    t=await open_page(br,site,"shot",w=1440,h=900)
    await t.wait(1500); await t.pg.screenshot(path="/tmp/shots/home.png")
    await t.new_project(); await t.add_ply(fx["tilt"])
    await t.ev("addCamera();leaveThru();addLight('sun');addLight('spot')"); await t.wait(500)
    await t.ev("openTool('light')"); await t.wait(800); await t.pg.screenshot(path="/tmp/shots/editor_light.png")
    await t.pg.click("#tlBtn"); await t.wait(800); await t.pg.screenshot(path="/tmp/shots/editor_tl.png")
    return t.finish()
import harness
sys.exit(asyncio.run(harness.run_all([("shot",run)],None)))
