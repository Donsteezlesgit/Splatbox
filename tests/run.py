"""Run everything:  python3 tests/run.py        Run one:  python3 tests/run.py camera"""
import sys, asyncio, os
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import harness
import test_timeline, test_select, test_folder, test_roundtrip, test_backup, test_beta, test_camera, test_overlap, test_core, test_presets, test_timeline
TESTS=[("core",test_core.run),("folder",test_folder.run),("select",test_select.run),("timeline",test_timeline.run),("roundtrip",test_roundtrip.run),("backup",test_backup.run),("beta",test_beta.run),("presets",test_presets.run),("camera",test_camera.run),("overlap",test_overlap.run)]
if __name__=="__main__":
    only=sys.argv[1] if len(sys.argv)>1 else None
    sys.exit(asyncio.run(harness.run_all(TESTS,only)))
