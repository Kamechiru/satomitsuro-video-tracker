"""登録した人物(state.json の people)が「本人のチャンネル以外」に出演している直近の動画を
YouTube検索(新着順)で探し、work/pending.json に kind="appearance" として追記する。

本人のチャンネルが検索上位を占めるため、「対談」「ゲスト」「出演」等を足した複数クエリで探す。
実際に出演しているかの最終判断は字幕を読んだ後に行う(出演していなければ .skip を書く)。
"""
import json
import random
import re
import sys
import time
import urllib.parse

from common import (WORK, curl, duration_seconds, ensure_work, load_state,
                    relative_days, relative_to_iso)

WINDOW_DAYS = 14        # これより古い動画は対象外
MAX_PER_PERSON = 4      # 1回の実行で人物ごとに拾う上限
MAX_TOTAL = 10          # 1回の実行で拾う総数の上限
MIN_SECONDS = 180       # 3分未満(ショート等)は対象外
MODIFIERS = ["対談", "ゲスト", "出演", "コラボ", "インタビュー"]
CLIP_RE = re.compile(r"切り抜き|切抜|クリップ|まとめ|shorts|ショート", re.I)


def search(query):
    url = ("https://www.youtube.com/results?search_query="
           + urllib.parse.quote(query) + "&sp=CAI%253D")      # 新着順
    for _ in range(3):
        status, body = curl(url)
        m = re.search(r"var ytInitialData = (\{.*?\});</script>", body, re.S)
        if status == 200 and m:
            try:
                data = json.loads(m.group(1))
                break
            except ValueError:
                pass
        time.sleep(random.uniform(2, 4))
    else:
        return None

    found = []

    def walk(o):
        if isinstance(o, dict):
            if "videoRenderer" in o:
                found.append(o["videoRenderer"])
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    walk(data)
    out = []
    for v in found:
        runs = v.get("ownerText", {}).get("runs", [{}])
        owner = "".join(r.get("text", "") for r in runs)
        cid = runs[0].get("navigationEndpoint", {}).get("browseEndpoint", {}).get("browseId")
        title = "".join(r.get("text", "") for r in v.get("title", {}).get("runs", []))
        snip = "".join(r.get("text", "") for s in v.get("detailedMetadataSnippets", [])
                       for r in s.get("snippetText", {}).get("runs", []))
        when = v.get("publishedTimeText", {}).get("simpleText")
        out.append({"video_id": v["videoId"], "title": title, "owner": owner, "cid": cid,
                    "when": when, "length": v.get("lengthText", {}).get("simpleText"),
                    "snippet": snip})
    return out


def main():
    ensure_work()
    state = load_state()
    pending_path = WORK + "/pending.json"
    try:
        with open(pending_path, encoding="utf-8") as f:
            pending = json.load(f)
    except (OSError, ValueError):
        pending = {"items": []}

    known = set(state.get("appearance_checked_ids", []))
    known |= {a["video_id"] for a in state.get("appearances", [])}
    known |= {it["video_id"] for it in pending["items"]}
    # 各登録チャンネルの最新動画は「本人の動画」なので出演扱いにしない
    known |= {c.get("last_video_id") for c in state["channels"]}

    candidates = {}
    for person in state.get("people", []):
        aliases = person.get("aliases") or [person["name"]]
        own_ids = set(person.get("own_channel_ids", []))
        own_names = person.get("own_name_contains") or aliases
        results, ok = {}, 0
        queries = list(aliases) + [person["name"] + " " + m for m in MODIFIERS]
        for q in queries:
            res = search(q)
            time.sleep(random.uniform(1.5, 2.5))
            if res is None:
                continue
            ok += 1
            for r in res:
                results.setdefault(r["video_id"], r)
        if ok == 0:
            print("WARNING: 検索に全て失敗:", person["name"])
            continue
        picked = []
        for r in results.values():
            days = relative_days(r["when"])
            secs = duration_seconds(r["length"])
            hay = r["title"] + " " + r["snippet"]
            if r["video_id"] in known:
                continue
            if days is None or days > WINDOW_DAYS:
                continue
            if secs is None or secs < MIN_SECONDS:
                continue
            if (r["cid"] in own_ids) or any(n in r["owner"] for n in own_names):
                continue
            if CLIP_RE.search(r["title"]) or CLIP_RE.search(r["owner"]):
                continue
            if not any(a in hay for a in aliases):
                continue
            picked.append((days, r))
        picked.sort(key=lambda x: x[0])
        for days, r in picked[:MAX_PER_PERSON]:
            c = candidates.setdefault(r["video_id"], {"r": r, "days": days, "persons": []})
            if person["name"] not in c["persons"]:
                c["persons"].append(person["name"])

    chosen = sorted(candidates.values(), key=lambda c: c["days"])[:MAX_TOTAL]
    for c in chosen:
        r = c["r"]
        pending["items"].append({
            "kind": "appearance", "persons": c["persons"], "video_id": r["video_id"],
            "title": r["title"], "url": "https://www.youtube.com/watch?v=" + r["video_id"],
            "host_channel": r["owner"], "host_channel_id": r["cid"],
            "published": relative_to_iso(r["when"]), "duration": r["length"],
            "snippet": r["snippet"][:160]})
    with open(pending_path, "w", encoding="utf-8") as f:
        json.dump(pending, f, ensure_ascii=False, indent=2)
    print("appearance candidates:", len(chosen))
    for c in chosen:
        r = c["r"]
        print("  +", "/".join(c["persons"]), "|", r["owner"], "|", r["title"][:50],
              "|", r["video_id"], "|", r["when"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
