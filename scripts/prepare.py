"""毎朝の最初の1コマンド: 最新化 → work初期化 → 新着チェック → 出演検索。

 python3 /Users/kameyamakenta/satomitsuro-video-tracker/scripts/prepare.py
承認が必要なコマンドを減らすため、git pull・work初期化・2つのスクリプトをここにまとめている。
"""
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import REPO, WORK, ensure_work  # noqa: E402


def main():
    p = subprocess.run(["git", "pull", "--ff-only", "origin", "main"], cwd=REPO,
                       capture_output=True, text=True)
    print("git pull:", (p.stdout + p.stderr).strip().splitlines()[-1] if (p.stdout + p.stderr).strip() else "ok")
    shutil.rmtree(WORK, ignore_errors=True)
    ensure_work()
    for script in ("check_channels.py", "find_appearances.py"):
        print("\n=== %s ===" % script, flush=True)
        r = subprocess.run([sys.executable, os.path.join(REPO, "scripts", script)], cwd=REPO)
        if r.returncode != 0:
            print("WARNING: %s がエラー終了 (code %d)" % (script, r.returncode))
    print("\n=== pending.json ===")
    print(open(os.path.join(WORK, "pending.json"), encoding="utf-8").read())
    return 0


if __name__ == "__main__":
    sys.exit(main())
