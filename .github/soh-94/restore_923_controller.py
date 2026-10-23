#!/usr/bin/env python3
"""SoH Switch 9.4: exactly restore the 9.2.3-nx5 controller config.
Built against the official 9.3.1-nx1 pinned submodule; no earlier experiments.
"""
from pathlib import Path
import subprocess
import sys

EXPECTED_SUBMODULE = "0ab83783bdf68d5fb4fa88124c512e6df942145c"
RELATIVE_PATH = "libultraship/src/ship/port/switch/SwitchImpl.cpp"
OLD = "padConfigureInput(8, HidNpadStyleSet_NpadStandard | HidNpadStyleTag_NpadGc | HidNpadStyleTag_NpadLark |\n                                     HidNpadStyleTag_NpadHandheldLark | HidNpadStyleTag_NpadLucia |\n                                     HidNpadStyleTag_NpadLagon | HidNpadStyleTag_NpadLager |\n                                     HidNpadStyleTag_NpadSystemExt | HidNpadStyleTag_NpadSystem);"
NEW = "padConfigureInput(8, HidNpadStyleSet_NpadStandard);"


def replace_exact(source):
    if source.count(OLD) != 1:
        raise RuntimeError("Original 9.3.1 configuration was not found exactly once")
    if NEW in source:
        raise RuntimeError("9.2.3 patch was already applied")
    result = source.replace(OLD, NEW, 1)
    if result.replace(NEW, OLD, 1) != source:
        raise AssertionError("Unexpected extra source edit")
    return result


def main():
    from argparse import ArgumentParser
    ap = ArgumentParser()
    ap.add_argument("--test", action="store_true")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    if args.test:
        source = "before\n" + OLD + "\nafter"
        assert replace_exact(source) == "before\n" + NEW + "\nafter"
        try:
            replace_exact("before\n" + NEW + "\nafter")
        except RuntimeError:
            pass
        else:
            raise AssertionError("Double application not rejected")
        print("PASS: exact one-call-only 9.2.3 substitution")
        return

    root = Path(__file__).resolve().parents[2]
    lib = root / "libultraship"
    sha = subprocess.run(
        ["git", "-C", str(lib), "rev-parse", "HEAD"],
        capture_output=True, text=True, check=True
    ).stdout.strip()
    if sha != EXPECTED_SUBMODULE:
        raise RuntimeError(f"Unexpected submodule SHA: {sha}")

    path = root / RELATIVE_PATH
    source = path.read_text(encoding="utf-8")
    result = replace_exact(source)
    if not args.check:
        path.write_text(result, encoding="utf-8")
    print(("CHECK " if args.check else "PATCH ") + RELATIVE_PATH)


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, AssertionError, subprocess.CalledProcessError) as exc:
        sys.exit(f"ERROR: {exc}")
