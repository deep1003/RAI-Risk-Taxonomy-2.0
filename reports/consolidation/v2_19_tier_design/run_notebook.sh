#!/bin/bash
# 3-Tier Pipeline 노트북 실행 스크립트
# 사용법: bash reports/consolidation/v2_19_tier_design/run_notebook.sh
set -e
cd "$(dirname "$0")/../../.."   # repo root로 이동
echo "repo root: $(pwd)"

# 의존성 확인 (없으면 설치)
python3 -c "import scipy, sentence_transformers, matplotlib, jupyter" 2>/dev/null || \
  pip3 install scipy sentence-transformers matplotlib jupyterlab

# JupyterLab에서 노트북 열기 (브라우저 자동 오픈)
exec jupyter lab reports/consolidation/v2_19_tier_design/three_tier_pipeline.ipynb
