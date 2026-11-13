# Splatbox changelog
Newest first. Stable = the main link. Each version is also a git tag (v018 etc.) you can roll back to.

## Version 021
- Project folders (PC/Mac Chrome or Edge): on the home screen choose a project folder, e.g. inside Dropbox. Each project becomes a sub-folder with project.json, its splat/model files and a thumbnail. Saving overwrites it; opening reads from it.
- The browser keeps a mirror copy, but the folder always wins when it is available. If the folder can't be reached, work keeps saving to the browser and the home screen offers Reconnect.
- "Move N browser projects into folder" copies existing projects over; nothing is deleted from the browser.
- A small lock note warns if another computer had the project open in the last 10 minutes.
- Unreadable or half-synced projects show their own card instead of breaking the list.
- Phone/Safari/Firefox behave as before (browser storage only).

## Version 020 (BETA)
- Presets: File menu > Presets. Save all settings, looks and your imported LUT under a name, apply them in any project. Kept on this device (not in backup files yet).

## Version 019
- Backup: export one project or all projects to a `.splatbox` file; import adds copies (never overwrites).
- Every project now carries a format number. Old projects are upgraded when opened; projects from a newer app are refused, not damaged.
- Beta link with its own separate storage, so testing can't touch real projects.
- Tests now live in the repo (`python3 tests/run.py`), including a save round-trip guard.

## Version 018
- Save project button (top bar, File menu, Ctrl+S). Projects reopen exactly as left: view, mode, cameras, effects.

## Version 017
- Fixed inverted left-drag look in free fly.

## Version 016
- Free-fly viewport by default. Placeable cameras (look through, leave, place at view). Depth effects anchored to the camera focus point. Better sorting where splat objects overlap.

## Version 015
- Empty-space projects, Edit/Render modes, regrouped menus, lens fix.

## Version 014
- Multi-object scenes (extra splats, 3D models, sun/point lights), outliner, gizmo, 3D box crop, relighting, scene export.

## Version 013
- Auto-level scans, lens effects, looks + .cube LUT import, XYZ grids, DoF sharp zone, hide GUI.

## Versions 001-012
- See git log (`git log --oneline`). Early PWA, AI depth, true Gaussian splat rendering, desktop controls.
