#!/usr/bin/env python3
"""Add source-faithful Korean guideline terminology to the public glossary."""

from __future__ import annotations

import html
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GLOSSARY = ROOT / "glossary.html"
INDEX = ROOT / "index.html"
DATA = ROOT / "data" / "glossary" / "korean_guideline_terms_20260907.json"

KOSA = "https://www.sw.or.kr/site/sw/ex/board/View.do?bcIdx=64993&cbIdx=390"
MSIT_EN = "https://www.msit.go.kr/eng/bbs/view.do?bbsSeqNo=42&nttSeqNo=1215"
ETHICS = "https://www.kisdi.re.kr/bbs/view.do?bbsSn=115104&key=m2101113055944"
PIPC = "https://pipc.go.kr/np/cop/bbs/selectBoardArticle.do?bbsId=BS217&mCode=G010030000&nttId=11680"
KCC = "https://www.copyright.or.kr/information-materials/publication/research-report/view.do?brdclasscode=&brdctsno=55211&brdctsstatecode=&nationcode=&searchTarget=ALL&searchText=&servicecode=06"
NCF = "https://www.ncfoundation.or.kr/business/ai"
IAAE = "https://www.iaae.ai/emotionalAIguideline"


def term(en: str, ko: str, en_def: str, ko_def: str, cat: str, source: str,
         source_label: str, page: str) -> dict[str, str]:
    return {
        "en": en,
        "ko": ko,
        "definition_en": en_def,
        "definition_ko": ko_def,
        "category": cat,
        "source_url": source,
        "source_label": source_label,
        "page": page,
        "tag": "ko",
        "language_status": "Korean source wording; English is an unofficial translation",
    }


