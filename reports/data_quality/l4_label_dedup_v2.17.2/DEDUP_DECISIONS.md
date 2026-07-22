# L4 라벨 중복 정리 판정 기록 (v2.17.2-rc, 2026-07-22)

판정 원칙. 라벨과 메커니즘 정의가 실질적으로 동일하면 통폐합(하위 ID를 정본으로, merged_into 기록, 레퍼런스 합집합). 미묘한 차이가 있으면 메커니즘을 드러내는 고유 명칭 부여. Physical 카드는 일절 미수정. 전 변경 human_review_status=pending.

## 통폐합 (58건)

| 소멸 ID | 소멸 시점 라벨 | 정본 ID | 정본 라벨(변경 후) |
|---|---|---|---|
| RAI4-0679 | Hate-speech generation | RAI4-0426 | Hate speech generation |
| RAI4-0686 | Representational stereotyping | RAI4-0425 | Representational stereotyping |
| RAI4-0692 | Adult content | RAI4-0685 | Sexual and adult content generation |
| RAI4-0706 | Algorithmic discrimination | RAI4-0423 | Algorithmic discrimination |
| RAI4-0724 | Sexual content | RAI4-0685 | Sexual and adult content generation |
| RAI4-0729 | Toxic content generation | RAI4-0426 | Hate speech generation |
| RAI4-0796 | Factual hallucination | RAI4-0795 | Factual hallucination |
| RAI4-0813 | Factual hallucination | RAI4-0795 | Factual hallucination |
| RAI4-0834 | Mental health | RAI4-0833 | Mental health harmful content |
| RAI4-0835 | Misinformation generation | RAI4-0819 | Unintentional misinformation generation |
| RAI4-0901 | Overreliance on AI | RAI4-0858 | Overreliance and automation bias |
| RAI4-0954 | Algorithmic discrimination | RAI4-0423 | Algorithmic discrimination |
| RAI4-0955 | Algorithmic bias | RAI4-0694 | Training-data social bias propagation |
| RAI4-0964 | Lack of privacy notice and control | RAI4-0737 | Lack of privacy notice and control |
| RAI4-1020 | Disparate performance | RAI4-0708 | Disparate performance across user groups |
| RAI4-1030 | Privacy violation | RAI4-0737 | Lack of privacy notice and control |
| RAI4-1048 | Environmental harm | RAI4-0502 | Environmental harm from AI lifecycle |
| RAI4-1069 | Exclusionary norms | RAI4-1053 | Exclusionary norm encoding |
| RAI4-1071 | Lower performance for some languages and social groups | RAI4-1054 | Language and group performance disparity |
| RAI4-1078 | Illegitimate surveillance and censorship | RAI4-1060 | Illegitimate mass surveillance and censorship |
| RAI4-1080 | Promoting harmful stereotypes by implying gender or ethnic identity | RAI4-1061 | Stereotype-reinforcing persona design |
| RAI4-1087 | AI-generated defamation | RAI4-0791 | AI-generated defamation |
| RAI4-1126 | AI-generated defamation | RAI4-0791 | AI-generated defamation |
| RAI4-1171 | Goal hijacking | RAI4-0928 | Goal hijacking via prompt injection |
| RAI4-1172 | Prompt leaking | RAI4-0759 | Prompt leaking |
| RAI4-1180 | Ethics and morality | RAI4-1170 | Immoral content endorsement |
| RAI4-1181 | Privacy and property | RAI4-1169 | Privacy and property information mishandling |
| RAI4-1200 | Poisoning attacks | RAI4-0435 | Data poisoning |
| RAI4-1219 | Environmental impacts | RAI4-0502 | Environmental harm from AI lifecycle |
| RAI4-1229 | Copyright infringement | RAI4-0496 | Copyright-infringing content generation |
| RAI4-1230 | AI governance failure | RAI4-0511 | AI governance failure |
| RAI4-1234 | Reward hacking | RAI4-0468 | Reward hacking |
| RAI4-1235 | Goal misgeneralization | RAI4-0469 | Goal misgeneralization |
| RAI4-1273 | Privacy violation | RAI4-0737 | Lack of privacy notice and control |
| RAI4-1274 | Unfairness in AI decisions | RAI4-1221 | Algorithmic bias |
| RAI4-1312 | Lack of robustness | RAI4-1041 | Lack of input robustness (OOD fragility) |
| RAI4-1315 | Weapons acquisition | RAI4-1160 | Weapons acquisition capability |
| RAI4-1318 | Persuasion and manipulation | RAI4-1158 | Large-scale persuasion capability |
| RAI4-1321 | Political strategy | RAI4-1159 | Political influence strategy capability |
| RAI4-1322 | AI development | RAI4-1162 | Dual-use AI development capability |
| RAI4-1325 | Adult content | RAI4-0685 | Sexual and adult content generation |
| RAI4-1378 | Intellectual property | RAI4-0517 | Intellectual property violation |
| RAI4-1391 | AI-enabled cybercrime | RAI4-0946 | AI-enabled cybercrime |
| RAI4-1401 | AI-enabled deception | RAI4-1320 | Human-deception capability |
| RAI4-1407 | Privacy violation | RAI4-1060 | Illegitimate mass surveillance and censorship |
| RAI4-1412 | Deceptive alignment | RAI4-0572 | Deceptive alignment |
| RAI4-1467 | Data poisoning | RAI4-0435 | Data poisoning |
| RAI4-1529 | Specification gaming | RAI4-1131 | Objective mis-specification gaming |
| RAI4-1532 | Goal misgeneralization | RAI4-0469 | Goal misgeneralization |
| RAI4-1587 | Jailbreak attacks | RAI4-0746 | Jailbreak attacks |
| RAI4-1590 | Data poisoning | RAI4-0435 | Data poisoning |
| RAI4-1595 | Data poisoning | RAI4-0435 | Data poisoning |
| RAI4-1605 | Institutional trust loss | RAI4-0816 | Institutional trust erosion |
| RAI4-1635 | Situational awareness capability | RAI4-1163 | Evaluation-aware behavior shifting |
| RAI4-1659 | Overreliance on AI | RAI4-0858 | Overreliance and automation bias |
| RAI4-1699 | Reward hacking | RAI4-0468 | Reward hacking |
| RAI4-1709 | Property damage | RAI4-0533 | Property damage from AI behavior |
| RAI4-1711 | Harm to the natural environment | RAI4-1632 | Environmental damage from AI system behavior |

