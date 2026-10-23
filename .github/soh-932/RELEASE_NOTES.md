# Ship of Harkinian — Nintendo Switch 9.3.2

**Status: experimental, hardware testing required.** This release is a fork-specific fix build based on timschneeb's `9.3.1-nx1` (Ship of Harkinian 9.3.1), not an upstream HarbourMasters engine release 9.3.2.

## Changes under test

1. Work around libnx's inability to rename a file over an existing destination: stage config in `.tmp`, move the previous `shipofharkinian.json` to `.bak`, then promote the new file. Recover from `.bak` if interrupted.
2. Wait for and join the Switch save-file worker during normal shutdown.
3. Unregister the libnx applet callback before shutting down services.

Reference: https://github.com/timschneeb/Shipwright-Switch/issues/20

## Important

**A successful CI build is NOT confirmation the crash is fixed.** Back up the entire `/switch/soh/` directory (including saves/configuration) before testing. Keep the original 9.3.1-nx1 `soh.nro` in a separate location. Test multiple launch-exit-launch cycles on FW 23.0.1 / Atmosphère 1.12.1, then verify config persistence. Collect crash logs if failures continue. No copyrighted ROMs/assets are included.
