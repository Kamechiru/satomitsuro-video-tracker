# satomitsuro-video-tracker

さとうみつろうさんのYouTube公式チャンネル(哲理学作家さとうみつろう『神さまとのおしゃべり』チャンネル、
channel_id: `UC-N7pA0rR1PrUBOfs2OA0oA`、ハンドル `@mitsu-low`)の新着動画を毎日自動チェックし、
新着があれば字幕から要約するために、`state.json` に「最後にチェックした動画ID」を保存するための
状態管理専用リポジトリです。

このリポジトリは Claude Code の定期実行ルーティン(cloud routine)から更新されます。