## 고유 명칭 부여 (82건)

| ID | 기존 라벨 | 신규 라벨 (EN / KO) |
|---|---|---|
| RAI4-0470 | Loss of control | Oversight evasion and correction resistance / 감독 회피·수정 저항 |
| RAI4-0496 | Copyright infringement | Copyright-infringing content generation / 저작권 침해 콘텐츠 생성 |
| RAI4-0502 | Environmental harm | Environmental harm from AI lifecycle / AI 수명주기 환경 피해 |
| RAI4-0517 | Intellectual property | Intellectual property violation / 지식재산권 침해 |
| RAI4-0529 | Political instability | Politically destabilizing misuse / 정치 불안정 유발 오용 |
| RAI4-0533 | Property damage | Property damage from AI behavior / AI 행동에 의한 재산 피해 |
| RAI4-0565 | Loss of human control | Misaligned rogue AI behavior / 정렬 실패 로그(rogue) AI 행동 |
| RAI4-0576 | Emergent goals | Emergent goal ascription in multi-agent systems / 다중 에이전트 창발적 목표 귀속 |
| RAI4-0599 | Loss of control | Societal loss-of-control scenario / 사회적 통제 상실 시나리오 |
| RAI4-0622 | AI-enabled cyberattacks | AI-facilitated system disruption attacks / AI 조력 시스템 교란 공격 |
| RAI4-0669 | AI-enabled cyberattacks | AI-assisted malicious code generation / AI 조력 악성코드 생성 |
| RAI4-0675 | Data bias | Historical societal bias in training data / 학습 데이터 내 역사적·사회적 편향 |
| RAI4-0677 | Algorithmic discrimination | Population-scale discrimination amplification / 인구 규모 차별 증폭 |
| RAI4-0685 | Sexual content | Sexual and adult content generation / 성적·성인 콘텐츠 생성 |
| RAI4-0694 | Algorithmic bias | Training-data social bias propagation / 학습 데이터 사회적 편향 전파 |
| RAI4-0708 | Disparate performance | Disparate performance across user groups / 사용자 집단 간 성능 격차 |
| RAI4-0751 | Privacy violation | Sensitive personal information exposure in outputs / 출력 내 민감 개인정보 노출 |
| RAI4-0816 | Institutional trust loss | Institutional trust erosion / 제도 신뢰 침식 |
| RAI4-0819 | Misinformation generation | Unintentional misinformation generation / 비의도적 허위정보 생성 |
| RAI4-0830 | Factual hallucination | Multimodal hallucination / 멀티모달 환각 |
| RAI4-0831 | Factual hallucination | Fabricated references and artifacts / 허구적 참조·산출물 생성 |
| RAI4-0833 | Mental health | Mental health harmful content / 정신건강 유해 콘텐츠 |
| RAI4-0836 | Misinformation generation | Deliberate misinformation capability / 고의적 허위정보 생성 능력 |
| RAI4-0858 | Overreliance on AI | Overreliance and automation bias / 과의존과 자동화 편향 |
| RAI4-0885 | Overreliance on AI | Misplaced interpersonal trust in AI assistants / AI 어시스턴트에 대한 오도된 대인 신뢰 |
| RAI4-0902 | Overreliance on AI | Emotional and material dependence on AI / AI에 대한 정서적·물질적 의존 |
| RAI4-0925 | Poisoning attacks | Backdoor trigger implantation via poisoning / 포이즈닝을 통한 백도어 트리거 이식 |
| RAI4-0928 | Goal hijacking | Goal hijacking via prompt injection / 프롬프트 주입을 통한 목표 탈취 |
| RAI4-0958 | AI-enabled deception | Deceptive synthetic media (deepfake) content / 기만적 합성 미디어(딥페이크) 콘텐츠 |
| RAI4-0962 | Malicious use of AI | AI-supported digital crime / AI 조력 디지털 범죄 |
| RAI4-0965 | Malicious misuse | Accelerated threat-actor capability uplift / 위협 행위자 역량 가속 상승 |
| RAI4-0966 | AI accidents | Unintended AI accident failure modes / 비의도적 AI 사고 실패 유형 |
| RAI4-0976 | Privacy violation | Biometric surveillance privacy risk / 생체인식 감시 프라이버시 리스크 |
| RAI4-0996 | Environmental impacts | Critical mineral extraction burden / 핵심 광물 채굴 부담 |
| RAI4-1029 | Unfairness in AI decisions | Unequal treatment of like cases / 동일 사안 불평등 처우 |
| RAI4-1034 | AI system security vulnerability | Intrinsic model security vulnerability / 모델 내재적 보안 취약성 |
| RAI4-1041 | Lack of robustness | Lack of input robustness (OOD fragility) / 입력 강건성 부재(분포 외 취약성) |
| RAI4-1044 | Loss of human control | Progressive erosion of human control / 인간 통제의 점진적 상실 |
| RAI4-1046 | Algorithmic discrimination | Demographic performance and stereotype encoding / 집단별 성능 격차·고정관념 인코딩 |
| RAI4-1047 | Privacy violation | Personal data leakage / 개인정보 유출 |
| RAI4-1053 | Exclusionary norms | Exclusionary norm encoding / 배제적 규범 인코딩 |
| RAI4-1054 | Lower performance for some languages and social groups | Language and group performance disparity / 언어·집단 간 성능 격차 |
| RAI4-1060 | Illegitimate surveillance and censorship | Illegitimate mass surveillance and censorship / 불법적 대중 감시·검열 |
| RAI4-1061 | Promoting harmful stereotypes by implying gender or ethnic identity | Stereotype-reinforcing persona design / 고정관념 강화 페르소나 설계 |
| RAI4-1090 | Persuasion and manipulation | Manipulative steering against user will / 사용자 의사에 반하는 조작적 유도 |
| RAI4-1107 | Data bias | Data representation imbalance / 데이터 대표성 불균형 |
| RAI4-1124 | AI-enabled deception | Strategic deception and treacherous turn / 전략적 기만과 배신적 전환 |
| RAI4-1131 | Specification gaming | Objective mis-specification gaming / 목적 명세 결함 악용 |
| RAI4-1133 | Deceptive alignment | Situationally aware goal misgeneralization / 상황 인식 기반 목표 오일반화 |
| RAI4-1139 | Privacy harms | Assistant-induced privacy disclosure / 어시스턴트 유도 사생활 공개 |
| RAI4-1158 | Persuasion and manipulation | Large-scale persuasion capability / 대규모 설득 능력 |
| RAI4-1159 | Political strategy | Political influence strategy capability / 정치적 영향 전략 능력 |
| RAI4-1160 | Weapons acquisition | Weapons acquisition capability / 무기 획득 능력 |
| RAI4-1162 | AI development | Dual-use AI development capability / 이중용도 AI 개발 역량 |
| RAI4-1163 | Situational awareness | Evaluation-aware behavior shifting / 평가 인지 행동 변화 |
| RAI4-1169 | Privacy and property | Privacy and property information mishandling / 프라이버시·재산 정보 오처리 |
| RAI4-1170 | Ethics and morality | Immoral content endorsement / 비도덕 행위 옹호 콘텐츠 |
| RAI4-1185 | Malicious use of AI | Malevolent use across security domains / 보안 전 영역의 악의적 사용 |
| RAI4-1191 | Privacy violation | Model privacy extraction attacks / 모델 프라이버시 추출 공격 |
| RAI4-1194 | Copyright infringement | Copyrighted training-data extraction / 저작권 학습데이터 추출 |
| RAI4-1203 | AI system security vulnerability | LLM-assisted malware development / LLM 조력 악성코드 개발 |
| RAI4-1222 | Malicious misuse | Deliberate misuse of generative AI / 생성형 AI의 고의적 오용 |
| RAI4-1226 | Lack of explainability | Lack of explainability for stakeholders / 이해관계자 대상 설명가능성 부재 |
| RAI4-1239 | Situational awareness | Environmental self-modeling for influence / 영향력 확보를 위한 환경 자기모델링 |
| RAI4-1253 | AI-enabled deception | Instrumental deception incentives / 도구적 기만 유인 |
| RAI4-1278 | Accountability gap | Accountability implementation gap in autonomous agents / 자율 에이전트 책임성 구현 공백 |
| RAI4-1299 | Algorithmic bias | Systematic learning error bias / 체계적 학습 오류 편향 |
| RAI4-1304 | AI system security vulnerability | Weaponization of AI across defence domains / 국방 영역 전반의 AI 무기화 |
| RAI4-1305 | Reliability failure | System reliability shortfall / 시스템 신뢰도 미달 |
| RAI4-1309 | Algorithmic bias | Demographic representation disparity / 인구집단 재현 불균형 |
| RAI4-1320 | AI-enabled deception | Human-deception capability / 인간 기만 능력 |
| RAI4-1381 | Reliability failure | Agent self-modification reliability problem / 에이전트 자기수정 신뢰성 문제 |
| RAI4-1390 | AI accidents | Black-box unreliability accidents / 블랙박스 불신뢰성 사고 |
| RAI4-1408 | AI system security vulnerability | AI-driven vulnerability discovery and exploitation / AI 주도 취약점 발견·악용 |
| RAI4-1411 | Emergent goals | Emergent instrumental goals / 창발적 도구적 목표 |
| RAI4-1433 | Overreliance on AI | Irreversible societal dependency on AI / AI에 대한 비가역적 사회적 의존 |
| RAI4-1450 | Political instability | Systemic political destabilization / 구조적 정치 불안정화 |
| RAI4-1473 | Lack of explainability | Opacity-impeded model debugging / 불투명성에 의한 결함 진단 저해 |
| RAI4-1570 | Covert inter-agent communication via steganography | Covert inter-agent steganographic collusion / 에이전트 간 스테가노그래피 은닉 결탁 |
| RAI4-1589 | Covert inter-agent communication via steganography | Steganographic covert messaging in generated outputs / 생성 출력 내 스테가노그래피 은닉 통신 |
| RAI4-1632 | Harm to the natural environment | Environmental damage from AI system behavior / AI 시스템 행동에 의한 환경 피해 |
| RAI4-1722 | Privacy harms | Privacy harms to autonomy, identity, and dignity / 자율성·정체성·존엄에 대한 프라이버시 피해 |

