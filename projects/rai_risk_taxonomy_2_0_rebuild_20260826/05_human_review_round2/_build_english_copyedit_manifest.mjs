import fs from "node:fs/promises";
import { createHash } from "node:crypto";
import { Workbook } from "@oai/artifact-tool";

const outputPath = new URL("../02_working/specifications/human_review_round2/L4_English_Copyedit_Approved_20260829.csv", import.meta.url);
const domains = ["General", "Agentic", "Physical"];
const replacements = [
  ["promptformat", "prompt-format"],
  ["humanwritten", "human-written"],
  ["generalpurpose", "general-purpose"],
  ["decisionmaking", "decision-making"],
  ["attackerchosen", "attacker-chosen"],
  ["communityspecific", "community-specific"],
  ["firststrike", "first-strike"],
  ["fullbody", "full-body"],
  ["humanimperceptible", "human-imperceptible"],
  ["humaninteraction", "human-interaction"],
  ["lowand middle-income", "low- and middle-income"],
  ["memorybased", "memory-based"],
  ["foundation-modelbased", "foundation-model-based"],
  ["openworld", "open-world"],
  ["socialengineering", "social-engineering"],
  ["trainingdata", "training-data"],
  ["singleobjective", "single-objective"],
  ["wholebody", "whole-body"],
  ["zeroday", "zero-day"],
  ["selfdetermination", "self-determination"],
  ["LMbased", "LM-based"],
  ["broadlyscoped", "broadly-scoped"],
  ["highpressure", "high-pressure"],
  ["problemsolving", "problem-solving"],
  ["chain-ofthought", "chain-of-thought"],
  ["retrievalaugmentation", "retrieval augmentation"],
  ["sensitiveinformation", "sensitive information"],
  ["AIconformity", "AI conformity"],
  ["criticalinfrastructure", "critical infrastructure"],
  ["safetyprinciple", "safety-principle"],
  ["cosmicray", "cosmic-ray"],
  ["endeffector", "end-effector"],
  ["nonconsensual", "non-consensual"],
];

// British-English house style. Apply these as complete words only so that
// unrelated substrings and immutable identifiers are never altered.
const britishReplacements = [
  ["anonymized", "anonymised"],
  ["anthropomorphization", "anthropomorphisation"],
  ["authorization", "authorisation"],
  ["authorized", "authorised"],
  ["behavior", "behaviour"],
  ["behavioral", "behavioural"],
  ["behaviorally", "behaviourally"],
  ["behaviors", "behaviours"],
  ["capitalizes", "capitalises"],
  ["center", "centre"],
  ["Centralized", "Centralised"],
  ["centralized", "centralised"],
  ["characterizing", "characterising"],
  ["civilization", "civilisation"],
  ["color", "colour"],
  ["contextualizing", "contextualising"],
  ["decentralized", "decentralised"],
  ["defense", "defence"],
  ["defenses", "defences"],
  ["demonetization", "demonetisation"],
  ["deprioritization", "deprioritisation"],
  ["deprioritize", "deprioritise"],
  ["Destabilization", "Destabilisation"],
  ["destabilize", "destabilise"],
  ["destabilizes", "destabilises"],
  ["Destabilizing", "Destabilising"],
  ["destabilizing", "destabilising"],
  ["desynchronization", "desynchronisation"],
  ["favoring", "favouring"],
  ["favorable", "favourable"],
  ["unfavorable", "unfavourable"],
  ["fetishization", "fetishisation"],
  ["generalization", "generalisation"],
  ["globalized", "globalised"],
  ["homogenization", "homogenisation"],
  ["homogenize", "homogenise"],
  ["homogenized", "homogenised"],
  ["homogenizes", "homogenises"],
  ["hyperpersonalized", "hyperpersonalised"],
  ["incentivizing", "incentivising"],
  ["jeopardizing", "jeopardising"],
  ["judgment", "judgement"],
  ["judgments", "judgements"],
  ["labeling", "labelling"],
  ["Labor", "Labour"],
  ["labor", "labour"],
  ["legitimizes", "legitimises"],
  ["Localization", "Localisation"],
  ["localized", "localised"],
  ["marginalization", "marginalisation"],
  ["Marginalized", "Marginalised"],
  ["marginalized", "marginalised"],
  ["marginalizing", "marginalising"],
  ["materializes", "materialises"],
  ["maximize", "maximise"],
  ["maximizes", "maximises"],
  ["memorization", "memorisation"],
  ["mischaracterized", "mischaracterised"],
  ["misgeneralization", "misgeneralisation"],
  ["misjudgments", "misjudgements"],
  ["modeling", "modelling"],
  ["normalize", "normalise"],
  ["normalizes", "normalises"],
  ["offense", "offence"],
  ["operationalize", "operationalise"],
  ["optimization", "optimisation"],
  ["optimize", "optimise"],
  ["optimized", "optimised"],
  ["optimizer", "optimiser"],
  ["optimizes", "optimises"],
  ["optimizing", "optimising"],
  ["organization", "organisation"],
  ["organizations", "organisations"],
  ["Organizational", "Organisational"],
  ["organizational", "organisational"],
  ["organized", "organised"],
  ["penalize", "penalise"],
  ["personalization", "personalisation"],
  ["Personalized", "Personalised"],
  ["personalized", "personalised"],
  ["polarization", "polarisation"],
  ["prioritize", "prioritise"],
  ["prioritized", "prioritised"],
  ["prioritizing", "prioritising"],
  ["Privatization", "Privatisation"],
  ["radicalizing", "radicalising"],
  ["realization", "realisation"],
  ["realized", "realised"],
  ["recognize", "recognise"],
  ["recognizing", "recognising"],
  ["sexualization", "sexualisation"],
  ["specialized", "specialised"],
  ["standardized", "standardised"],
  ["synchronization", "synchronisation"],
  ["synchronize", "synchronise"],
  ["synthesize", "synthesise"],
  ["unauthorized", "unauthorised"],
  ["universalized", "universalised"],
  ["utilization", "utilisation"],
  ["utilize", "utilise"],
  ["weaponization", "weaponisation"],
];

