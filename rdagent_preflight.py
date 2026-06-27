#!python3
"""周末因子挖掘 + HARNESS 前置；可选 --save-weekend-data 落盘 weekend_data.json（Option C）"""
import argparse
import os
import subprocess
import sys
import tempfile
import sys; sys.path.insert(0, '/config/quant_scripts')
from system_config import cfg

HARNESS = cfg.system.hermes_root + "/scripts/hermes_harness_preflight.py"
PYTHON = cfg.python  # 2026-06-27 修复：原为裸 "python3"（解析到系统 python3，无 numpy/qlib），导致周末 rdagent_weekend_preflight 报 ModuleNotFoundError: numpy
RDAGENT_WRAPPER = cfg.root + "/rdagent_weekend_preflight.py"
EXPORT = cfg.path.apps_dir + "/weekend_data_export.py"
OUT_JSON = cfg.path.weekend_data


def _save_weekend_bundle(rd_stdout: str) -> None:
    if not rd_stdout:
        rd_stdout = ""
    with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8", suffix=".txt") as tf:
        tf.write(rd_stdout)
        tmp_path = tf.name
    try:
        r2 = subprocess.run(
            [PYTHON, EXPORT, "--save", OUT_JSON, "--rdagent-text-file", tmp_path],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if r2.stdout:
            print(r2.stdout.strip())
        if r2.stderr:
            print(r2.stderr, file=sys.stderr)
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def main() -> None:
    p = argparse.ArgumentParser(add_help=False)
    p.add_argument("--save-weekend-data", action="store_true")
    args, _unknown = p.parse_known_args()

    # Step 0: Harness preflight
    r = subprocess.run([PYTHON, HARNESS], capture_output=True, text=True, timeout=30)
    if r.stdout.strip():
        print(r.stdout.strip())

    # Step 1: RD-Agent因子挖掘
    r = subprocess.run([PYTHON, RDAGENT_WRAPPER], capture_output=True, text=True, timeout=600)
    rd_stdout = r.stdout or ""
    if rd_stdout.strip():
        print(rd_stdout.strip())
    if r.stderr:
        print(r.stderr, file=sys.stderr)

    if args.save_weekend_data:
        _save_weekend_bundle(rd_stdout)

    sys.exit(r.returncode)


if __name__ == "__main__":
    main()
