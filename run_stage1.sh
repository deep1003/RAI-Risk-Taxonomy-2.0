#!/bin/bash
# Stage-1 파이프라인 노트북을 Chrome으로 실행
# 사용법: bash run_stage1.sh
set -e
cd "$(dirname "$0")"
REPO="$(pwd)"
NB="${1:-reports/consolidation/v2_19_tier_design/stage2_l3_mapping.ipynb}"
PORT=8899

echo "repo: $REPO"
[ -f "$NB" ] || { echo "노트북 없음: $NB"; exit 1; }

# 의존성 확인
python3 -c "import scipy, sentence_transformers, matplotlib, jupyterlab" 2>/dev/null \
  || pip3 install -q scipy sentence-transformers matplotlib jupyterlab

# 기존 서버 정리
lsof -ti tcp:$PORT | xargs kill -9 2>/dev/null || true

# JupyterLab 백그라운드 기동 (자동 브라우저 열기 끔)
jupyter lab --no-browser --port=$PORT --ServerApp.token='' --ServerApp.password='' \
            --notebook-dir="$REPO" > /tmp/jupyter_stage1.log 2>&1 &
JPID=$!
echo "JupyterLab 기동 중 (pid $JPID, port $PORT)..."

# 서버 준비 대기
for i in $(seq 1 40); do
  curl -s "http://localhost:$PORT/api" > /dev/null && break
  sleep 0.5
done

URL="http://localhost:$PORT/lab/tree/$NB"
open -a "Google Chrome" "$URL" 2>/dev/null || open "$URL"

cat <<EOF

  Chrome에서 열림: $URL

  실행 순서
    S0 → S1 → S2            설정 · 로드 · 보호용어/수준 태깅
    GATE-1                  제거 승인 확인 (removals.json 준비됨)
    S3                      제거 40장 적용
    GATE-2                  정규화 결정 확인 (normalization.json 준비됨)
    S4 → S5                 정규화 적용 + 임베딩 재생성 (수 분 소요)
    GATE-3                  "대기" 뜨면 Claude에게 알림 → 통합 사전 생성
    S6                      덴드로그램 + tau 절단
    GATE-4                  "대기" 뜨면 Claude에게 알림 → 명명 검정
    S7 → S8                 세트 확정 + 검증 + Before/After HTML

  검토 HTML
    open $REPO/data/experiments/stage1/out/gate2_normalization_review.html

  서버 종료: kill $JPID     로그: tail -f /tmp/jupyter_stage1.log

EOF
