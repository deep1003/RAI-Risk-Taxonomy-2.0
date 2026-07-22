# v2.17.0-rc 작업 기록 (2026-07-22, Claude 세션)

## 수행 내용
1. 정의 검토 패스 (비Physical 1,529 대상, Physical 182 바이트 동일 유지)
   - v2.16.0 remediation audit의 title_definition_rewrite_candidate 147건 전량을 메커니즘 중심 EN·KO 정의로 재작성
   - 비서술적 라벨 16건 개명 (원 라벨은 definition_revision.original_label_en에 보존)
   - 나머지 카드 기계적 정정 187건 (하이픈 줄바꿈 잔재, 문말 마침표, 중복 토큰)
   - 검증된 거버넌스 레퍼런스 5건 부착 (NIST AI 100-1, OWASP LLM Top 10 2025. URL 2026-07-22 실접속 확인)
   - 모든 수정 human_review_status=pending, 원문 보존
2. 가드 적용 constrained-EM 재배치 (TR §3.7)
   - S=0.60c+0.30d+0.10w, 개선≥0.020, 키워드 코사인≥0.015, Agentic 필요조건, Physical 잠금
   - 목적지별 정의 가드 추가 구현 (generic shared term 'harm' 등에 의한 오배치 차단). 무가드 대조 실행 47건 → 가드 적용 22건
   - 이동 22건 전건 decision_required=true (신규 HOLD 14, 기존 HOLD 8). HOLD 큐 720 → 734
3. 신뢰성 검증 재실행 (TR §7 절차, encoder-transfer)
   - 샌드박스에서 BGE-M3 확보 불가(HF 스로틀링) → multilingual-e5-small로 동일 절차 수행
   - BGE-M3 수치와 직접 비교 불가. 단 비무작위 구조(perm p=0.0002)와 HOLD 분리 효과는 제2 인코더에서도 재현
   - 전체 top-1 60.2→60.3%, non-HOLD 72.0→72.9% (재배치 영향은 미미, 개별 카드 교정이 목적)
4. Technical Report 갱신
   - reports/latex/..._en.tex에 §7.8, §7.9 (v2.17.0-rc 개정·가드 감사·encoder-transfer 신뢰성) 추가
   - 샌드박스 폰트 대체 미리보기 PDF: reports/pdf/..._en_v217rc_preview.pdf (19p)
   - 정식 PDF는 Mac에서 재컴파일 필요 (Times New Roman/Arial/Menlo)

## 산출물 위치
- public/data/releases/v2.17.0-rc/{cards.json, manifest.json, revision_changelog.json}
- public/data/releases/v2.17.0-rc/card_embeddings_multilingual_e5_small.npy (+meta) — 최종 정의 기준 1,711 임베딩
- reports/validation/v2_17_0_rc_audit_e5_guarded/ — 이동 제안, 최종 배치, 신뢰성 지표
- reports/validation/v2_17_0_rc_audit_e5/ — 무가드 대조 실행 (보존)
- scripts/run_v2_17_audit_pipeline.py — BGE-M3로 재실행용 (python3 scripts/run_v2_17_audit_pipeline.py BAAI/bge-m3)

## 백업·원복
- 전체 백업: /Users/deep1003/data3/rai_taxonomy_backups/RAI-Risk-Taxonomy_pre_v2.17_20260722.tar.gz (.git·tmp 제외, v2.16.0 미커밋 상태 포함)
- 원복: tex는 `git checkout -- reports/latex/rai_risk_taxonomy_technical_report_2_0_en.tex`, 신규 폴더(v2.17.0-rc, *_audit_e5*, 스크립트, 본 노트) 삭제
- v2.16.0 데이터는 일절 수정하지 않음

## 커밋 안내 (사용자 직접 수행)
- 검토 후: `git add public/data/releases/v2.17.0-rc reports/validation/v2_17_0_rc_audit_e5_guarded reports/validation/v2_17_0_rc_audit_e5 scripts/run_v2_17_audit_* reports/latex/rai_risk_taxonomy_technical_report_2_0_en.tex reports/V2_17_0_RC_RELEASE_NOTES.md && git commit -m "Add v2.17.0-rc definition revision and guarded constrained-EM audit" && git push`
- 주의: index.html, assets/site.js의 기존 수정분(v2.16.0 작업)은 이 세션에서 건드리지 않았으므로 별도 판단