TERMS = [
    term("AI technology", "인공지능기술",
         "Hardware or software technology necessary to implement artificial intelligence, or technology for its application. (unofficial translation)",
         "인공지능을 구현하기 위하여 필요한 하드웨어ㆍ소프트웨어 기술 또는 그 활용 기술.",
         "gen", KOSA, "고영향 인공지능 판단 가이드라인", "PDF p. 11"),
    term("AI development operator", "인공지능개발사업자",
         "A person that develops and provides artificial intelligence. (unofficial translation)",
         "인공지능을 개발하여 제공하는 자.",
         "law", KOSA, "고영향 인공지능 판단 가이드라인", "PDF p. 11"),
    term("AI utilization operator", "인공지능이용사업자",
         "A person that provides an AI product or AI service by using artificial intelligence supplied by an AI development operator. (unofficial translation)",
         "인공지능개발사업자가 제공한 인공지능을 이용하여 인공지능제품 또는 인공지능서비스를 제공하는 자.",
         "law", KOSA, "고영향 인공지능 판단 가이드라인", "PDF p. 11"),
    term("AI product", "인공지능제품",
         "A product that is, or contains as a component, an AI system, including a product that connects to an AI system to perform a required function. (unofficial translation)",
         "인공지능시스템 또는 이를 요소로 포함하는 제품으로서, 인공지능시스템에 접속하여 필요로 하는 기능을 수행하는 것을 포함한다.",
         "gen", KOSA, "고영향 인공지능 판단 가이드라인", "PDF p. 11"),
    term("AI service", "인공지능서비스",
         "A service that enables use of artificial intelligence, an AI system, or an AI product and provides functions such as information analysis, prediction, recommendation, or creation. (unofficial translation)",
         "인공지능, 인공지능시스템 또는 인공지능제품을 활용할 수 있도록 제공하는 서비스로 정보 분석, 예측, 추천, 창작 등의 기능을 제공하는 것을 말한다.",
         "gen", KOSA, "고영향 인공지능 판단 가이드라인", "PDF p. 11"),
    term("AI lifecycle", "인공지능 수명주기",
         "The entire process from development, deployment, and operation of artificial intelligence through its disposal. (unofficial translation)",
         "인공지능의 개발, 배포, 운영 및 폐기에 이르기까지의 전 과정.",
         "gen", KOSA, "고영향 인공지능 사업자 책무 가이드라인", "PDF p. 11"),
    term("Cumulative compute", "누적연산량",
         "The total amount of computation used to train artificial intelligence, expressed in floating point operations (FLOPs). (unofficial translation)",
         "인공지능 학습에 사용된 총 연산량을 말하며, 부동소수점연산(Floating Point Operations, FLOPs)으로 표기한다.",
         "gen", KOSA, "인공지능 안전성 확보 가이드라인", "PDF p. 9"),
    term("AI-related safety incident", "인공지능 관련 안전사고",
         "A case in which a risk materializes because of an AI malfunction or similar event, or serious harm to public safety occurs. (unofficial translation)",
         "인공지능의 장애 등으로 인하여 위험이 현실적으로 발생하거나 공공의 안전에 중대한 위해가 발생한 경우.",
         "risk", KOSA, "인공지능 안전성 확보 가이드라인", "PDF p. 9"),
    term("Risk (Korean AI Safety Guideline)", "위험 (인공지능 안전성 확보 가이드라인)",
         "The likelihood that human life, bodily safety, or fundamental rights will be infringed throughout the AI lifecycle, together with the severity of the potential harm. (unofficial translation)",
         "인공지능 수명주기 전반에 걸쳐 사람의 생명ㆍ신체의 안전 또는 기본권이 침해될 가능성과 그 잠재적 피해의 심각성.",
         "risk", KOSA, "인공지능 안전성 확보 가이드라인", "PDF p. 9"),
    term("Risk management system (Korean AI Safety Guideline)", "위험관리체계 (인공지능 안전성 확보 가이드라인)",
         "A system that specifies the authority and obligations of responsible parties that monitor and respond to AI-related safety incidents. (unofficial translation)",
         "인공지능 관련 안전사고를 모니터링하고 대응하는 책임 주체의 권한과 의무 등을 규정한 체계.",
         "law", KOSA, "인공지능 안전성 확보 가이드라인", "PDF p. 9"),
    term("Fundamental rights", "기본권",
         "Inviolable basic rights of citizens, including human dignity and worth and the right to pursue happiness, which the state has a duty to affirm and guarantee. (unofficial translation)",
         "인간 존엄성과 가치, 행복을 추구할 권리 등 국가가 확인ㆍ보장할 의무를 지니고 있는 국민의 불가침한 기본적 권리.",
         "law", KOSA, "고영향 인공지능 영향평가 가이드라인", "PDF p. 8"),
    term("AI impact assessment (Korean Framework Act)", "인공지능 영향평가 (인공지능기본법)",
         "A procedure through which an AI business operator assesses in advance the effects on fundamental rights when providing a product or service using high-impact AI. (unofficial translation)",
         "인공지능사업자가 고영향 인공지능을 이용한 제품 또는 서비스를 제공하는 경우, 사전에 사람의 기본권에 미치는 영향을 평가하기 위한 절차.",
         "law", KOSA, "고영향 인공지능 영향평가 가이드라인", "PDF p. 8"),
    term("Prior notice requirement", "사전 고지 의무",
         "The obligation to inform users in advance that a product or service is operated on the basis of high-impact AI or generative AI. (unofficial translation)",
         "고영향 인공지능이나 생성형 인공지능을 이용한 제품ㆍ서비스가 인공지능에 기반하여 운용된다는 사실을 이용자에게 사전에 고지해야 하는 의무.",
         "law", KOSA, "인공지능 투명성 확보 가이드라인", "PDF p. 5"),
    term("Labeling requirement", "표시 의무",
         "The obligation of an AI business operator that provides a product or service using generative AI to indicate that its output was generated by generative AI. (unofficial translation)",
         "생성형 인공지능을 활용한 제품ㆍ서비스를 제공하는 인공지능사업자가 그 결과물이 생성형 인공지능에 의해 생성되었다는 사실을 표시해야 하는 의무.",
         "law", KOSA, "인공지능 투명성 확보 가이드라인", "PDF p. 5"),
    term("Human-recognizable labeling", "사람이 인식할 수 있는 표시 방법",
         "A method that communicates that content is AI-generated through a form people can perceive, such as visible wording, a visual identifier, or an audible notice. (unofficial translation)",
         "사람이 시각 또는 청각으로 인식할 수 있는 문구, 시각적 식별자 또는 음성 안내 등을 통해 결과물이 인공지능으로 생성되었다는 사실을 표시하는 방법.",
         "law", KOSA, "인공지능 투명성 확보 가이드라인", "PDF pp. 5-6"),
    term("Machine-readable labeling", "기계가 판독할 수 있는 표시 방법",
         "A method that embeds machine-readable information, such as metadata, to indicate that content is AI-generated; at least one textual or audible notice must also be provided. (unofficial translation)",
         "메타데이터 등 기계가 판독할 수 있는 정보를 삽입하여 결과물이 인공지능으로 생성되었다는 사실을 표시하는 방법으로, 최소 1회 이상 안내 문구 또는 음성 등을 함께 제공해야 한다.",
         "law", KOSA, "인공지능 투명성 확보 가이드라인", "PDF pp. 5-6"),
    term("Artistic and creative work", "예술적ㆍ창의적 표현물",
         "An output resulting from creative expressive activity, including art, film, literature, photography, publishing, comics, games, and animation. (unofficial translation)",
         "미술, 영화, 문학, 사진, 출판, 만화, 게임, 애니메이션 등 창의적 표현 활동에 따른 결과물.",
         "law", KOSA, "인공지능 투명성 확보 가이드라인", "PDF p. 5"),
    term("AI actor", "AI 행위자",
         "An individual or organization that performs a substantive role in the AI lifecycle or is directly or indirectly involved in it, including AI providers, users, government, public institutions, and civil society. (unofficial translation)",
         "AI 생애주기에서 실질적인 역할을 수행하거나 그 과정에 직간접적으로 관여하는 개인과 조직을 말한다. AI 공급자와 이용자를 비롯하여 정부, 공공기관, 시민사회 등 AI 생애주기에 관여하는 다양한 주체를 포함한다.",
         "gen", ETHICS, "대한민국 인공지능 윤리원칙", "PDF p. 3"),
    term("AI provider (Korean AI Ethics Principles)", "AI 공급자",
         "An individual or organization involved in planning, data processing, development, provision, operation, or management of an AI system or AI-enabled product or service across the AI lifecycle. (unofficial translation)",
         "AI 생애주기에서 AI 시스템 또는 AI가 적용된 제품ㆍ서비스의 기획, 데이터 처리, 개발, 제공, 운영 및 관리에 관여하는 개인과 조직.",
         "gen", ETHICS, "대한민국 인공지능 윤리원칙", "PDF p. 3"),
    term("AI user (Korean AI Ethics Principles)", "AI 이용자",
         "An individual or organization that receives and uses an AI system or AI-enabled product or service, or applies it to work or other activities. (unofficial translation)",
         "AI 시스템 또는 AI가 적용된 제품ㆍ서비스를 제공받아 이용하거나 업무ㆍ활동에 활용하는 개인과 조직.",
         "gen", ETHICS, "대한민국 인공지능 윤리원칙", "PDF p. 3"),
    term("Human dignity", "인간의 존엄성",
         "A value directing AI development and use toward a human-centered society in which every person is respected as an end in themselves and fully enjoys dignity and human rights. (unofficial translation)",
         "AI의 개발과 활용에서 인간을 중심에 두고, 모든 사람이 수단이 아닌 목적 그 자체로 존중받으며 존엄과 인권을 온전히 누릴 수 있는 사회를 지향하는 가치.",
         "gen", ETHICS, "대한민국 인공지능 윤리원칙", "PDF p. 4"),
    term("Common good of society", "사회의 공공선",
         "A value directing AI benefits not only toward improving individual lives but also toward a society in which social trust and shared interests advance together. (unofficial translation)",
         "AI가 만들어 내는 편익이 개인의 삶을 나아지게 하는 데 그치지 않고, 사회적 신뢰와 공동의 이익이 함께 증진되는 사회를 지향하는 가치.",
         "gen", ETHICS, "대한민국 인공지능 윤리원칙", "PDF p. 4"),
    term("Sustainability of humanity", "인류의 지속가능성",
         "A value directing AI benefits and opportunities to be shared by present and future generations while sustaining the environmental and social foundations of human life. (unofficial translation)",
         "AI가 만들어 내는 편익과 가능성을 현재와 미래 세대가 함께 누리며, 인류의 삶을 뒷받침하는 환경과 사회의 기반이 지속되는 미래를 지향하는 가치.",
         "gen", ETHICS, "대한민국 인공지능 윤리원칙", "PDF p. 4"),
    term("Human-centeredness", "인간중심성",
         "The principle that AI actors develop and use AI to support human judgment and choice and strengthen creativity and problem-solving, define the scope of AI roles, enable human intervention when needed, and guard against overreliance. (unofficial translation)",
         "AI 행위자가 AI를 사람의 판단과 선택을 지원하고 창의성과 문제 해결 역량을 강화하는 방향으로 개발ㆍ활용하며, AI의 역할 범위를 구체적으로 설정하고 필요한 경우 사람이 개입할 수 있도록 하고, 과도한 의존을 경계하는 원칙.",
         "gen", ETHICS, "대한민국 인공지능 윤리원칙", "PDF p. 5"),
    term("Privacy protection", "프라이버시 보호",
         "The principle that AI actors prevent AI from being used for unjust surveillance or invasion of privacy, process personal information only as necessary for specified purposes, and respect data subjects' right to informational self-determination. (unofficial translation)",
         "AI 행위자가 AI가 부당한 감시 등 타인의 사생활을 침해하는 데 활용되지 않도록 하고, AI 생애주기 전반에서 개인정보를 정해진 목적에 한해 필요한 범위에서 처리하며, 정보주체의 개인정보 자기결정권을 존중하는 원칙.",
         "gen", ETHICS, "대한민국 인공지능 윤리원칙", "PDF p. 5"),
    term("Fairness and inclusiveness", "공정성ㆍ포용성",
         "The principle that AI actors prevent unfair discrimination and bias, promote equitable access to AI benefits and opportunities, and recognize stakeholder participation throughout AI development and use. (unofficial translation)",
         "AI 행위자가 AI 개발 및 활용 전 과정에서 부당한 차별과 편향을 방지하고, 모든 사람이 AI에 접근하여 혜택과 기회를 공평하게 누리며, 이해관계자의 참여를 보장하도록 노력하는 원칙.",
         "gen", ETHICS, "대한민국 인공지능 윤리원칙", "PDF p. 5"),
    term("Reliability (Korean AI Ethics Principles)", "신뢰성 (대한민국 인공지능 윤리원칙)",
         "The principle that an AI system meets minimum performance requirements for its purpose and context, operates within its intended purpose and authorized scope, and maintains stable and consistent performance across relevant conditions. (unofficial translation)",
         "AI의 목적과 활용 맥락에 필요한 최소 성능 기준을 충족하고, 의도된 목적과 허용된 권한 범위 안에서 작동하며, 다양한 사용 조건에서 성능과 작동 상태가 안정적이고 일관되게 유지되도록 하는 원칙.",
         "gen", ETHICS, "대한민국 인공지능 윤리원칙", "PDF p. 6"),
    term("Personal information (Korean PIPA)", "개인정보 (개인정보 보호법)",
         "Information relating to a living individual that identifies the individual directly or can identify the individual when readily combined with other information; pseudonymized information is also included. (unofficial translation)",
         "살아있는 개인에 관한 정보로서 성명, 주민등록번호 및 영상 등을 통하여 개인을 알아볼 수 있는 정보와, 해당 정보만으로는 특정 개인을 알아볼 수 없더라도 다른 정보와 쉽게 결합하여 개인을 알아볼 수 있는 정보. 추가 정보 없이는 특정 개인을 알아볼 수 없도록 가명처리한 정보도 포함한다.",
         "law", PIPC, "개인정보 영향평가 수행안내서(2025.10. 개정)", "PDF p. 15"),
    term("Processing of personal information", "처리",
         "Collection, generation, interconnection, linkage, recording, storage, retention, alteration, editing, retrieval, output, correction, restoration, use, provision, disclosure, destruction, or a similar act involving personal information. (unofficial translation)",
         "개인정보의 수집, 생성, 연계, 연동, 기록, 저장, 보유, 가공, 편집, 검색, 출력, 정정, 복구, 이용, 제공, 공개, 파기, 그 밖에 이와 유사한 행위.",
         "law", PIPC, "개인정보 영향평가 수행안내서(2025.10. 개정)", "PDF p. 15"),
    term("Data subject (Korean PIPA)", "정보주체",
         "A person who is identifiable by the information being processed and is the subject of that information. (unofficial translation)",
         "처리되는 정보에 의하여 알아볼 수 있는 사람으로서 그 정보의 주체가 되는 사람.",
         "law", PIPC, "개인정보 영향평가 수행안내서(2025.10. 개정)", "PDF p. 15"),
    term("Personal information file", "개인정보파일",
         "A collection of personal information systematically arranged or organized under defined rules so that the information can be readily retrieved. (unofficial translation)",
         "개인정보를 쉽게 검색할 수 있도록 일정한 규칙에 따라 체계적으로 배열하거나 구성한 개인정보의 집합물.",
         "law", PIPC, "개인정보 영향평가 수행안내서(2025.10. 개정)", "PDF p. 15"),
    term("Personal information controller", "개인정보처리자",
         "A public institution, legal person, organization, individual, or other entity that processes personal information directly or through another person to operate a personal information file for work purposes. (unofficial translation)",
         "업무를 목적으로 개인정보파일을 운용하기 위하여 스스로 또는 다른 사람을 통하여 개인정보를 처리하는 공공기관, 법인, 단체 및 개인 등.",
         "law", PIPC, "개인정보 영향평가 수행안내서(2025.10. 개정)", "PDF p. 15"),
    term("Fixed visual data processing device", "고정형 영상정보처리기기",
         "A device installed in a fixed space that continuously or periodically captures images of people or objects or transmits them over wired or wireless networks. (unofficial translation)",
         "일정한 공간에 설치되어 지속적 또는 주기적으로 사람 또는 사물의 영상 등을 촬영하거나 이를 유ㆍ무선망을 통하여 전송하는 장치.",
         "law", PIPC, "개인정보 영향평가 수행안내서(2025.10. 개정)", "PDF p. 15"),
    term("Mobile visual data processing device", "이동형 영상정보처리기기",
         "A device worn or carried by a person, or attached to or mounted on a movable object, that captures images of people or objects or transmits them over wired or wireless networks. (unofficial translation)",
         "사람이 신체에 착용 또는 휴대하거나 이동 가능한 물체에 부착 또는 거치하여 사람 또는 사물의 영상 등을 촬영하거나 이를 유ㆍ무선망을 통하여 전송하는 장치.",
         "law", PIPC, "개인정보 영향평가 수행안내서(2025.10. 개정)", "PDF p. 16"),
    term("Sensitive information (Korean PIPA)", "민감정보 (개인정보 보호법)",
         "Personal information concerning ideology, beliefs, trade-union or political-party membership, political views, health, sex life, genetic information, criminal records, biometric information for uniquely identifying a person, race, ethnicity, or other matters whose processing may seriously infringe privacy. (unofficial translation)",
         "사상ㆍ신념, 노동조합ㆍ정당의 가입ㆍ탈퇴, 정치적 견해, 건강, 성생활, 유전정보, 범죄경력자료, 특정 개인을 알아볼 목적으로 생성한 신체적ㆍ생리적ㆍ행동적 특징 정보, 인종이나 민족에 관한 정보 등 정보주체의 사생활을 현저히 침해할 우려가 있는 개인정보.",
         "law", PIPC, "개인정보 영향평가 수행안내서(2025.10. 개정)", "PDF p. 16"),
    term("Unique identifying information", "고유식별정보",
         "Identifiers assigned under law to uniquely distinguish an individual, namely resident registration number, passport number, driver's licence number, and alien registration number. (unofficial translation)",
         "법령에 따라 개인을 고유하게 구별하기 위하여 부여된 식별정보로서 주민등록번호, 여권번호, 운전면허번호, 외국인등록번호를 의미한다.",
         "law", PIPC, "개인정보 영향평가 수행안내서(2025.10. 개정)", "PDF p. 16"),
    term("Personal information handler", "개인정보취급자",
         "A person who handles personal information under the direction and supervision of a personal information controller, including employees, dispatched workers, and part-time workers. (unofficial translation)",
         "개인정보처리자의 지휘ㆍ감독을 받아 개인정보를 처리하는 업무를 담당하는 자로서 임직원, 파견근로자, 시간제근로자 등을 말한다.",
         "law", PIPC, "개인정보 영향평가 수행안내서(2025.10. 개정)", "PDF p. 16"),
    term("Personal information processing system", "개인정보처리시스템",
         "A systematically configured system, such as a database system, that can process personal information. (unofficial translation)",
         "데이터베이스시스템 등 개인정보를 처리할 수 있도록 체계적으로 구성한 시스템.",
         "law", PIPC, "개인정보 영향평가 수행안내서(2025.10. 개정)", "PDF p. 16"),
    term("Risk analysis (personal information)", "위험도 분석",
         "A comprehensive analysis that identifies and evaluates risk factors that may contribute to personal information leakage and establishes measures to control them appropriately. (unofficial translation)",
         "개인정보 유출에 영향을 미칠 수 있는 다양한 위험요소를 식별ㆍ평가하고 해당 위험요소를 적절하게 통제할 수 있는 방안 마련을 위해 종합적으로 분석하는 행위.",
         "risk", PIPC, "개인정보 영향평가 수행안내서(2025.10. 개정)", "PDF p. 16"),
    term("Privacy impact assessment (Korea)", "개인정보 영향평가",
         "An assessment conducted by the head of a public institution to analyze risk factors and identify improvements when operating a qualifying personal information file may infringe data subjects' personal information. (unofficial translation)",
         "공공기관의 장이 개인정보파일의 운용으로 인하여 정보주체의 개인정보 침해가 우려되는 경우에 그 위험요인의 분석과 개선 사항 도출을 위해 수행하는 평가.",
         "law", PIPC, "개인정보 영향평가 수행안내서(2025.10. 개정)", "PDF p. 17"),
    term("Privacy impact assessment institution", "개인정보 영향평가기관",
         "A legal person designated by the Personal Information Protection Commission to conduct a public institution's privacy impact assessment after meeting all statutory requirements. (unofficial translation)",
         "공공기관의 개인정보 영향평가를 수행하기 위하여 법정 요건을 모두 갖추고 개인정보보호위원회가 지정한 법인.",
         "law", PIPC, "개인정보 영향평가 수행안내서(2025.10. 개정)", "PDF p. 17"),
    term("Target system (privacy impact assessment)", "대상시스템",
         "An information system intended to establish, operate, change, or interconnect a personal information file subject to a privacy impact assessment. (unofficial translation)",
         "개인정보 영향평가 대상 개인정보파일을 구축ㆍ운용, 변경 또는 연계하려는 정보시스템.",
         "law", PIPC, "개인정보 영향평가 수행안내서(2025.10. 개정)", "PDF p. 17"),
    term("Generative AI training", "생성형 인공지능 학습(GAI 학습)",
         "A process in which data containing works are collected and preprocessed, and a generative AI model learns statistical rules and patterns that are fixed in its internal parameters. (unofficial translation)",
         "생성형 인공지능 모델을 구현하기 위해 저작물이 포함된 데이터를 수집하고, 이를 전처리한 데이터를 이용해 모델이 통계적 규칙ㆍ패턴을 학습하여 내부 매개변수로 고정시키는 일련의 과정.",
         "law", KCC, "생성형 인공지능의 저작물 학습에 대한 저작권법상 공정이용 안내서", "PDF p. 9"),
    term("Generative AI output", "생성형 인공지능 결과물(GAI 결과물)",
         "Text, audio, video, or another output generated when a user enters a specific request or prompt into generative AI. (unofficial translation)",
         "이용자가 생성형 인공지능에 특정한 요구인 프롬프트를 입력함에 따라 텍스트, 오디오, 비디오 등으로 생성된 것.",
         "law", KCC, "생성형 인공지능의 저작물 학습에 대한 저작권법상 공정이용 안내서", "PDF p. 9"),
    term("Generative AI-generated output", "생성형 인공지능 산출물(GAI 산출물)",
         "A generative AI output produced under human instruction without human creative contribution. (unofficial translation)",
         "인간의 지시에 따른 결과물 중 인간의 창작적 기여가 없는 생성형 인공지능 결과물.",
         "law", KCC, "생성형 인공지능의 저작물 학습에 대한 저작권법상 공정이용 안내서", "PDF p. 9"),
    term("Generative AI-assisted work", "생성형 인공지능 활용 저작물(GAI 활용 저작물)",
         "An output made by a human using generative AI as a tool in the creative process and containing a part for which human creative contribution can be recognized. (unofficial translation)",
         "인간이 창작 과정에서 생성형 인공지능을 도구로 활용하여 만들어낸 결과물로서 인간의 창작적 기여가 인정될 수 있는 부분이 있는 것.",
         "law", KCC, "생성형 인공지능의 저작물 학습에 대한 저작권법상 공정이용 안내서", "PDF p. 9"),
    term("Fair use (Korean Copyright Act)", "공정이용",
         "Use of a work that is permitted without the right holder's authorization when the statutory conditions are met, assessed by factors including purpose and character, type and purpose of the work, amount and substantiality used, and effect on the market. (unofficial translation)",
         "저작물의 통상적인 이용 방법과 충돌하지 않고 저작자의 정당한 이익을 부당하게 해치지 않는 경우에, 이용의 목적과 성격, 저작물의 종류와 용도, 이용된 부분의 비중과 중요성, 시장에 미치는 영향을 고려하여 저작물을 이용할 수 있도록 한 제도.",
         "law", KCC, "생성형 인공지능의 저작물 학습에 대한 저작권법상 공정이용 안내서", "PDF pp. 20-23"),
    term("Right holder opt-out", "권리자 옵트아웃(Opt-out)",
         "A reservation by a right holder, in an appropriate manner, of the right to prevent works lawfully accessible online from being used for text and data mining. (unofficial translation)",
         "온라인으로 공중에게 제공되는 저작물 등을 텍스트 및 데이터 마이닝에 이용하지 못하도록 권리자가 적절한 방식으로 권리를 유보하는 것.",
         "law", KCC, "생성형 인공지능의 저작물 학습에 대한 저작권법상 공정이용 안내서", "PDF p. 21"),
    term("Transformative use", "변형적 이용",
         "Use that does not merely replace the original work but adds a new purpose or character distinct from the original purpose. (unofficial translation)",
         "이용되는 저작물을 단순히 대체하는 것이 아니라 원저작물의 목적과 다른 새로운 목적이나 성격을 부가하는 이용.",
         "law", KCC, "생성형 인공지능의 저작물 학습에 대한 저작권법상 공정이용 안내서", "PDF p. 29"),
    term("Embedded EthiCS", "임베디드 에틱스(Embedded EthiCS)",
         "An educational approach that embeds ethical reasoning within computer science and engineering curricula by inserting ethics modules into disciplinary courses. (unofficial translation)",
         "컴퓨터공학 및 공학 전공 교과 과정 자체에 윤리적 사고를 내재화하는 교육 방법으로, 전공 수업 안에 윤리 모듈을 삽입해 수업 시간 일부를 윤리 교육에 할애한다.",
         "gen", NCF, "가장 인간적인 미래를 위한 다학제적 AI 윤리 교육: Embedded EthiCS", "PDF p. 6"),
    term("Ethics module", "윤리 모듈",
         "A course unit embedded in a computing or engineering class and designed through interdisciplinary collaboration to examine the ethical and social issues of the technology taught in that class. (unofficial translation)",
         "컴퓨터공학자와 철학자 등 다학제적 협력을 통해 설계되어 전공 수업 안에 삽입되고, 해당 수업의 기술이 야기할 윤리적ㆍ사회적 이슈를 검토하는 교육 단위.",
         "gen", NCF, "가장 인간적인 미래를 위한 다학제적 AI 윤리 교육: Embedded EthiCS", "PDF pp. 6-7"),
    term("Emotional AI", "감정교류AI",
         "AI used in an emotional-interaction context to recognize or analyze a user's emotional state, or to simulate or modulate emotional responses, using text, voice, facial expression, biometric signals, or other data. (unofficial translation)",
         "독립된 기술 범주가 아니라 인공지능이 감정교류적 맥락에서 활용될 때 나타나는 상호작용을 지칭하며, 텍스트, 음성, 얼굴 표정, 생체 신호 등 다양한 데이터를 바탕으로 사용자의 감정 상태를 인식ㆍ분석하거나 정서적 반응을 모의ㆍ조정하는 기능을 포함한다.",
         "gen", IAAE, "감정교류AI 윤리 가이드라인", "PDF p. 6"),
    term("Dedicated companion AI", "관계 지향형 AI 서비스",
         "A service designed primarily for emotional exchange and relationship formation that understands and empathizes with user emotions and builds a personalized relationship through sustained dialogue. (unofficial translation)",
         "정서적 교감과 관계 형성을 주된 목적으로 설계되어 사용자의 감정을 이해하고 공감하며, 지속적 대화를 통해 개인화된 관계를 구축하는 서비스.",
         "gen", IAAE, "감정교류AI 윤리 가이드라인", "PDF p. 6"),
    term("General-purpose conversational AI", "범용 대화형 AI",
         "A large-language-model service developed for multiple purposes such as information retrieval and content generation but also used for emotional support or counselling. (unofficial translation)",
         "정보 검색, 콘텐츠 생성 등 다목적으로 개발되었으나 사용자가 정서적 지지나 상담을 위해서도 활용하는 대규모 언어 모델 기반 서비스.",
         "gen", IAAE, "감정교류AI 윤리 가이드라인", "PDF p. 6"),
    term("Embedded emotion analytics AI", "임베디드 감정 분석 AI",
         "Technology integrated into another service or product to analyze a user's emotions for a specific purpose. (unofficial translation)",
         "다른 서비스나 제품에 통합되어 특정 목적을 위해 사용자의 감정을 분석하는 기술.",
         "gen", IAAE, "감정교류AI 윤리 가이드라인", "PDF p. 6"),
    term("ELIZA effect", "일라이자 효과(ELIZA effect)",
         "The tendency for users to attribute human characteristics to AI and form deep emotional bonds through sustained personalized interaction. (unofficial translation)",
         "지속적이고 개인화된 상호작용 과정에서 사용자가 AI에 인간적 특성을 부여하고 깊은 정서적 유대를 형성하는 현상.",
         "risk", IAAE, "감정교류AI 윤리 가이드라인", "PDF p. 8"),
]

