#!/bin/bash
# 덴드로그램 시뮬레이션 notebook을 Jupyter Lab으로 띄운다.
# 사용법: ./run_notebook.sh          (브라우저 자동 오픈)
#        ./run_notebook.sh --exec    (headless 일괄 실행 후 결과 저장)

DIR="/Users/deep1003/data3/RAI-Risk-Taxonomy/reports/consolidation/simulation"
NB="dendrogram_simulation_1660.ipynb"
PY="/opt/anaconda3/bin"

cd "$DIR" || exit 1

# ollama 구동 확인 (BGE-M3 임베딩에 필요)
if ! curl -s http://localhost:11434/api/tags >/dev/null; then
  echo "[warn] ollama가 실행 중이 아닙니다. 'ollama serve' 먼저 실행하세요."
fi

if [ "$1" = "--exec" ]; then
  "$PY/jupyter" nbconvert --to notebook --execute --inplace "$NB" \
    --ExecutePreprocessor.timeout=3600 && \
  "$PY/jupyter" nbconvert --to html "$NB" && \
  echo "실행 완료: $DIR/$NB (+ HTML 리포트)"
else
  "$PY/jupyter" lab "$NB"
fi
