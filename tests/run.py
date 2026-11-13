"""Run everything:  python3 tests/run.py        Run one:  python3 tests/run.py camera"""
import sys, asyncio, os
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import harness
import test_scan, test_sharp, test_sortworker, test_photo, test_fx, test_spz, test_td, test_render, test_curves, test_autokey, test_dock, test_timeline, test_select, test_folder, test_roundtrip, test_backup, test_beta, test_camera, test_overlap, test_core, test_presets, test_timeline
TESTS=[("core",test_core.run),("folder",test_folder.run),("select",test_select.run),("timeline",test_timeline.run),("dock",test_dock.run),("autokey",test_autokey.run),("curves",test_curves.run),("render",test_render.run),("td",test_td.run),("spz",test_spz.run),("fx",test_fx.run),("photo",test_photo.run),("sortworker",test_sortworker.run),("sharp",test_sharp.run),("scan",test_scan.run),("roundtrip",test_roundtrip.run),("backup",test_backup.run),("beta",test_beta.run),("presets",test_presets.run),("camera",test_camera.run),("overlap",test_overlap.run)]
if __name__=="__main__":
    only=sys.argv[1] if len(sys.argv)>1 else None
    sys.exit(asyncio.run(harness.run_all(TESTS,only)))
