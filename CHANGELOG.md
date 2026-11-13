# Splatbox changelog
Newest first. Stable = the main link. Each version is also a git tag (v018 etc.) you can roll back to.

## Version 038
- Play now starts from the playhead instead of always from the start. If the playhead is at the end (or outside the preview range) it starts over.

## Version 037
- Timeline layout: two tidy rows. Top row has transport (start, previous key, Play, next key, end, Once/Loop/Bounce), the time, Length, and the range and marker buttons. Second row has keying, easing, copy/paste and the view buttons.
- Stretch keys: select two or more keys and drag the handles at either end of the orange band in the ruler. The keys squeeze or stretch to fit instead of moving.
- Change the Length (seconds or frames, or the Length slider in the Camera menu) and every key, marker and range is scaled to fit. Untick "Stretch keys" to leave them alone. Undo restores both.
- Keys: J/K or Up/Down jump between keys, Home/End go to the start and end, F fits, Shift+F frames the selected keys, Tab swaps Dope sheet and Curves, 1 to 6 set the easing, Ctrl+C / Ctrl+V / Ctrl+D copy, paste and duplicate keys.
- Preview range: I and O set it, Play then loops just that part. Loop button cycles Once, Loop and Bounce.
- Markers: M adds or removes one at the playhead, , and . jump between them. Snap (on by default) pulls the playhead and dragged keys to markers, the range and the playhead.
- Row buttons: M mutes a row, L locks it. Muted rows stop driving their setting; locked rows can't be edited.

## Version 036
- SHARP is removed. Apple's licence only allows personal, non-commercial use, so it doesn't belong in an app used for client work. The "One photo to 3D" card (photo plus optional depth map) stays.
- The Windows app no longer carries the AI runtime, so the installer is smaller. If you already downloaded the 1.3 GB SHARP model, it's in the app's data folder (%APPDATA%\Splatbox\sharp) and you can delete it.

## Version 035
- Photo scans: two new quality levels, Draft (quick check, a few minutes) and Ultra (slowest, best detail).
- Blurry photos are spotted before solving and left out, as long as enough sharp ones remain. The training screen says which ones.
- Stray floating splats are masked automatically after a scan (switch on the training screen). Undo brings them back.
- "Solved X of Y photos" now names the photos that couldn't be placed.
- Uses up to 12 CPU cores for the photo-matching step.

## Version 034
- The app now says which one you're in: "Splatbox Desktop" in the Windows app, "Splatbox Web" in the browser, next to the version number and in the window title.

## Version 033
- SHARP (desktop app only): turn one photo into a real 3D scene with Apple's SHARP model. Add it from the Add panel. The 1.3 GB model downloads once, the first time you use it, and then everything runs on your PC. No photo ever leaves it.
- It uses your graphics card when it can (DirectML), otherwise the CPU, which is slower and wants about 8 GB of free memory.
- Personal, non-commercial use only, because that is what Apple's licence for the model allows.
- The web version doesn't have this; its one-photo option still works from a photo and an optional depth map.

## Version 032
- TouchDesigner export (Capture panel): camera path (json, csv, chan), 16-bit depth PNG per frame, optional colour frames and a point cloud .ply, all in one zip with a README.
- SPZ: import .spz files (versions 2 and 3, also by drag and drop) and export the whole scene as .spz, about 10 times smaller than .ply.
- Splat effects: Dissolve, Scatter and Pulse (Depth panel). All can be keyframed on the timeline. They show in Render mode, video and images.
- Presets now travel inside "Back up everything", and can be exported and imported on their own.
- After solving cameras for a photo scan, the app says "Solved X of Y photos".
- One photo to 3D: add a photo (and a depth map if you have one, white = near) to get a 3D splat card.
- Big scenes sort in a background thread, so orbiting stays smooth. Renders are unchanged.

## Version 031
- Desktop app: render straight to ProRes 4444 (with transparency), ProRes 422 HQ, DNxHR HQX or MP4 (H.264). Pick it under Output in the Capture panel; PNG zip is still there.
- ffmpeg is bundled inside the app, so there is nothing to install. It encodes frame by frame as the render runs, and asks where to save first.
- Only ProRes 4444 keeps a transparent background; the others say so instead of rendering a wrong result.
- Web version unchanged (PNG zip only).

## Version 030
- Windows desktop app (Electron). Same app, installed per-user, runs offline.
- Updates itself in place from GitHub Releases: checks on launch and every 4 hours, then offers "Restart now". One install, no pile of exes.
- GitHub builds the installer automatically when a new version is pushed.
- Web version unchanged.

## Version 029
- New: frame-exact render. Capture tool > Render PNG sequence steps the animation one frame at a time (timeline keys, or the move preset) and gives you numbered PNGs in a zip, the same on any computer. Pick the frame rate (24, 25, 30, 60). A progress card with Cancel (or Esc) shows while it runs.
- New: render size. This view, 720p, 1080p, 1440p, 4K, Square or Vertical, for sequences and for Save image.
- New: transparent background. Tick it for PNGs with a real alpha channel (stills and sequences). It skips lens and look effects (vignette, grain, distortion, LUT).
- Every render re-sorts the splats for each frame, so frames never show stale ordering.

## Version 028
- New: Curves tab in the timeline dock. It plots the selected row's values over time. Select a key to get Bezier handles for the segments on either side, and drag them to shape the easing. Ease in, Ease out and In-out presets; Smooth, Linear and Step still work. Dragging a key up or down in Curves changes its value (single-value rows).
- Drag in empty space in the timeline to box-select keys (Shift adds). Clicking empty space no longer moves the playhead; only the ruler along the top does.
- Double-click a row name to open that property's menu (and select its object).
- Curve shapes are saved with the project.

## Version 027
- Keyframe diamonds next to everything you can animate (colour, depth and lens sliders; position, rotation and scale; camera lens and focus distance; light intensity; crop box; the eye toggle in object lists). Grey = not animated, orange outline = animated, filled = a key at the playhead. Click to key, click a filled one to remove.
- Auto-key: change something that already has keys, at a new time, and a key is written there. Works for sliders, number boxes, the gizmo and flying an animated camera. A drag is one Ctrl+Z step.
- Timeline: click a row in the list to select it, then Key it keys that row at the playhead (the track picker still works for adding new ones).
- Deleting a key now lets the value follow the timeline instead of snapping back.
- Diamonds are hidden on phones (view and play only).

## Version 026
- New: timeline dock. Tap the timeline button (top bar, desktop only) for a dope sheet along the bottom of the view. Closed by default.
- One row per animated property, a diamond per key. Click the ruler or drag to scrub, drag diamonds to retime them, Shift-click to pick several, Delete removes keys.
- Double-click a row to add a key. "Add a track" lists everything that can be keyed. Smooth, Linear and Step set how a key blends into the next.
- Ctrl+wheel zooms time, Shift+wheel pans, Fit shows the whole length. Length of the animation can be set in the dock. Left/Right arrows step one frame, Space plays.
- Everything is undoable. Phones stay view and play only.

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
