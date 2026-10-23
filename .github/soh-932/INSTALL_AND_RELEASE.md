# Testing the 9.3.2 Switch candidate

This is an **experimental Switch-specific fork build**, derived from timschneeb's 9.3.1-nx1.
The GitHub release tag is **9.3.2** (without suffixes). The underlying HarbourMasters engine and resource format have **not** been bumped to 9.3.2, to preserve compatibility with the 9.3.1-nx1 base.

## Build
Pushing to `release/9.3.2` triggers `.github/workflows/generate-builds.yml`.
The Switch jobs apply `apply_fixes.py` to the pinned libultraship submodule and game source, then generate the NRO.
The publish job runs only if both Switch build variants succeed and the requested archive exists.
Any release is marked as **prerelease** until tested on a real Switch.

## Install and rollback
1. Back up `/switch/soh/` from the SD card before doing anything.
2. Download `soh-switch-9.3.2.zip` from the `9.3.2` release **if and only if that release exists**.
3. Extract its `soh.nro` and `soh.o2r` into the existing SoH directory, keeping the backup.
4. Ensure you use a ROM-derived game archive that was already compatible with 9.3.1-nx1. The release includes **no game ROM**.
5. Follow `HARDWARE_TEST_PLAN.md` to confirm repeated relaunches, setting persistence, and save-game integrity.
6. Restore the backed-up directory to roll back if the console crashes.

## Limitations
A successful compilation does not prove the firmware 23.0.1 crash is fixed. Configuration file recovery and orderly shutdown remain hypotheses to be tested on the target device.
