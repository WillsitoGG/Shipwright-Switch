# Ship of Harkinian 9.3.3 — experimental Switch relaunch fix

This is a fork-specific prerelease, built from timschneeb's 9.3.1-nx1 engine. Game data / saves are NOT upgraded, and no proprietary ROM is included.

## What the crash reports actually show
- AM service process \`0100000000000023\`: 2202-1044 / User Break.
- Controller process \`0100000000001003\`: 2011-0301 / User Break.
- These do not contain a SoH executable backtrace, so the underlying firmware/system-module fault cannot be confirmed just from these reports.

## Changes from fork 9.3.2
- Avoid optional gameplay-video-recording initialization and teardown IPC into AM.
- Stop starting motion sensors for every logical controller unconditionally. Acquire/start sensors lazily for the active connected controller, and stop started sensors on exit.
- Initialize vibration handles only on demand, check returned errors before use.
- Retain the 9.3.2 save/backup and background-save-worker fixes; avoid modifying the game's save data format, mappings, or other normal game logic.

## Device validation
1. Back up your entire existing \`switch/soh/\` folder, especially saves and \`shipofharkinian.json\`.
2. Keep a known-good copy of the earlier \`soh.nro\` so you can revert.
3. Run 9.3.3 in full-memory homebrew mode on the same firmware/Atmosphere configuration.
4. Try five consecutive launch → normal exit → launch cycles without changing input mappings.
5. Verify existing controller mappings, gyro (if used), rumble (if used), configuration persistence, and a disposable save slot.
6. If the blue screen returns, collect new Atmosphere fatal reports for AM/controller, and separately test a clean Atmosphere boot with optional third-party system modules disabled to isolate firmware/mod interaction.

**This is a test candidate, not a guaranteed fix.** A GitHub Actions successful build verifies compilation only. See https://github.com/timschneeb/Shipwright-Switch/issues/20