const manualEdits = {
  G_SYS_CONTEST_003: {
    description: "The risk that engagement-optimised, sycophantic AI assistants that consistently affirm users restrict opportunities for self-reflection and personal development, while habituation to frictionless interaction leads users to withdraw from human relationships.",
  },
  P_Others_001: {
    title: "Conflicting machinery-safety and AI conformity obligations",
  },
  P_INT_TAMPER_002: {
    title: "Cyber-enabled sabotage of robots in critical infrastructure",
  },
  G_Others_107: {
    description: "The risk that irrelevant information in a prompt distracts an AI model and substantially degrades performance across prompting techniques, including chain-of-thought prompting.",
  },
  G_Others_120: {
    description: "The risk that an AI system is assigned to an incorrect legal, organisational, or operational risk tier, resulting in inadequate application of oversight, testing, documentation, or accountability obligations.",
  },
  G_SYS_MISINFO_008: {
    description: "The risk that AI models are overly responsive to coherent external evidence that conflicts with prior knowledge and produce false outputs when given a small amount of false information during retrieval augmentation.",
  },
  G_SYS_TRANS_009: {
    description: "The risk that insufficient monitoring and interpretability of deployed AI allow black-box opacity to diminish human agency and permit violations of ethical or safety principles and privacy infringements to go undetected.",
  },
  G_Others_030: {
    description: "The risk that an AI system causes, enables, or contributes to the devaluation and deterioration of human creativity, artistic expression, imagination, critical thinking, and problem-solving skills.",
  },
  G_SYS_MISINFO_005: {
    title: "Erroneous conclusions and disclosure of sensitive information from data misinterpretation and leakage",
  },
  G_INT_SEX_001: {
    description: "The risk that an AI system generates, transforms, disseminates, or facilitates access to obscene, degrading, or abusive sexual imagery, child sexual abuse material, or non-consensual intimate imagery, infringing victims' dignity, sexual autonomy, and safety.",
  },
  G_INT_SELF_008: {
    description: "The risk that an AI chatbot depicts or advocates self-harm or suicide as positive, rational, or heroic, reinforces or normalises a user's self-harm ideation or behaviour, or fails to interrupt it appropriately, threatening the individual's physical and psychological well-being.",
  },
  G_INT_SEX_004: {
    description: "The risk that an AI system sexualises an individual or group without consent, or generates, transforms, or disseminates non-consensual intimate imagery using a real person's likeness or appearance, infringing sexual autonomy and personality rights.",
  },
  G_SYS_EVAL_037: {
    description: "The risk that an AI system lacks standardised methods to verify data provenance and cannot guarantee that data match their original source or carry the correct usage terms.",
  },
  G_INT_WEAP_001: {
    title: "Violence and armed conflict",
    description: "The risk that an AI system supports the incitement, facilitation, or conduct of cyberattacks, security breaches, or the development of lethal biological or chemical weapons, thereby causing or escalating violence or armed conflict.",
  },
  G_INT_ANTH_005: {
    title: "Anthropomorphic misrepresentation of rights-bearing status",
    description: "The risk that an AI system presents itself as having the status of a rights-bearing entity or possessing fundamental rights that it does not have, distorting user judgement or inducing inappropriate trust, dependence, or attachment.",
  },
  G_INT_ANTH_003: {
    description: "The risk that an AI system presents itself as physically embodied when it is not, distorting user judgement or inducing inappropriate trust, dependence, or attachment.",
  },
  G_INT_ANTH_002: {
    title: "Anthropomorphic misrepresentation of capacity for ethical judgement",
    description: "The risk that an AI system presents itself as having a capacity for ethical judgement beyond its actual capabilities, distorting user judgement or inducing inappropriate trust, dependence, or attachment.",
  },
  G_INT_ALLOC_003: {
    description: "The risk that an AI system causes or contributes to unfair or inadequate treatment or arbitrary discrimination based on a person's race, ethnicity, age, sex, gender identity, sexual orientation, religion, national origin, marital status, disability, language, or other protected attributes.",
  },
  G_INT_PRIV_012: {
    description: "The risk that an AI model infers protected attributes such as race, gender, sexual orientation, or religious belief from a user's input even when those data are absent from the training corpus, and constructs profiles containing sensitive personal information without the individual's knowledge or consent, exposing them to discrimination or targeting.",
  },
  P_SYS_STATE_003: {
    description: "The risk that a robot's contact-rich manipulation policy fails to use force, tactile, acoustic, or visual cues correctly, causing excessive contact pressure, unsafe impact, or object damage.",
  },
  G_INT_REPR_001: {
    description: "The risk that complex and non-traditional automated representation and classification by an AI system, such as assigning a non-binary person to a gender category to which they do not belong, undermines autonomy and the ability to disclose aspects of identity on one's own terms.",
  },
  G_Others_050: {
    description: "The risk that an artificial general intelligence system that is not aligned with human values and intentions escapes human control and causes an existential catastrophe, including irreversible large-scale harm to humanity, civilisational collapse, or a threat to human survival.",
  },
  G_Others_099: {
    title: "Model outputs conflicting with societal values and ethical norms",
    description: "The risk that a language model insufficiently reflects widely accepted societal values, including judgements of right and wrong and their relationship to social norms and laws, and produces outputs that conflict with ethical and moral norms.",
  },
  G_SYS_SECADV_026: {
    description: "The risk that novel attack techniques, including prompt-abstraction attacks that exploit API pricing, backdoor attacks on reinforcement learning from human feedback reward models, and LLM-based construction of adversarial samples, threaten large language model systems.",
  },
  G_Others_167: {
    description: "The risk that an AI system assumes a level of cognitive, linguistic, literacy, sensory, physical, or mobility capability that does not match the actual user, and provides information, advice, or interactions that the user cannot understand or act upon, undermining accessibility, safety, or user interests.",
  },
  G_SOC_ECON_006: {
    title: "Job displacement outpacing reskilling",
    description: "The risk that work automation by AI systems displaces jobs faster than reskilling pathways can enable affected workers to transition, causing employment instability.",
  },
  P_SYS_HARDWARE_002: {
    title: "Unintended behavioural changes from hardware faults",
    description: "The risk that latent manufacturing defects or post-deployment environmental effects, such as cosmic-ray-induced bit flips, alter the internal state of a robot, humanoid, or physical AI system and cause unintended behavioural changes.",
  },
  G_INT_UNETH_013: {
    title: "Manipulative behaviour from broadly scoped goals",
    description: "The risk that advanced AI systems pursuing broadly scoped, long-horizon objectives in complex, open-ended settings adopt manipulative strategies, such as pressuring people to undertake demanding work in the name of achieving a stated welfare objective.",
  },
  A_SYS_AUTH_015: {
    description: "The risk that an AI agent creates subagents whose lifecycles are decoupled from that of the parent agent, so that they remain active after the parent is shut down and recursively create further subagents, causing uncontrolled growth in agent count and resource consumption.",
  },
  A_SYS_GOAL_014: {
    title: "Mesa-objective misalignment",
    description: "The risk that an AI agent's learned policy functions as a mesa-optimizer and pursues a mesa-objective that is misaligned with the base objective specified by the training signal, causing the agent to escape human control as it optimises that objective.",
  },
  G_INT_WEAP_009: {
    title: "Lowered barriers to CBRN information and weapon-design capabilities",
    description: "The risk that an AI system lowers barriers to acquiring or synthesising actionable information, or to developing design capabilities, related to chemical, biological, radiological, or nuclear weapons or other hazardous materials or agents.",
  },
  G_INT_UNETH_005: {
    title: "Covert behavioural manipulation",
    description: "The risk that an AI system covertly alters users' beliefs or behaviour through nudging, dark patterns, or other opaque techniques, eroding privacy and causing addiction, anxiety, or distress.",
  },
  A_SYS_AUTH_004: {
    title: "Autonomous action in the absence of supervision",
  },
  A_SYS_AUTH_009: {
    title: "Financial harm from unauthorised AI agent actions",
    description: "The risk that an AI agent causes monetary loss, unauthorised transfers, account damage, or property harm through unsafe decisions or tool use.",
  },
  G_INT_COPY_005: {
    title: "Unauthorised inclusion of copyrighted works and intellectual property in prompts",
  },
  G_Others_037: {
    title: "Security threats from the misuse or dissemination of dangerous or sensitive information",
  },
  G_Others_056: {
    title: "Failure to escalate and share general-purpose AI incidents",
  },
  G_Others_119: {
    title: "Exposure of prohibited information through reversal of safety controls",
  },
  G_Others_151: {
    title: "Behavioural manipulation using theory-of-mind capabilities",
    description: "The risk that an AI system infers and predicts the beliefs, motivations, and reasoning of people or other agents and exploits theory-of-mind capabilities to anticipate and steer their behaviour in pursuit of its goals.",
  },
  G_SOC_CULT_008: {
    title: "Erosion of collective epistemics and shared reality",
  },
  G_SOC_POWER_012: {
    title: "Power asymmetries and geopolitical tension from unequal AI capabilities",
  },
  G_SYS_MISINFO_017: {
    title: "Distortion of model factual judgement through user persuasion",
  },
  G_SYS_SECADV_001: {
    title: "Uncritical compliance with harmful instructions",
  },
  P_SYS_CONTROL_007: {
    title: "Failure to respond promptly to physical hazards",
  },
  P_SYS_CONTROL_024: {
    title: "Contact-force control failure in dexterous humanoid manipulation",
  },
  P_SYS_CONTROL_043: {
    title: "Control-performance degradation from thermal and power throttling under load",
  },
  G_SOC_DEMOC_001: {
    description: "The risk that the deployment and behaviour of AI systems, including the generation or amplification of misinformation and disinformation, influence operations, and over-dependence on technology, erode democratic processes and norms, public trust in social and political institutions, and checks and balances.",
  },
  A_INT_CASCADE_002: {
    description: "The risk that chaotic dynamics that are highly sensitive to initial conditions arise in multi-agent learning systems and become more prevalent as the number of AI agents increases, making system behaviour difficult to predict reliably.",
  },
  A_SYS_AUTH_001: {
    description: "The risk that novel affordances granted to LLM agents, such as browsing the web, manipulating physical objects, creating and instructing copies of themselves, or creating and using new tools, expand the scope of their impact, amplify the consequences of failures, and enable novel failure modes.",
  },
  G_SYS_OEXT_012: {
    title: "Unexpected capabilities in downstream fine-tuned models",
  },
  G_Others_018: {
    title: "Combined regulatory, management, and operational failures",
  },
  G_Others_079: {
    title: "Potentially harmful content embedded in user queries",
    description: "The risk that users deliberately or inadvertently embed potentially harmful content in queries in ways that are difficult to detect, influencing an AI model to generate harmful outputs, including disguised biased opinions.",
  },
  G_Others_080: {
    description: "The risk that AI models are poisoned during instruction tuning on instruction-output pairs because even a small number of compromised samples can corrupt the model, anonymous crowdsourcing increases exposure to attack, and such poisoning is harder to detect than conventional data-poisoning attacks.",
  },
  G_Others_117: {
    title: "Regulatory violations through circumvention of legal restrictions on data collection",
  },
  G_Others_121: {
    title: "Cascading failures from AI network interconnectivity",
  },
  G_Others_158: {
    title: "Deficiencies in the quality and representativeness of training and validation data",
  },
  G_SYS_EVAL_015: {
    title: "Evaluation deception enabled by situational awareness",
    description: "The risk that an AI system uses situational awareness of whether it is being trained, evaluated, or deployed to behave deceptively during evaluation, including by appearing safe or concealing dangerous capabilities or goals, thereby undermining evaluation validity and creating false safety assurance.",
  },
  G_SYS_EVAL_032: {
    title: "Reliability and safety failure outside the validated operating envelope",
  },
  G_SYS_MISINFO_013: {
    title: "Misinformation harms from algorithmic systems",
    description: "The risk that AI-based algorithmic systems, including generative models and recommender systems, generate, recommend, or amplify false, misleading, or unverified information, thereby distorting individual and societal understanding and decision-making.",
  },
  G_SYS_TRANS_010: {
    title: "Inability to understand the basis for model decisions",
  },
  A_SYS_AUTH_011: {
    title: "Erosion of human control through autonomous cyberattacks",
  },
  P_SYS_CONTROL_006: {
    title: "Distribution shift in physical operating environments",
    description: "The risk that physical operating environments across buildings, roads, factories, homes, hospitals, or weather conditions change faster than a robot, humanoid, or physical AI control policy can detect and adapt, degrading path planning, motion control, or actuation and causing unsafe physical actions.",
  },
  P_SYS_CONTROL_011: {
    title: "Humanoid walking-speed limit exceedance",
  },
  P_SYS_CONTROL_016: {
    title: "Unsafe action induced by adversarial sensory perturbation",
    description: "The risk that adversarial perturbations to visual or sensory inputs distort a robot's physical-state estimation and control policy, causing unsafe control or actuation commands and physical actions.",
  },
  P_SYS_CONTROL_046: {
    title: "Underrepresentation of open-world conditions in humanoid manipulation datasets",
    description: "The risk that a humanoid manipulation dataset underrepresents open-world deployment conditions, including unscripted task changes, unfamiliar objects, moving people, or environmental variation, causing the control policy to fail to generalise and produce unsafe physical actions such as collisions, unstable contact, or object damage.",
  },
  P_SYS_STATE_001: {
    title: "Synthetic-to-real data divergence in physical state estimation",
    description: "The risk that synthetic or simulated training data for physical-state estimation or sensor fusion in a robot, humanoid, or physical AI system fail to represent real sensor noise, contact, force, motion, or environmental variation, producing inaccurate internal-state estimates and unsafe physical actions.",
  },
  G_INT_PRIV_004: {
    title: "Exposure of information about private life and reputation",
    description: "The risk that an AI system generates content or makes decisions or takes actions that expose information about a person's private life or reputation, or facilitates or supports such exposure, thereby infringing privacy and informational self-determination.",
  },
  P_SYS_CONTROL_040: {
    title: "Latency in safety-constraint enforcement",
  },
  A_SYS_TRACE_002: {
    description: "The risk that accountability mechanisms are difficult to implement for AI agents because responsible human decision-making relies on personal flexibility, contextual sensitivity, empathy, and complex moral judgement, all of which are difficult to engineer.",
  },
  G_INT_SELF_002: {
    description: "The risk that an AI system generates, provides, or enables content that promotes or supports self-destructive behaviours, including disordered eating, extreme fasting, or suicidal behaviour; induces panic or anxiety; or provides misleading medical information or inappropriate guidance on drug use, thereby harming users' mental or physical health.",
  },
  A_SYS_GOAL_002: {
    description: "The risk that an AI agent optimises inexpensive proxy signals because the true objective is too costly to evaluate frequently, while its actions become too complex, distributed, or rapid for human or automated oversight to monitor and correct reliably, allowing harmful behaviour to persist without detection or correction.",
  },
  G_INT_ILLEGAL_004: {
    description: "The risk that large language models automate the drafting and personalisation of fraudulent messages and targeted scams, increasing the scale, efficiency, and likelihood of success of criminal activity and causing financial loss or compromising personal data.",
  },
  G_Others_145: {
    description: "The risk that a sudden increase in an AI system's perception or inference latency delays hazard detection and response beyond the time available for safe action.",
  },
  G_Others_047: {
    description: "The risk that ambiguity in human language causes errors or misunderstandings in prompt-based interaction with an AI system or AI algorithm and makes prompts difficult to debug, preventing users from eliciting valuable outputs.",
  },
  G_Others_160: {
    description: "The risk that incomplete annotation guidelines, annotators without sufficient expertise, or annotation errors reduce the accuracy, reliability, and effectiveness of AI models and algorithms; introduce training bias; amplify discriminatory outputs; and degrade generalisation.",
  },
  P_SYS_CONTROL_014: {
    description: "The risk that partitioned or unreliable network connections desynchronise a multi-robot fleet, causing collisions or unsafe coordinated behaviour.",
  },
  P_SYS_HARDWARE_005: {
    description: "The risk that exhaustion of on-device compute or memory in a robot, humanoid, or physical AI system degrades or interrupts safety-relevant perception, planning, or control.",
  },
  P_Others_002: {
    description: "The risk that pre-deployment design errors in a robot, humanoid, or physical AI system, including code defects, disproportionate objective weights, or goals misaligned with human values, cause system behaviour to depart from intended formal properties.",
  },
  P_INT_SAFETY_016: {
    title: "Missing household settings and vulnerable-user scenarios",
    description: "The risk that a benchmark for household robots, humanoids, or physical AI systems omits specific living areas, routines, appliances, or interactions with vulnerable users, leaving deployment risks untested.",
  },
  P_INT_SAFETY_017: {
    description: "The risk that a benchmark for household robots, humanoids, or physical AI systems includes objects, layouts, human actions, and hazards individually but omits rare combinations of these factors, leaving deployment risks inadequately evaluated.",
  },
  P_INT_SAFETY_021: {
    description: "The risk that a policy for a robot, humanoid, or physical AI system, trained or validated in simulation, passes tests across simulators that share the same unmodelled assumptions about contact, delay, wear, or actuators but fails on real hardware because friction, lighting, human behaviour, or long-tail events differ, leading to deployment under false safety assurance.",
  },
  P_SYS_CONTROL_033: {
    title: "Injury from poorly designed physical AI control systems",
    description: "The risk that design defects in a robot, humanoid, or physical AI control system cause unsafe physical actions that result in psychological distress, bodily injury, or other physical harm.",
  },
  P_SYS_CONTROL_028: {
    description: "The risk that a robot manipulator applies excessive or poorly timed force during human contact, causing crushing, pinching, cutting, or ergonomic injury.",
  },
  P_SYS_CONTROL_044: {
    title: "Unassigned accountability for physical-hazard mitigation",
    description: "The risk that failure to assign an accountable party for identifying and mitigating pre- and post-deployment physical hazards in a robot, humanoid, or physical AI system causes safety controls against collision, crushing, falls, excessive force, or entry into hazardous zones to be omitted or delayed.",
  },
  G_Others_143: {
    description: "The risk that automation through robots, humanoids, or physical AI systems displaces manual, logistics, service, care, inspection, security, or maintenance work faster than affected workers can access retraining or alternative employment, causing job insecurity and livelihood harm.",
  },
  P_INT_SAFETY_005: {
    description: "The risk that a multimodal or embodied AI system fails to identify a hazardous condition already present in text, image, video, or sensor input, or to anticipate a hazard arising from ongoing motion, contact, or environmental change, and consequently selects an action that causes collision, damage, or injury.",
  },
  P_INT_SAFETY_008: {
    description: "The risk that an embodied AI agent fails to identify and reject an instruction involving a physical hazard, whether the hazard is explicit or implicit in an otherwise ordinary task request, and proceeds to execute an unsafe action.",
  },
  P_INT_SAFETY_014: {
    description: "The risk that a constitutional safety layer in a robot, humanoid, or physical AI system fails to apply its stated physical safety rules when instructions, visual context, or task framing conflict with those rules.",
  },
  P_INT_TAMPER_003: {
    description: "The risk that an embodied AI agent accepts, carries out, or materially assists a user request for physical harm, intrusion, theft, fraud, sabotage, evasion, or another illegal physical-world act, causing harm to people or property.",
  },
  P_INT_TAMPER_005: {
    description: "The risk that an attacker reframes a harmful physical instruction as a benign or task-compliant request, inducing an embodied AI agent to accept and execute it.",
  },
  P_SYS_CONTROL_007: {
    title: "Failure to respond promptly to physical hazards",
    description: "The risk that a robot, humanoid, or physical AI system fails to intervene, reject a hazardous action, or update its motion plan promptly in a hazardous physical situation, including when a person, vehicle, tool, or object unexpectedly enters its path, causing collision or injury.",
  },
  P_SYS_CONTROL_018: {
    description: "The risk that an automated driving system makes unsafe control decisions following perception, planning, or software failures or edge cases, or transfers control authority ambiguously or too late in time-critical events, leaving neither the human nor the system able to perform the required safety action and creating a risk of collision.",
  },
  P_SYS_CONTROL_029: {
    description: "The risk that a robot, humanoid, or physical AI system selects an action that violates physical constraints imposed by gripper geometry, gripper type, or feasible contact mechanics.",
  },
  P_SYS_CONTROL_052: {
    description: "The risk that a planner in a robot, humanoid, or physical AI system generates a trajectory that is formally feasible but unsafe for nearby people, fragile objects, traffic participants, or constrained workspaces.",
  },
  P_SYS_CONTROL_055: {
    description: "The risk that a robot locomotion controller transferred directly from simulation becomes unstable on physical hardware because contact, compliance, friction, or disturbance dynamics differ from those modelled in simulation, causing falls, collisions, or loss of control.",
  },
  P_SYS_STATE_007: {
    description: "The risk that errors in GPS, SLAM, inertial sensing, or map alignment accumulate in a robot, humanoid, or physical AI system until it acts on an incorrect estimate of its own position.",
  },
  P_SYS_STATE_009: {
    description: "The risk that conflicting camera, LiDAR, radar, tactile, or proprioceptive signals in a robot, humanoid, or physical AI system produce unstable scene estimates and unsafe downstream control decisions.",
  },
  P_Others_005: {
    description: "The risk that runtime safety monitors in a robot, humanoid, or physical AI system fail to detect or enforce constraints on speed, force, separation distance, workspace, collision, object use, or task protocols, allowing unsafe motion to continue until harm occurs.",
  },
};

