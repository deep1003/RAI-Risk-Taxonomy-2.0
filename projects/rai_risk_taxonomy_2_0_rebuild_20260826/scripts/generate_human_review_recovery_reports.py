#!/usr/bin/env python3
from pathlib import Path
P=Path(__file__).resolve().parents[1]; R=P.parents[1]/'releases/RAI-Risk-Taxonomy-2.0-master'; O=R/'reports'
COMMON=r'''\documentclass[11pt,a4paper]{article}
\usepackage[margin=22mm]{geometry}\usepackage{fontspec}\usepackage{graphicx}\usepackage{booktabs}\usepackage{xcolor}\usepackage{hyperref}\usepackage{longtable}\usepackage{array}\usepackage{fancyhdr}\usepackage{titling}\setlength{\droptitle}{8mm}
\setmainfont{Apple SD Gothic Neo}\hypersetup{colorlinks=true,linkcolor=blue,urlcolor=blue}\pagestyle{fancy}\fancyhf{}\rhead{RAI Risk Taxonomy 2.0}\lhead{Human Review Recovery}\cfoot{\thepage}\setlength{\parskip}{6pt}\setlength{\parindent}{0pt}
\begin{document}
'''
KO=COMMON+r'''\title{RAI Risk Taxonomy 2.0\\2차 휴먼 검수 복구 기술보고서}\author{Human-review recovery release}\date{2026년 8월 29일}\maketitle
\section*{요약}
본 보고서는 798개 기준선 L4 카드에 2차 휴먼 검수 지시를 행 단위로 다시 적용하고, 이어서 사용자가 승인한 의미 중복 제거, 복합 카드 분리와 범위·세분성 정제를 수행한 작업을 기록한다. 이번 단계에서는 EM 또는 Hybrid EM을 다시 실행하지 않았다. 마지막 정제에서는 지나치게 넓거나 특정 사례에 과도하게 한정된 카드 8건을 검토하여 7건을 기존 카드에 흡수·폐기하고 재현성 위험 1건을 신설했으며 물리 안전 카드 1건의 범위를 축소했다. 최종 결과는 L4 카드 777건이며 General 607건, Agentic 77건, Physical 93건이다. Others 배정은 0건이다.
\section{복구 원칙}
기준 커밋의 유효한 편집과 사용자 승인 통합은 보존했다. 2차 검수 원문의 삭제, 통합, 분리, 재배정, 정의 수정 지시만 source\_row\_id 계보를 통해 적용했다. Instruction Prompt와 L3 마스터가 충돌할 때는 L3 마스터를 우선했다. L3는 신설하거나 수정하지 않았으며 SHA-256 해시를 고정했다.
\section{적용 결과}
\begin{table}[h]\centering\begin{tabular}{lr}\toprule 조치 & 검수행 수\\\midrule 재배정 & 80\\정의 수정 후 유지 & 39\\분리 & 19\\통합 & 14\\삭제 & 14\\\bottomrule\end{tabular}\caption{승인된 166건의 휴먼 검수 조치}\end{table}
\begin{figure}[h]\centering\includegraphics[width=.82\linewidth]{../figures/human_review_recovery_domain_counts.png}\caption{도메인별 최종 L4 카드 수}\end{figure}
\begin{figure}[h]\centering\includegraphics[width=.88\linewidth]{../figures/human_review_recovery_actions.png}\caption{휴먼 검수 조치 분포}\end{figure}
\section{복합 카드 분리}
기존 휴먼 검수에서 분리한 계보를 보존한 상태에서 추가 복합 카드 10건을 검토했다. 기존 카드가 이미 해당 의미를 충분히 나타내면 source\_row\_id 계보와 고유 의미를 흡수했고, 독립적인 피해 기제 7건만 새 카드로 분리했다. 내용이 지나치게 포괄적이었던 2건은 구체 카드에 흡수한 뒤 폐기했다. 각 한영 정의는 AI 기술 주체, 인과 기제와 불리한 결과를 명시한다.
\section{의미 중복 제거}
위험행위, 피해대상, 작동기제와 실질적 통제목표가 동일하고 차이가 채널, 사례, 배포환경 또는 좁은 재진술에 한정된 카드만 통합했다. 자해·자살 조장, 대량 감시, 맥락적 개인정보 노출, 저작물 무단 이용, 역할 지시 기반 안전장치 우회, 평가 기만, 정서적 의존, 사회경제적 불평등, 책임 공백, 가정환경 인간-로봇 안전 실패의 10개 통합군에서 13개 카드를 폐기했다. 통합 카드에는 폐기 카드의 고유한 의미와 source\_row\_id 계보를 보존했다. 보호특성별 차별적 표상과 서로 다른 피해 기제는 분리 유지했다.
\section{범위·세분성 정제}
폭력·무력 충돌, 포괄적 보안 위협, 사회적 적응 혼란처럼 L3 수준으로 넓은 카드는 구체적인 기존 카드에 계보와 의미를 흡수한 뒤 폐기했다. 가이드라인 오염, 비플레이어 캐릭터 조작, 고인 모사 챗봇 의존처럼 특정 사례나 채널에 한정된 카드는 각각 평가 오염, 외부 지시 기반 목표 탈취, 정서적·사회적 의존의 일반 카드로 통합했다. 설명가능성·출처·재현성을 결합한 카드는 기존 설명가능성·출처 카드에 흡수하고 재현성만 독립 카드로 신설했다.
\section{데이터 무결성 및 검증}
L3 마스터 SHA-256은 \texttt{e9439ced64fb49c1496f1955013b5f038ecc7d271b9d6c9704f1e1bf6b0094df}로 입력과 출력에서 동일하다. L4 ID는 최종 L3별로 연속 재발급했다. 중복 ID, 정확 중복 카드, 알 수 없는 L3, 계층 불일치, 빈 한영 필드, AI 기술 주체가 없는 정의는 모두 0건이다. 두 번의 독립 실행에서 세 L4 CSV의 SHA-256이 동일했다.
\section{산출물}
최종 배포는 L1 CSV 1개, L1/L2/L3 CSV 1개, General, Agentic, Physical L4 CSV 3개로 구성한다. 검증 폴더에는 808행 지시 등록부, 166건 승인 결정표, source\_row\_id와 최종 L4의 계보 간선, 삭제 기록, 의미 중복 통합 로그, 적용 로그, 검증 기록을 보존한다.
\section{결론}
이번 복구는 의미 유사도 재분류가 아니라 휴먼 검수 의도의 충실한 이행이다. 최종 데이터에는 Others가 남지 않았고, L3 마스터는 변경되지 않았다. 이후 재매핑은 별도의 명시적 사용자 지시가 있을 때만 수행해야 한다.
\end{document}'''
EN=COMMON+r'''\title{RAI Risk Taxonomy 2.0\\Second Human-Review Recovery Technical Report}\author{Human-review recovery release}\date{29 August 2026}\maketitle
\section*{Executive summary}
This report documents the row-level reapplication of the second-round human-review instructions to 798 baseline L4 cards, followed by user-approved semantic deduplication, mechanism-level splitting, and scope-granularity curation. Neither EM nor Hybrid EM was rerun. The final curation reviewed eight cards that were L3-like, difficult to operationalise, or excessively example-specific. Seven were absorbed and retired, one reproducibility risk was created, and one physical-safety card was narrowed. The final release contains 777 L4 cards: 607 General, 77 Agentic, and 93 Physical. No card remains assigned to Others.
\section{Recovery principles}
Valid edits and user-approved consolidations in the baseline commit were retained. Only explicit second-round instructions to delete, merge, split, remap, or rewrite were applied through source\_row\_id lineage. The L3 master prevailed over conflicting prompts. No L3 was created or modified, and its SHA-256 digest was frozen.
\section{Applied decisions}
\begin{table}[h]\centering\begin{tabular}{lr}\toprule Action & Reviewed rows\\\midrule Remap & 80\\Rewrite and retain & 39\\Split & 19\\Merge & 14\\Delete & 14\\\bottomrule\end{tabular}\caption{The 166 approved human-review decisions}\end{table}
\begin{figure}[h]\centering\includegraphics[width=.82\linewidth]{../figures/human_review_recovery_domain_counts.png}\caption{Final L4 cards by domain}\end{figure}
\begin{figure}[h]\centering\includegraphics[width=.88\linewidth]{../figures/human_review_recovery_actions.png}\caption{Distribution of approved human-review actions}\end{figure}
\section{Splitting compound cards}
Existing human-review split lineage was preserved while ten additional compound cards were reviewed. Where an existing card already represented a branch adequately, its unique meaning and source\_row\_id lineage were absorbed. Only seven independent harm mechanisms were created as new cards, and two overbroad umbrella cards were retired after their meanings were absorbed into specific cards. Every bilingual definition identifies an AI technical subject, a causal mechanism, and an adverse outcome.
\section{Semantic deduplication}
Cards were consolidated only when their risk event, affected interest, causal mechanism, and practical control objective were materially the same and any difference was limited to a channel, example, deployment context, or narrower restatement. Thirteen cards were retired across ten consolidation clusters covering self-harm and suicide facilitation, mass surveillance, contextual privacy disclosure, unauthorised use of copyrighted works, role-instruction safeguard bypass, evaluation deception, emotional dependence, socioeconomic inequality, accountability gaps, and domestic human-robot safety failure. Distinct protected characteristics and materially different harm mechanisms remained separate. The revised canonical cards preserve unique meaning and source\_row\_id lineage from every contributor.
\section{Scope and granularity curation}
Cards framed at L3 breadth, including violence and armed conflict, generic security threats, and disruption from societal adaptation, were absorbed into concrete existing mechanisms and retired. Example-specific cards concerning guideline contamination, non-player-character manipulation, and griefbot dependence were integrated into general cards for evaluation contamination, goal hijacking through untrusted external intent, and emotional or social dependence. The compound explainability, provenance, and reproducibility card was absorbed into existing explainability and provenance cards, while reproducibility was retained as one independent measurable risk.
\section{Integrity and validation}
The L3 master SHA-256 remained \texttt{e9439ced64fb49c1496f1955013b5f038ecc7d271b9d6c9704f1e1bf6b0094df}. L4 identifiers were reissued continuously within each final L3. Duplicate identifiers, exact duplicate cards, unknown L3 assignments, hierarchy mismatches, blank bilingual fields, and definitions without an AI technical subject all returned zero failures. Two independent executions produced identical SHA-256 hashes for the three L4 CSV files.
\section{Deliverables}
The release contains one L1 CSV, one combined L1/L2/L3 CSV, and separate General, Agentic, and Physical L4 CSVs. The validation directory preserves the 808-row instruction register, the 166 approved decisions, lineage edges from source\_row\_id to final L4, deletion tombstones, the semantic-consolidation log, the application log, and the validation record.
\section{Conclusion}
This recovery implements human-review intent rather than a new similarity-based classification. No Others assignments remain and the L3 master is unchanged. Any future remapping must be run only after a separate explicit user instruction.
\end{document}'''
KO=KO.replace(r'\section',r'\par\section'); EN=EN.replace(r'\section',r'\par\section')
O.mkdir(parents=True,exist_ok=True); (O/'technical_report_ko.tex').write_text(KO,encoding='utf-8'); (O/'technical_report_en.tex').write_text(EN,encoding='utf-8')
if __name__=='__main__':print(O)
