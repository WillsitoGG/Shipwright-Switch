# 9.3.3 validation matrix

**Baseline:** 9.3.2 still causes a blue screen on launch-after-exit on Nintendo Switch FW 23.0.1 + Atmosphère 1.12.1.

1. Back up entire current SoH folder; preserve previous NRO and all save/config files.
2. Install the **9.3.3** build's `soh.nro` and `soh.o2r` without deleting saves.
3. Five normal launch → exit → relaunch cycles, recording exact reproduction steps.
4. Verify configuration persists after normal exit/relaunch.
5. Verify controller inputs, handheld/docked, rumble and gyro if used.
6. Verify in-game save and load with a disposable backed-up save slot.
7. If fatal report persists, check process/program IDs and compare with a clean Atmosphère system-module environment; do not assume it is directly caused by SoH.

**Safety:** No firmware downgrade, no deletion of NAND/system files, no resetting configuration or saves as a first step.
