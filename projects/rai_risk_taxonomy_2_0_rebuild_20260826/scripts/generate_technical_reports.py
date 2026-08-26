#!/usr/bin/env python3
"""Generate synchronized Korean and English LaTeX technical reports."""

from __future__ import annotations

import json
from pathlib import Path
from string import Template

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "technical_report"
RELEASE = ROOT / "03_outputs/release"
AUDIT = ROOT / "03_outputs/audit"
REPORT.mkdir(parents=True, exist_ok=True)


def data() -> dict[str, str]:
    manifest = json.loads((RELEASE / "release_manifest.json").read_text(encoding="utf-8"))
    summary = manifest["summary"]
    cards = pd.concat([pd.read_csv(RELEASE / f"L4_{d}.csv") for d in ("General", "Agentic", "Physical")])
    baseline_root = ROOT / "04_baseline_pre_keyword/release"
    baseline_cards = pd.concat([
        pd.read_csv(baseline_root / f"L4_{d}.csv") for d in ("General", "Agentic", "Physical")
    ])
    values: dict[str, str] = {
        "source": str(summary["source_total"]), "final": str(summary["cleaned_total"]),
        "deleted": str(summary["deleted"]), "merged": str(summary["merged_away"]),
        "split": str(summary["split_net_addition"]), "em": str(summary["em_total"]),
        "hd": str(summary["others_total"]), "g": str(summary["final_domain_counts"]["General AI"]),
        "a": str(summary["final_domain_counts"]["Agentic AI"]), "p": str(summary["final_domain_counts"]["Physical AI"]),
        "g_em": str(summary["mapping_method_counts"]["General AI"]["EM"]),
        "g_hd": str(summary["mapping_method_counts"]["General AI"]["HD"]),
        "a_em": str(summary["mapping_method_counts"]["Agentic AI"]["EM"]),
        "a_hd": str(summary["mapping_method_counts"]["Agentic AI"]["HD"]),
        "p_em": str(summary["mapping_method_counts"]["Physical AI"]["EM"]),
        "p_hd": str(summary["mapping_method_counts"]["Physical AI"]["HD"]),
        "em_share": f"{100 * summary['em_total'] / summary['cleaned_total']:.1f}",
        "hd_share": f"{100 * summary['others_total'] / summary['cleaned_total']:.1f}",
        "l3hash": manifest["source_hashes"]["L3"], "ghash": manifest["source_hashes"]["General"],
        "ahash": manifest["source_hashes"]["Agentic"], "phash": manifest["source_hashes"]["Physical"],
        "new_retained": str(int(cards["Source_L4_ID"].str.lower().eq("new").sum())),
        "checks": str(summary["validation_passed"]),
        "ai_rewrites": str(summary["definition_ai_grounding_rewrites"]),
        "ai_validated": str(summary["cleaned_total"] - summary["definition_ai_grounding_rewrites"]),
        "l3_scope_deletions": str(summary["l3_scope_deletions"]),
        "pre_scope": str(summary["cleaned_total"] + summary["l3_scope_deletions"] + summary["semantic_near_duplicate_deletions"]),
        "post_scope": str(summary["cleaned_total"] + summary["semantic_near_duplicate_deletions"]),
        "title_normalisations": str(summary["title_terminology_normalisations"]),
        "title_validated": str(summary["title_terminology_validated"]),
        "duplicate_candidates": str(summary["semantic_near_duplicate_candidates"]),
        "duplicate_deletions": str(summary["semantic_near_duplicate_deletions"]),
        "duplicate_retained": str(summary["semantic_near_duplicate_candidates"] - summary["semantic_near_duplicate_deletions"]),
        "g_delta": f"{summary['final_domain_counts']['General AI'] - 591:+d}",
        "a_delta": f"{summary['final_domain_counts']['Agentic AI'] - 83:+d}",
        "p_delta": f"{summary['final_domain_counts']['Physical AI'] - 218:+d}",
        "total_delta": f"{summary['cleaned_total'] - summary['source_total']:+d}",
        "keyword_count": str(summary["keyword_count_per_language"]),
        "anchor_weight": f"{summary['thresholds']['General']['anchor_weight']:.1f}",
        "score_floor": f"{summary['thresholds']['General']['score_floor']:.3f}",
        "margin_floor": f"{summary['thresholds']['General']['margin_floor']:.3f}",
        "stability_floor": f"{summary['thresholds']['General']['stability_floor']:.2f}",
        "anchor_floor": f"{summary['thresholds']['General']['anchor_score_floor']:.2f}",
        "baseline_em": str(int(baseline_cards["Mapping_Method"].eq("EM").sum())),
        "baseline_hd": str(int(baseline_cards["Mapping_Method"].eq("HD").sum())),
        "em_delta": str(summary["em_total"] - int(baseline_cards["Mapping_Method"].eq("EM").sum())),
    }
    for domain, prefix in (("General AI", "gm"), ("Agentic AI", "am"), ("Physical AI", "pm")):
        subset = cards[cards["L1_Title_en"].eq(domain)]
        values[f"{prefix}_score"] = f"{subset['EM_Score'].mean():.4f}"
        values[f"{prefix}_margin"] = f"{subset['EM_Margin'].median():.4f}"
        values[f"{prefix}_stability"] = f"{subset['EM_Stability'].mean():.4f}"
        values[f"{prefix}_agreement"] = f"{100 * subset['KO_Top_L3_ID'].eq(subset['EN_Top_L3_ID']).mean():.1f}"
        values[f"{prefix}_hd_share"] = f"{100 * subset['Mapping_Method'].eq('HD').mean():.1f}"
    return values


