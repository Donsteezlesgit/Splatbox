# Splatbox: notes for Claude (read this first, keep it short)

Splatbox is Max's Gaussian-splat viewer/editor. One file, `app/index.html` (about 5,500 lines), shipped as a PWA (web + phone) and wrapped by a Windows Electron app (`desktop/`). Repo: Donsteezlesgit/splatbox. Max = Maximilian Thompson, Manchester, creative technologist.

## Working with Max
- Short, specific steps. No walls of text. He has dyslexia and ADHD; clear beats clever.
- Plan before building when the request is open ("let's talk", "plan"): don't build until he says so.
- **Push or release only when he says so.** Batch changes. Say plainly what was and wasn't checked.
- Before building a visual change: say what the real app can't match from the mockup, and get a nod.
- Notion logging only on "log" or "End Convo". Commit trailers (end of every commit message):
  `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>` and the `Claude-Session:` line from the session reminder.

## Where things are
- **Source of truth: `app/index.html` + `app/sw.js`.** Root `index.html`/`sw.js` = the live copy (made by `release.sh`). `beta/` = test copy. Never hand-edit root or beta.
- Do not read the whole file. Run `tools/map.sh` (section map with line ranges, always current), or `tools/map.sh timeline`, then `sed -n 'A,Bp' app/index.html`.
- Style: old-style JS (`var`, `function`, no arrow functions), one big wrapper. Some lines are very long; use `grep -n` then `cut -c1-200`.
- Key functions: `openTool` (panels), `setK` (settings), `addLight`, `saveNow`/`openSpace`/`upgradeRec` (save/load/migrate), `setStatus` (toast), `DEF` (all default settings), `TL` (timeline), `GM` (gizmo mode), `OBJS`/`SEL` (scene objects).
- Look: colour tokens are in `:root` at the top. V047's look is an override block at the END of `<style>` (`/* V047 ... */`), after the older rules. Edit tokens first; add overrides there, not in the old rules.
- Keys are handled in several `keydown` listeners (search `addEventListener("keydown"`). Check all before adding a key. Current clashes: W is both fly-forward and gizmo Move; 1-5 open tools in the editor but pick easing in the timeline.
- Adding anything new (settings, object kinds, saved state): follow the checklist in `RELEASING.md`. `tests/test_roundtrip.py` fails until you do.

## Testing
- `python3 tests/run.py <name>` runs suites whose name contains `<name>`; no name = all (about 14 min, 628 checks; too long for one foreground call: run with `nohup ... > /tmp/full.log &` and poll). Node test: `node tests/inbox_queue.js`.
- Pick suites by area from `tools/areas.txt` (e.g. look-and-css, timeline, save-folder-inbox). Run `full` before a release.
- The harness serves a copy of `app/index.html` with a hook inserted before the **last** `})();`. Anything you append must stay INSIDE that final wrapper, or tests can't see app functions.
- Tests run on a software GPU: no judgement on feel, touch or speed.
- Each suite's browser pages are now closed when it ends (harness.py). That cut the full run from 37 to 13 min and removed the load flakes (7 failures to 0). If a test fails only in the full run, re-run that suite alone before calling it real; say which you did.
- **Look check:** `python3 tests/run.py visual` (about 15 s). Compares home, editor+light, editor+timeline and phone light sheet with saved images in `tests/baselines/`, and checks layout (toolbar rows not wrapped, buttons on screen, no sideways scroll). Renders here are identical run to run, so any change over 0.02% of pixels fails; diff images go to `/tmp/visual_fail/`. Changed the look on purpose? Look at the new screenshots first, then `python3 tests/run.py visual --update` and commit the PNGs. Baselines only hold in this sandbox (fonts, software GPU). `ship.sh` runs it on every release that runs tests.
- Screenshots: `python3 tools/shot.py` (desktop) and `tools/shot_phone.py`; PNGs land in `/tmp/shots/`; view with Read. Do this for any visual change.

## Shipping (use `./ship.sh`, see its header)
- `./ship.sh --check 048` = dry run (no push). `./ship.sh 048 "short message" --tests full|area:timeline|"dock tl2"` = real release.
- It checks the changelog entry, bumps both VERSION strings, runs the tests, runs `release.sh stable` (copies app -> root, the step that was missed in V047), commits, pushes with retries, then checks the Pages deploy, the Windows build and the live version.
- **Tags can't be pushed from this sandbox** (documented in `RELEASING.md`). Not an error. Rollback finds a version by commit message.
- Only Max decides when to run the real thing.
- `publish_files` (artifacts) refuses files under `/tmp`: copy into `/home/claude` first.

## Hard-won
- A visual check by eye is not optional: 600 passing tests did not catch a three-row toolbar.
- `git push` can drop the connection once: retry.
- The old docs (`RELEASING.md`, `TESTING.md`) were right and I skipped them. Read before improvising.
