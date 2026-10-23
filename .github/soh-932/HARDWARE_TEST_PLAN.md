# Hardware validation protocol — 9.3.2

Target: Nintendo Switch firmware 23.0.1, Atmosphère 1.12.1.
Base: timschneeb/Shipwright-Switch 9.3.1-nx1.
Upstream bug report: https://github.com/timschneeb/Shipwright-Switch/issues/20

## Preconditions
- Back up the entire existing `/switch/soh/` folder to a computer, including saves and `shipofharkinian.json`.
- Keep the original 9.3.1-nx1 `soh.nro` available for rollback.
- Do not overwrite any known-good save data while diagnosing a crash.
- Use the same game launch method for the old and new build (full-memory homebrew, not Applet mode).
- Do not change firmware, Atmosphère, plugins, or controller mappings as part of this comparison.

## Test A: Relaunch without changing configuration
1. Cold-boot the console and launch 9.3.2.
2. Load a game; do not modify settings.
3. Exit normally and reopen SoH.
4. Repeat exit/relaunch at least five times.
5. Record any system error, including 2202-1044 or 2011-0301. Save crash reports.

## Test B: Configuration persistence
1. Back up the existing configuration before changing it.
2. Make one easily reversible setting change, then exit normally.
3. Reopen SoH and verify the setting persists.
4. Repeat twice and check that `shipofharkinian.json` is valid JSON.
5. Verify that `shipofharkinian.json.bak` is present after a successful replacement.
6. Do not delete `.bak` before testing complete.

## Test C: Game saves
1. Use a disposable slot or an already-backed-up save.
2. Save in-game, exit and relaunch.
3. Check game progress and verify it is not corrupted.

## Acceptance
- CI builds `soh.nro` and produces `soh.o2r` successfully.
- All relaunch tests pass without a blue screen.
- Configuration changes survive at least three normal exit/relaunch cycles.
- Game saves remain valid.
- No additional errors appear in Atmosphère logs.

**Important:** A build that passes GitHub Actions is not proof of device compatibility or a fix for issue #20. The `9.3.2` GitHub release is marked as a prerelease until hardware validation.
