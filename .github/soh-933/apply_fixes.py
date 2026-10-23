#!/usr/bin/env python3
"""Apply pinned SoH 9.3.1 Switch fixes for the 9.3.3 test build.

Upstream: timschneeb/Shipwright-Switch @ 9.3.1-nx1.
libultraship: 0ab83783bdf68d5fb4fa88124c512e6df942145c.
This is deliberately applied during CI: the upstream submodule is not mutated in Git.
"""
from pathlib import Path
import subprocess
import sys

PINNED_LUS = "0ab83783bdf68d5fb4fa88124c512e6df942145c"

RELOAD_OLD = '''void Config::Reload() {
    if (mPath == "None" || !fs::exists(mPath) || !fs::is_regular_file(mPath)) {
'''
RELOAD_NEW = '''void Config::Reload() {
#if defined(__SWITCH__)
    // On Switch, libnx rename does not replace an existing destination. If
    // the previous run stopped after moving config to .bak, recover it.
    if (mPath != "None") {
        const fs::path backupPath = fs::path(mPath).string() + ".bak";
        std::error_code recoveryEc;
        const bool configExists = fs::exists(mPath, recoveryEc);
        if (!recoveryEc && !configExists && fs::exists(backupPath, recoveryEc) && !recoveryEc) {
            fs::rename(backupPath, mPath, recoveryEc);
            if (recoveryEc) {
                SPDLOG_ERROR("Could not recover configuration from {}: {}", backupPath.string(),
                             recoveryEc.message());
            }
        }
    }
#endif
    if (mPath == "None" || !fs::exists(mPath) || !fs::is_regular_file(mPath)) {
'''

SAVE_OLD = '''    fs::rename(tempPath, configPath, ec);
    if (ec) {
        SPDLOG_ERROR("Could not replace config \\"{}\\": {}", mPath, ec.message());
        std::error_code removeEc;
        fs::remove(tempPath, removeEc);
    }
}'''
SAVE_NEW = '''#if defined(__SWITCH__)
    const fs::path backupPath = configPath.parent_path() / (configPath.filename().string() + ".bak");
    ec.clear();
    const bool hadOriginal = fs::exists(configPath, ec);
    if (ec) {
        SPDLOG_ERROR("Could not check existing config \\"{}\\": {}", mPath, ec.message());
        std::error_code cleanupEc;
        fs::remove(tempPath, cleanupEc);
        return;
    }
    if (hadOriginal) {
        // Keep the current configuration intact if backup preparation fails.
        fs::remove(backupPath, ec);
        if (ec) {
            SPDLOG_ERROR("Could not prepare config backup \\"{}\\": {}", backupPath.string(), ec.message());
            std::error_code cleanupEc;
            fs::remove(tempPath, cleanupEc);
            return;
        }
        fs::rename(configPath, backupPath, ec);
        if (ec) {
            SPDLOG_ERROR("Could not back up config \\"{}\\": {}", mPath, ec.message());
            std::error_code cleanupEc;
            fs::remove(tempPath, cleanupEc);
            return;
        }
    }
    // Destination is now absent: no unsupported replace-existing rename.
    fs::rename(tempPath, configPath, ec);
    if (ec) {
        SPDLOG_ERROR("Could not promote config \\"{}\\": {}", mPath, ec.message());
        if (hadOriginal) {
            std::error_code restoreEc;
            fs::rename(backupPath, configPath, restoreEc);
            if (restoreEc) {
                SPDLOG_ERROR("CONFIG RECOVERY REQUIRED: backup at \\"{}\\": {}",
                             backupPath.string(), restoreEc.message());
            }
        }
        std::error_code cleanupEc;
        fs::remove(tempPath, cleanupEc);
    }
    // Keep .bak on success for recovery from unexpected interruption.
#else
    fs::rename(tempPath, configPath, ec);
    if (ec) {
        SPDLOG_ERROR("Could not replace config \\"{}\\": {}", mPath, ec.message());
        std::error_code removeEc;
        fs::remove(tempPath, removeEc);
    }
#endif
}'''