REPLACEMENTS = {
    "Dark pattern": term(
        "Dark pattern", "다크 패턴",
        "A design that intentionally induces overdependence or otherwise impairs user autonomy and decision-making; the Emotional AI guideline identifies such deceptive design as a serious ethical problem. (unofficial translation)",
        "사용자 유지 등을 위해 의도적으로 과의존을 유도하거나 사용자의 자율성과 의사결정을 저해하는 기만적 설계로, 감정교류AI 윤리 가이드라인은 이를 심각한 윤리적 문제로 본다.",
        "risk", IAAE, "감정교류AI 윤리 가이드라인", "PDF p. 8"),
}

SUMMARY_TITLES = {
    "Prior notice requirement",
    "Labeling requirement",
    "Human-recognizable labeling",
    "Machine-readable labeling",
    "Human dignity",
    "Common good of society",
    "Sustainability of humanity",
    "Human-centeredness",
    "Privacy protection",
    "Fairness and inclusiveness",
    "Reliability (Korean AI Ethics Principles)",
    "Personal information (Korean PIPA)",
    "Sensitive information (Korean PIPA)",
    "Fair use (Korean Copyright Act)",
    "Right holder opt-out",
    "Transformative use",
    "Embedded EthiCS",
    "Ethics module",
    "Emotional AI",
    "Dedicated companion AI",
    "General-purpose conversational AI",
    "Embedded emotion analytics AI",
    "ELIZA effect",
    "Dark pattern",
}
for _item in TERMS + list(REPLACEMENTS.values()):
    if _item["en"] in SUMMARY_TITLES:
        _item["tag"] = "ad"
        _item["language_status"] = "Source-faithful summary; English is an unofficial translation unless the English title appears in the source"

