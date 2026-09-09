#!/usr/bin/env bash
# Pack apps/sunset-stereo/dist for Stake Engine ACP upload.
# Engine requires static files only (index.html at the game root, relative URLs, no external fonts).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
DIST="$ROOT/apps/sunset-stereo/dist"
STAGE="$ROOT/publish/STAKE_UPLOAD"
ZIP="$ROOT/publish/Sunset-Stereo-frontend.zip"

if [[ ! -f "$DIST/index.html" ]]; then
  echo "missing $DIST/index.html — run: make frontend-build" >&2
  exit 1
fi

rm -rf "$STAGE/frontend"
mkdir -p "$STAGE/frontend"
cp -a "$DIST"/. "$STAGE/frontend/"

cat > "$STAGE/КАК_ЗАЛИТЬ.txt" <<'EOF'
Sunset Stereo — что заливать в Stake Engine ACP
==============================================

MATH: 1 000 000 книг, ~95% RTP, потолок 15000×.
FRONTEND: статический Vite-билд (base="./"), без внешних шрифтов.

1) MATH
   Скачай: http://13.143.132.112:1337/Sunset-Stereo-math.zip
   Распакуй в Z:\ — получится Z:\Sunset Stereo\math
   В ACP выбери папку math. В ней ровно три файла:
     index.json
     books_base.jsonl.zst
     lookUpTable_base_0.csv

2) FRONTEND
   Скачай: http://13.143.132.112:1337/Sunset-Stereo-frontend.zip
   Распакуй в Z:\ — получится Z:\Sunset Stereo\frontend
   В ACP выбери папку frontend. В ней должны быть:
     index.html
     assets\
     audio\
     sunset-scene.jpg
   Не грузи внешние шрифты и не оборачивай папку ещё одним корнем.

3) Игра в ACP
   Game id: sunset_stereo
   После заливки открывай из play modal — Engine сам подставит
   sessionID, rgs_url, lang, device.

   CDN:
   https://{team}.cdn.stake-engine.com/sunset_stereo/{version}/index.html?sessionID=…&rgs_url=…&lang=en&device=desktop

4) Replay (для ревью)
   ?replay=true&game=sunset_stereo&version=…&mode=base&event={bookId}&rgs_url=…

Не лей:
  games/_inactive_sunset_stereo_5x3
  frontend/  (старый 5x3 DOM)
  lookUpTable_bonus_*
EOF

rm -f "$ZIP"
STAGE_ZIP="$(mktemp -d)"
mkdir -p "$STAGE_ZIP/Sunset Stereo"
cp -a "$STAGE/frontend" "$STAGE_ZIP/Sunset Stereo/frontend"
cp -a "$STAGE/КАК_ЗАЛИТЬ.txt" "$STAGE_ZIP/Sunset Stereo/КАК_ЗАЛИТЬ.txt"
(
  cd "$STAGE_ZIP"
  zip -r -q "$ZIP" "Sunset Stereo"
)
rm -rf "$STAGE_ZIP"
echo "wrote $ZIP ($(du -h "$ZIP" | cut -f1))"
echo "ACP folder: $STAGE/frontend"
