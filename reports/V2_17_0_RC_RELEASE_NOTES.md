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

## 추가 작업 (2026-07-22 야간, 논문판 재구성)
- **논문판 신규 파일**: `reports/latex/rai_risk_taxonomy_technical_report_2_0_en_paper.tex` → `reports/pdf/..._en_paper.pdf` (24p). 기존 `..._en.tex`(v2.17.1 상태)는 무수정 보존
- 구조: Introduction / Evidence corpus / Classification methodology / Results / Discussion / Conclusion + Appendix A(버전 이력) B(HOLD 정책) C(탐색적 분석: L3 후보·반사실 시뮬레이션·벡터공간) D(과거 신뢰성 결과) E(반올림 정책)
- 중복 제거: 신뢰성 표는 v2.17 BGE-M3 표를 본문 대표로, v2.12/2.14/2.15 표·그림은 Appendix D로 이동. HOLD 사유 표는 v2.17(본문)과 v2.12(부록) 각 1회만
- 한글 깨짐 해결: 플랫폼 감지 폰트 폴백(Mac은 Times/Apple SD Gothic Neo, 그 외 TeX Gyre/Noto CJK) + 한글 구간 \ko{} 래핑. 표 넘침은 tabularx 전환·\small로 해결 (잔여 overfull 2.5pt 1건)
- Discussion 5.3에 cross-cutting risk / category overlap / boundary case / multi-label classification / polyhierarchy 문단(영문) 추가
- 한글판 `..._ko.tex` '보류 55개와 불확실성' 절에 동일 취지 한글 문단 추가. kotex 부재로 샌드박스 컴파일 불가, Mac에서 재컴파일 필요

## 추가 작업 (2026-07-22, L4 라벨 중복 정리 → v2.17.2-rc)
- 동일 정규화 라벨 클러스터 62개(약 150카드) 전수 실사
- 통폐합 58건 (status=retired, merged_into, 레퍼런스 합집합, merged_labels 별칭 보존) → 활성 1,653개
- 고유 명칭 부여 82건 (EN·KO, 원 라벨 label_revision에 보존), 정본 정의 개선 4건
- 활성 카드 라벨 정확 중복 0건 확인, Physical 무수정 (활성 189)
- 판정 기록: reports/data_quality/l4_label_dedup_v2.17.2/DEDUP_DECISIONS.md
- 후속: 임베딩 재생성 및 신뢰성 재실행 필요, HOLD 수치·사이트 데이터는 v2.17.2 확정 시 갱신

## 추가 작업 (2026-07-22, v2.17.2-rc 재배치·신뢰성 재실행)
- 통폐합 반영 활성 1,653카드 재임베딩 (e5-small encoder transfer, BGE-M3는 로컬 재실행 권장)
- 가드 constrained-EM 재실행. 이동 제안 2건만 발생 (Algorithmic radicalisation → Political Neutrality, Accountability implementation gap → Accountability), 전건 HOLD 적용
- 신뢰성 재검증. 전체 top-1 60.6→61.1%, non-HOLD 72.9% 유지, perm p=0.0002 — 통폐합이 의미 구조를 훼손하지 않음을 확인
- 산출물: reports/validation/v2_17_2_rc_audit_e5_guarded/, 임베딩 public/data/releases/v2.17.2-rc/card_embeddings_*

## 추가 작업 (2026-07-22, 통폐합 재심사·부활 패스)
- 카드 보존 우선 원칙 적용. 통폐합 58건 재심사 → 미묘한 차이가 있는 12건 부활(고유 명칭·구분 근거 기록), 축어적 중복 46건만 통합 유지
- 최종 활성 1,665개. 재임베딩·가드 감사 재실행 결과 추가 이동 0건, 지표 안정

## 추가 작업 (2026-07-22, L4 라벨 노이즈 5개 유형 정비)
- 개명 182건(일반명·괄호형·분야명형·다중 메커니즘), 축어적 중복 추가 통합 5건 → 최종 활성 1,660개
- secondary_mechanisms 메타데이터 도입(8건), 비Physical 괄호·쉼표형 라벨 0건, 라벨 중복 0건
- 재임베딩·가드 감사 재실행 (이동 1건 HOLD), 지표 안정. 상세: reports/data_quality/l4_label_dedup_v2.17.2/DEDUP_DECISIONS.md

## 최종 작업 (2026-07-22, v2.17.2 published sync)
- ID 레지스트리는 1,711개로 불변. 사이트와 보고서 집계는 `1,711 registered IDs, 1,660 active cards`로 병기
- 51개 통합 카드는 삭제하지 않고 `status=retired`, `merged_into` provenance를 유지. taxonomy 브라우저에서는 `MERGED` 배지와 별도 필터로 계속 탐색 가능
- BGE-M3 constrained-EM 신뢰성 검증은 active 1,660개 기준으로 재실행. 전체 Top-1 70.2%, 비HOLD Top-1 79.7%, 비HOLD 노이즈 안정성 79.8%
- 144개 guarded move 후보는 자동 정답으로 확정하지 않고 HOLD 검토 상태로 반영. 최종 active HOLD는 765개
