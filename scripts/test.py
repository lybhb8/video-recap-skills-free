#!/usr/bin/env python3
"""Cross-platform test runner: one isolated pytest process per skill group.

Each skill ships its OWN lib.py (the bundle has no shared code), so a single
`pytest tests/` would import several skills' modules into one process and collide
on the `lib` (and `narration`) module names. Run one group per subprocess instead.

Works on macOS, Linux, and Windows (the bash equivalent is scripts/test.sh).

Usage: python scripts/test.py            # run every skill group
       python scripts/test.py script     # run one or more named groups
"""
import os
import subprocess
import sys
from pathlib import Path

GROUPS = ["understanding", "cut", "voiceover", "assemble", "script", "orchestrator", "inspect"]


def _require_pytest():
    """Fail with the actual problem instead of reporting every group as a test failure.

    Without this, a missing pytest prints "No module named pytest" seven times and then
    "FAILED groups: understanding, cut, ..." — indistinguishable from real failures.
    """
    import importlib.util

    if importlib.util.find_spec("pytest") is not None:
        return True
    print(
        f"pytest is not installed for this interpreter ({sys.executable}).\n"
        f"  Install it:  {sys.executable} -m pip install pytest\n"
        "  Or run the suite with an interpreter that has it (PYTHON=... scripts/test.sh).",
        file=sys.stderr,
    )
    return False


def main(argv):
    if not _require_pytest():
        return 2
    root = Path(__file__).resolve().parent.parent
    groups = argv or GROUPS
    failed = []
    test_env = dict(os.environ)
    # Keep the suite hermetic: strip configuration knobs that a developer may
    # legitimately have set (process-level or Windows registry User scope) so
    # tests exercise defaults, not the local machine's setup. Both routes are
    # covered: registry merge is disabled via the switch, and variables already
    # inherited into this process's environment are dropped explicitly.
    test_env["VIDEO_RECAP_LOAD_USER_ENV"] = "0"
    for knob in (
        "MIMO_API_KEY",
        "MIMO_API_URL",
        "MIMO_API_KEY_SOURCE",
        "MIMO_AUTH_SCHEME",
        "MIMO_MODEL",
        "MIMO_VIDEO_MODEL",
        "MIMO_QC_MODEL",
        "MIMO_VIDEO_API_KEY",
        "MIMO_VIDEO_API_URL",
        "MIMO_TTS_API_KEY",
        "MIMO_TTS_API_URL",
        "MIMO_ASR_API_KEY",
        "MIMO_ASR_API_URL",
        "MIMO_TTS_VOICE",
        "MIMO_TTS_MODEL",
        "MIMO_ASR_MODEL",
        "MIMO_MEDIA_RESOLUTION",
        "MIMO_DISABLE_THINKING",
        "MIMO_TOKEN_PLAN_CLUSTER",
        "TTS_ENGINE",
        "EDGE_TTS_VOICE",
        "VOICE_REF",
        "ASR_ENGINE",
        "FUNASR_BIN",
        "FUNASR_MODEL",
        "FUNASR_VAD",
        "EDIT_MODE",
        "TARGET_DURATION",
        "MIMO_QC",
        "BURN_SUBTITLES",
        "VIDEO_RECAP_MATERIAL_LIBRARY_DIR",
    ):
        test_env.pop(knob, None)
    for group in groups:
        print(f"== {group} ==", flush=True)
        result = subprocess.run(
            # -rs prints skip reasons so a silently-skipped real-render test (e.g. ffmpeg
            # missing) is visible in CI output instead of a bare "s".
            [sys.executable, "-m", "pytest", str(root / "tests" / group), "-q", "-rs"],
            cwd=str(root),
            env=test_env,
        )
        if result.returncode != 0:
            failed.append(group)
    if failed:
        print(f"FAILED groups: {', '.join(failed)}")
        return 1
    print("All skill groups passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