PREAMBLE_KO = r"""% !TEX program = xelatex
\documentclass[10pt,a4paper]{article}
\usepackage[a4paper,margin=22mm,headheight=15pt]{geometry}
\usepackage{fontspec,kotex,microtype}
\usepackage{booktabs,longtable,tabularx,array,enumitem,xcolor,hyperref,fancyhdr,lastpage}
\usepackage{amsmath,amssymb,graphicx,titlesec,seqsplit}
\IfFontExistsTF{Apple SD Gothic Neo}{\setmainhangulfont{Apple SD Gothic Neo}}{\setmainhangulfont{Noto Sans CJK KR}}
\IfFontExistsTF{Times New Roman}{\setmainfont{Times New Roman}}{\setmainfont{Latin Modern Roman}}
\IfFontExistsTF{TeX Gyre Heros}{\setsansfont{TeX Gyre Heros}}{\setsansfont{Arial}}
\definecolor{navy}{HTML}{173458}\definecolor{blue}{HTML}{3366CC}\definecolor{darkgray}{HTML}{44546A}
\hypersetup{colorlinks=true,linkcolor=navy,urlcolor=blue,pdfauthor={RAI Risk Taxonomy 2.0 Project},pdftitle={RAI Risk Taxonomy 2.0 Rebuild Technical Report}}
\pagestyle{fancy}\fancyhf{}\lhead{\small RAI Risk Taxonomy 2.0 Master}\rhead{\small Technical Report, Korean}\cfoot{\small \thepage\ / \pageref{LastPage}}
\titleformat{\section}{\Large\bfseries\color{navy}}{\thesection}{0.7em}{}\titleformat{\subsection}{\large\bfseries\color{darkgray}}{\thesubsection}{0.7em}{}
\setlist[itemize]{leftmargin=1.5em,itemsep=2pt}\setlist[enumerate]{leftmargin=1.7em,itemsep=3pt}\renewcommand{\arraystretch}{1.22}
\newcommand{\hashval}[1]{\texttt{\small\seqsplit{#1}}}\graphicspath{{../output/figures/}}
\begin{document}
"""

PREAMBLE_EN = PREAMBLE_KO.replace("fontspec,kotex,microtype", "fontspec,microtype").replace(
    "\\IfFontExistsTF{Apple SD Gothic Neo}{\\setmainhangulfont{Apple SD Gothic Neo}}{\\setmainhangulfont{Noto Sans CJK KR}}\n", ""
).replace("Technical Report, Korean", "Technical Report, English").replace(
    "Rebuild Technical Report}", "Rebuild Technical Report, English}"
)