SOURCE_ITEMS = [
    (KOSA, "인공지능기본법 주요 가이드라인 5종", "한국인공지능소프트웨어산업협회·인공지능기본법 지원데스크, 2026 · 판단, 책무, 안전성, 투명성, 영향평가 · 확인 2026-09-07"),
    (ETHICS, "대한민국 인공지능 윤리원칙", "과학기술정보통신부·정보통신정책연구원·관계부처 합동, 2026 · 3대 가치와 7대 원칙 · 확인 2026-09-07"),
    (PIPC, "개인정보 영향평가 수행안내서(2025.10. 개정)", "개인정보보호위원회, 2025 · 법정 용어와 영향평가 용어 · 확인 2026-09-07"),
    (KCC, "생성형 인공지능의 저작물 학습에 대한 저작권법상 공정이용 안내서", "한국저작권위원회, 2026 · 생성형 인공지능 학습·결과물·공정이용 용어 · 확인 2026-09-07"),
    (NCF, "가장 인간적인 미래를 위한 다학제적 AI 윤리 교육: Embedded EthiCS", "NC문화재단, 2026 · Embedded EthiCS와 윤리 모듈 · 확인 2026-09-07"),
    (IAAE, "감정교류AI 윤리 가이드라인", "국제인공지능윤리협회, 2025 · 감정교류AI와 서비스 유형 · 확인 2026-09-07"),
    (MSIT_EN, "Guidelines on Ensuring AI Transparency", "Ministry of Science and ICT, 2026 · official English release for notice and labelling terminology · 확인 2026-09-07"),
]