PATCHES = {
    "libultraship/src/ship/config/Config.cpp": [
        (RELOAD_OLD, RELOAD_NEW),
        (SAVE_OLD, SAVE_NEW),
    ],
    "soh/soh/SaveManager.h": [
        ('''    bool SaveFile_Exist(int fileNum);
    void ThreadPoolWait();
''', '''    bool SaveFile_Exist(int fileNum);
    void ThreadPoolWait();
    void StopSaveWorker(); // Join the Switch save worker during orderly shutdown.
'''),
    ],
    "soh/soh/SaveManager.cpp": [
        ('''void SaveManager::ThreadPoolWait() {
#if defined(__SWITCH__)
''', '''void SaveManager::StopSaveWorker() {
#if defined(__SWITCH__)
    if (mSaveWorkerRunning) {
        ShutdownSaveWorker();
    }
#endif
}

void SaveManager::ThreadPoolWait() {
#if defined(__SWITCH__)
'''),
    ],
    "soh/soh/OTRGlobals.cpp": [
        ('''extern "C" void DeinitOTR() {
    SaveManager_ThreadPoolWait();
    WaitForRandoGeneration();
''', '''extern "C" void DeinitOTR() {
    SaveManager_ThreadPoolWait();
#ifdef __SWITCH__
    // Drain and join save I/O before the Switch services are released.
    SaveManager::Instance->StopSaveWorker();
#endif
    WaitForRandoGeneration();
'''),
    ],
    "libultraship/src/ship/port/switch/SwitchImpl.cpp": [
        ('''void Ship::Switch::Exit() {
    Keyboard::Close();
''', '''void Ship::Switch::Exit() {
    // A pending applet callback must not access services after shutdown.
    appletUnhook(&applet_hook_cookie);
    Keyboard::Close();
'''),
    ],
}

