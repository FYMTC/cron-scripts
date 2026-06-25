#!python3
"""周六第二档：仅将 weekend_data.json 回显到 stdout（不重跑 RD-Agent）。"""
import json
import sys
import sys; sys.path.insert(0, '/config/quant_scripts')
from system_config import cfg

PATH = cfg.path.weekend_data


def main() -> None:
    try:
        with open(PATH, encoding="utf-8") as f:
            body = f.read()
    except OSError as e:
        print(json.dumps({"error": "cannot_read_weekend_data", "path": PATH, "detail": str(e)}))
        sys.exit(1)
    if not body.strip():
        print(json.dumps({"error": "empty_file", "path": PATH}))
        sys.exit(1)
    sys.stdout.write(body)


if __name__ == "__main__":
    main()