CAT_LABEL = {"gen": "일반", "risk": "리스크·보안", "law": "법·제도"}


def article(item: dict[str, str]) -> str:
    esc = html.escape
    name = esc(f"{item['en']} {item['ko']}".lower(), quote=True)
    tag = item.get("tag", "ko")
    tag_label = "원문 KO" if tag == "ko" else "요약"
    return (
        f'<article class="term" data-cat="{item["category"]}" data-name="{name}">\n'
        f'  <div class="term__head"><h3>{esc(item["en"])}</h3><span class="ko">{esc(item["ko"])}</span>\n'
        f'    <span class="cat cat--{item["category"]}">{CAT_LABEL[item["category"]]}</span><span class="tag tag--{tag}">{tag_label}</span></div>\n'
        f'  <div class="term__body">\n'
        f'    <p class="def def--en">{esc(item["definition_en"])}</p>\n'
        f'    <p class="def def--ko">{esc(item["definition_ko"])}</p>\n'
        f'    <p class="src"><a href="{esc(item["source_url"], quote=True)}" target="_blank" rel="noopener noreferrer">{esc(item["source_label"])} · {esc(item["page"])}</a></p>\n'
        f'  </div>\n'
        f'</article>'
    )


def title_of(block: str) -> str:
    match = re.search(r"<h3>(.*?)</h3>", block, flags=re.S)
    if not match:
        raise ValueError("term block without h3")
    return html.unescape(re.sub(r"<[^>]+>", "", match.group(1))).strip()


