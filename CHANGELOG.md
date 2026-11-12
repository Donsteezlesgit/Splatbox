# Splatbox changelog
Newest first. Stable = the main link. Each version is also a git tag (v018 etc.) you can roll back to.

## Version 019 (BETA first)
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
