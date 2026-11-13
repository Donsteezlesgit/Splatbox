# V032 build notes (one big update, built in stages, released once at the end)
Rule: stages are committed to app/ only (no release.sh), so nothing ships until the final step. Root index.html stays at Version 031 until then.
Targeted tests per stage; ONE full run at the end.

- [x] 1 TouchDesigner export (depth pass, camera path, clean PLY)
- [x] 2 SPZ export and import
- [x] 3 Splat effects (dissolve, scatter, pulse), keyframable
- [x] 4 Presets in backups + preset export/import; "Solved X of Y photos" report
- [x] 5 Single-photo splats (depth-based; SHARP later, local helper)
- [x] 6 Sort in a Worker (big scenes)
- [ ] F full suite, bump to Version 032, changelog, release.sh stable, push, confirm Windows build, update Plan Doc + Whiteboard