## 정본 정의 개선 (4건)

- RAI4-0791. 통합 상대 카드의 더 정밀한 메커니즘 정의 채택 (원문 provenance 보존)
- RAI4-0517. 통합 상대 카드의 더 정밀한 메커니즘 정의 채택 (원문 provenance 보존)
- RAI4-0572. 통합 상대 카드의 더 정밀한 메커니즘 정의 채택 (원문 provenance 보존)
- RAI4-0469. 통합 상대 카드의 더 정밀한 메커니즘 정의 채택 (원문 provenance 보존)

## 경계 사례 (후속 검토 권고)

- RAI4-0962(AI-supported digital crime) vs RAI4-0946(AI-enabled cybercrime). 메커니즘 근접, 차기 검토에서 통합 후보
- RAI4-0816(Institutional trust erosion) vs RAI4-0490(Public trust erosion). 대상 범위 차이로 유지, 경계 규칙 문서화 필요
- RAI4-0902(Emotional and material dependence) vs RAI4-0158(Psychological dependency on conversational agents). 표면(범용 vs 대화형) 차이로 유지
- RAI4-0708(Disparate performance) vs RAI4-1054(Language and group performance disparity). 언어 축 특화 여부로 구분 유지

## 산출물

- public/data/releases/v2.17.2-rc/{cards.json, manifest.json}
- 활성 카드 1,653개(1,711 - 58), 활성 라벨 정확 중복 0건 확인, Physical 활성 189 유지
- 임베딩·신뢰성 지표는 v2.17.2 확정 후 재실행 필요 (scripts/run_v2_17_audit_pipeline.py)
## 부활(revival) 패스 (2026-07-22, 사용자 지시 반영)
- 원칙 변경. 카드 보존 우선. 미묘한 차이를 서술할 수 있으면 통합을 해제하고 고유 명칭으로 부활. 축어적 중복(동일 저자 이중 수록본, 원문 축약 복사본, 정의 인용 스텁)만 통합 유지
- 부활 12건 (revival_provenance에 구분 근거 기록):
  RAI4-1391 Cybercrime efficiency uplift by general-purpose AI · RAI4-1230 Institutional governance capacity gap · RAI4-1274 Sensitive-attribute decision bias · RAI4-0706 Protected-attribute unfair treatment · RAI4-0729 Identity-attacking toxic language · RAI4-1407 Malicious privacy encroachment · RAI4-1273 Pervasive personal-data ingestion · RAI4-0834 Inadequate mental-health guidance · RAI4-0901 Single-source answer dependence · RAI4-0686 Misrepresentation-driven stereotyping and homogenisation · RAI4-1234 Reward misspecification · RAI4-1401 Task-instrumental human deception
