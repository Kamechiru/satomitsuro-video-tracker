# YouTube新着チェック＆要約(毎朝6時のルーティン)

作業フォルダ: `/Users/kameyamakenta/satomitsuro-video-tracker`(コマンドは最初に必ず `cd` してから実行する)。
このタスクは無人で実行される。確認を求めて止まらず、最後まで実行すること。

## 目的
ユーザーは「動画を見なくても内容が具体的にわかる」ことを求めている。次の2種類を検出して、字幕から詳細に要約する。
1. **監視チャンネルの新着動画** — `state.json` の `channels`(さとうみつろう / ひすいこたろう / 崔の店長日誌=崔燎平 / UP&UP / 南山紘輝)
2. **他チャンネルでの出演動画** — `state.json` の `people`(さとうみつろう / ひすいこたろう / 崔燎平 / 南山紘輝)が、本人のチャンネル以外(対談・ゲスト・コラボ・インタビュー等)に出演している直近14日以内の動画

検出・保存・ダッシュボード生成は `scripts/` のスクリプトが行う。**あなたの仕事は、字幕を読んで要約を書くことと、出演の最終判断だけ。**
`state.json` と `dashboard.html` は手で編集しない(必ずスクリプト経由)。

## 手順
承認が必要なコマンドを減らすため、コマンドは次の3種類だけを使う(いずれも絶対パス。`cd` や `&&` で連結しない)。

1. **準備**: `python3 /Users/kameyamakenta/satomitsuro-video-tracker/scripts/prepare.py`
   最新化(git pull)・`work/` の初期化・新着チェック・他チャンネルへの出演検索をまとめて行い、`work/pending.json` の内容を表示する。2〜5分かかる(YouTubeのRSSが不安定なため自動でリトライ/代替取得する)。
2. `pending.json` の `items` が空なら手順4へ進む。空でなければ、`items` を**1件ずつ順番に**(並列にしない。YouTubeの制限を避けるため)処理する:
   - 字幕取得: `python3 /Users/kameyamakenta/satomitsuro-video-tracker/scripts/fetch_transcript.py <video_id>`(`kind` が `appearance` のときは `--names 人物名,別名` も付ける。人物名・別名は `state.json` の `people` を参照)。
   - `OK` なら `/Users/kameyamakenta/satomitsuro-video-tracker/work/transcripts/<video_id>.txt`(動画説明文＋約60秒ごとに `[mm:ss]` 付きの字幕)を**最初から最後まで通して読む**。
   - 要約を Write ツールで `/Users/kameyamakenta/satomitsuro-video-tracker/work/summaries/<video_id>.txt` に書く(形式は下記)。
   - `kind` が `appearance` で、**本人が実際には出演していない**(名前が出るだけ・無関係・他人の切り抜きや転載・本人チャンネルの別名義など)と判断したら、要約は書かず `work/summaries/<video_id>.skip` に理由を1行で書く。字幕中の名前の出現回数が0でも、自動字幕は固有名詞を誤変換するので、それだけで不出演とは判断しない(タイトル・説明文・文脈で判断する)。
   - `TRANSCRIPT_UNAVAILABLE`(字幕なし・取得不可)の場合: `channel` は表示された説明文とタイトルから簡易要約を書き、冒頭に「※字幕が取得できなかったため、タイトルと説明文のみに基づく簡易的な要約です。」と明記する。`appearance` は説明文だけで出演が明確なときに限り同様に簡易要約、不明なら `.skip`。
3. すべての `items` を処理したら **仕上げ**: `python3 /Users/kameyamakenta/satomitsuro-video-tracker/scripts/finish.py`
   要約の反映(`state.json`)・ダッシュボード生成・`git commit`/`push`(新着が0件でも必ずコミット。GitHub Pages: https://kamechiru.github.io/satomitsuro-video-tracker/dashboard.html が自動更新される)・デスクトップ通知(新着があるときだけ。terminal-notifier)までを行う。要約を書かなかった `channel` 項目は次回の実行で再検出される。
4. 最終回答を出力する(下記)。

## 要約の形式(`work/summaries/<video_id>.txt`)
ダッシュボードにそのまま表示するので**プレーンテキスト**(`**`や`#`などのMarkdown記法は使わない)。簡潔にまとめすぎず、詳細に書く。
- 冒頭: チャンネル名 / 動画タイトル / URL / 公開日時 / 形式(通常動画・ライブ配信・ショート・対談など)と長さ。
- 「この動画は何の話か」を1〜2文で。
- **動画の実際の話の流れ(構成・段落・話題の区切り)に沿って、話された順番通りに区切り、区切りごとに `【見出し (mm:ss〜)】` を付けて詳細にまとめる。** 話者の主張・エピソード・数字・比喩・引用を具体的に盛り込み、読むだけでその部分で何が語られたか分かるようにする。区切りは字幕の `[mm:ss]` と説明文のチャプターを手がかりに、話題が変わるところで切る。独自のカテゴリに並べ替えない。区切りの数は内容量に応じて決める。
- 最後に `【まとめ】` として、動画全体を貫くメッセージを1段落で。
- `appearance` の場合は、冒頭に「<人物>が<ホストチャンネル>に出演(対談/ゲスト/コラボ等)。ホスト: …、共演者: …」を書き、**本人が話している・関わっている部分を特に詳しく**(本人の主張・エピソード・質問への回答)まとめる。
- 事実だけを書く。字幕の誤変換は文脈で補正してよいが、推測は推測と明記する。

## 最終回答(=ルーティンの実行結果ページに表示される。ここで読めるようにする)
長くなってよい。次の順で日本語で出力する。
1. 新着動画ごと: `work/summaries/` に書いた要約の**全文**(チャンネル名の見出し付き)。
2. 他チャンネルでの出演動画ごと: 同様に要約の全文。`.skip` にしたものは「除外: タイトル — 理由」を1行ずつ。
3. 新着が無かったチャンネル名の一覧、取得に失敗したチャンネルや注意点(RSS失敗で代替取得した等)。
4. ダッシュボードのURL: https://kamechiru.github.io/satomitsuro-video-tracker/dashboard.html
新着も出演も無かった場合は「新着なし」と上記3〜4を短く書くだけでよい。

## 注意
- スクリプトがエラーで止まったら、エラー内容を最終回答に書き、できる範囲で続行する(`state.json` は壊さない)。`youtube_transcript_api` が無ければ `pip3 install --quiet youtube-transcript-api`。
- `last_summary` の書き込みや `dashboard.html` の `CHANNELS_DATA` の書き換えを自分でやらない(過去に `re.sub` の置換文字列で `\n` が実改行になり壊れたため、`scripts/build_dashboard.py` に任せる)。
- 監視対象の追加・削除は `state.json` の `channels` / `people` を編集して push する(削除したチャンネルは `archived_channels` に残してある)。
