"""共通ユーティリティ(state.json の読み書き、curl、相対時刻の解釈)。"""
import datetime
import json
import os
import re
import subprocess

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_PATH = os.path.join(REPO, "state.json")
WORK = os.path.join(REPO, "work")
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")


def now_utc():
    return datetime.datetime.now(datetime.timezone.utc)


def iso_z(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def load_state():
    with open(STATE_PATH, encoding="utf-8") as f:
        return json.load(f)


def save_state(state):
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
        f.write("\n")


def ensure_work():
    for sub in ("", "summaries", "transcripts"):
        os.makedirs(os.path.join(WORK, sub), exist_ok=True)


def curl(url, timeout=40):
    """(HTTPステータス, 本文) を返す。失敗時は (0, '')。"""
    try:
        p = subprocess.run(
            ["curl", "-sL", "-A", UA, "-H", "Accept-Language: ja-JP",
             "-w", "\n__HTTP__%{http_code}", url],
            capture_output=True, timeout=timeout)
    except Exception:
        return 0, ""
    out = p.stdout.decode("utf-8", "ignore")
    body, _, code = out.rpartition("\n__HTTP__")
    try:
        return int(code), body
    except ValueError:
        return 0, ""


_UNIT_DAYS = {"秒": 1 / 86400, "分": 1 / 1440, "時間": 1 / 24, "日": 1,
              "週間": 7, "か月": 30, "ヶ月": 30, "年": 365}


def relative_days(text):
    """「3 日前」「2 週間前 に配信済み」等 -> 経過日数(float)。解釈不能は None。"""
    if not text:
        return None
    m = re.search(r"(\d+)\s*(秒|分|時間|日|週間|か月|ヶ月|年)\s*前", text)
    if not m:
        return None
    return int(m.group(1)) * _UNIT_DAYS[m.group(2)]


def relative_to_iso(text):
    d = relative_days(text)
    if d is None:
        return iso_z(now_utc())
    return iso_z(now_utc() - datetime.timedelta(days=d))


def duration_seconds(text):
    """「1:19:53」「31:49」-> 秒。ライブ中などで無ければ None。"""
    if not text:
        return None
    parts = text.strip().split(":")
    try:
        nums = [int(p) for p in parts]
    except ValueError:
        return None
    sec = 0
    for n in nums:
        sec = sec * 60 + n
    return sec
