"""Install/status the macOS user service after a read-only paper preflight.

Run with the repository venv. Secrets remain in .env, never in the plist.
Stop safely using `python -m cash_cow.paper stop`, then verify flat before unload.
"""
import argparse
import json
import os
from pathlib import Path
import plistlib
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from cash_cow.paper.client import PaperClient

LABEL = "com.cashcow.paper"
PLIST = Path.home() / "Library/LaunchAgents" / (LABEL + ".plist")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("install", "status"))
    args = parser.parse_args()
    target = f"gui/{os.getuid()}/{LABEL}"
    if args.command == "status":
        subprocess.run(["launchctl", "print", target], check=True)
        return
    if sys.platform != "darwin":
        raise SystemExit("This installer supports macOS user LaunchAgents only")
    client = PaperClient()
    account, positions, orders = client.account(), client.positions(), client.open_orders()
    config = json.loads((ROOT / "configs/paper_v1.json").read_text())
    if account.get("status") != "ACTIVE" or any(account.get(k) for k in ("trading_blocked", "account_blocked", "trade_suspended_by_user")):
        raise SystemExit("Paper account is blocked or inactive")
    if positions or orders or float(account["cash"]) < config["capital"]:
        raise SystemExit("Initial installation requires a flat dedicated paper account with sufficient cash")
    client.quote(config["feed"])
    logs = ROOT / ".local/paper"
    logs.mkdir(parents=True, exist_ok=True)
    spec = {"Label": LABEL, "ProgramArguments": [str(ROOT / ".venv/bin/python"), "-u", "-m", "cash_cow.paper", "run"],
            "WorkingDirectory": str(ROOT), "RunAtLoad": True,
            "KeepAlive": {"SuccessfulExit": False}, "ThrottleInterval": 60,
            "StandardOutPath": str(logs / "runner.log"), "StandardErrorPath": str(logs / "error.log"),
            "ProcessType": "Background", "Umask": 63}
    PLIST.parent.mkdir(parents=True, exist_ok=True)
    if PLIST.exists():
        raise SystemExit("Existing service plist retained; inspect loaded service before changing it")
    with PLIST.open("xb") as stream:
        plistlib.dump(spec, stream)
    os.chmod(PLIST, 0o600)
    subprocess.run(["plutil", "-lint", str(PLIST)], check=True)
    subprocess.run(["launchctl", "bootstrap", f"gui/{os.getuid()}", str(PLIST)], check=True)
    print(f"Installed {LABEL}; inspect fresh runner status before claiming it is operating.")


if __name__ == "__main__":
    main()
