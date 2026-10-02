import argparse
import json

from app.core.db import SessionLocal
from app.governance.engine import execute_controls
from app.quality.service import execute_quality
from app.services.seed import seed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["seed", "quality", "controls"])
    args = parser.parse_args()
    with SessionLocal.begin() as db:
        result = {"seed": seed, "quality": execute_quality, "controls": execute_controls}[
            args.command
        ](db)
        print(json.dumps(result))


if __name__ == "__main__":
    main()
