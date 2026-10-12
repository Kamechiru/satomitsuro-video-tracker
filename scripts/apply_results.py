"""AIが書いた要約(work/summaries/<id>.txt / .skip)を state.json に反映する。

 - kind=channel     : 要約があれば last_video_* と last_summary を更新(新着扱い)。要約が無ければ何もしない
                      (次回の実行でもう一度「新着」として検出される=取りこぼし防止)。
 - kind=appearance  : 要約があれば appearances に追加、.skip(実際には出演していない等)なら確認済みにするだけ。
最後に work/notify.txt へ通知文(NEW:... か NONE)を書く。
"""
import datetime
import json
import os
import sys

from common import WORK, ensure_work, iso_z, load_state, now_utc, save_state

KEEP_APPEARANCES = 40
KEEP_DAYS = 45
KEEP_CHECKED = 600


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read().strip()


def main():
    ensure_work()
    state = load_state()
    try:
        with open(WORK + "/pending.json", encoding="utf-8") as f:
            items = json.load(f)["items"]
    except (OSError, ValueError, KeyError):
        items = []

    checked = state.setdefault("appearance_checked_ids", [])
    apps = state.setdefault("appearances", [])
    now = now_utc()
    new_channels, new_apps, skipped, unresolved = [], [], [], []

    for it in items:
        vid = it["video_id"]
        sp = "%s/summaries/%s.txt" % (WORK, vid)
        kp = "%s/summaries/%s.skip" % (WORK, vid)
        if it["kind"] == "channel":
            if not os.path.exists(sp):
                unresolved.append(it["title"])
                continue
            ch = next(c for c in state["channels"] if c["channel_id"] == it["channel_id"])
            ch.update(last_video_id=vid, last_video_title=it["title"],
                      last_video_url=it["url"], last_video_published=it["published"],
                      new_in_last_check=True, check_failed=False, last_summary=read(sp))
            new_channels.append(ch["name"])
        else:
            if os.path.exists(kp):
                if vid not in checked:
                    checked.append(vid)
                skipped.append("%s (%s)" % (it["title"][:30], read(kp)[:40]))
            elif os.path.exists(sp):
                apps.insert(0, {"video_id": vid, "persons": it["persons"], "title": it["title"],
                                "url": it["url"], "host_channel": it["host_channel"],
                                "published": it["published"], "found_at": iso_z(now),
                                "summary": read(sp)})
                if vid not in checked:
                    checked.append(vid)
                new_apps.append(it)
            else:
                unresolved.append(it["title"])

    cutoff = iso_z(now - datetime.timedelta(days=KEEP_DAYS))
    apps[:] = sorted((a for a in apps if a["published"] >= cutoff),
                     key=lambda a: a["published"], reverse=True)[:KEEP_APPEARANCES]
    state["appearance_checked_ids"] = checked[-KEEP_CHECKED:]
    state["last_checked_at"] = iso_z(now)
    save_state(state)

    parts = []
    if new_channels:
        parts.append("新着 " + "、".join(new_channels))
    if new_apps:
        who = []
        for a in new_apps:
            for p in a["persons"]:
                if p not in who:
                    who.append(p)
        parts.append("他チャンネル出演 " + "、".join(who))
    with open(WORK + "/notify.txt", "w", encoding="utf-8") as f:
        f.write(("NEW:YouTube新着: " + " / ".join(parts) + " — 要約ができました。") if parts else "NONE")

    print("applied channels:", len(new_channels), "| applied appearances:", len(new_apps),
          "| skipped:", len(skipped), "| unresolved:", len(unresolved))
    for s in skipped:
        print("  skip:", s)
    for u in unresolved:
        print("  UNRESOLVED(要約が無いので次回に持ち越し):", u)
    return 0


if __name__ == "__main__":
    sys.exit(main())