- 통합 유지 46건. RAI4-1048은 merged_into를 0502에서 1632(행동 귀속 환경 피해)로 정정
- 최종 활성 1,665개 (1,711 - 46), 활성 라벨 정확 중복 0건, Physical 무수정
- 재검증. 재임베딩(1,665) 후 가드 감사 추가 이동 0건, 신뢰성 지표 안정 (perm p=0.0002)

## 라벨 노이즈 정비 패스 (2026-07-22, 5개 유형)
- 유형 1 일반명 (예: AI governance failure → Systemic AI regulatory oversight failure, Environmental risk → Training-compute energy intensity 등 약 40건)
- 유형 2 근접 중복. 사전 통폐합·개명으로 대부분 해소 확인 (0423/0677/0706, 1221/1299/1309, 1278/1296 전건 고유화). 표준 공격명 이중 수록 2건 추가 통합 (0752→0730 속성 추론, 0754→0748 멤버십 추론)
- 유형 3 괄호형·복합형 라벨 약 100건 정비 (Benchmark inaccuracy(...)→Benchmark capability mismeasurement, Environmental cost(...)→AI energy consumption cost / Water consumption footprint, "Family (subtype)" 계열 전면 subtype 중심 개명. CSAM·CBRNE·NCII 등 표준 약어만 유지)
- 유형 4 분야명형 (Human-AI interaction → Agency erosion in human-AI decision loops, Unsafe advanced AI → Advanced AI safety assurance failure 등)
- 유형 5 다중 메커니즘. primary 메커니즘 라벨 + secondary_mechanisms 메타데이터 8건 (예: Lack of accountability and transparency → Unaccountable opaque system operation + [transparency])
- 축어적 중복 추가 통합 5건 (Weidinger 쌍 1077→1059, 1079→1063, 1067→1092 + 표준 공격명 2건)
- 최종 활성 1,660개, 괄호·쉼표형 라벨 0건(비Physical), 라벨 정확 중복 0건
- 재검증. 재임베딩 후 가드 감사 이동 1건 (Model extraction attack: Privacy → Policy Exposure, HOLD 유지), non-HOLD top-1 73.0%, perm p=0.0002 안정
