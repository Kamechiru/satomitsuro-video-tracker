あなたは複数のYouTubeチャンネルの新着動画を検知して要約し、ステータスダッシュボードを更新するタスクを行う。作業ディレクトリはこのGitリポジトリ(satomitsuro-video-tracker)そのもの。state.json の channels 配列に監視対象の全チャンネルが、dashboard.html にダッシュボードのHTMLテンプレートが保存されている。

このマシンはローカル(住宅用IP)なので、YouTubeへのアクセス・字幕(文字起こし)取得ともに問題なく行える。

手順:
1. `git pull origin main` を実行し、最新の状態を取得する。
2. state.json を読み、channels 配列を取得する。
3. channels 配列の各チャンネルについて、以下を順番に実行する:
   a. `curl -s -A 'Mozilla/5.0' -H 'Accept-Language: ja-JP' "https://www.youtube.com/feeds/videos.xml?channel_id=<channel_id>"` でRSSフィードを取得し、最初の<entry>(最新動画)から yt:videoId, title, published(ISO8601そのまま)、動画URL(https://www.youtube.com/watch?v=VIDEOID)を抽出する。取得に失敗したら数秒待って1回だけリトライする。videoIdやタイトルは絶対に推測・捏造せず、実際に取得した値のみ使うこと。
   b. 取得したvideoIdがそのチャンネルの last_video_id と同じなら、new_in_last_check=false, check_failed=false として記録(last_video_*は更新しない)。
   c. RSS取得が最終的に失敗したら check_failed=true として記録(last_video_*やnew_in_last_checkは前回値のまま保持)。
   d. videoIdが異なる場合(新着動画あり):
      - `pip3 install --quiet youtube-transcript-api` を実行(既にインストール済みの可能性あり)。Pythonで字幕を取得する(このライブラリはバージョン1.x系のインスタンスAPIを使う):
        ```python
        from youtube_transcript_api import YouTubeTranscriptApi
        api = YouTubeTranscriptApi()
        transcript = api.fetch(VIDEO_ID, languages=['ja', 'ja-JP', 'en'])
        full_text = " ".join(seg.text for seg in transcript)
        ```
        日本語字幕が無ければ英語自動字幕にフォールバックしてよい。字幕が全く取得できない場合のみ、その旨を明記した上でタイトル情報のみで簡易要約する。
      - 字幕が取得できた場合、文字起こし全文を最初から最後まで通して読み、日本語で以下の形式の要約を作成する(動画を見なくても内容が具体的にわかることが目的なので、簡潔にまとめすぎず、詳細に書くこと):
        - 冒頭にチャンネル名・動画タイトル・URL・公開日時・(わかれば)動画の形式や長さ
        - 冒頭に「この動画は何の話か(ひとことで)」を1〜2文で
        - その後、**動画の実際の話の流れ(構成・段落・話題の区切り)に沿って、話が展開する順番通りに区切り、区切りごとに見出しをつけて詳細にまとめる**。話者が独自にカテゴリ分けしたり時系列を並べ替えたりせず、実際にその順番で話されていた通りの構成を保つこと。各区切りには、具体的な発言内容・エピソード・数字・比喩・引用などをできるだけ盛り込み、読むだけでその部分で何が語られたか具体的にわかるようにする。区切りの数は動画の内容量に応じて自然に決めてよい(短い動画なら少なく、長い配信なら多くなってよい)。
        - 最後に「まとめ」として、動画全体を通して一貫しているメッセージや結論を1段落でまとめる。
      - state.json のそのチャンネルの項目を更新: last_video_id, last_video_title, last_video_url, last_video_published, new_in_last_check=true, check_failed=false, **last_summary=(今作成した要約テキスト全文をそのまま文字列として)**。
      - この動画の要約テキストを `new_summaries.txt` というファイルに追記する(チャンネル名の見出し付きで)。
4. 全チャンネルの処理が終わったら、state.json の last_checked_at(現在UTC時刻)を更新する。
5. dashboard.html を開き、JavaScript内の `const CHANNELS_DATA = {...}` のブロックを、最新のstate.jsonの内容で中身を完全に置き換える(HTML構造やCSSは一切変更しない、このJSONデータ部分のみ更新する)。checkedAtフィールドにはstate.jsonのlast_checked_atを、channels配列の各要素にはname, isNew(=new_in_last_check), videoTitle(=last_video_title), videoUrl(=last_video_url), published(=last_video_published), failed(=check_failed), **summary(=last_summary、無ければnull)**を対応させる。dashboard.htmlのUIには既に「詳細な要約を読む」という展開ボタン(`.summary-toggle`/`.summary-body`)が実装済みなので、summaryフィールドにテキストを入れるだけでよい(HTML/CSS/JSのロジック部分は一切変更しないこと)。

   **重要な注意(過去にバグが発生した箇所)**: summaryフィールドの値には改行を含む長いテキストが入る。CHANNELS_DATAブロックを書き換える際は、必ずPythonで `json.dumps(obj, ensure_ascii=False)` を使って各チャンネルのオブジェクトをJS用の文字列に変換し、それをファイルに書き込むこと。その際、`re.sub(pattern, replacement_string, text)` のように**置換文字列を直接re.subに渡してはいけない**(Pythonの正規表現モジュールは置換文字列中の `\n` を実際の改行バイトに変換してしまうバグを誘発する)。必ず `re.sub(pattern, lambda m: replacement_string, text)` のように**関数(lambda)経由で置換する**か、あるいは単純に文字列の分割・結合(`text.split(marker)` など正規表現を使わない方法)でファイル全体を組み立てること。書き込み後は、`grep -c $'\n'` 等でCHANNELS_DATAブロック内の実改行数が想定より大幅に多くないか(15行前後のはず)を確認し、異常に多い場合は書き直すこと。
6. `git add state.json dashboard.html` / commit(例: "Update state and dashboard: <日時>")/ `git push origin main` する(新着が1件もなかった場合でもこのコミットは必ず行う)。pushするとGitHub Pages(https://kamechiru.github.io/satomitsuro-video-tracker/dashboard.html)が自動的に更新される。
7. 新着動画が1件以上あった場合は、`notify_status.txt` というファイルに以下の1行を書き込む(既存の内容は上書きする):
   `NEW:YouTube新着: <チャンネル名をカンマ区切りで列挙> — 要約ができました。`
   新着が1件もなかった場合は、`notify_status.txt` に `NONE` とだけ書き込む。
8. 最終的な返答として、日本語で以下を出力する:
   - 新着があった動画: チャンネルごとに上記の要約
   - 新着が無かったチャンネル: チャンネル名を一覧で短く列挙
   - 取得に失敗したチャンネルがあれば、その旨を明記

注意: 出力は必ず日本語。実在しない情報を作らないこと。チャンネルは10個程度あるので、1つずつ確実に処理すること。dashboard.htmlのHTML/CSS部分は絶対に壊さず、CHANNELS_DATAの中身のみを書き換えること。手順7の notify_status.txt は必ず作成・更新すること(呼び出し元スクリプトがこれを読んで通知を出す)。