def rebuild_list(document: str) -> tuple[str, dict[str, int]]:
    start_marker = '  <div id="list">\n'
    end_marker = '\n  </div>\n  <p class="empty"'
    start = document.index(start_marker) + len(start_marker)
    end = document.index(end_marker, start)
    body = document[start:end]
    blocks = re.findall(r'<article class="term".*?</article>', body, flags=re.S)
    by_title = {title_of(block): block for block in blocks}
    if len(by_title) != len(blocks):
        raise ValueError("duplicate English term titles in existing glossary")

    if DATA.exists():
        previous = json.loads(DATA.read_text(encoding="utf-8"))
        current_new_titles = {item["en"] for item in TERMS}
        for old_item in previous.get("new_terms", []):
            old_title = old_item.get("en")
            if old_title and old_title not in current_new_titles:
                by_title.pop(old_title, None)

    for title, item in REPLACEMENTS.items():
        if title not in by_title:
            raise ValueError(f"replacement target missing: {title}")
        by_title[title] = article(item)
    for item in TERMS:
        by_title[item["en"]] = article(item)

    parts: list[str] = []
    current_letter = None
    for title in sorted(by_title, key=lambda value: value.casefold()):
        letter = re.sub(r"[^A-Za-z]", "", title)[:1].upper() or "Z"
        if letter != current_letter:
            parts.append(f'<h2 class="letter" id="L{letter}">{letter}</h2>')
            current_letter = letter
        parts.append(by_title[title])

    counts = {cat: sum(f'data-cat="{cat}"' in block for block in by_title.values())
              for cat in CAT_LABEL}
    counts["all"] = len(by_title)
    rebuilt = "\n".join(parts)
    return document[:start] + rebuilt + document[end:], counts


