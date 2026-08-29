#!/usr/bin/env python3
from pathlib import Path
P=Path(__file__).resolve().parents[1]; R=P.parents[1]/'releases/RAI-Risk-Taxonomy-2.0-master'; O=R/'reports'
COMMON=r'''\documentclass[11pt,a4paper]{article}
\usepackage[margin=22mm]{geometry}\usepackage{fontspec}\usepackage{graphicx}\usepackage{booktabs}\usepackage{xcolor}\usepackage{hyperref}\usepackage{longtable}\usepackage{array}\usepackage{fancyhdr}
\setmainfont{Apple SD Gothic Neo}\hypersetup{colorlinks=true,linkcolor=blue,urlcolor=blue}\pagestyle{fancy}\fancyhf{}\rhead{RAI Risk Taxonomy 2.0}\lhead{Human Review Recovery}\cfoot{\thepage}\setlength{\parskip}{6pt}\setlength{\parindent}{0pt}
\begin{document}
'''
KO=COMMON+r'''\title{RAI Risk Taxonomy 2.0\\2차 휴먼 검수 복구 기술보고서}\author{Human-review recovery release}\date{2026년 8월 29일}\maketitle
\section*{요약}
본 보고서는 798개 기준선 L4 카드를 보존하면서 2차 휴먼 검수 지시를 행 단위로 다시 해석하고 적용한 복구 작업을 기록한다. 이번 단계에서는 EM 또는 Hybrid EM을 다시 실행하지 않았다. 고정된 L3 마스터와 808행 검수 등록부를 기준으로 전문 에이전트 2명이 독립 검토하고 교차 검토한 166건의 결정을 적용했다. 최종 결과는 L4 카드 791건이며 General 620건, Agentic 77건, Physical 94건이다. Others 배정은 0건이다.
\section{복구 원칙}
기준 커밋의 유효한 편집과 사용자 승인 통합은 보존했다. 2차 검수 원문의 삭제, 통합, 분리, 재배정, 정의 수정 지시만 source\_row\_id 계보를 통해 적용했다. Instruction Prompt와 L3 마스터가 충돌할 때는 L3 마스터를 우선했다. L3는 신설하거나 수정하지 않았으며 SHA-256 해시를 고정했다.
\section{적용 결과}
\begin{table}[h]\centering\begin{tabular}{lr}\toprule 조치 & 검수행 수\\\midrule 재배정 & 80\\정의 수정 후 유지 & 39\\분리 & 19\\통합 & 14\\삭제 & 14\\\bottomrule\end{tabular}\caption{승인된 166건의 휴먼 검수 조치}\end{table}
\begin{figure}[h]\centering\includegraphics[width=.82\linewidth]{../figures/human_review_recovery_domain_counts.png}\caption{도메인별 최종 L4 카드 수}\end{figure}
\begin{figure}[h]\centering\includegraphics[width=.88\linewidth]{../figures/human_review_recovery_actions.png}\caption{휴먼 검수 조치 분포}\end{figure}
\section{복합 카드 분리}
기존에 이미 올바르게 분리된 6건은 보존했다. 단일 출력으로 남아 있던 12건은 각 L3의 피해 기제에 맞춰 별도 카드로 작성했다. 각 한영 정의는 AI 시스템, AI 알고리즘, AI 에이전트 또는 이에 준하는 기술 주체, 인과 기제, 불리한 결과를 명시한다. 명칭은 L3 마스터의 명사구 문체를 따르며 한국어에 리스크 또는 위험을 기계적으로 덧붙이지 않았다.
\section{데이터 무결성 및 검증}
L3 마스터 SHA-256은 \texttt{e9439ced64fb49c1496f1955013b5f038ecc7d271b9d6c9704f1e1bf6b0094df}로 입력과 출력에서 동일하다. L4 ID는 최종 L3별로 연속 재발급했다. 중복 ID, 정확 중복 카드, 알 수 없는 L3, 계층 불일치, 빈 한영 필드, AI 기술 주체가 없는 정의는 모두 0건이다. 두 번의 독립 실행에서 세 L4 CSV의 SHA-256이 동일했다.
\section{산출물}
최종 배포는 L1 CSV 1개, L1/L2/L3 CSV 1개, General, Agentic, Physical L4 CSV 3개로 구성한다. 검증 폴더에는 808행 지시 등록부, 165건 승인 결정표, source\_row\_id와 최종 L4의 계보 간선, 삭제 기록, 적용 로그, 검증 기록을 보존한다.
\section{결론}
이번 복구는 의미 유사도 재분류가 아니라 휴먼 검수 의도의 충실한 이행이다. 최종 데이터에는 Others가 남지 않았고, L3 마스터는 변경되지 않았다. 이후 재매핑은 별도의 명시적 사용자 지시가 있을 때만 수행해야 한다.
\end{document}'''
EN=COMMON+r'''\title{RAI Risk Taxonomy 2.0\\Second Human-Review Recovery Technical Report}\author{Human-review recovery release}\date{29 August 2026}\maketitle
\section*{Executive summary}
This report documents a recovery that preserved 798 baseline L4 cards while reinterpreting and applying the second-round human-review instructions row by row. Neither EM nor Hybrid EM was rerun. Two specialist agents independently reviewed and cross-reviewed 166 decisions against the frozen L3 master and an 808-row instruction register. The final release contains 791 L4 cards: 620 General, 77 Agentic, and 94 Physical. No card remains assigned to Others.
\section{Recovery principles}
Valid edits and user-approved consolidations in the baseline commit were retained. Only explicit second-round instructions to delete, merge, split, remap, or rewrite were applied through source\_row\_id lineage. The L3 master prevailed over conflicting prompts. No L3 was created or modified, and its SHA-256 digest was frozen.
\section{Applied decisions}
\begin{table}[h]\centering\begin{tabular}{lr}\toprule Action & Reviewed rows\\\midrule Remap & 80\\Rewrite and retain & 39\\Split & 19\\Merge & 14\\Delete & 14\\\bottomrule\end{tabular}\caption{The 166 approved human-review decisions}\end{table}
\begin{figure}[h]\centering\includegraphics[width=.82\linewidth]{../figures/human_review_recovery_domain_counts.png}\caption{Final L4 cards by domain}\end{figure}
\begin{figure}[h]\centering\includegraphics[width=.88\linewidth]{../figures/human_review_recovery_actions.png}\caption{Distribution of approved human-review actions}\end{figure}
\section{Splitting compound cards}
Six records that had already been split correctly were retained. Twelve compound records that still had a single output were rewritten as distinct children aligned with their respective L3 mechanisms. Every bilingual definition identifies an AI system, algorithm, agent, or equivalent technical subject, a causal mechanism, and an adverse outcome. Titles follow the nominal tone of the L3 master and do not receive a mechanical risk suffix.
\section{Integrity and validation}
The L3 master SHA-256 remained \texttt{e9439ced64fb49c1496f1955013b5f038ecc7d271b9d6c9704f1e1bf6b0094df}. L4 identifiers were reissued continuously within each final L3. Duplicate identifiers, exact duplicate cards, unknown L3 assignments, hierarchy mismatches, blank bilingual fields, and definitions without an AI technical subject all returned zero failures. Two independent executions produced identical SHA-256 hashes for the three L4 CSV files.
\section{Deliverables}
The release contains one L1 CSV, one combined L1/L2/L3 CSV, and separate General, Agentic, and Physical L4 CSVs. The validation directory preserves the 808-row instruction register, the 165 approved decisions, lineage edges from source\_row\_id to final L4, deletion tombstones, the application log, and the validation record.
\section{Conclusion}
This recovery implements human-review intent rather than a new similarity-based classification. No Others assignments remain and the L3 master is unchanged. Any future remapping must be run only after a separate explicit user instruction.
\end{document}'''
O.mkdir(parents=True,exist_ok=True); (O/'technical_report_ko.tex').write_text(KO,encoding='utf-8'); (O/'technical_report_en.tex').write_text(EN,encoding='utf-8')
if __name__=='__main__':print(O)
