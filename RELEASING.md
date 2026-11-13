# How Splatbox is released

**Source of truth:** `app/index.html` and `app/sw.js`. Never edit the root or `beta/` copies by hand.
- Root = stable (the normal link).
- `beta/` = test copy at `/beta/`, with its own project storage.

## Small fix
1. Edit `app/`, bump `VERSION` in both files.
2. `./release.sh stable` (runs all tests, copies to root).
3. Commit, `git tag vNNN`, push. Check the live page shows the new version.

## Big update
1. Edit `app/`, bump version.
2. `./release.sh beta`. Commit, tag `beta-vNNN`, push.
3. Max exports a real project (File > Export backup), opens `/beta/`, imports it, and tests with `TESTING.md`.
4. Max says "promote" -> `./release.sh promote`, commit, tag `vNNN`, push.

## Roll back
`./release.sh rollback v018`, commit, push. (Tags could not be pushed to GitHub from this setup, so rollback also finds the version by its commit message.) Projects saved by a newer format are refused by the old app (not damaged). Backups still import.

## Adding anything new (checklist)
- New setting -> add to `DEF`. Add a non-default value to `PERTURB` in `tests/test_roundtrip.py` (the test fails until you do).
- New object kind -> add to `OBJ_KINDS` and `persistObjs`, and to the scene in `test_roundtrip.py`.
- New state outside `S` / `OBJS` -> save it in `saveNow`, restore it in `openSpace`, add it to `snapshotState()`.
- Changed what is saved in a way old projects need fixing -> raise `FORMAT` and add a step in `upgradeRec`. Never delete old steps.
- Run `python3 tests/run.py` (about 4 minutes).

## Honest limits
Tests run headless on a software GPU (SwiftShader). They cannot judge how it feels on a real GPU, touch controls, or big-scene speed. That is what `TESTING.md` is for.

## Windows app (desktop/)
- Electron wrapper around the released root `index.html` (served from `app://splatbox`, no service worker). Installed per-user, no admin.
- Pushing a new `index.html` to `main` triggers `.github/workflows/desktop.yml`: it builds the installer on GitHub and publishes release `v0.<Version>.<REV>` (Version 030 = 0.30.0). The installed app checks on launch and every 4 h, downloads quietly, and offers "Restart now".
- Changed only the wrapper (`desktop/*`)? Bump the number in `desktop/REV` so a new release is made.
- Needs the repo public (it is) so installed apps can read releases. Unsigned, so Windows shows a SmartScreen warning on first install only.
- Local check: `cd desktop && npm i && node prepare.js`, then `python3 tests/desktop_smoke.py`.
- Browser storage is per-origin: projects made on the github.io page are not inside the desktop app. Use the project folders / backup import to move them.
