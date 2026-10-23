# Ship of Harkinian Switch 9.4 — controller experiment

**Experimental prerelease; NOT validated on a physical Switch.**

Base: original upstream Switch `9.3.1-nx1` commit `ccc1d766160f6ead6f96fdf3d50ad8d18edc45c1`, with its original `libultraship` submodule `0ab83783bdf68d5fb4fa88124c512e6df942145c`.

## Sole source-level runtime change

In `libultraship/src/ship/port/switch/SwitchImpl.cpp`, replace **only** the multi-line `padConfigureInput(8, ...)` call with exactly this call from the `9.2.3-nx5` release:

```cpp
padConfigureInput(8, HidNpadStyleSet_NpadStandard);
```

All other runtime source, game mechanics, mapping, SDL device detection, UI, save/exit code, rendering, input processing, Anchor multiplayer and networking remain **exactly 9.3.1-nx1**. Standard Switch controllers and handheld modes remain declared. Specialized system/retro/GameCube controller style flags added in 9.3.0+ are excluded and may no longer function.

## Evidence and limitations

On a Switch running **firmware 23.0.1 and Atmosphère 1.12.1**, the 9.3.4 experiment (changing only 8 to 1 but retaining all styles) did **not** stop the Nintendo controller confirmation screen; reopening after exiting normally also triggered the blue crash. New Atmosphère reports show User Breaks in system processes `am` (2202-1044) and `controller` (2011-0301). They do not contain a symbolicated SoH stack or prove causation.

The 9.2.3 controller call is a **hypothesis to test**, not a verified fix for the Nintendo applet or relaunch crash.

## Install/test

1. Back up `SD:/switch/soh/` (especially saves and configuration).
2. From `soh-switch-9.4.zip`, replace only `soh.nro` and `soh.o2r` in the existing folder.
3. Start with the normal controller connected. Note whether Nintendo's confirmation screen appears.
4. Play and exit normally; repeat start/exit **five times**. Check saves and input in normal handheld/docked setups.
5. If the system blue screen returns, preserve the new Atmosphère logs. A successful compilation does **not** verify a hardware fix.

The package includes no copyrighted game assets; preserve your separate `oot.o2r` / `oot-mq.o2r`.
