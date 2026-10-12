"""監視チャンネルの最新動画を取得し、前回から変わっていれば work/pending.json に積む。

最新動画の判定:
 1. RSS(feeds/videos.xml)が最も正確(公開順)。ただし間欠的に404/500を返すので、
    チャンネルフィード → アップロード再生リストフィードの順に最大5回試す。
 2. RSSが全滅したときのフォールバック: チャンネルの /videos と /streams ページの動画一覧から、
    「経過時間が最小のもの」を最新とみなす(先頭に固定表示された古い動画を避けるため、先頭=最新とは考えない)。
    経過時間は「3 日前」程度の粗さで、ショート動画は含まれない。 -> pending に source="page" を付ける。
"""
import datetime
import html
import json
import random
import re
import sys
import time
import xml.etree.ElementTree as ET

from common import (WORK, curl, ensure_work, iso_z, load_state, now_utc,
                    relative_days, relative_to_iso, save_state)

NS = {"a": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015"}


def fetch_rss(channel_id):
    urls = ["https://www.youtube.com/feeds/videos.xml?channel_id=" + channel_id]
    if channel_id.startswith("UC"):
        urls.append("https://www.youtube.com/feeds/videos.xml?playlist_id=UU" + channel_id[2:])
    for attempt in range(5):
        status, body = curl(urls[attempt % len(urls)])
        if status == 200 and "<entry>" in body:
            try:
                e = ET.fromstring(body).find("a:entry", NS)
                vid = e.find("yt:videoId", NS).text
                return {"video_id": vid,
                        "title": html.unescape(e.find("a:title", NS).text or ""),
                        "published": e.find("a:published", NS).text,
                        "url": "https://www.youtube.com/watch?v=" + vid,
                        "source": "rss"}
            except Exception:
                pass
        time.sleep(random.uniform(2, 4))
    return None


def page_videos(channel_id, tab):
    status, body = curl("https://www.youtube.com/channel/%s/%s" % (channel_id, tab))
    m = re.search(r"var ytInitialData = (\{.*?\});</script>", body, re.S)
    if status != 200 or not m:
        return []
    try:
        data = json.loads(m.group(1))
    except ValueError:
        return []
    out = []

    def walk(o):
        if isinstance(o, dict):
            lv = o.get("lockupViewModel")
            if lv and lv.get("contentType") == "LOCKUP_CONTENT_TYPE_VIDEO":
                md = lv.get("metadata", {}).get("lockupMetadataViewModel", {})
                title = md.get("title", {}).get("content", "")
                texts = [p.get("text", {}).get("content", "")
                         for row in md.get("metadata", {}).get("contentMetadataViewModel", {})
                         .get("metadataRows", []) for p in row.get("metadataParts", [])]
                when = next((t for t in texts if relative_days(t) is not None), None)
                if lv.get("contentId") and when:
                    out.append({"video_id": lv["contentId"], "title": title, "when": when})
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    walk(data)
    return out


def fetch_from_pages(channel_id):
    items = page_videos(channel_id, "videos") + page_videos(channel_id, "streams")
    if not items:
        return None
    best = min(items, key=lambda x: relative_days(x["when"]))  # 同点は先に出たもの
    return {"video_id": best["video_id"], "title": best["title"],
            "published": relative_to_iso(best["when"]),
            "url": "https://www.youtube.com/watch?v=" + best["video_id"],
            "source": "page", "age_days": relative_days(best["when"])}


def main():
    ensure_work()
    state = load_state()
    items, failed, unchanged, notes = [], [], [], []
    for ch in state["channels"]:
        latest = fetch_rss(ch["channel_id"])
        if latest is None:
            latest = fetch_from_pages(ch["channel_id"])
            if latest is not None:
                notes.append("%s: RSS失敗 -> 一覧ページで代替" % ch["name"])
                # 既知の最新動画より古いものを「新着」と誤検知しないための安全弁
                if ch.get("last_video_id"):
                    last_age = (now_utc() - datetime.datetime.fromisoformat(
                        ch["last_video_published"].replace("Z", "+00:00"))).total_seconds() / 86400
                    if latest["age_days"] > last_age + 0.5:
                        latest["video_id"] = ch["last_video_id"]
        if latest is None:
            ch["check_failed"] = True
            failed.append(ch["name"])
            continue
        ch["check_failed"] = False
        if latest["video_id"] == ch.get("last_video_id"):
            ch["new_in_last_check"] = False
            unchanged.append(ch["name"])
        else:
            items.append({"kind": "channel", "channel_id": ch["channel_id"],
                          "channel_name": ch["name"],
                          **{k: v for k, v in latest.items() if k != "age_days"}})
        time.sleep(1)
    save_state(state)
    with open(WORK + "/pending.json", "w", encoding="utf-8") as f:
        json.dump({"generated_at": iso_z(now_utc()), "items": items}, f,
                  ensure_ascii=False, indent=2)
    print("NEW channel videos:", len(items))
    for it in items:
        print("  +", it["channel_name"], "|", it["title"], "|", it["video_id"], "|", it["source"])
    print("unchanged:", ", ".join(unchanged) or "-")
    print("FAILED:", ", ".join(failed) or "-")
    for n in notes:
        print("NOTE:", n)
    return 0


if __name__ == "__main__":
    sys.exit(main())
