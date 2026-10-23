#!/usr/bin/env python3
"""Switch 9.3.4: use one controller slot, preserve original controller styles.

Base: exactly SoH 9.3.1-nx1 and pinned libultraship commit.
Only runtime edit: change max_players from 8 to 1, preserving all original style flags.
This does not directly invoke or suppress the Nintendo controller applet.
"""
from pathlib import Path
import subprocess
import sys

EXPECTED_SUBMODULE = "0ab83783bdf68d5fb4fa88124c512e6df942145c"
OLD = "padConfigureInput(8, HidNpadStyleSet_NpadStandard | HidNpadStyleTag_NpadGc | HidNpadStyleTag_NpadLark |\n                                     HidNpadStyleTag_NpadHandheldLark | HidNpadStyleTag_NpadLucia |\n                                     HidNpadStyleTag_NpadLagon | HidNpadStyleTag_NpadLager |\n                                     HidNpadStyleTag_NpadSystemExt | HidNpadStyleTag_NpadSystem);"
NEW = OLD.replace("padConfigureInput(8,", "padConfigureInput(1,", 1)
RELATIVE_PATH = "libultraship/src/ship/port/switch/SwitchImpl.cpp"


def replace_exact(source):
    if source.count(OLD) != 1:
        raise RuntimeError("Expected original controller configuration exactly once")
    if NEW in source:
        raise RuntimeError("One-player patch already present")
    changed = source.replace(OLD, NEW, 1)
    if changed.replace(NEW, OLD, 1) != source:
        raise AssertionError("Unexpected changes beyond the controller configuration")
    return changed


def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--test", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    if args.test:
        fixture = "prefix\\n" + OLD + "\\nsuffix"
        result = replace_exact(fixture)
        assert result == "prefix\\n" + NEW + "\\nsuffix"
        try:
            replace_exact(result)
            raise AssertionError("Double-application was not rejected")
        except RuntimeError:
            pass
        print("PASS: exact one-digit player count patch and double-application guard")
        return

    root = Path(__file__).resolve().parents[2]
    lib = root / "libultraship"
    result = subprocess.run(["git", "-C", str(lib), "rev-parse", "HEAD"],
                            capture_output=True, text=True, check=True)
    if result.stdout.strip() != EXPECTED_SUBMODULE:
        raise RuntimeError("Wrong libultraship source commit: " + result.stdout.strip())
    target = root / RELATIVE_PATH
    original = target.read_text(encoding="utf-8")
    updated = replace_exact(original)
    if not args.check:
        target.write_text(updated, encoding="utf-8")
    print(("CHECK " if args.check else "PATCH ") + RELATIVE_PATH)


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, AssertionError, subprocess.CalledProcessError) as e:
        sys.exit(f"ERROR: {e}")
