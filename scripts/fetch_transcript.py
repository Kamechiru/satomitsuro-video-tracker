"""字幕(文字起こし)と動画説明文を取得して work/transcripts/<id>.txt に保存する。

使い方: python3 scripts/fetch_transcript.py VIDEO_ID [--names 名前1,名前2]
 - 約60秒ごとに [mm:ss] の目印を入れる(話の構成・段落分けの手がかり)。
 - --names を渡すと、その名前が字幕に何回・どの時刻に出てくるかを表示する(出演判定用)。
 - 取得できない場合は "TRANSCRIPT_UNAVAILABLE: 理由" を表示して終了コード2。
"""
import json
import re
import sys
import time

from common import WORK, curl, ensure_work

MARK_EVERY = 60  # 秒


def mmss(sec):
    sec = int(sec)
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    return "%d:%02d:%02d" % (h, m, s) if h else "%02d:%02d" % (m, s)


def get_description(video_id):
    status, body = curl("https://www.youtube.com/watch?v=" + video_id)
    m = re.search(r'"shortDescription":"((?:[^"\\]|\\.)*)"', body)
    if not m:
        return ""
    try:
        return json.loads('"' + m.group(1) + '"')
    except ValueError:
        return ""


def main():
    args = sys.argv[1:]
    if not args:
        print("usage: fetch_transcript.py VIDEO_ID [--names a,b]")
        return 1
    video_id = args[0]
    names = []
    if "--names" in args:
        names = [n for n in args[args.index("--names") + 1].split(",") if n]
    ensure_work()

    from youtube_transcript_api import YouTubeTranscriptApi
    api = YouTubeTranscriptApi()
    transcript, err = None, None
    for attempt in range(3):
        try:
            transcript = api.fetch(video_id, languages=["ja", "ja-JP", "en"])
            break
        except Exception as e:  # 字幕無効・IPブロック・非公開など
            err = type(e).__name__ + ": " + str(e).strip().splitlines()[0][:120]
            if type(e).__name__ in ("TranscriptsDisabled", "VideoUnavailable",
                                    "VideoUnplayable", "NoTranscriptFound"):
                break
            time.sleep(4)
    desc = get_description(video_id)
    if transcript is None:
        print("TRANSCRIPT_UNAVAILABLE:", err)
        print("--- description (先頭1500字) ---")
        print(desc[:1500])
        return 2

    lines, next_mark, buf = [], 0, []
    for seg in transcript:
        if seg.start >= next_mark:
            if buf:
                lines.append("".join(buf))
                buf = []
            buf.append("[%s] " % mmss(seg.start))
            next_mark = (int(seg.start) // MARK_EVERY + 1) * MARK_EVERY
        buf.append(seg.text.replace("\n", " ") + " ")
    if buf:
        lines.append("".join(buf))
    full = "\n".join(lines)
    path = "%s/transcripts/%s.txt" % (WORK, video_id)
    with open(path, "w", encoding="utf-8") as f:
        f.write("# 動画説明文(先頭1500字)\n" + desc[:1500] + "\n\n# 字幕\n" + full + "\n")
    last = transcript[-1].start if len(transcript) else 0
    print("OK saved:", path)
    print("chars:", len(full), "| length ~", mmss(last))
    for n in names:
        hits = [mmss(seg.start) for seg in transcript if n in seg.text]
        print("name '%s': %d hits; first at %s" % (n, len(hits), ", ".join(hits[:5]) or "-"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
