# Splatbox changelog
Newest first. Stable = the main link. Each version is also a git tag (v018 etc.) you can roll back to.

## Version 025
- New: timeline engine. Camera position, rotation, lens and focus distance, object transforms and visibility, light intensity, crop boxes and the colour/lens/depth settings can all hold keyframes.
- Keys are saved in the project (format 5; older projects upgrade by themselves) and can be undone with Ctrl+Z.
- Camera tool: a time slider, "Key camera here", and "Turn the move into keys", which converts Orbit, Push in and the other moves into editable camera keys.
- Play follows the keys when a project has any, and uses the old move presets when it has none.
- The full timeline panel (dope sheet, then curves) comes next.

## Version 024
- Fixed: Backspace/Delete in the Select tool no longer removes the whole splat object; it only deletes the selected splats.
- Removing an object (Delete with no tool open) can now be undone with Ctrl+Z.

## Version 023
- New Select tool (left rail, between Crop and Orient). Select splats with Brush, Box, Lasso or Sphere. Shift adds, Alt removes, right-drag still moves the view.
- Delete selected, Keep only selected, Invert, Select all, Clear, and Bring deleted back. Deleting never changes your splat file: it is a mask that is saved with the project and left out of exports.
- Undo and redo (Ctrl+Z, Ctrl+Shift+Z or Ctrl+Y, and buttons in the Select panel) for every selection and delete.
- Clean floaters: "Find floaters" selects stray splats floating away from the main body; check them, then Delete.
- Project format 4 (older projects open as before).

## Version 022
- Renaming a project now renames its folder too (the new folder is written, then the old one removed). It waits until you stop typing in the name box.

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