# Follow-up after on-device logs showed fatal AM / controller process errors.
# Do not alter Nintendo system modules. Restrict changes to unnecessary IPCs
# and resource lifecycle of sensors created by the homebrew app.
PATCHES.update({
"libultraship/src/ship/port/switch/SwitchImpl.cpp": [
("#include \"SwitchKeyboard.h\"\n", "#include \"SwitchKeyboard.h\"\n#include \"SwitchController.h\"\n"),
("            appletInitializeGamePlayRecording();\n            appletSetGamePlayRecordingState(true);\n", "            // Gameplay video recording is not required by this homebrew app;\n            // avoid unnecessary AM recording IPC and its 96 MiB transfer buffer.\n"),
("    Keyboard::Close();\n    hidsysExit();", "    SwitchController::GetInstance().Shutdown();\n    Keyboard::Close();\n    hidsysExit();"),
("    appletSetGamePlayRecordingState(false);\n", "    // No gameplay recording session was created.\n")
],
"libultraship/src/ship/port/switch/SwitchController.h": [
("    bool Initialized = false;\n", "    bool Initialized = false;\n    bool SensorHandlesReady[4] = {};\n    bool SensorRunning[4] = {};\n    bool HandheldRumbleReady = false;\n"),
("    static void Update();\n", "    static void Update();\n    void Shutdown();\n")
],
"libultraship/src/ship/port/switch/SwitchController.cpp": [
("void SwitchController::Update() {", "void SwitchController::Shutdown() {\n    // Called before libnx exits: release only sensors actually started by SoH.\n    for (auto& controller : mControllers) {\n        for (size_t i = 0; i < 4; ++i) {\n            if (controller.SensorRunning[i]) {\n                const Result result = hidStopSixAxisSensor(controller.Sensors[i]);\n                if (R_FAILED(result)) {\n                    SPDLOG_WARN(\"Could not stop Switch motion sensor {} (result {:#x})\", i, result);\n                }\n                controller.SensorRunning[i] = false;\n            }\n        }\n    }\n    ClearDeviceSlots();\n}\n\nvoid SwitchController::Update() {"),
("    hidInitializeVibrationDevices(controller.Handles[0], 2, HidNpadIdType_Handheld, HidNpadStyleTag_NpadHandheld);\n    hidInitializeVibrationDevices(controller.Handles[1], 2, npadId, HidNpadStyleTag_NpadJoyDual);\n\n    hidGetSixAxisSensorHandles(&controller.Sensors[0], 1, HidNpadIdType_Handheld, HidNpadStyleTag_NpadHandheld);\n    hidGetSixAxisSensorHandles(&controller.Sensors[1], 1, npadId, HidNpadStyleTag_NpadFullKey);\n    hidGetSixAxisSensorHandles(&controller.Sensors[2], 2, npadId, HidNpadStyleTag_NpadJoyDual);\n\n    for (auto& sensor : controller.Sensors) {\n        hidStartSixAxisSensor(sensor);\n    }\n\n", "    // Motion sensors and vibration handles are opened lazily for connected devices.\n\n"),
("bool SwitchController::ReadSixAxisState(uint8_t portIndex, HidSixAxisSensorState& state) {\n    if (!EnsureInitialized(portIndex)) {\n        return false;\n    }\n\n    auto& controller = mControllers[portIndex];\n    padUpdate(&controller.State);\n    const uint64_t styleSet = padGetStyleSet(&controller.State);\n\n    if (styleSet & HidNpadStyleTag_NpadJoyDual) {\n        const uint64_t attributes = padGetAttributes(&controller.State);\n        if (attributes & HidNpadAttribute_IsLeftConnected) {\n            hidGetSixAxisSensorStates(controller.Sensors[2], &state, 1);\n            return state.delta_time > 0;\n        }\n        if (attributes & HidNpadAttribute_IsRightConnected) {\n            hidGetSixAxisSensorStates(controller.Sensors[3], &state, 1);\n            return state.delta_time > 0;\n        }\n    }\n\n    if (styleSet & HidNpadStyleTag_NpadHandheld) {\n        hidGetSixAxisSensorStates(controller.Sensors[0], &state, 1);\n        return state.delta_time > 0;\n    }\n\n    if (styleSet & HidNpadStyleTag_NpadFullKey) {\n        hidGetSixAxisSensorStates(controller.Sensors[1], &state, 1);\n        return state.delta_time > 0;\n    }\n\n    return false;\n}\n\n", "bool SwitchController::ReadSixAxisState(uint8_t portIndex, HidSixAxisSensorState& state) {\n    if (!EnsureInitialized(portIndex)) {\n        return false;\n    }\n\n    auto& controller = mControllers[portIndex];\n    padUpdate(&controller.State);\n    if (!padIsConnected(&controller.State)) {\n        return false;\n    }\n    const uint64_t styleSet = padGetStyleSet(&controller.State);\n\n    // Start only the sensor actually needed by the connected controller.\n    // Opening all sensors on eight ports previously sent unnecessary HID IPCs.\n    auto readActiveSensor = [&](size_t sensorIndex) -> bool {\n        if (!controller.SensorHandlesReady[sensorIndex]) {\n            Result result = 0;\n            if (sensorIndex == 0) {\n                result = hidGetSixAxisSensorHandles(&controller.Sensors[0], 1,\n                                                   HidNpadIdType_Handheld, HidNpadStyleTag_NpadHandheld);\n            } else if (sensorIndex == 1) {\n                result = hidGetSixAxisSensorHandles(&controller.Sensors[1], 1,\n                                                   GetNpadId(portIndex), HidNpadStyleTag_NpadFullKey);\n            } else {\n                result = hidGetSixAxisSensorHandles(&controller.Sensors[2], 2,\n                                                   GetNpadId(portIndex), HidNpadStyleTag_NpadJoyDual);\n            }\n            if (R_FAILED(result)) {\n                return false;\n            }\n            if (sensorIndex >= 2) {\n                controller.SensorHandlesReady[2] = true;\n                controller.SensorHandlesReady[3] = true;\n            } else {\n                controller.SensorHandlesReady[sensorIndex] = true;\n            }\n        }\n        if (!controller.SensorRunning[sensorIndex]) {\n            const Result result = hidStartSixAxisSensor(controller.Sensors[sensorIndex]);\n            if (R_FAILED(result)) {\n                return false;\n            }\n            controller.SensorRunning[sensorIndex] = true;\n        }\n        state = {};\n        hidGetSixAxisSensorStates(controller.Sensors[sensorIndex], &state, 1);\n        return state.delta_time > 0;\n    };\n\n    if (styleSet & HidNpadStyleTag_NpadJoyDual) {\n        const uint64_t attributes = padGetAttributes(&controller.State);\n        if (attributes & HidNpadAttribute_IsLeftConnected) {\n            return readActiveSensor(2);\n        }\n        if (attributes & HidNpadAttribute_IsRightConnected) {\n            return readActiveSensor(3);\n        }\n    }\n    if (styleSet & HidNpadStyleTag_NpadHandheld) {\n        return readActiveSensor(0);\n    }\n    if (styleSet & HidNpadStyleTag_NpadFullKey) {\n        return readActiveSensor(1);\n    }\n    return false;\n}\n\n"),
("    if (externalStyle != 0 && controller.LastExternalRumbleStyle != externalStyle) {\n        hidInitializeVibrationDevices(controller.Handles[1], 2, GetNpadId(portIndex),\n                                      static_cast<HidNpadStyleTag>(externalStyle));\n        controller.LastExternalRumbleStyle = externalStyle;\n    }\n", ""),
("    if (padIsHandheld(&controller.State)) {\n        hidSendVibrationValues(controller.Handles[0], vibrationValues, 2);\n    } else if (externalStyle != 0) {\n        hidSendVibrationValues(controller.Handles[1], vibrationValues, 2);\n    }", "    if (padIsHandheld(&controller.State)) {\n        if (!controller.HandheldRumbleReady) {\n            const Result result = hidInitializeVibrationDevices(controller.Handles[0], 2,\n                                                                HidNpadIdType_Handheld,\n                                                                HidNpadStyleTag_NpadHandheld);\n            if (R_FAILED(result)) {\n                return;\n            }\n            controller.HandheldRumbleReady = true;\n        }\n        hidSendVibrationValues(controller.Handles[0], vibrationValues, 2);\n    } else if (externalStyle != 0) {\n        if (controller.LastExternalRumbleStyle != externalStyle) {\n            const Result result = hidInitializeVibrationDevices(controller.Handles[1], 2,\n                                                                GetNpadId(portIndex),\n                                                                static_cast<HidNpadStyleTag>(externalStyle));\n            if (R_FAILED(result)) {\n                return;\n            }\n            controller.LastExternalRumbleStyle = externalStyle;\n        }\n        hidSendVibrationValues(controller.Handles[1], vibrationValues, 2);\n    }")
]
})