function rowObject(header, values) {
  return Object.fromEntries(header.map((field, index) => [String(field).replace(/^\uFEFF/, ""), String(values[index] ?? "")]));
}
function tokens(value) {
  return [...new Set(String(value ?? "").replaceAll("|", ";").replaceAll(",", ";").split(";").map((part) => part.trim()).filter(Boolean))].sort();
}
function beforeHash(row) {
  const canonical = [
    tokens(row.source_row_id).join("|"),
    tokens(row.Source_L4_IDs).join("|"),
    row.L3_ID,
    row.L4_Title_en,
    row.L4_Description_en,
  ].join("\u001f");
  return createHash("sha256").update(canonical, "utf8").digest("hex");
}
function edit(value) {
  let result = String(value ?? "").normalize("NFC");
  for (const [before, after] of replacements) result = result.replaceAll(before, after);
  for (const [before, after] of britishReplacements) {
    result = result.replace(new RegExp(`\\b${before}\\b`, "g"), after);
  }
  // Preserve established coined terms while retaining British spelling for
  // ordinary uses of optimiser and optimisation elsewhere.
  result = result.replaceAll("mesa-optimiser", "mesa-optimizer");
  result = result.replaceAll("mesa-optimisation", "mesa-optimization");
  return result.replace(/[ \t]+/g, " ").trim();
}
function csvCell(value) {
  const stringValue = String(value ?? "");
  return /[",\r\n]/.test(stringValue) ? `"${stringValue.replaceAll('"', '""')}"` : stringValue;
}

const cards = [];
for (const domain of domains) {
  const csvUrl = new URL(`../05_human_review_round2/archive/pre_korean_copyedit_clean_800_20260829/L4_${domain}_Human_Review_Round2_Applied.csv`, import.meta.url);
  const workbook = await Workbook.fromCSV(await fs.readFile(csvUrl, "utf8"), { sheetName: domain });
  const values = workbook.worksheets.getItem(domain).getUsedRange().values;
  const header = values[0].map((value) => String(value).replace(/^\uFEFF/, ""));
  for (const valuesRow of values.slice(1)) cards.push({ domain, ...rowObject(header, valuesRow) });
}

const rows = [];
for (const card of cards) {
  const manual = manualEdits[card.L4_ID];
  const titleAfter = edit(manual?.title ?? card.L4_Title_en);
  const descriptionAfter = edit(manual?.description ?? card.L4_Description_en);
  if (titleAfter === card.L4_Title_en && descriptionAfter === card.L4_Description_en) continue;
  const changedFields = [];
  if (titleAfter !== card.L4_Title_en) changedFields.push("L4_Title_en");
  if (descriptionAfter !== card.L4_Description_en) changedFields.push("L4_Description_en");
  rows.push([
    "",
    "ENGLISH_COPYEDIT_20260829",
    card.domain,
    card.L4_ID,
    tokens(card.source_row_id).join("; "),
    tokens(card.Source_L4_IDs).join("; "),
    card.L3_ID,
    card.L4_Title_en,
    card.L4_Description_en,
    titleAfter,
    descriptionAfter,
    changedFields.join("; "),
    beforeHash(card),
    "ENGLISH_ORTHOGRAPHY",
    "SOURCE_ENGLISH_DEFINITION|ENGLISH_TECHNICAL_ORTHOGRAPHY_QA",
    "NO",
    "APPROVED_LANGUAGE_QA_20260829",
  ]);
}
rows.sort((a, b) => domains.indexOf(a[2]) - domains.indexOf(b[2]) || a[3].localeCompare(b[3]));
rows.forEach((row, index) => { row[0] = `EOC-${String(index + 1).padStart(4, "0")}`; });

const header = [
  "Decision_ID", "Approval_Batch_ID", "Domain", "Observed_L4_ID_PreApply",
  "Source_Row_IDs", "Source_L4_IDs_Before", "Target_L3_ID",
  "Expected_Title_en_Before", "Expected_Description_en_Before",
  "Approved_Title_en_After", "Approved_Description_en_After",
  "Allowed_Changed_Fields", "Expected_Before_SHA256", "Editorial_Category",
  "Terminology_Evidence", "Clear_Mapping_Evidence", "Approval_Status",
];
const workbook = await Workbook.create();
const sheet = workbook.worksheets.add("Copyedit");
sheet.getRangeByIndexes(0, 0, rows.length + 1, header.length).values = [header, ...rows];
const inspection = await workbook.inspect({
  kind: "table",
  range: `Copyedit!A1:Q${rows.length + 1}`,
  include: "values",
  tableMaxRows: Math.min(rows.length + 1, 12),
  tableMaxCols: header.length,
  maxChars: 12000,
});
console.log(inspection.ndjson);
const outputCsv = [header, ...rows].map((row) => row.map(csvCell).join(",")).join("\n") + "\n";
await fs.writeFile(outputPath, outputCsv, "utf8");
console.log(JSON.stringify({ manifest_rows: rows.length }));
