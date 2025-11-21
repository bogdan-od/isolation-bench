#!./.venv/bin/python3
import os
import yaml
from core.logger import log
from core.orchestrator import Orchestrator

def load_config(path='config.yaml'):
    if not os.path.exists(path):
        log(f"Config file {path} not found", "FATAL")
        return None
    with open(path, 'r') as f:
        return yaml.safe_load(f)

def main():
    if os.geteuid() != 0:
        log("MUST RUN AS ROOT (sudo)", "FATAL")
        exit(1)

    config = load_config()
    if not config:
        return

    # Initialize and run orchestrator
    app = Orchestrator(config)
    app.setup()
    app.execute_all()

if __name__ == "__main__":
    main()
