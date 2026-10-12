"""state.json から dashboard.html の `const CHANNELS_DATA = {...};` ブロックだけを書き換える。

文字列の位置検索+連結で差し替える(正規表現の置換文字列は `\\n` を実改行に変えてしまうので使わない)。
"""
import json
import os
import sys

from common import REPO, load_state

PATH = os.path.join(REPO, "dashboard.html")


def js(obj):
    # </script> 等で <script> が閉じてしまわないよう "</" をエスケープ
    return json.dumps(obj, ensure_ascii=False).replace("</", "<\\/")


def main():
    state = load_state()
    channels = [{"name": c["name"], "isNew": bool(c.get("new_in_last_check")),
                 "videoTitle": c.get("last_video_title", ""), "videoUrl": c.get("last_video_url", ""),
                 "published": c.get("last_video_published", ""), "failed": bool(c.get("check_failed")),
                 "summary": c.get("last_summary")} for c in state["channels"]]
    apps = [{"persons": a["persons"], "title": a["title"], "url": a["url"],
             "hostChannel": a["host_channel"], "published": a["published"],
             "summary": a.get("summary")} for a in state.get("appearances", [])]

    lines = ["  const CHANNELS_DATA = {",
             "    checkedAt: %s," % js(state.get("last_checked_at", "")),
             "    channels: ["]
    lines += ["      " + js(c) + "," for c in channels]
    lines += ["    ],", "    appearances: ["]
    lines += ["      " + js(a) + "," for a in apps]
    lines += ["    ]", "  };"]
    block = "\n".join(lines)

    with open(PATH, encoding="utf-8") as f:
        html = f.read()
    start = html.index("  const CHANNELS_DATA = {")
    end_marker = "\n  };"
    end = html.index(end_marker, start) + len(end_marker)
    new_html = html[:start] + block + html[end:]
    with open(PATH, "w", encoding="utf-8") as f:
        f.write(new_html)

    # 各要素は1行(JSONは実改行を出さない)のはず。ずれていたら壊れているので失敗させる
    assert block.count("\n") == len(lines) - 1, "CHANNELS_DATA に想定外の改行がある"
    print("dashboard.html updated: channels=%d appearances=%d" % (len(channels), len(apps)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
