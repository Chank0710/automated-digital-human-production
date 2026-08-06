from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from project_io import create_project, load_config, validate_config


def main() -> None:
    parser = argparse.ArgumentParser(description="Create or validate a digital-human project")
    parser.add_argument("project", type=Path)
    parser.add_argument("--init", action="store_true", help="Create config.json and state.json")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--stage", choices=("intake", "generate"), default="intake")
    args = parser.parse_args()

    try:
        if args.init:
            config_path, state_path = create_project(args.project, overwrite=args.overwrite)
            print(json.dumps({"config": str(config_path), "state": str(state_path)}, indent=2))
            return
        result = validate_config(load_config(args.project), stage=args.stage)
    except ValueError as exc:
        sys.exit(str(exc))

    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["missing"] or result["errors"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