KO = Template(PREAMBLE_KO + r"""
\begin{titlepage}\pagecolor{navy}\color{white}\vspace*{25mm}
{\sffamily\bfseries\fontsize{27}{33}\selectfont RAI Risk Taxonomy 2.0\par}\vspace{5mm}
{\sffamily\fontsize{21}{27}\selectfont Rebuild Technical Report\par}\vspace{12mm}
{\Large 리스크 적격성 정제, EM 기반 L3 매핑 및 마스터 릴리스\par}\vfill
{\large 기준일: 2026년 8월 26일\par}\vspace{3mm}{\normalsize 한국어판\par}\vspace{18mm}
\end{titlepage}\nopagecolor\color{black}\tableofcontents\newpage

\section{요약}
본 작업은 초기 의미 유사도 파이프라인이 응급·재난 대응과 같은 적용 맥락을 폭력 리스크로 오분류한 문제를 계기로 RAI Risk Taxonomy 2.0을 원천 데이터부터 다시 구축한 결과이다. 원천 L4 $source건을 동결하고, 의미적 매핑 전에 리스크 적격성 심사, 삭제, 통합, 분리, 한영 명칭·정의 재작성, 동료 검토를 수행하였다. 최종 L4는 $final건이며 보존식은 \($source-$deleted-$merged+$split=$final\)이다.

최종 카드 중 $em건($em_share\%)은 기존 L3에 EM으로 배정했고, $hd건($hd_share\%)은 기존 L3 후보 사이의 경계성, 낮은 확신, 불안정성 또는 한영 불일치 때문에 도메인별 Others와 인간 결정(HD) 대기열로 분리하였다. 최종 분포는 General $g건, Agentic $a건, Physical $p건이다. 원본 L3 46행은 변경하지 않았고, 도메인별 Others 3행만 파생 구조로 추가하였다. 내부 자동 검증 $checks개는 모두 통과하였다.

\section{문제 진단과 재설계 원칙}
\subsection{확인된 실패}
초기 방식은 모든 입력 행을 리스크로 가정하고 곧바로 의미 공간에 투입하였다. 이 때문에 생명, 안전, 응급, CPR, 응급처치와 같은 어휘가 폭력 L3 임베딩을 끌어올려, 정상적인 응급·재난 대응 맥락이 폭력으로 배정되는 오류가 발생했다. 이는 유사도가 리스크 성립 여부를 판정할 수 없고, 가까운 어휘가 곧 올바른 위험 메커니즘을 의미하지 않음을 보여준다.

\subsection{재설계된 순서}
\begin{enumerate}
\item 원천 CSV·PDF와 L3 마스터를 SHA-256으로 동결한다.
\item AI 관여 원인, 발생 메커니즘, 부정적 결과, 영향 대상을 기준으로 리스크 적격성을 심사한다.
\item Instruction Prompt에 따른 삭제·통합·분리를 적용하고 원본 계보를 별도 보존한다.
\item 유효한 인간 수정 정의를 우선해 L4 수준의 구체적 한영 명칭과 정의를 작성한다.
\item L3 마스터와 같은 자연스러운 명사구를 명칭에 사용한다. `리스크'나 `위험'은 의미상 필요할 때만 사용한다.
\item 원문 기반 임시 EM으로 L3 작성 기준점을 산출하고, 현재 L3 명칭·정의와 의미적으로 연결되는지 심사한다.
\item 한국어와 영어 정의 각각에 AI 시스템·알고리즘·에이전트·로봇·학습 기술 또는 모델을 명시하고 L3식 위험 문장으로 통일한다.
\item 명칭에서 AI-mediated, AI-facilitated, AI-assisted와 같은 관용적 개입 수식어를 제거하고, L3 마스터 및 공신력 있는 기관의 통제 용어군으로 명칭을 검증한다. 기술적 대상을 구분하는 AI model, AI agent, AI-generated content 등은 유지한다.
\item 수정된 명칭·정의를 대상으로 한영 BGE-M3 유사도 후보를 만들고, 같은 L3 범위, 피해 대상, 위해 메커니즘, 용어 대표성을 대조해 실질적 중복만 폐기한다.
\item 중복 제거 후 한·영 각 3개의 대표 개념을 추출하고, L3 어휘 프로파일을 보완 신호로 결합해 최종 EM을 새로 적합한다.
\item 현행 L3 어디에도 맞지 않거나 단일 L3로 표현할 수 없는 카드는 삭제 보관하고, 현행 L3 범위 안에서 후보 간 판단이 모호한 카드만 Others에 배치하여 HD 사유와 상위 2개 L3 후보를 기록한다.
\end{enumerate}

\section{원천 데이터와 무결성}
\begin{table}[htbp]\centering\caption{도메인별 원천 및 최종 L4 수}
\begin{tabular}{lrrr}\toprule 도메인 & 원천 & 최종 & 순변화\\\midrule
General AI & 591 & $g & $g_delta\\ Agentic AI & 83 & $a & $a_delta\\ Physical AI & 218 & $p & $p_delta\\\midrule 합계 & $source & $final & $total_delta\\\bottomrule\end{tabular}\end{table}

\begin{longtable}{p{0.28\textwidth}p{0.64\textwidth}}\caption{핵심 원천 해시}\\\toprule 자료 & SHA-256\\\midrule\endfirsthead\toprule 자료 & SHA-256\\\midrule\endhead
L3 마스터 CSV & \hashval{$l3hash}\\ General L4 CSV & \hashval{$ghash}\\ Agentic L4 CSV & \hashval{$ahash}\\ Physical L4 CSV & \hashval{$phash}\\\bottomrule\end{longtable}

L3 원본 46행의 L1, L2, L3 한영 명칭·정의와 비고는 셀 단위로 대조하였다. 최종 계층의 추가 3행은 정식 L3가 아니라 HD 라우팅을 위한 G\_Others, A\_Others, P\_Others이다.

\section{L4 정제와 동료 검토}
명시적 삭제 39건, 비리스크 적용 맥락 8건, 동료 검토 폐기 1건을 삭제 보관본으로 이동하였다. 14개 통합 그룹에서 20건을 대표 카드로 흡수했고, 다중 의미 카드 1건을 두 카드로 분리하여 순증 1건을 만들었다. 원천에서 `new'로 표시된 100건 가운데 비리스크 맥락 8건을 제거하고 $new_retained건을 재정의·재발급하였다.

\begin{figure}[htbp]\centering\includegraphics[width=0.96\textwidth]{cleaning_reconciliation.png}\caption{리스크 적격성 게이트를 포함한 L4 수량 대조}\end{figure}

Claude 보조 검토는 713건의 한글 표기 복원, 8건의 실질적 재정의, 1건의 폐기 권고를 제시하였다. 표기 복원과 재정의는 원천 의미를 보존하는지 검토한 뒤 수용하였다. RAI4-0568은 AI 개발자의 관여와 정보주체 권리를 더 명시적으로 수정하였다. RAI4-1157은 재정의 후 사이버 공격 메커니즘이 명확해져 Physical에서 General로 이동하고 G\_SYS\_SECADV에 강한 작성 사전정보를 제공하였다. 모든 명칭에 `리스크'를 붙이는 규칙은 폐기했으며, 의미상 필요할 때만 피해·침해·위험 표현을 유지하였다.

이후 $pre_scope개 카드를 L3 마스터의 명칭·정의와 전수 대조했다. $ai_validated건은 이미 AI 기술 주체와 위험 구조가 완결되어 유지했고, $ai_rewrites건은 원래 의미를 보존하면서 한·영 정의에 AI 시스템·알고리즘·에이전트·로봇·학습 기술 또는 모델을 명시하도록 보완했다. 현행 L3 중 어느 범위에도 들어가지 않거나 단일 L3로 표현할 수 없는 $l3_scope_deletions건은 삭제 보관하였다. Others는 하나 이상의 현행 L3 범위에는 들어가지만 후보 간 경계가 모호한 경우에만 사용하였다.

최종 명칭 중 $title_normalisations건은 관용적 AI 개입 수식어를 제거하거나 표준 용어로 정규화했다. 유지된 $title_validated건 모두에 L3 마스터와 ISO, NIST, OECD, UNESCO, UNICEF, WHO, UNODC, WIPO, IMF 또는 국내 AI 기본법의 용어군 근거를 기록했다. 단, 기관 문구를 카드명에 기계적으로 복사하지 않고 해당 L3의 위해·실패·침해 개념과 일치하는 명사구로 검증했다.

$post_scope개 수정 카드를 대상으로 같은 L3 안의 한영 의미 유사도 후보 $duplicate_candidates쌍을 검토했다. 유사도는 후보 생성에만 사용했고, 보호 특성, 무기 유형, 피해 대상 또는 위해 메커니즘이 다르면 $duplicate_retained쌍을 유지했다. 별도 의미를 추가하지 않는 하위·포괄 중복 $duplicate_deletions건만 대표 카드에 연결하여 삭제 보관했다.

\begin{table}[htbp]\centering\caption{고유사도 L4 중복 검토 결과}
\begin{tabular}{lrr}\toprule 판정 & 후보 쌍 & 카드 삭제 수\\\midrule
구별되는 범위로 유지 & $duplicate_retained & 0\\ 대표성이 낮은 중복 폐기 & $duplicate_deletions & $duplicate_deletions\\\midrule 합계 & $duplicate_candidates & $duplicate_deletions\\\bottomrule\end{tabular}\end{table}

\begin{figure}[htbp]\centering\includegraphics[width=0.72\textwidth]{semantic_near_duplicate_review.png}\caption{한영 의미 고유사도 후보의 유지·폐기 판정}\end{figure}

\begin{figure}[htbp]\centering\includegraphics[width=0.90\textwidth]{definition_grounding_by_domain.png}\caption{L3 마스터 대조 후 AI 기술 정의 유지·보완 결과}\end{figure}

\section{L1 라우팅과 ID}
Instruction Prompt가 명시한 L1 이동 103건과 별도 해결 지시 1건을 반영하였다. 동료 검토로 메커니즘이 변경된 RAI4-1157 한 건은 의미 기준으로 General에 추가 이동하였다. \texttt{facet}과 \texttt{act-type}은 L4 속성으로 유지했지만 의미 매핑 입력에서는 제외했다. 모든 L4 ID는 \texttt{L3\_ID + 순번} 형식으로 다시 발급하였다.

\begin{figure}[htbp]\centering\includegraphics[width=0.90\textwidth]{domain_counts_before_after.png}\caption{재구축 전후 도메인별 L4 수}\end{figure}

\section{EM 매핑 방법}
BAAI/BGE-M3의 동일 로컬 스냅샷에서 한국어와 영어를 별도로 임베딩하고 CLS 벡터를 L2 정규화하였다. L4 카드 \(i\)와 L3 후보 \(k\)의 결합 점수는
\begin{equation}s_{ik}=0.5\cos(\mathbf{x}^{ko}_i,\boldsymbol{\mu}^{ko}_k)+0.5\cos(\mathbf{x}^{en}_i,\boldsymbol{\mu}^{en}_k)\end{equation}
이다. E-step은 L1 내부에서 최고 점수를 선택하고, M-step은 L3 마스터 anchor 가중치 $anchor_weight와 배정 L4 평균을 결합해 중심을 갱신한다. 20260826부터 20260830까지 5개 초기값으로 반복하였다.

각 L4에서 한·영 각 $keyword_count개 대표 개념을 추출하고, 46개 L3 정의에서 구성한 어휘 프로파일과 제외어를 E-step의 보완 사전정보로 사용했다. 선택된 후보의 키워드 지지도가 강하면 보수적 거절 조건을 일부 보완했지만, L3 정의 대신으로 사용하지 않았다. 민감 범주는 필수 개념어가 없는 카드의 후보에서 제외했다. 작성 힌트는 후보를 하나로 제한하지 않고 강한 사전정보로만 적용했다. 단일 현행 L3로 표현할 수 없는 복합 메커니즘이나 현행 L3와 의미적으로 양립할 수 없는 카드는 EM 입력에서 제외했다. 최고 점수 $score_floor 미만, 하이브리드 마진 $margin_floor 미만, 안정성 $stability_floor 미만, 원본 anchor 점수 $anchor_floor 미만, 낮은 마진에서의 한영 Top-1 불일치 등을 HD 신호로 사용했다.

\section{매핑 결과}
\begin{table}[htbp]\centering\caption{도메인별 EM 및 HD 결과}
\begin{tabular}{lrrrr}\toprule 도메인 & 최종 L4 & EM & HD/Others & HD 비율\\\midrule
General AI & $g & $g_em & $g_hd & $gm_hd_share\%\\ Agentic AI & $a & $a_em & $a_hd & $am_hd_share\%\\ Physical AI & $p & $p_em & $p_hd & $pm_hd_share\%\\\midrule 합계 & $final & $em & $hd & $hd_share\%\\\bottomrule\end{tabular}\end{table}

\begin{figure}[htbp]\centering\includegraphics[width=0.90\textwidth]{mapping_method_by_domain.png}\caption{도메인별 EM 확정과 HD/Others 대기열}\end{figure}

\begin{table}[htbp]\centering\caption{EM 품질 진단}
\begin{tabular}{lrrrr}\toprule 도메인 & 평균 최고점수 & 중앙 마진 & 평균 안정성 & 한영 Top-1 일치\\\midrule
General AI & $gm_score & $gm_margin & $gm_stability & $gm_agreement\%\\ Agentic AI & $am_score & $am_margin & $am_stability & $am_agreement\%\\ Physical AI & $pm_score & $pm_margin & $pm_stability & $pm_agreement\%\\\bottomrule\end{tabular}\end{table}

\begin{figure}[htbp]\centering\includegraphics[width=0.98\textwidth]{em_quality_diagnostics.png}\caption{도메인별 최고 유사도, 마진, 반복 안정성 분포}\end{figure}
\begin{figure}[htbp]\centering\includegraphics[width=0.99\textwidth]{largest_l3_categories.png}\caption{도메인별 EM 배정 상위 L3}\end{figure}

기준 키워드를 사용하지 않은 배정선에서는 EM $baseline_em건, HD $baseline_hd건이었다. 키워드 보강과 L3 기반 정의 검토 후 EM은 $em건으로 $em_delta건 늘었으며, 임금 양극화는 G\_SOC\_ECON, 대규모 사이버범죄 오용은 G\_SYS\_SECADV로 회수했다. 단, HD $hd건은 매핑 실패가 아니라 경계 사례를 명시적으로 격리한 결과이며 자동 확정된 L3로 해석해서는 안 된다.

\begin{figure}[htbp]\centering\includegraphics[width=0.78\textwidth]{em_baseline_comparison.png}\caption{키워드 보강 전·후 EM과 HD 건수 비교}\end{figure}

\section{세 가지 내부 검증}
\subsection{원본 대조 및 계보 검증}
처리 전후 원천 해시, L3 46행의 셀 값, 삭제·통합·분리 보존식, 892개 원천의 crosswalk 포함 여부를 확인했다. 이는 데이터 유실, 중복, L3 변조를 검출한다.
\subsection{반복 수렴 및 안정성 검증}
도메인별 5개 초기화의 목적함수, 반복 수, 카드별 배정 합의율을 기록했다. 낮은 합의는 HD 신호로 처리하였다.
\subsection{한영 교차검증 및 의미 전제 검증}
한국어와 영어 Top-1을 별도로 기록하고, 민감 L3의 개념 전제와 원본 anchor 점수를 함께 검사했다. 정상 활동이나 적용 맥락은 EM 이전의 리스크 적격성 게이트에서 제거하였다.

자동 검증은 원천 해시, L3 불변성, 수량 보존, ID 유일성, 한영 필드, AI 기술 명시, L3식 정의문 구조, 명칭 용어 근거, 관용적 AI 수식어 제거, 중복 후보 판정과 대표 카드 계보, L3 범위 게이트, Others의 HD 전용성, crosswalk, 3개 대표 키워드, 상위 2개 후보, 5개 CSV 구성을 포함한 $checks개 항목에서 모두 PASS였다.

\section{웹 기반 인간 검수 로그}
모든 L4 카드는 현재 배정과 무관하게 상위 2개 비-Others L3 후보의 기본 EM 점수와 하이브리드 점수를 표시한다. 검수자가 후보를 선택하면 릴리스 해시와 검수 스냅샷을 포함한 GitHub Issue가 작성된다. 일일 자동화는 스냅샷이 일치하는 표만 유효화하고, 검수자·카드별 최신 표를 유지하며, 최소 3명의 검수자와 50\% 초과 다수를 충족한 비구속적 권고안을 생성한다. 재배치는 사용자가 로그 분석과 반영을 명시적으로 지시할 때만 수행한다.

\section{마스터 릴리스와 동기화}
최종 정본은 L1 CSV 1개, L1/L2/L3 CSV 1개, General·Agentic·Physical L4 CSV 3개이다. 동일 CSV에서 웹 탐색용 \texttt{cards.json}, \texttt{hierarchy.json}, 공개 manifest, Validation Record, 한영 보고서와 그림을 생성하였다. 웹사이트의 행 수, 다운로드 링크, current release 포인터와 해시도 같은 릴리스에 맞췄다.

\section{한계와 후속 검토}
EM은 확률 혼합모형의 완전한 EM이 아니라 L3 anchor를 둔 제약 구면 hard EM이다. 점수 임계값은 내부 운영 기준이며 전문가 라벨로 외부 보정되지 않았다. Others $hd건은 삭제 대상이 아니라 인간 결정 대기열이다. 향후 독립 검증은 도메인·L3·점수 구간을 층화한 표본을 사용해 자동 배정의 정확도와 HD 회수율을 평가해야 한다.

\section{결론}
재구축은 어휘 유사도가 정상 응급 대응을 폭력으로 오인한 오류를 리스크 적격성 문제로 재정의하였다. 적격성 게이트, L3 불변성, 한영 정의 재작성, 보수적 EM과 HD 격리를 결합함으로써 $final개 L4와 완전한 계보를 가진 RAI Risk Taxonomy 2.0 master를 생성하였다.
\end{document}
""")