def update_counts(document: str, counts: dict[str, int]) -> str:
    total = counts["all"]
    document = re.sub(r"출처 기반 한·영 정의 \d+개", f"출처 기반 한·영 정의 {total}개", document)
    document = re.sub(r"출처 기반 한·영 정의 \d+개 \(A–Z 통합\)", f"출처 기반 한·영 정의 {total}개 (A–Z 통합)", document)
    document = re.sub(r'data-f="all">전체 \d+</button>', f'data-f="all">전체 {total}</button>', document)
    document = re.sub(r'data-f="gen">일반 \d+</button>', f'data-f="gen">일반 {counts["gen"]}</button>', document)
    document = re.sub(r'data-f="risk">리스크·보안 \d+</button>', f'data-f="risk">리스크·보안 {counts["risk"]}</button>', document)
    document = re.sub(r'data-f="law">법·제도 \d+</button>', f'data-f="law">법·제도 {counts["law"]}</button>', document)
    document = re.sub(r'<span class="count" id="count">\d+개 표시</span>', f'<span class="count" id="count">{total}개 표시</span>', document)
    return document


def add_sources(document: str) -> str:
    source_start = document.index('<section class="sources">')
    source_end = document.index("</ul></section>", source_start)
    source_section = document[source_start:source_end]
    additions = []
    for url, title, detail in SOURCE_ITEMS:
        escaped_url = html.escape(url, quote=True)
        if f'href="{escaped_url}"' in source_section:
            continue
        additions.append(
            f'<li><a href="{html.escape(url, quote=True)}" target="_blank" rel="noopener noreferrer"><b>{html.escape(title)}</b></a><br><span>{html.escape(detail)}<br>한국어 정의는 문서 원문을 보존하고 영어는 비공식 번역</span></li>'
        )
    if additions:
        marker = "</ul></section>"
        document = document.replace(marker, "".join(additions) + marker, 1)
    document = re.sub(r"확인일 \d{4}-\d{2}-\d{2}\.", "확인일 2026-09-07.", document)
    return document


