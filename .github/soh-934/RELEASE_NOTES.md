# Ship of Harkinian Switch 9.3.4 — one-player controller configuration

**Experimental build — not yet verified on physical Switch hardware.**

Starting point: exactly the official Switch `9.3.1-nx1` source from commit `ccc1d766160f6ead6f96fdf3d50ad8d18edc45c1`, including its original pinned `libultraship` submodule. No 9.3.2/9.3.3 modifications.

## Sole runtime source change

File: `libultraship/src/ship/port/switch/SwitchImpl.cpp`

In its `padConfigureInput` call, replace the first parameter **8** with **1**. Every single original controller style flag is **left unchanged**, including GameCube, NES, SNES, N64, Genesis, handheld, system and standard supported styles.

Effect: report one supported controller-player ID (plus handheld where supported) rather than eight. This **does not** disable Anchor online multiplayer, which is unrelated to local controller-player IDs. It does not alter game logic, saves, mapping classes, rendering, or settings.

**Goal:** launch with the already connected controller without needing to re-select the controller at every game startup. The Nintendo controller-selection applet is **not directly called or bypassed** by this change. Whether this fixes the launch UI or firmware-23.0.1 relaunch crash remains **unconfirmed until tested on the actual device**. If the controller is assigned to a non-primary slot, input behavior also needs to be tested.

## Installation and validation

1. Back up the entire existing `/switch/soh/` folder, including saves and configuration.
2. From the release ZIP, copy `soh.nro` and `soh.o2r` into the existing folder without deleting saves.
3. Verify it launches with the already-connected Pro Controller/Joy-Con and does **not** show the Nintendo controller-selection screen.
4. Test handheld mode, any previously configured controllers, normal gameplay, and save/load.
5. Exit and relaunch at least five times; collect Atmosphère crash reports if the blue system error recurs.

A successful GitHub Actions build only confirms compilation, not hardware behavior. The ZIP contains no game ROM.
