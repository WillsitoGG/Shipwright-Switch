#!/usr/bin/env python3
"""Apply pinned SoH 9.3.1 Switch fixes for the 9.3.2 test build.

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
