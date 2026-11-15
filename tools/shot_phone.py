"""phone screenshot: light sheet. Run: python3 tools/shot_phone.py  ->  PNGs in /tmp/shots/ (view them with the Read tool)."""
import sys,asyncio,os
os.makedirs("/tmp/shots",exist_ok=True)
sys.path.insert(0,os.path.join(os.path.dirname(os.path.abspath(__file__)),"..","tests"))
from harness import *
import harness
async def run(br,site,fx):
    t=await open_page(br,site,"shot2",w=390,h=844)
    await t.new_project(); await t.add_ply(fx["tilt"])
    await t.ev("addLight('point')"); await t.ev("openTool('light')"); await t.wait(900)
    await t.pg.screenshot(path="/tmp/shots/mobile.png")
    return t.finish()
sys.exit(asyncio.run(harness.run_all([("shot2",run)],None)))
