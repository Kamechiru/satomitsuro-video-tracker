"""毎朝の最後の1コマンド: 要約の反映 → ダッシュボード生成 → git commit/push → 通知。

 python3 /Users/kameyamakenta/satomitsuro-video-tracker/scripts/finish.py
"""
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import REPO, WORK, iso_z, now_utc  # noqa: E402

TERMINAL_NOTIFIER = "/opt/homebrew/bin/terminal-notifier"


def run(args, **kw):
    return subprocess.run(args, cwd=REPO, capture_output=True, text=True, **kw)


def main():
    for script in ("apply_results.py", "build_dashboard.py"):
        r = run([sys.executable, os.path.join(REPO, "scripts", script)])
        print(r.stdout.strip())
        if r.returncode != 0:
            print("ERROR in %s:\n%s" % (script, r.stderr.strip()))
            return 1

    try:
        notify = open(os.path.join(WORK, "notify.txt"), encoding="utf-8").read().strip()
    except OSError:
        notify = "NONE"
    n_new = notify.count("、") + 1 if notify.startswith("NEW:") else 0

    run(["git", "add", "state.json", "dashboard.html"])
    c = run(["git", "commit", "-m",
             "Update state and dashboard: %s (%s)" % (iso_z(now_utc()), "new" if n_new else "no new")])
    print("git commit:", (c.stdout + c.stderr).strip().splitlines()[0] if (c.stdout + c.stderr).strip() else "")
    p = run(["git", "push", "origin", "main"])
    print("git push:", "ok" if p.returncode == 0 else "FAILED\n" + p.stderr.strip())

    if notify.startswith("NEW:"):
        # 注意: -open オプションは付けない(launchd/無人実行で通知が出なくなる)
        n = run([TERMINAL_NOTIFIER, "-title", "YouTube新着チェッカー",
                 "-message", notify[len("NEW:"):], "-sound", "Glass"])
        print("notify:", "sent" if n.returncode == 0 else "FAILED " + n.stderr.strip())
    else:
        print("notify: none (新着なし)")
    return 0 if p.returncode == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
