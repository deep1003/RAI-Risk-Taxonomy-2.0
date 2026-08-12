#!/bin/bash
# 노트북을 Chrome으로 실행
# 사용법: bash run_notebook.sh [노트북경로]
#   기본값: Stage-2 (stage2_l3_mapping.ipynb)
#   Stage-1: bash run_notebook.sh reports/consolidation/v2_19_tier_design/three_tier_pipeline.ipynb
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

  Stage-2 실행 순서
    T0 → T1 → T2            설정 · Stage-1 세트/L3 로드 · 임베딩 변형 4종 (수 분)
    T3 → T4 → T4b → T4c     EM 엔진 · 1단계 자동배정 + 민감도 3축x2회 · hold 산출
    GATE-S2                 "대기" 뜨면 Claude에게 알림 → hold 심의
    T5 → T6                 2단계 강제배정 · 민감도 재현
    T7                      검증 + 산출물 + L3 분포 HTML

  결과 폴더
    data/experiments/stage2/out/

  서버 종료: kill $JPID     로그: tail -f /tmp/jupyter_stage1.log

EOF