def patch(root: Path, dry_run: bool = False) -> None:
    submodule = root / "libultraship"
    result = subprocess.run(
        ["git", "-C", str(submodule), "rev-parse", "HEAD"],
        capture_output=True, text=True, check=False
    )
    if result.returncode != 0 or result.stdout.strip() != PINNED_LUS:
        raise RuntimeError("Unexpected libultraship commit: " + result.stdout.strip())
    staged = {}
    for relative, replacements in PATCHES.items():
        path = root / relative
        original = path.read_text(encoding="utf-8-sig")
        changed = original
        for before, after in replacements:
            if after in changed:
                raise RuntimeError("Patch already applied: " + relative)
            count = changed.count(before)
            if count != 1:
                raise RuntimeError(f"Unexpected source anchor in {relative}: {count}")
            changed = changed.replace(before, after, 1)
        staged[path] = changed
    if not dry_run:
        for path, content in staged.items():
            path.write_text(content, encoding="utf-8")
    for path in staged:
        print(("CHECKED " if dry_run else "PATCHED ") + str(path.relative_to(root)))

def test_fixtures() -> None:
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        for name, replacements in PATCHES.items():
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("\n".join(old for old, _ in replacements))
        for name, replacements in PATCHES.items():
            data = (root / name).read_text()
            for before, after in replacements:
                assert data.count(before) == 1
                data = data.replace(before, after, 1)
                assert data.count(after) == 1
            (root / name).write_text(data)
        for name, replacements in PATCHES.items():
            assert all(after in (root / name).read_text() for _, after in replacements)
    print("PASS: source anchor/patch fixture test")

def main() -> None:
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--check", action="store_true")
    p.add_argument("--test", action="store_true")
    args = p.parse_args()
    if args.test:
        test_fixtures()
    else:
        patch(Path(__file__).resolve().parents[2], dry_run=args.check)

if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, AssertionError) as error:
        sys.exit(f"ERROR: {error}")