def main() -> None:
    document = GLOSSARY.read_text(encoding="utf-8")
    document, counts = rebuild_list(document)
    document = update_counts(document, counts)
    document = add_sources(document)
    document = document.replace(
        "EU 인공지능법 · 인공지능기본법 · NIST · OWASP · MITRE ATLAS 출처 기반",
        "EU 인공지능법 · 인공지능기본법 · 국내 공식 가이드라인 · NIST · OWASP · MITRE ATLAS 출처 기반",
    )
    GLOSSARY.write_text(document, encoding="utf-8")

    index = INDEX.read_text(encoding="utf-8")
    index = re.sub(r">\d+ terms · 한·영 · A–Z · HTML<", f">{counts['all']} terms · 한·영 · A–Z · HTML<", index)
    INDEX.write_text(index, encoding="utf-8")

    DATA.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": "2026-09-07",
        "scope": "Terms extracted from ten user-provided Korean policy and guidance PDFs",
        "translation_note": "Korean names and definitions preserve source wording. English renderings are unofficial unless the source itself supplies the English label.",
        "new_terms": TERMS,
        "updated_terms": list(REPLACEMENTS.values()),
        "sources": [
            {"url": url, "title": title, "verification": detail}
            for url, title, detail in SOURCE_ITEMS
        ],
        "counts_after_update": counts,
    }
    DATA.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(counts, ensure_ascii=False))


if __name__ == "__main__":
    main()