EN = Template(PREAMBLE_EN + r"""
\begin{titlepage}\pagecolor{navy}\color{white}\vspace*{25mm}
{\sffamily\bfseries\fontsize{27}{33}\selectfont RAI Risk Taxonomy 2.0\par}\vspace{5mm}
{\sffamily\fontsize{21}{27}\selectfont Rebuild Technical Report\par}\vspace{12mm}
{\Large Risk-eligibility cleaning, EM-based L3 mapping, and master release\par}\vfill
{\large Reference date: 26 August 2026\par}\vspace{3mm}{\normalsize English edition\par}\vspace{18mm}
\end{titlepage}\nopagecolor\color{black}\tableofcontents\newpage

\section{Executive summary}
This report documents the complete rebuild of RAI Risk Taxonomy 2.0 after the initial semantic pipeline assigned an emergency and disaster response context to Violence. The $source source L4 records were frozen, then subjected to risk-eligibility review, deletion, consolidation, splitting, bilingual rewriting, and peer review before any semantic mapping. The resulting $final cards satisfy \($source-$deleted-$merged+$split=$final\).

EM assigned $em cards ($em_share\%) to existing L3 categories. The remaining $hd cards ($hd_share\%) were routed to domain-specific Others queues for human decision because of ambiguity between eligible current L3 candidates, weak anchor support, instability, or bilingual disagreement. The final distribution is $g General, $a Agentic, and $p Physical. All 46 source L3 rows remain unchanged, with three derived Others routing rows. All $checks internal validation checks passed.

\section{Failure analysis and redesign}
The earlier procedure assumed that every input was a risk. Terms such as life, safety, emergency, CPR, first aid, and actions increased similarity to Violence even though the card described a normal application context rather than an AI interaction risk. The failure demonstrates that semantic proximity cannot establish risk eligibility and that lexical proximity does not identify the causal harm mechanism.

The revised sequence is: freeze sources and L3; test AI involvement, mechanism, adverse outcome, and affected party; execute explicit deletion, merge, and split instructions; write bilingual L4-level titles and definitions; route L1; compute a provisional L3 drafting anchor; compare each card with the current L3 names and definitions; discard cards that fit no current L3 or cannot be represented by one L3; require each retained Korean and English definition to name an AI technology; remove formulaic AI involvement modifiers from titles while retaining terms that identify a technical object; review bilingual high-similarity pairs against target and mechanism distinctiveness; extract three representative concepts in each language after deduplication; refit the final constrained EM; and place only within-scope but uncertain records in Others with an HD reason and two review candidates. Titles follow the nominal style of the L3 master. Risk or hazard suffixes are retained only where they are semantically necessary.

\section{Data integrity baseline}
\begin{table}[htbp]\centering\caption{Source and final L4 counts}
\begin{tabular}{lrrr}\toprule Domain & Source & Final & Net change\\\midrule
General AI & 591 & $g & $g_delta\\ Agentic AI & 83 & $a & $a_delta\\ Physical AI & 218 & $p & $p_delta\\\midrule Total & $source & $final & $total_delta\\\bottomrule\end{tabular}\end{table}

\begin{longtable}{p{0.28\textwidth}p{0.64\textwidth}}\caption{Core source hashes}\\\toprule Source & SHA-256\\\midrule\endfirsthead\toprule Source & SHA-256\\\midrule\endhead
L3 master CSV & \hashval{$l3hash}\\ General L4 CSV & \hashval{$ghash}\\ Agentic L4 CSV & \hashval{$ahash}\\ Physical L4 CSV & \hashval{$phash}\\\bottomrule\end{longtable}

The source-defined fields of all 46 L3 rows were compared cell by cell. The only additional hierarchy rows are G\_Others, A\_Others, and P\_Others, which are derived HD routes rather than formal L3 modifications.

\section{L4 cleaning and peer review}
The archive contains 39 explicit deletions, eight application-context records rejected by the risk-eligibility gate, and one peer-reviewed drop. Fourteen consolidation groups absorbed 20 records, and one multi-meaning record was split into two, adding one net record. Of 100 source records labelled `new', eight context-only records were removed and $new_retained were redefined and reissued.

\begin{figure}[htbp]\centering\includegraphics[width=0.96\textwidth]{cleaning_reconciliation.png}\caption{L4 reconciliation including the risk-eligibility gate}\end{figure}

Claude-assisted review proposed 713 Korean spacing restorations, eight substantive redefinitions, and one drop. The changes were adopted only after comparison with source meaning. RAI4-0568 was further refined to identify developer conduct, data-subject rights, and organisational liability. The revised RAI4-1157 describes cyberattack enablement, so it was routed from Physical to General and given a strong G\_SYS\_SECADV drafting prior without suppressing the second candidate. Mechanical addition of a risk suffix to every Korean title was discontinued. Harm, infringement, hazard, or risk wording remains only where semantically needed.

All $pre_scope records remaining before the L3 scope gate were compared with the immutable L3 names and definitions. The existing definitions of $ai_validated records already named an AI technology and used a complete risk-statement structure. The other $ai_rewrites records were amended, without replacing their source meaning, to name an AI system, algorithm, agent, robot, humanoid, learning technology, or model in both languages. The gate archived $l3_scope_deletions records that did not fit any current L3 or could not be represented by one L3 without inventing or suppressing meaning. Others was reserved for cases inside at least one current L3 scope but ambiguous between eligible candidates.

The terminology review normalised $title_normalisations titles by removing formulaic AI involvement modifiers or replacing them with a standard risk noun phrase. All $title_validated retained titles have an audit trail to the immutable L3 master and terminology families used by ISO, NIST, OECD, UNESCO, UNICEF, WHO, UNODC, WIPO, IMF, or the Korean AI Basic Act. Institutional wording was not copied mechanically. Each title was checked for consistency with the harm, failure, or infringement concept of its L3.

The $post_scope revised cards produced $duplicate_candidates bilingual high-similarity candidate pairs within the same L3. Similarity generated candidates but never deleted a card automatically. The review retained $duplicate_retained pairs with distinct protected attributes, weapon types, affected targets, or harm mechanisms. It discarded only $duplicate_deletions less representative cards that added no distinct scope, linking each discarded source row to a retained representative.

\begin{table}[htbp]\centering\caption{Semantic near-duplicate review results}
\begin{tabular}{lrr}\toprule Decision & Candidate pairs & Cards discarded\\\midrule
Retained as distinct scope & $duplicate_retained & 0\\ Less representative duplicate discarded & $duplicate_deletions & $duplicate_deletions\\\midrule Total & $duplicate_candidates & $duplicate_deletions\\\bottomrule\end{tabular}\end{table}

\begin{figure}[htbp]\centering\includegraphics[width=0.72\textwidth]{semantic_near_duplicate_review.png}\caption{Decisions for bilingual high-similarity candidate pairs}\end{figure}

\begin{figure}[htbp]\centering\includegraphics[width=0.90\textwidth]{definition_grounding_by_domain.png}\caption{Definitions retained or amended after immutable-L3 and AI-technology review}\end{figure}

\section{Routing and identifiers}
The pipeline applied 103 explicit L1 movement instructions, one separately resolved instruction, and one peer-review semantic route. \texttt{facet} and \texttt{act-type} remain L4 attributes but do not enter the embedding. All L4 identifiers were regenerated as \texttt{L3\_ID + sequence}.

\begin{figure}[htbp]\centering\includegraphics[width=0.90\textwidth]{domain_counts_before_after.png}\caption{L4 counts before and after rebuilding and routing}\end{figure}

\section{EM mapping method}
Korean and English texts were embedded separately using one coherent local BAAI/BGE-M3 snapshot. CLS vectors were L2-normalised. For card \(i\) and candidate L3 \(k\),
\begin{equation}s_{ik}=0.5\cos(\mathbf{x}^{ko}_i,\boldsymbol{\mu}^{ko}_k)+0.5\cos(\mathbf{x}^{en}_i,\boldsymbol{\mu}^{en}_k).\end{equation}
The E-step selects the highest eligible L3 within the confirmed L1. The M-step combines the fixed L3 master anchor with the mean of assigned L4 vectors, using anchor weight $anchor_weight. Five initialisations used seeds 20260826 to 20260830.

Each L4 contributes $keyword_count representative concepts in Korean and English. Auditable lexical profiles and exclusion terms derived from the 46 L3 definitions provide a complementary E-step prior. They do not replace the L3 definitions. Sensitive categories require mechanism-specific terms. Curated drafting hints act as strong priors rather than one-candidate constraints, preserving two reviewable candidates. Cards semantically incompatible with every current L3 are excluded before EM. HD/Others is limited to cards that remain inside current L3 scope but are ambiguous between eligible candidates. The rejection signals include a joint score below $score_floor, a hybrid top-two margin below $margin_floor, stability below $stability_floor, raw-anchor score below $anchor_floor, and bilingual Top-1 disagreement at a low margin.

\section{Results}
\begin{table}[htbp]\centering\caption{EM and HD results by domain}
\begin{tabular}{lrrrr}\toprule Domain & Final L4 & EM & HD/Others & HD share\\\midrule
General AI & $g & $g_em & $g_hd & $gm_hd_share\%\\ Agentic AI & $a & $a_em & $a_hd & $am_hd_share\%\\ Physical AI & $p & $p_em & $p_hd & $pm_hd_share\%\\\midrule Total & $final & $em & $hd & $hd_share\%\\\bottomrule\end{tabular}\end{table}

\begin{figure}[htbp]\centering\includegraphics[width=0.90\textwidth]{mapping_method_by_domain.png}\caption{EM assignments and HD/Others queues by domain}\end{figure}

\begin{table}[htbp]\centering\caption{EM quality diagnostics}
\begin{tabular}{lrrrr}\toprule Domain & Mean top score & Median margin & Mean stability & Bilingual Top-1 agreement\\\midrule
General AI & $gm_score & $gm_margin & $gm_stability & $gm_agreement\%\\ Agentic AI & $am_score & $am_margin & $am_stability & $am_agreement\%\\ Physical AI & $pm_score & $pm_margin & $pm_stability & $pm_agreement\%\\\bottomrule\end{tabular}\end{table}

\begin{figure}[htbp]\centering\includegraphics[width=0.98\textwidth]{em_quality_diagnostics.png}\caption{Top similarity, margin, and run-stability distributions}\end{figure}
\begin{figure}[htbp]\centering\includegraphics[width=0.99\textwidth]{largest_l3_categories.png}\caption{Largest EM-assigned L3 categories}\end{figure}

The pre-keyword baseline contained $baseline_em EM assignments and $baseline_hd HD records. Keyword augmentation and L3-referenced definition review increased the final EM count to $em, a net recovery of $em_delta records. Wage polarisation was recovered to G\_SOC\_ECON and cybercrime misuse at scale to G\_SYS\_SECADV. The remaining $hd HD records represent explicit uncertainty preservation and must not be interpreted as automatically confirmed L3 assignments.

\begin{figure}[htbp]\centering\includegraphics[width=0.78\textwidth]{em_baseline_comparison.png}\caption{EM and HD counts before and after keyword augmentation}\end{figure}

\section{Three internal validation methods}
\subsection{Source reconciliation and lineage}
The pipeline checked pre/post source hashes, exact preservation of the 46 L3 rows, the cleaning identity, and representation of all 892 source records in the crosswalk. This detects loss, duplication, or L3 alteration.
\subsection{Convergence and initialisation stability}
Five initialisations per domain retained objective values, iteration counts, and card-level agreement. Low agreement contributed to HD routing.
\subsection{Bilingual and semantic-prerequisite checking}
Korean and English Top-1 categories were stored separately. Sensitive-category prerequisites and raw-anchor support were tested alongside bilingual agreement. Normal activities and application contexts were removed before EM by the risk-eligibility gate.

All $checks automated checks passed. They cover source hashes, L3 immutability, count reconciliation, identifier uniqueness, bilingual completeness, explicit AI-technology naming, L3-style definition structure, title terminology evidence, removal of formulaic AI modifiers, near-duplicate decisions and representative-card lineage, the L3 scope gate, valid L3 references, HD-only Others, crosswalk coverage, three representative concepts, two reviewable candidates, and the five-file release structure.

\section{Web-based human review log}
Every L4 card exposes the top two non-Others L3 candidates with their base EM and hybrid scores. Selecting a candidate opens a prefilled GitHub Issue containing the release identifier and review-snapshot hash. A daily workflow accepts only votes matching the current snapshot, retains the latest vote for each reviewer and card, and produces non-binding recommendations when at least three unique reviewers and a strict majority above 50\% are present. It never reassigns a card. Reassignment occurs only after the user explicitly instructs the system to analyse and apply the logs.

\section{Synchronized master release}
The canonical release contains one L1 CSV, one L1/L2/L3 CSV, and three L4 CSVs. The same records generate the web explorer's \texttt{cards.json} and \texttt{hierarchy.json}, public manifests, Validation Record, bilingual reports, figures, download links, and current-release pointer.

\section{Limitations}
The method is anchor-constrained spherical hard EM rather than a full probabilistic mixture-model EM. Thresholds are internal operating rules and have not been calibrated on an external expert-labelled sample. The $hd Others records form a human-decision queue, not a deletion set. Independent validation should use samples stratified by domain, L3, score, margin, and decision route.

\section{Conclusion}
The rebuild converted a lexical-similarity error into an explicit risk-eligibility design requirement. Combining eligibility screening, immutable L3 definitions, bilingual rewriting, conservative EM, and transparent HD isolation produced an auditable $final-card RAI Risk Taxonomy 2.0 master release.
\end{document}
""")


def main() -> None:
    values = data()
    (REPORT / "rai_risk_taxonomy_2_0_rebuild_technical_report_ko.tex").write_text(KO.substitute(values), encoding="utf-8")
    (REPORT / "rai_risk_taxonomy_2_0_rebuild_technical_report_en.tex").write_text(EN.substitute(values), encoding="utf-8")
    print(REPORT)


if __name__ == "__main__":
    main()
