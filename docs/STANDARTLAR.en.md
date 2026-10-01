# Standards and conformity matrix (Wave S-0)

Türkçe: [STANDARTLAR.md](STANDARTLAR.md). This is the English version of `docs/STANDARTLAR.md`;
section numbers, table rows, source names and clause numbers are identical. If the two ever
differ, `docs/STANDARTLAR.md` is authoritative.

Status: S-0 research output, 30.09.2026. This document checks the "Wave S — standards map" table
of the plan against primary sources. It contains no code. A source link is given next to every
claim; everything that could not be verified is marked **NOT VERIFIED**.

Copyright note: ANS, ASME, ISO and IEEE standards are paid documents. The summaries below are not
quotations from these texts; they are written in our own words from the scope summaries on the
publishers' pages and from open secondary sources. A clause number is given only if it was seen in
an open source. Open sources (NUREG, NRC SRP, IAEA, JCGM, BIPM, NEA) were read directly.

---

## 1. Honest framing

This program **does not certify** conformity with any standard and cannot approve an analysis
as "compliant with a standard". What it does is **produce the evidence** that standards and good
practice would ask for, for a run or a model (traceability of inputs and data, uncertainty
statements, convergence indicators, benchmark comparisons, bias/USL calculation), and **make gaps
visible**. For the licensing of a facility or for use in a safety analysis, the user
organisation additionally needs its own quality assurance programme (e.g. a software QA
programme of the ASME NQA-1 Subpart 2.7 type), qualified personnel, independent review and its
own validation report. NUREG/CR-6698 says this explicitly: validation depends not only on the
code and the library but also on the hardware on which the code is installed and on the
competence of the person who builds the model; responsibility for input files prepared elsewhere
passes to the organisation that uses them
([NUREG/CR-6698 §1.2, §2.3](https://www.nrc.gov/docs/ML0502/ML050250061.pdf)).
No threshold whose source cannot be shown is built into the tool; thresholds live in the profile
file and can be changed by the user.

For the program's target audience (universities, research and education) the most suitable
software framework is **ANSI/ANS-10.4**: this standard is explicitly for the V&V of
*non-safety-related* (research, education, non-critical) scientific and engineering programs
([ANSI webstore](https://webstore.ansi.org/standards/ansi/ansians102008r2021)).

---

## 2. Table of verified standards

Columns: full title; current edition; status; access; scope; what it requires / does not require
of this tool.

### 2.1 Software quality and V&V

| ID | Full title | Current edition / status | Access | Scope (summary) | What it requires of the tool | What it does not require | Source |
|---|---|---|---|---|---|---|---|
| ANSI/ANS-10.4 | Verification and Validation of Non-Safety-Related Scientific and Engineering Computer Programs for the Nuclear Industry | **2008 (R2021)** in force; revision ANS-10.4-202x at draft stage | paid | V&V guidance for scientific software in non-safety-related, research/non-critical applications (new and existing software) | S-4: V&V plan and report, requirement→test traceability, list of known limitations, "what we verified" in the release note | QA of safety-related software; NQA-1 is needed for that | [ANSI](https://webstore.ansi.org/standards/ansi/ansians102008r2021), [ANS What's New](https://www.ans.org/standards/new/) |
| ANSI/ANS-10.3 | Documentation of Computer Software | **1995 — historical, not current**; the ANS-10 subcommittee now maintains only 10.2, 10.4, 10.5 | paid (historical copy) | Documentation of scientific software | May be cited only as an inspiration for the document set; must not be made the basis of a conformity claim | — | [ANSI](https://webstore.ansi.org/standards/ansi/ansians101995); year of withdrawal **NOT VERIFIED** |
| ANSI/ANS-10.5 | Accommodating User Needs in Scientific and Engineering Computer Software Development | **2006**; sources conflict on the reaffirmation year: the ANSI blog shows **R2026**, ANSI webstore searches show R2016 → **R-year NOT VERIFIED** | paid | Taking user needs (usability, robustness, documentation, error messages) into account in software development | User guide (13b), clarity of error messages, input validation, example problems | A particular interface design | [ANSI blog](https://blog.ansi.org/ansi/ansi-ans-10-5-2006-r2026-user-needs-software/) |
| ANSI/ANS-10.7 | (High-integrity, non-real-time nuclear software — developer requirements) | 2013 (R2023) | paid | Development of high-integrity software | Not needed for this tool; information only | — | [ANSI blog](https://blog.ansi.org/ansi/ansi-ans-10-7-2013-r2023-nuclear-industry-software/); full title **NOT VERIFIED** |
| ASME NQA-1 (Subpart 2.7) | Quality Assurance Requirements for Nuclear Facility Applications; Subpart 2.7: QA requirements for computer software for nuclear facility applications | The ASME page shows the **latest edition as 2026** (previous: 2024, published 24.07.2024). Subpart 2.7 **still exists**; the ASME page states that "Subpart 2.7 and 3.2-2.7.1 were restructured" — in which edition is **NOT VERIFIED** | paid (USD 310–415) | Facility life-cycle QA; development, acquisition, maintenance and use of software | S-4: version/environment lock, change log, configuration management, evaluation of changes in the operating environment. The tool is **not developed under NQA-1**; an organisation that wants to use it applies its own acquisition/acceptance (dedication) process | The tool being NQA-1 certified (it cannot be; NQA-1 is an organisational programme) | [ASME](https://www.asme.org/codes-standards/find-codes-standards/quality-assurance-requirements-for-nuclear-facility-applications), [ANSI blog 2024](https://blog.ansi.org/ansi/asme-nqa-1-2024-nuclear-facility-applications/), [BSB Edge 2026](https://www.bsbedge.com/standard/quality-assurance-requirements-for-nuclear-facility-applications-asme-nqa-1-2026/ASME-NQA-1-2026) |
| IEEE 1012 | IEEE Standard for System, Software, and Hardware Verification and Validation | **1012-2024** (revision of 1012-2016; published in 2025) | paid | V&V process requirements scaled by integrity level; analysis, review, audit, test | S-4: declare the tool's integrity level (low) explicitly and select the V&V tasks accordingly | All tasks of the high integrity levels | [IEEE Xplore](https://ieeexplore.ieee.org/document/11134780), [ANSI](https://webstore.ansi.org/standards/ieee/ieee10122024) |
| ISO/IEC/IEEE 12207 | Systems and software engineering — Software life cycle processes | **12207:2026** (April 2026; cancelled and replaced the 2017 edition) | paid | Software life-cycle processes (configuration, risk, verification, maintenance…) | Framework for the process naming of the S-4 document set | Implementation of all processes; the standard allows tailoring | [IEEE Xplore 2026](https://ieeexplore.ieee.org/iel8/11481696/11481697/11481698.pdf), [ANSI blog](https://blog.ansi.org/ansi/iso-iec-ieee-12207-2026-software-life-cycle/); the iso.org page could not be accessed (403) — withdrawal date **NOT VERIFIED** |

### 2.2 Criticality safety and validation of calculation methods

| ID | Full title | Current edition / status | Access | Scope | What it requires of the tool | What it does not require | Source |
|---|---|---|---|---|---|---|---|
| ANSI/ANS-8.1 | Nuclear Criticality Safety in Operations with Fissionable Materials Outside Reactors | **2014 (R2023)** in force; revision ANS-8.1-202x in draft | paid | Basic principles of criticality safety in operations with fissionable material outside reactors; validation of calculation methods against experiments, the concepts of bias and area of applicability | Profile B: require that the calculation method be validated against benchmark experiments and that the bias and the AOA be reported | Facility operational controls, application of double contingency — outside the tool's scope | [ANS What's New](https://www.ans.org/standards/new/); clause numbers **NOT VERIFIED** |
| ANSI/ANS-8.24 | Validation of Neutron Transport Methods for Nuclear Criticality Safety Calculations | **2017 (R2023)** in force; revision ANS-8.24-202x in draft | paid | Validation of neutron transport methods used in criticality safety analysis and establishment of their applicability (requirements + recommendations) | S-3: bias, bias uncertainty, AOA, margin of subcriticality and documentation | Whether it imposes a particular statistical method is **NOT VERIFIED** (text not seen) | [ANSI](https://webstore.ansi.org/standards/ansi/ansians242017r2023), [ANS What's New](https://www.ans.org/standards/new/) |
| **NUREG/CR-6698** | Guide for Validation of Nuclear Criticality Safety Calculational Methodology (J.C. Dean, R.W. Tayloe Jr., SAIC; NRC NMSS) | **January 2001**; no revision known; guide (not binding) | **open** (NRC ADAMS) | Steps of criticality calculation method validation: operating parameters → selection of experiments → modelling → bias/uncertainty → trends → normality → statistical method → margin of subcriticality → USL → AOA → report | **Primary source of the statistical method** of S-3 (see §4). The 25-point example data in the document can be used for a numerical cross-check of the tool | A particular code or library | [ML050250061](https://www.nrc.gov/docs/ML0502/ML050250061.pdf) |
| NUREG-1520 Chapter 5 Appendix B (formerly FCSS ISG-10) | Justification for Minimum Margin of Subcriticality for Safety | ISG-10 (2006) was incorporated into NUREG-1520 Chapter 5 Appendix B | open | Justification of the minimum margin of subcriticality (MMS); the statement in NUREG-1718 §6.4.3.3.4 that 0.05 is generally accepted without further justification (search summary) | Source for the default margin proposed in Profile B | — | [NRC ISG list](https://www.nrc.gov/docs/ML0616/ML061650370.pdf); the 0.05 statement only from a search summary → **NOT VERIFIED** |
| NRC RG 3.71 | Nuclear Criticality Safety Standards for Nuclear Materials Outside Reactor Cores | **Rev. 3 (October 2018)**; endorses the ANSI/ANS-8 standards | open | Acceptance of the ANS-8 standards by the NRC | Information; not binding for users outside the US | — | [RG 3.71 Rev.3](https://www.nrc.gov/docs/ML1816/ML18169A258.pdf), [FR 2018-21534](https://www.govinfo.gov/app/details/FR-2018-10-03/2018-21534) |
| ISO 1709 | Nuclear energy — Fissile materials — Principles of criticality safety in storing, handling and processing | **ISO 1709:2018** (3rd edition) + **Amd 1:2022** (control methods and safety equipment); reviewed and confirmed in 2023 | paid | Basic principles and limitations of criticality safety in operations with fissile material outside reactors; basis of assessment, criticality safety margin, demonstration of safety; contains no QA requirement | General framework of Profile B (margin concept, demonstration) | Statistics of calculation validation (not in this standard) | [ISO 1709:2018](https://www.iso.org/standard/68617.html), [Amd 1](https://www.iso.org/standard/81439.html), [NCSP summary](https://ncsp.llnl.gov/sites/ncsp/files/2023-12/iso1709_summary_issue3.pdf) |
| IAEA SSG-27 (Rev. 1) | Criticality Safety in the Handling of Fissile Material | **2022** | **open** | Ensuring subcriticality; safety assessments; **verification, benchmarking and validation of calculation methods**; accident response | Open international source for Profile B (not in the plan table) | — | [IAEA](https://www.iaea.org/publications/14883/criticality-safety-in-the-handling-of-fissile-material) |
| NEA/NSC/WPNCS/DOC(2013)7 | Overview of Approaches Used to Determine Calculational Bias in Criticality Safety Assessment (UACSA state-of-the-art report, part 1; Ivanova et al.) | 2013 | open | Comparison of national practices for determining bias/USL | Justification of the S-3 method choice, limitations (normality, correlation) | — | [NEA PDF](https://oecd-nea.org/science/wpncs/UACSA/publications/EGUACSASOAR1.pdf) |
| NUREG/CR-7109 | An Approach for Validating Actinide and Fission Product Burnup Credit Criticality Safety Analyses — Criticality (keff) Predictions | 2012 (ORNL) | open | Validation of burnup credit; sensitivity/similarity (c_k > 0.8) | Out of scope (the tool has no sensitivity calculation); idea of a similarity measure for the AOA in the future | — | [NRC](https://www.nrc.gov/regulations-legislation/nureg-series-publications/publications-prepared-by-nrc-contractors/cr7109) |

### 2.3 Reactor core design and reactor physics methods

| ID | Full title | Current edition / status | Access | Scope | What it requires of the tool | What it does not require | Source |
|---|---|---|---|---|---|---|---|
| IAEA SSG-52 | Design of the Reactor Core for Nuclear Power Plants | **2019**; supports SSR-2/1 (Rev. 1) | **open** | Core design of **nuclear power plants**: neutronics, thermal-hydraulics, thermomechanics; core control, shutdown, monitoring, core management | Profile C (power reactor sub-profile) | Research reactors (the SSR-3 family covers them) | [IAEA](https://www.iaea.org/publications/13382/design-of-the-reactor-core-for-nuclear-power-plants) |
| IAEA SSR-3 | Safety of Research Reactors (Specific Safety Requirements) | **2016** | **open** | The whole life cycle of research reactors; Section 6 design requirements | Profile C (research reactor sub-profile) | — | [IAEA](https://www.iaea.org/publications/7024/safety-of-research-reactors), [PDF](https://www-pub.iaea.org/MTCD/Publications/PDF/P1751_web.pdf) |
| IAEA SSG-22 (Rev. 1) | Use of a Graded Approach in the Application of the Safety Requirements for Research Reactors | **2023** ("Rev. 1" missing in the plan table) | **open** | Graded application of the SSR-3 requirements (a way of meeting a requirement, not an exemption from it) | Justification of the graded approach: adjusting profiles and thresholds to the reactor type | — | [IAEA](https://www.iaea.org/publications/15080/use-of-a-graded-approach-in-the-application-of-the-safety-requirements-for-research-reactors) |
| IAEA SSG-20 (Rev. 1) | Safety Assessment for Research Reactors and Preparation of the Safety Analysis Report | 2022 (**Rev. number and year NOT VERIFIED**) | open | Safety assessment of research reactors and SAR content | Information for naming report sections | — | [IAEA PDF](https://www-pub.iaea.org/MTCD/Publications/PDF/PUB1981_web.pdf) |
| IAEA SSG-82 | Core Management and Fuel Handling for Research Reactors (replaces NS-G-4.3) | year **NOT VERIFIED** | open | Core management and fuel handling of research reactors | Profile C research reactor | — | [IAEA](https://www.iaea.org/publications/15095/core-management-and-fuel-handling-for-research-reactors) |
| IAEA SSG-2 (Rev. 1) | Deterministic Safety Analysis for Nuclear Power Plants | 2019 | open | Deterministic safety analysis; conservative and best estimate + uncertainty approaches | Information (expectations on code validation); the tool does not perform transient analysis | — | [IAEA](https://www.iaea.org/publications/12335/deterministic-safety-analysis-for-nuclear-power-plants) |
| NUREG-0800 §4.3 | Standard Review Plan, Section 4.3 "Nuclear Design" | **Rev. 3, March 2007** (ML070740003); no newer revision (NRC Chapter 4 page) | **open** | Review of nuclear design against GDC 10, 11, 12, 13, 20, 25, 26, 27, 28: power distribution, reactivity coefficients, control requirements, shutdown margin, most reactive rod stuck out, validation of analytical methods by measurement | US LWR sub-profile of Profile C (see the K7 correction in §3) | Numerical acceptance ranges for the coefficients (the SRP explicitly **does not give** them); a numerical value for the shutdown margin (left blank in the SRP, plant-specific) | [SRP 4.3 Rev.3](https://www.nrc.gov/docs/ML0707/ML070740003.pdf), [NRC Chapter 4](https://www.nrc.gov/regulations-legislation/nureg-series-publications/publications-prepared-by-nrc-staff/nureg-0800/chapter-4) |
| NRC RG 1.203 | Transient and Accident Analysis Methods | **Rev. 0, December 2005** (single revision) | open | Process for the development and assessment of evaluation models used in design-basis **transient and accident** analysis (EMDAP, 4 elements); graded approach | Only **by analogy**: the ideas of an "assessment base", applicability and a graded approach inspire S-3/S-4 | A direct requirement for static core neutronic design or criticality safety (not its scope) | [RG 1.203](https://www.nrc.gov/docs/ML0535/ML053500170.pdf) |
| ANSI/ANS-19.3 | Steady-State Neutronics Methods for Power Reactor Analysis | **2022** (revision of 2011) | paid | Performing and **validating** steady-state reaction rate distribution, reactivity and nuclide composition calculations; method selection, V&V criteria, range of applicability, documentation; MOX out of scope | The most direct ANS source for the method-validation rules of Profile C (not in the plan table) | — | [Accuris](https://store.accuristech.com/standards/ans-19-3-2022?product_id=2523230), [ANSI 2011](https://webstore.ansi.org/standards/ansi/ansians192011) |
| ISO 18075 | Steady-state neutronics methods for power-reactor analysis | 2018 | paid | ISO counterpart of ANS-19.3 | Profile C, international source | — | [ISO](https://www.iso.org/standard/61293.html) |
| ANSI/ANS-19.11 | Calculation and Measurement of the Moderator Temperature Coefficient of Reactivity for Pressurized Water Reactors | 2017 | paid | Calculation and measurement of the PWR MTC | Profile C, K7 MTC note | — | [ANSI](https://webstore.ansi.org/standards/ansi/ansians19112017) |
| ANSI/ANS-19.6.1 | Reload Startup Physics Tests for Pressurized Water Reactors | 2019 (R2024) | paid | Verification of core nuclear characteristics by tests after reload | Information (culture of measurement–calculation comparison) | — | [Intertek](https://www.intertekinform.com/en-gb/standards/ansi-ans-19-6-1-2019-r2024--94754_saig_ans_ans_3441905/) |
| ANSI/ANS-19.13 | Initial Fuel Loading and Startup Physics Tests for First-of-a-Kind Advanced Reactors | 2024 | paid | First loading and startup physics tests in advanced reactors | Information | — | [ANSI](https://webstore.ansi.org/standards/ansi/ansians19132024) |
| ANS-19.5-202x | Requirements for Reference Reactor Physics Measurements | draft (historical 19.5-1995, W2005) | — | Reference reactor physics measurements | Should be followed; if published, relevant to the use of IRPhEP | — | [ANS What's New](https://www.ans.org/standards/new/) |

### 2.4 Benchmark handbooks

| ID | Current edition | Access and terms of use | Source |
|---|---|---|---|
| ICSBEP Handbook (International Handbook of Evaluated Criticality Safety Benchmark Experiments), NEA/NSC/DOC(95)03 | **2024 edition, published December 2025** (search summary; the NEA page returned 403 → **NOT VERIFIED**) | "On request"; distributed **to named users and with a detailed statement of the intended use**; the request **must be renewed** for every new edition; code models on NEA GitLab (currently Serpent only) — redistribution terms are not on the page (**NOT VERIFIED**). NUREG/CR-6698 stresses that the experiment descriptions in the handbook are considered peer reviewed, but that the sample calculations in the handbook are no substitute for a validation | [NEA ICSBEP](https://www.oecd-nea.org/jcms/pl_20291/international-criticality-safety-benchmark-evaluation-project-icsbep-handbook), [NEA Data Bank GitLab](https://databank.io.oecd-nea.org/benchmarks/icsbep/), [NUREG/CR-6698 §2.2](https://www.nrc.gov/docs/ML0502/ML050250061.pdf) |
| IRPhE Handbook (International Handbook of Evaluated Reactor Physics Benchmark Experiments) | **2022/23 edition** (NEA-1765) | DVD or online; package by request form; the request is renewed for every edition; **to authorised users in OECD member countries** and to contributing organisations; others are considered case by case. Turkey is an OECD/NEA member; the eligibility of Turkish universities is **NOT VERIFIED** | [NEA-1765](https://www.oecd-nea.org/tools/abstract/detail/nea-1765/), [NEA IRPhE](https://www.oecd-nea.org/jcms/pl_20279/international-handbook-of-evaluated-reactor-physics-benchmark-experiments-irphe) |
| mit-crpg/benchmarks (GitHub) | active (last push 17.09.2025) | **MIT-licensed** OpenMC/MCNP models (~120 ICSBEP evaluations); `icsbep/icsbep/uncertainties.csv` benchmark k and σ values. Note: although the models are openly licensed, the source of the benchmark definition is ICSBEP; the ICSBEP identifier and edition must be written in the report | [GitHub](https://github.com/mit-crpg/benchmarks) |
| LANL MCNP criticality validation suite (Mosteller) | LA-UR-02-0878 (2002, 26 cases); extended 119 cases LA-UR-10-06230 | "Approved for public release; distribution is unlimited" — open | [LA-UR-02-0878](https://mcnpx.lanl.gov/pdf_files/TechReport_2002_LANL_LA-UR-02-0878_Mosteller.pdf), [OSTI 1092464](https://www.osti.gov/biblio/1092464) |

### 2.5 Uncertainty, quantities/units and terminology

| ID | Current edition | Access | What it requires of the tool | Source |
|---|---|---|---|---|
| JCGM 100:2008 (GUM) | 2008 + **Amd. 1:2026** (non-linearity) | **open** | K5: explicit labelling of the standard uncertainty; result format (§7.2.2); uncertainty given **with at most two significant digits** (§7.2.6); if the "±" format is used for a standard uncertainty, a statement that it is not a confidence interval (§7.2.2 note); stating k for an expanded uncertainty (§7.2.3) | [BIPM JCGM](https://www.bipm.org/en/committees/jc/jcgm/publications), [JCGM 100 PDF](https://www.bipm.org/documents/20126/2071204/JCGM_100_2008_E.pdf) |
| JCGM 101:2008 | GUM Supplement 1 — propagation of distributions by Monte Carlo; still current | **open** | Method source if input uncertainty propagation is done (e.g. density/enrichment sampling); not for the Monte Carlo transport statistics itself | same |
| JCGM GUM-1:2023, GUM-6:2020 | new GUM parts (introduction; developing measurement models) | open | Information | same |
| BIPM SI Brochure | 9th edition (2019); downloaded version **V3.01 (2024)**; the BIPM page says "updated in 2026" — current sub-version number **NOT VERIFIED** | **open** (CC BY 4.0) | Writing of units; separating % from the number with a space; if definitional terms such as "ppm" are used, their definition must be stated explicitly (the same principle for pcm) | [BIPM SI Brochure](https://www.bipm.org/en/publications/si-brochure), [V3.01 PDF](https://www.bipm.org/documents/d/guest/si-brochure-9-3_01) |
| ISO 80000-10 | **2019 + Amd 1:2025** | paid | Names/symbols of quantities in atomic and nuclear physics (e.g. effective multiplication factor, reactivity) — clause numbers **NOT VERIFIED** | [ISO 80000-10](https://www.iso.org/standard/64980.html), [Amd 1](https://www.iso.org/standard/87106.html) |
| IAEA Nuclear Safety and Security Glossary | **2022 (Interim) Edition** (formerly the IAEA Safety Glossary) | **open** | `docs/SOZLUK.md` and the English interface terms | [IAEA](https://www.iaea.org/publications/15236/iaea-nuclear-safety-and-security-glossary) |
| ISO 921:1997 | **Withdrawn**; replaced by the **ISO 12749** series (e.g. 12749-3:2024 nuclear installations/processes; 12749-5:2018 nuclear reactors) | paid | If an ISO source is needed for terminology, 12749 should be cited | [ISO 921](https://www.iso.org/standard/5333.html), [ISO 12749-3:2024](https://www.iso.org/standard/82724.html), [ISO 12749-5:2018](https://www.iso.org/standard/67429.html) |

---

## 3. Skeleton of the conformity matrix

The rule identifiers keep K1–K7 of the plan; S-0 proposes new rules (K8–K17). Profiles:
**A** Monte Carlo good practice (every run), **B** criticality safety, **C** reactor core design,
**D** reporting, **Y** software quality evidence (S-4; proposed new letter). The "Status" column
reflects the state after S-1…S-4 (01.10.2026). The "Test" column is the idea for a red→green
fixture.

**Profile B connection (01.10.2026, Wave 4).** S-3 calculates the bias/USL summary; the
conformity panel, the report appendix and the `openmc-arayuz-kosu uygunluk` command connect it
**automatically** through `cekirdek/vv/kume.uygulama_ozeti`. The USL is calculated only from the
subset with the application's fissile species, physical form and spectrum (for U-235 also the
enrichment class LEU/IEU/HEU); if the matching subset has fewer than 10 cases, **no USL is
given** (`testler/test_vv_altkume.py`). In the 26-case repository set the largest matching
subset has 5 cases, so **today no application gets a USL** (e.g. pwr_17x17: the only matching
case is LCT-008). The previous version selected the subset by spectrum only and gave pwr_17x17 a
USL of 0.93877 from 9 solutions + 1 lattice; fixed. This is why K6, K6-AOA and K8–K14 are
"partial" below: the rules are connected and tested, but the coverage of the set is not
sufficient for a USL.

| # | Source / topic | Rule | Profile | What is checked (summary) | Proposed test | Status |
|---|---|---|---|---|---|---|
| 1 | Good practice (not a standard); NUREG/CR-6698 §2.4 footnote: in Monte Carlo the convergence must be judged by the user | K1 | A | Shannon entropy plateau; number of inactive batches larger than the start of the plateau | A fake `statepoint` that moves to active batches before the entropy reaches a plateau | met (S-1 rule; S-2 panel + report appendix) |
| 2 | Good practice (not a standard): Brown, LA-UR-09-03136 (2009) §III.C ("1000s of neutrons/cycle" in every calculation → 1000), §V ("at least 5000" in a long production run; "a few hundred active cycles" → no number), §IV.A (correlation between batches makes σ underestimated); NUREG/CR-6698 eq. (36) uses the σ of k | K2 | A | σ_k ≤ profile target; lower limits for active batches and particles per batch; note on correlation between batches. The particle thresholds come **from a good-practice source** (not a standard); the σ target is a profile value. Brown's finding of "1.7–4.7 times" is for local tallies (§IV.B Table 2) and is not carried over to k-eff | Run with σ_k above the target | partial: lower particle limit and batch correlation are checked; the σ target and the lower limit of active batches have no sourced number → profile input (otherwise "not applicable") |
| 3 | Good practice (OpenMC) | K3 | A | Lost particles = 0 | Output containing a lost particle warning | met (S-1; S-2: an interface run also writes `kosu.log`, lost particles appear on the Run page — M5) |
| 4 | ANS-10.4 (traceability), NUREG/CR-6698 §2.3 (description of code, modules, library, hardware) | K4 | D | Library name + version, temperatures, S(α,β), data sha256, OpenMC version, operating system/hardware summary in the report | Report missing the library version | met (S-1 rule; report reproducibility block) |
| 5 | JCGM 100 §7.2.2, §7.2.3, §7.2.6; BIPM SI Brochure (definitional terms) | K5 | D | (a) standard uncertainty together with k and the label "1σ, standard uncertainty"; (b) uncertainty ≤ 2 significant digits, value rounded to the same digit; (c) if "±" is used, a statement that it is not a confidence interval, or the parenthesis format `1.00038(25)`; (d) pcm definition written **and it is clear to which quantity it applies**: Δk × 10⁵ (as in the C−E column of VV.md) or Δρ × 10⁵ (ρ = (k−1)/k; between two states Δρ = (k₂−k₁)/(k₁k₂)) | σ with 3 significant digits; undefined pcm | met (S-1 checker; S-2: the generated report passes K5 cleanly — `test_uygunluk_arayuz` S2-1) |
| 6 | NUREG/CR-6698 eqs. (1), (35), (36) | K6 (**corrected**) | B | `k_calc + 2σ_calc < USL`. The plan's generalisation `k + Kσ` may stay, but the **default must be K = 2** (the condition of 6698) and the inequality is strict (<) | k + 2σ = USL − ε and USL + ε | partial (S-3): V&V set of 26 experiments; the application's subset (species + form + spectrum + U-235 enrichment class) has at most 5 cases → **no USL is given**; the mixed spectrum-only subsets (fast 0.9444, thermal 0.9388) are descriptive (`docs/VV.md`); when K6 passes, the subset, n and the method are stated |
| 7 | NUREG/CR-6698 §2.5, Table 2.3 | K6-AOA | B | Area of applicability: same fissile element; enrichment band (e.g. ±1.5 for 2–5 %; ±10 weight percentage points for 80–100 %); same physical form (metal/oxide/solution/compound); H/X ±20 %; same reflector material; same spectrum class (thermal 0–1 eV, intermediate 1 eV–100 keV, fast 100 keV–20 MeV; by EALF) | Out-of-range enrichment and a different physical form | partial (S-3): AOA parameters are extracted from the spec and from the EALF tally (`cekirdek/vv/aoa.py`; AOA table in `docs/VV.md`); connected to the panel/report/CLI (note above) |
| 8 | NUREG/CR-6698 §2.4.1 eq. (8), §1.2 | K8 (new) | B | A positive bias is not credited (0 if bias > 0) | Set with mean k > 1 | partial (S-3): rule tested with the V&V set (VV7); the bias is negative in all subsets; connected to the panel/report/CLI (note above) |
| 9 | NUREG/CR-6698 §2.4.1 eq. (9) | K9 (new) | B | If the benchmark k_exp ≠ 1, k_norm = k_calc / k_exp is used; combined σ = √(σ_calc² + σ_exp²) | LCT-008 with k_exp = 1.0007 | partial (S-3): k_norm = k_calc / k_exp is applied in the set (e.g. LCT-008 E = 1.0007); connected to the panel/report/CLI (note above) |
| 10 | NUREG/CR-6698 §2.2 (fewer than 10 experiments require justification), Table 2.2 (confidence ≤ 40 % → more data needed) | K10 (new) | B | n < 10 → WARNING "technical justification required"; non-parametric confidence ≤ 40 % → **USL could not be calculated** | Sets with n = 5 and n = 9 | partial (S-3): n < 10 → no USL is given (additional rule of the tool, `n_usl_asgari`); β ≤ 40 % → "could not be calculated"; connected to the panel/report/CLI (note above) |
| 11 | NUREG/CR-6698 §2.4.5 (ΔSM ≥ 0.02 absolute lower limit); NUREG-1520 Ch.5 App. B / NUREG-1718 (0.05 generally accepted — **NOT VERIFIED**) | K11 (new) | B | Profile ΔSM < 0.02 → ERROR (invalid profile); default 0.05, source written | Profile with ΔSM = 0.01 | met (the profile ΔSM threshold is checked; no V&V needed) |
| 12 | NUREG/CR-6698 §5 | K12 (new) | B | If an application parameter lies outside the validation range: in the tolerance *limit* method extrapolation is forbidden → ERROR/WARNING; extrapolation by more than 10 % of the range → "the validation set should be extended"; ΔAOA a user input with a justification text | An application 12 % outside the range | partial (S-3): numerical AOA range from the set (enrichment, H/X, EALF); ΔAOA a user input; connected to the panel/report/CLI (note above) |
| 13 | NUREG/CR-6698 §2.4.2–2.4.3 | K13 (new) | B | Results of the trend test (weighted linear fit; slope significance) and of the normality test in the report; method selection depends on these results | Set with a clear H/X trend | partial (S-3): Shapiro–Wilk and weighted linear trend (t-test from SCALE/VADER, not in 6698); no significant trend in any subset; connected to the panel/report/CLI (note above) |
| 14 | WPNCS/UACSA 2013; UACSA Phase IV (correlation between experiments) | K14 (new) | B | If many cases from the same experimental series (e.g. the 17 cases of LCT-008) enter the set → INFO: "the cases are not independent; the statistical confidence may be overstated" | 10 cases from one series | partial (S-3): "not independent" note for LEU-SOL-THERM-002 cases 1/2; the correlation itself is not calculated; connected to the panel/report/CLI (note above) |
| 15 | NUREG/CR-6698 §6 (report format), §2 (independent reproducibility) | K15 (new) | D (+B) | Sections of the validation report: introduction, code system, method, experiment descriptions, analysis of results (trend, statistics, bias, uncertainty, AOA, USL), conclusion; the signature/independent reviewer field is left blank (filled in by the organisation) | Report with a missing section | partial: `docs/VV.md` (S-3) contains most sections of 6698 §6 (code system, method, experiment descriptions, trend/normality/bias/AOA/USL, limitations); no signature/independent reviewer field; no rule checks the report |
| 16 | NUREG-0800 §4.3 II.2 (GDC 11), SRP §4.3 III | K7 (**corrected**) | C | Sign of the **power coefficient and Doppler coefficient** (the net prompt feedback in the power operating range must be negative) → ERROR/WARNING. **A positive MTC alone is NOT an ERROR** (the SRP explicitly does not exclude a positive MTC; e.g. PWR beginning of life) → INFO + "should be evaluated in the transient analysis". **No** numerical acceptance range for the coefficients | Positive MTC + negative Doppler: info; positive power coefficient: error | partial: rule ready; coefficients from the "kor" key of `uygunluk_girdisi.json` (no connection to the Analysis page) |
| 17 | NUREG-0800 §4.3 (SDM, most reactive rod stuck out; value blank), GDC 26/27 | K7-SDM | C | The shutdown margin is calculated assuming the most reactive rod stuck out; the limit is a **user input**, no default; the rod worth uncertainty (including method error) is noted | Profile without a limit → "could not be compared" | partial: rule ready; margin and limit are user inputs (`uygunluk_girdisi.json`) |
| 18 | NUREG-0800 §4.3 (power distribution limits are plant-specific) | K7-F | C | F_ΔH, F_q are compared only with a user limit | Profile without limits | met (F_ΔH / F_q from the statepoint; without a limit "could not be compared") |
| 19 | ANS-19.3-2022 / ISO 18075 (method V&V, range of applicability, documentation) | K16 (new) | C | The report states with which benchmarks (IRPhEP / calculation-to-calculation) the core calculation was validated and the application range of these benchmarks | Core report without a benchmark reference | partial: "not met" note if no reference is entered; clause details **NOT VERIFIED** |
| 20 | IAEA SSG-22 (Rev. 1) graded approach | profile structure | C | Profile thresholds selectable by reactor type (power / research / critical assembly) | — | partial: Profile C `reaktor_turu` threshold; thresholds via `profiller.dosyadan_uyarla` |
| 21 | ANS-10.4-2008 (R2021); IEEE 1012-2024 (integrity level) | Y1 (new) | Y | Requirement (R-…) → test → latest result matrix; lists of requirements without tests and tests without requirements; declaration of the tool's integrity level | Requirement without a test | met (S-4): `docs/IZLENEBILIRLIK.md` (`araclar/izlenebilirlik.py`; R-S-15); integrity level declaration in `docs/YAZILIM_KALITE.md` §1. Note: the matrix in the repository was generated from result files from before the S-3 merge (R-M2-01 and R-S-14 are "without tests" there; their tests are now marked) — it should be regenerated |
| 22 | NQA-1 Subpart 2.7 (configuration management, change of operating environment); NUREG/CR-6698 §1.2 (periodic validation test) | Y2 (new) | Y | Environment lock (conda hash, OpenMC and library version); when the environment changes, rerun of a short benchmark package and comparison with earlier results | Run directory with a changed library hash | partial (S-4): `kapsul.json` in every run (hashes of spec, OpenMC, library and chain, environment lock summary) and the difference report of `openmc-arayuz-kosu yeniden` (R-S-16, R-S-17); rerunning the benchmark package when the environment changes is not automatic (by hand: `pytest testler/test_benchmark.py -m yavas`); no full lock file is stored (`docs/YAZILIM_KALITE.md` §4 item 7) |
| 23 | ANS-10.5 (user needs); ANS-10.3 (historical) | Y3 (new) | Y | Document set: user guide, known limitations, example problems, change log | — | partial (S-4): document set and its gaps in `docs/YAZILIM_KALITE.md` §2 (R-S-18); example problems in `docs/ORNEKLER.md`; known limitations scattered; user guide in `docs/kilavuz/{tr,en}` (TR + EN); the change log is separate Wave 4 work |
| 24 | ISO/IEC/IEEE 12207:2026 | Y4 | Y | Process names in the S-4 documents are mapped to 12207 terms (naming only) | — | met (S-4): last column of `docs/YAZILIM_KALITE.md` §2 (naming only; it is not claimed that the processes are implemented according to 12207) |
| 25 | IAEA Glossary 2022; ISO 12749 | terminology | D | SOZLUK.md terms are linked to the IAEA definitions | — | partial: `docs/SOZLUK.md` (Wave 3) takes the IAEA Glossary 2022 and OpenMC naming as its sources; no link to the IAEA definition per term |
| 26 | ANS-8.1 / ISO 1709 / SSG-27: operational controls, double contingency principle, accident alarm | — | — | The tool does not assess facility operation | — | out of scope |
| 27 | RG 1.203 EMDAP (transient and accident models) | — | — | The tool performs no transient/accident analysis; only the graded-approach idea is taken | — | out of scope |
| 28 | ANS-8.24 clause-level requirements | — | B | Text not seen | — | not verified |

Status vocabulary (Turkish original → English): karşılandı → met; kısmen → partial;
planlandı → planned; kapsam dışı → out of scope; doğrulanmadı → not verified.

---

## 4. Summary of the NUREG/CR-6698 method (can be turned into code)

Source: NUREG/CR-6698 (January 2001), [ML050250061](https://www.nrc.gov/docs/ML0502/ML050250061.pdf).
The equation numbers are those of the document. The document is an open NRC contractor report;
the formulas are mathematical expressions and are written below in our own notation. **All the
formulas below were verified by numerically reproducing the document's 25-point example in
§3–4** (see §4.9).

### 4.1 Inputs

For each benchmark case i = 1…n: `k_i` (calculated), `σ_calc,i` (Monte Carlo 1σ), `k_exp,i` and
`σ_exp,i` (benchmark value and its uncertainty), one or more trend parameters `x_i`
(H/X, enrichment, EALF…), and the AOA parameters.

1. **Normalisation** (eq. 9): `k_norm,i = k_i / k_exp,i`. The absolute value of the bias must
   never be reduced by this step.
2. **Combined uncertainty** (eq. 3): `σ_i = sqrt(σ_calc,i² + σ_exp,i²)`; weight `w_i = 1/σ_i²`.
   (The VADER implementation combines the σ's in relative terms; at k ≈ 1 the difference is
   negligible.)

### 4.2 Weighted statistics (eqs. 4–7)

```
W      = Σ w_i
k̄      = Σ w_i k_i / W                                  (6)  weighted mean
s²     = [ (1/(n−1)) Σ w_i (k_i − k̄)² ] / [ W / n ]      (4)  variance about the mean
σ̄²     = n / W                                          (5)  average total uncertainty
S_p    = sqrt(s² + σ̄²)                                  (7)  pooled standard deviation
bias   = k̄ − 1  (if k̄ < 1), otherwise 0                (8)  positive bias is not credited
```

### 4.3 Trend (eqs. 10–15)

Weighted linear fit `k_fit(x) = a + b·x`:
```
x̄    = Σ w_i x_i / W
b    = Σ w_i (x_i − x̄)(k_i − k̄) / Σ w_i (x_i − x̄)²
a    = k̄ − b·x̄
r    = Σ w_i (x_i − x̄)(k_i − k̄) / sqrt( Σ w_i (x_i − x̄)² · Σ w_i (k_i − k̄)² )
```
For goodness of fit the document recommends (i) plots with different axis scales and (ii) a
numerical measure (r, r² or χ²), and notes that r alone is not an absolute measure. The document
**does not define** a test for the significance of the slope; SCALE/VADER uses the following
t-test (a proposal, not in 6698):
`t = |b| / (σ_fit / sqrt(S_xx))`; the trend is significant if `t > t_{α/2, n−2}`
([SCALE VADER](https://scale-manual.ornl.gov/6.3.3/vader.html)).

### 4.4 Normality test (§2.4.3)

- For fewer than 50 samples, the **Shapiro–Wilk W test** (eqs. 16–19; coefficients in Appendix A,
  n = 10–50; percentage points in Table A.5). The values are sorted in increasing order;
  `W = (Σ_{j=1}^{v} a_j (y_(n+1−j) − y_(j)))² / Σ (y_i − ȳ)²`,
  `v = n/2` (even) or `(n−1)/2` (odd). If W is larger than the critical value at α = 0.05, the
  data are accepted as normal.
- Implementation note: `scipy.stats.shapiro` can be used in code (p > 0.05 ⇒ normal); for the
  document's example scipy gives W = 0.9201 and the document W = 0.9182 (difference in table
  coefficients); both are above the n = 25 critical value of 0.918. When the weighted mean is
  used the document finds W = 0.9177 and writes that the example is "borderline" → for borderline
  results the tool should report both methods.
- For n > 50 the document gives no method (**NOT VERIFIED**: no D'Agostino recommendation was
  seen in 6698). VADER offers χ² and Anderson–Darling.
- If normality fails, **the non-parametric method is mandatory**.

### 4.5 One-sided lower tolerance limit — no trend, normal data (eqs. 20–22)

```
K_L = min(k̄, 1) − U · S_p                                (20)–(21)
USL = K_L − ΔSM − ΔAOA                                   (22)
```
`U`: one-sided tolerance factor such that 95 % of the population lies above it with 95 %
confidence (Table 2.1: n=10 → 2.911; 15 → 2.566; 20 → 2.396; 25 → 2.292; 30 → 2.220; 40 → 2.126;
50 → 2.065). **For n > 50 the n = 50 value can be used conservatively.** In code the exact value
is calculated with the non-central t distribution and agrees with the table to 3 decimals
(verified):
```
U(n) = t⁻¹_nct(0.95; ν = n−1, δ = z_0.95 · sqrt(n)) / sqrt(n)
```
This method **cannot be used for extrapolation** outside the AOA.

### 4.6 One-sided lower tolerance band — with a trend (eqs. 23–30)

```
S_xx   = Σ w_i (x_i − x̄)² / (W / n)                                      (26)
s_fit² = (n/(n−2)) · Σ w_i (k_i − k_fit(x_i))² / W                       (30)
S_p    = sqrt(s_fit² + σ̄²)                                               (28)–(29)
k*(x)  = min(k_fit(x), 1)                     # positive bias not credited (24)
K_L(x) = k*(x) − S_p · [ sqrt( 2·F · (1/n + (x − x̄)²/S_xx) ) + z · sqrt( (n−2) / χ² ) ]   (23)
USL(x) = K_L(x) − ΔSM − ΔAOA
```
Constants (P = 0.95 confidence, n−2 degrees of freedom):
`F = F⁻¹(0.95; 2, n−2)` (Excel FINV(0.05,2,n−2)); `z = Φ⁻¹(0.95) = 1.645`;
`χ² = χ²⁻¹(0.025; n−2)`, i.e. the **lower** 2.5 % point (Excel CHIINV(0.975, n−2)).
For n = 25, F = 3.422 and χ² = 11.689. The band widens by itself as one moves outside the data
range; for this reason the document says that an additional ΔAOA may not be needed with the band
method (§5). The document also mentions a "confidence band" technique but gives no formula (the
USL-1/USL-2 of VADER originate from NUREG/CR-6361 — **not in 6698**; if S-3 wants them, they must
be coded from a separate source).

### 4.7 Non-parametric method — data not normal (eqs. 31–34)

```
β(m) = 1 − Σ_{j=0}^{m−1} C(n, j) (1−q)^j q^(n−j)     q = 0.95 (population fraction)  (31)
for m = 1 (the smallest value):  β = 1 − qⁿ                                           (32)
K_L = k_(1) − σ_(1) − NPM          (own combined σ of the smallest k_norm)              (33)
if k_(1) > 1:  K_L = 1 − S_p − NPM                                                     (34)
```
NPM (Table 2.2, "recommended", may be changed with justification):

| β (confidence) | NPM |
|---|---|
| > 90 % | 0.00 |
| > 80 % | 0.01 |
| > 70 % | 0.02 |
| > 60 % | 0.03 |
| > 50 % | 0.04 |
| > 40 % | 0.05 |
| ≤ 40 % | **more data needed** (roughly n < 10) → the tool should say "USL could not be calculated" |

For 95 %/95 % at least **59 experiments** are needed (NPM = 0). n = 19 → β = 62.3 %; n = 25 →
72.26 %.

### 4.8 Margin of subcriticality, USL and acceptance condition (§2.4.5–2.4.6, eqs. 1, 35, 36)

```
USL = 1 + bias − σ_bias − ΔSM − ΔAOA        (1)  (formal definition)
USL = K_L − ΔSM − ΔAOA                      (35) (form used in practice)
Acceptance:  k_calc + 2·σ_calc < USL         (36)
```
- **ΔSM ≥ 0.02 is the absolute lower limit**; the chosen value **must be justified** by the
  reactivity sensitivity of the controlled parameter and the type of control
  (physical/administrative). Example in the document: if a tolerance of ±½ inch gives 0.01 Δk,
  a margin of 0.02 is justified.
- ΔAOA: 0 if the AOA is not extended. An extrapolation of 5–10 % of the parameter counts as
  "large" and requires an additional margin; for an extrapolation beyond 10 % the validation set
  must be extended (§1.2, §5).
- The margin is **not** meant to cover process upsets or process uncertainties; it only sets the
  largest k that may be considered subcritical on the basis of the validation result.

### 4.9 Numerical cross-check data (for the S-3 test fixture)

With the 25 cases in NUREG/CR-6698 Table 3.1 (H/X, k, σ_calc; σ_exp = 0.0049 in all cases), the
following results were **reproduced exactly** in this work with Python/SciPy:

| Quantity | Document | Recalculated |
|---|---|---|
| k̄ (weighted) | 0.99983 | 0.999834 |
| s² | 8.47993e−5 | 8.47993e−5 |
| σ̄² | 2.67991e−5 | 2.67991e−5 |
| S_p | 1.056e−2 | 1.0564e−2 |
| K_L (U = 2.292) | 0.97562 | 0.97562 |
| USL (ΔSM 0.02, ΔAOA 0.03) | 0.92562 | 0.92562 |
| β (non-parametric, n = 25) | 72.26 % | 72.26 % |
| K_L non-parametric (0.9848 − 0.0051 − 0.02) | 0.9597 | — (arithmetic) |
| a, b (weighted linear) | 1.00967, −2.863e−5 | 1.00967, −2.8629e−5 |
| x̄ | 343.58 | 343.576 |
| s_fit², S_p (band) | 3.782e−5, 0.008039 | 3.782e−5, 0.0080386 |
| K_L(421.8) / USL | 0.9746 / 0.9546 | 0.9746 / 0.9546 |
| K_L(971.7) / USL | 0.9515 / 0.9315 | 0.9515 / 0.9315 |
| K_L(133.4) / USL | 0.9758 / 0.9558 | 0.9758 / 0.9558 |

Note: in the text extraction the H/X value of row 17 was read as "−133.4"; the correct value is
133.4 (the other values and the results confirm this). In the example ΔAOA = 0.03 is for
illustration only.

### 4.10 Limitations of the document that carry over to the code

- **Correlation** between experiments is not treated (independence assumption); the UACSA work
  shows this as an open topic ([PSI/UACSA 2007](https://www.oecd-nea.org/science/wpncs/UACSA/kick-off%20meeting/PSI-1.pdf)).
- The justification of the method choice belongs to the user organisation (§2.4.4); the tool
  proposes, it does not enforce.
- There is a warning that Excel statistical functions are wrong in some versions; the tool should
  use SciPy and compare with the Table 2.1 values in a unit test.

---

## 5. Candidate benchmark case list (target 20–30)

Selection criteria: (i) evaluated in ICSBEP; (ii) the benchmark k and σ are given in **an openly
published source** (LANL LA-UR-02-0878 "distribution is unlimited", or mit-crpg
`uncertainties.csv`); (iii) an **MIT-licensed OpenMC model** exists in the mit-crpg repository;
(iv) a geometry that the tool can build (sphere, cylinder, lattice, infinite medium). The green
set is formed by LANL's 26-case validation suite, because this set was chosen with attention to
spectrum and material variety and has been published openly
([LA-UR-02-0878 Tables 1–2](https://mcnpx.lanl.gov/pdf_files/TechReport_2002_LANL_LA-UR-02-0878_Mosteller.pdf)).

**Important warning:** E ± σ values can change between ICSBEP editions. Below, two open sources
are shown separately; conflicts are marked. S-3 must not formally add any case to the set without
verifying its value **in the current ICSBEP edition**. All of them should be considered **NOT
VERIFIED (handbook text not seen)**.

| # | ICSBEP ID | Short name | Material / form / spectrum | E ± σ (LA-UR-02-0878) | E ± σ (mit-crpg csv) | OpenMC model | Why suitable | Status in the tool |
|---|---|---|---|---|---|---|---|---|
| 1 | HEU-MET-FAST-001 | Godiva | HEU metal, bare sphere, fast | 1.0000 ± 0.0010 | 1.0 ± 0.001 | yes | The most basic fast U-235 case | **present** (godiva_kriter) |
| 2 | HEU-MET-FAST-028 | Flattop-25 | HEU metal, natural U reflected, fast | 1.0000 ± 0.0030 | 1.0 ± 0.0030 | yes | Heavy reflector effect | **present** |
| 3 | HEU-MET-FAST-004 | "Godiver" | HEU metal, water reflected, fast | 0.9985 ± 0.0011 | 0.9985 ± **0.0 (σ missing in the csv)** | yes | Light reflector | candidate |
| 4 | HEU-MET-INTER-006, case 2 | ZEUS | HEU plates, graphite moderator, copper reflector, intermediate | 0.9997 ± 0.0008 | **1.0001** ± 0.0008 (conflict) | yes | Intermediate spectrum (rare) | candidate |
| 5 | HEU-SOL-THERM-032 | ORNL-10 | HEU uranyl nitrate solution, large sphere, thermal | 1.0015 ± 0.0026 | 1.0015 ± 0.0026 | yes | HEU solution, thermal | candidate |
| 6 | HEU-SOL-THERM-013, case 1 | — | HEU solution, thermal | — | 1.0012 ± 0.0026 | yes | Solution variety | candidate |
| 7 | HEU-SOL-THERM-001, case 1 | — | HEU solution, thermal | — | 1.0004 ± 0.0060 | yes | Solution variety (large σ) | candidate |
| 8 | IEU-MET-FAST-003 | — | 36 % U metal, bare sphere, fast | 1.0000 ± 0.0017 | 1.0 ± 0.0017 | yes | Intermediate enrichment | candidate |
| 9 | IEU-MET-FAST-004 | — | 36 % U metal, graphite reflector, fast | 1.0000 ± 0.0030 | 1.0 ± 0.0030 | yes | Graphite reflector | candidate |
| 10 | IEU-MET-FAST-007 | Big Ten | 10 % U metal cylinder, natural U reflector, fast | 0.9948 ± 0.0013 (simple model) | 1.0045 ± 0.0007 (case 1; detailed model) — **depends on the model type** | yes | Low-enriched fast system; sensitive to U-238 data | candidate (model type to be chosen) |
| 11 | LEU-COMP-THERM-008, case 1 | B&W XI | LEU UO₂ pin lattice, borated water, thermal | 1.0007 ± 0.0012 | 1.0007 ± 0.0012 | yes | The case closest to an LWR | **present** (kriter_lct008) |
| 12 | LEU-COMP-THERM-008, case 2 | B&W XI (2) | same series | 1.0007 ± 0.0012 | 1.0007 ± 0.0012 | yes | The case in the LANL suite; because it is from the same series, **K14 correlation warning** | candidate |
| 13 | LEU-SOL-THERM-001 | SHEBA-II | 5 % U uranyl fluoride solution, annular cylinder, thermal | 0.9991 ± 0.0029 | 0.9991 ± 0.0029 | yes | LEU solution | candidate |
| 14 | LEU-SOL-THERM-002, case 1 | — | LEU solution, thermal | — | 1.0038 ± 0.0040 | yes | LEU solution variety | candidate |
| 15 | LEU-SOL-THERM-007, case 14 | (STACY — **NOT VERIFIED**) | ~10 % U uranyl nitrate, thermal | — | 0.9961 ± 0.0009 | yes | LEU solution with small σ | candidate |
| 16 | PU-MET-FAST-001 | Jezebel | Pu metal, bare sphere, fast | 1.0000 ± 0.0020 | 1.0 ± 0.0020 | yes | Basic Pu case | **present** (kriter_jezebel) |
| 17 | PU-MET-FAST-002 | Jezebel-240 | Pu (20.1 % Pu-240), bare sphere, fast | 1.0000 ± 0.0020 | 1.0 ± 0.0020 | yes | Pu-240 content | candidate |
| 18 | PU-MET-FAST-006 | Flattop-Pu | Pu sphere, natural U reflector, fast | 1.0000 ± 0.0030 | 1.0 ± 0.0030 | yes | Heavy reflector + Pu | candidate |
| 19 | PU-MET-FAST-011 | — | Pu sphere, water reflector, fast | 1.0000 ± 0.0010 | (csv row not seen in this work) | yes | Light reflector + Pu | candidate |
| 20 | PU-MET-FAST-003, case 3 | Pu Buttons | 3×3×3 array of small Pu cylinders, fast | 1.0000 ± 0.0030 | (only a "case-103" model seen in the repository — **match NOT VERIFIED**) | partly | Array geometry | candidate (conditional) |
| 21 | PU-COMP-INTER-001 | HISS/HPG | Pu + H + graphite infinite homogeneous mixture, intermediate | 1.0000 ± 0.0110 | 1.0 ± 0.0110 | yes | Infinite medium — the easiest to build; large σ_exp (low weight) | candidate |
| 22 | PU-SOL-THERM-021, case 3 | PNL-2 | Pu nitrate solution sphere, thermal | 1.0000 ± 0.0065 | 1.0 ± 0.0065 | yes | Pu solution | candidate |
| 23 | PU-SOL-THERM-001, case 1 | — | Pu nitrate solution, thermal | — | 1.0 ± 0.0050 | yes | Pu solution variety | candidate |
| 24 | MIX-COMP-THERM-002, PNL-33 | PNL-33 | MOX pin lattice, borated water, thermal | 1.0024 ± 0.0021 | 1.0024 ± 0.0024 (pnl-33) / 0.0021 (pnl-33d) — **σ difference from the model type** | yes | MOX lattice (thermal Pu) | candidate |
| 25 | U233-MET-FAST-001 | Jezebel-233 | U-233 metal, bare sphere, fast | 1.0000 ± 0.0010 | 1.0 ± 0.0010 | yes | U-233 (relevant to the Th cycle) | candidate |
| 26 | U233-MET-FAST-006 | Flattop-23 | U-233 sphere, natural U reflector, fast | 1.0000 ± 0.0014 | 1.0 ± 0.0014 | yes | U-233 + heavy reflector | candidate |
| 27 | U233-MET-FAST-005, case 2 | — | U-233 sphere, Be reflector, fast | 1.0000 ± 0.0030 | 1.0 ± 0.0030 | yes | Be reflector | candidate |
| 28 | U233-SOL-INTER-001, case 1 | Falstaff (1) | U-233 uranyl fluoride solution sphere, intermediate | 1.0000 ± 0.0083 | (csv row not seen) | yes | Intermediate-spectrum solution | candidate |
| 29 | U233-SOL-THERM-008 | ORNL-11 | U-233 uranyl nitrate large sphere, thermal | 1.0006 ± 0.0029 | (csv row not seen) | yes | U-233 thermal | candidate |

Three cases in the LANL suite **without an OpenMC model in mit-crpg**: HEU-COMP-INTER-004
(HISS/HUG), HEU-MET-THERM-003 case 4, IEU-COMP-THERM-002 case 3 — these cannot enter the set
unless they are remodelled from the ICSBEP text.

Coverage assessment and gaps:
- Spectrum: fast (≈17), intermediate (4), thermal (≈10) — varied; but they do not all fit into
  **a single AOA**. According to NUREG/CR-6698 the USL is calculated separately for each AOA;
  for example, for the "LEU thermal lattice" AOA this list contains only the LCT-008 series, and
  this single series does not meet the condition of 10 independent cases. For the LWR/LEU
  applications that universities use most often, **additional cases from the LEU-COMP-THERM series
  (e.g. LCT-001, -002, -039 etc.) are needed**; these are not in mit-crpg and must be obtained by
  requesting the ICSBEP handbook (access: §2.4).
- For this reason, in the first version the tool **should not calculate the USL** for the
  "LEU thermal lattice" AOA ("not enough independent cases") and should only show the C/E table.

---

## 6. Items in the plan table that turned out to be wrong or incomplete

1. **ANSI/ANS-10.3** is listed as if it were a current standard; the 1995 edition is in
   **historical** status, and the ANS-10 subcommittee now maintains only 10.2, 10.4 and 10.5.
   It must not be made the basis of conformity
   ([ANSI](https://webstore.ansi.org/standards/ansi/ansians101995)).
2. The scope of **ANSI/ANS-10.4** is incomplete in the plan table: the standard is only for
   **non-safety-related** (research/non-critical) software — this is the right framework for this
   tool, but a claim of "safety analysis software" cannot rest on it. Current: 2008 (R2021);
   revision in draft.
3. **ANSI/ANS-10.5**: 2006 edition; the reaffirmation year conflicts between sources
   (R2016 / R2026) — NOT VERIFIED.
4. **ASME NQA-1**: the ASME page shows the latest edition as **2026** (2024 also existed).
   Subpart 2.7 is in force, but to which edition the "restructured" note belongs is NOT VERIFIED.
   NQA-1 is an organisational QA programme; a tool cannot be "NQA-1 compliant".
5. **IEEE 1012** is now **1012-2024** (not 2016); **ISO/IEC/IEEE 12207** is now **12207:2026**
   (the 2017 edition was cancelled).
6. The editions of **ANS-8.1 / 8.24** were missing from the table: 8.1-2014 (R2023),
   8.24-2017 (R2023); revisions of both are in draft.
7. **Plan K6 "k_eff + Kσ ≤ USL"**: the NUREG/CR-6698 condition is **k + 2σ < USL** (strict
   inequality, K = 2). In addition, the plan did not mention the **0.02 lower limit** of ΔSM, the
   need for justification when **n < 10**, the need for **59 experiments for 95 %/95 %** in the
   non-parametric method, the non-crediting of a positive bias, or the k_calc/k_exp
   normalisation (new K8–K12).
8. **Plan K7 "sign of the reactivity coefficients"**: NUREG-0800 §4.3 Rev.3 states explicitly
   that it gives no numerical acceptance range for the coefficients and that it **does not exclude
   a positive MTC**; the direct requirement is GDC 11 (the net prompt feedback in the power
   operating range must compensate a reactivity increase; in an LWR this is achieved by the
   Doppler and a negative power coefficient). Counting a positive MTC as an ERROR produces false
   alarms. The numerical value of the shutdown margin is also blank in the SRP (plant-specific).
9. **IAEA SSG-52** is only for the core design of **nuclear power plants** (2019, under SSR-2/1
   Rev.1). For research reactors the basis is **SSR-3 (2016)** and **SSG-22 (Rev. 1) (2023)**;
   the "(Rev. 1)" suffix of SSG-22 is missing in the plan. Relevant IAEA documents not in the
   table: **SSG-27 (Rev. 1) 2022** (criticality safety — including validation of calculation
   methods; open international source for Profile B), SSG-20 (Rev. 1), SSG-82.
10. **RG 1.203** is for evaluation models of transient and accident analysis (EMDAP); it gives no
    direct acceptance criterion for static core neutronic design or criticality safety. It must
    not be linked to Profile C as a "source"; it may be cited only as an analogy (graded
    approach, assessment base). The right ANS source for core method validation is
    **ANS-19.3-2022** (and its ISO counterpart **ISO 18075:2018**) — not in the table.
11. **ISO 921** was withdrawn; it was replaced by the **ISO 12749** series (12749-3:2024,
    12749-5:2018).
12. The name **"IAEA Safety Glossary"** is outdated: the current publication is the **IAEA Nuclear
    Safety and Security Glossary, 2022 (Interim) Edition**.
13. The expression **ICSBEP/IRPhEP "open (registered)"** is incomplete: ICSBEP is given to named
    users, with a statement of the detailed intended use and **with a request renewed for every
    edition**; IRPhE is given to authorised users in OECD member countries. Redistribution of the
    handbook content is not free (terms NOT VERIFIED) → when packaging benchmark definitions the
    tool should use only open-source models (mit-crpg, MIT) and openly published E ± σ values, and
    should cite the source.
14. **JCGM 100** should now be cited together with **Amd. 1:2026**; JCGM 101:2008 is current.
    **ISO 80000-10:2019** has an **Amd 1:2025**. **SI Brochure**: 9th edition, V3.01 (2024) and
    later (sub-version NOT VERIFIED).
15. GUM detail for **K5**: the "±" format is not recommended by the GUM for a standard
    uncertainty (if it is used, it must be stated that it is not a confidence interval); the
    uncertainty is given with at most two significant digits (the plan's wording "1–2 significant
    digits" is consistent). When the pcm definition is written, **Δk or Δρ** must be
    distinguished — the "C − E [pcm]" of VV.md is Δk × 10⁵, not a reactivity difference.
16. **K1–K3** (entropy plateau, σ target, lost particles) are not clauses of any standard; they
    must be labelled "good practice" and must not be presented as if they had a standard as their
    source.
17. The acceptance criterion |C − E| ≤ 3·√(σc² + σe²) in VV.md is the project's own criterion; it
    does not come from a standard — this must be stated in the report.

---

## References (accessed 30.09.2026)

- NRC, NUREG/CR-6698 (2001): https://www.nrc.gov/docs/ML0502/ML050250061.pdf
- NRC, NUREG-0800 §4.3 Rev.3 (2007): https://www.nrc.gov/docs/ML0707/ML070740003.pdf
- NRC, RG 1.203 (2005): https://www.nrc.gov/docs/ML0535/ML053500170.pdf
- NRC, RG 3.71 Rev.3 (2018): https://www.nrc.gov/docs/ML1816/ML18169A258.pdf
- NRC, NUREG/CR-7109: https://www.nrc.gov/regulations-legislation/nureg-series-publications/publications-prepared-by-nrc-contractors/cr7109
- ANS, What's New: https://www.ans.org/standards/new/
- ASME NQA-1: https://www.asme.org/codes-standards/find-codes-standards/quality-assurance-requirements-for-nuclear-facility-applications
- IEEE 1012-2024: https://ieeexplore.ieee.org/document/11134780
- ISO/IEC/IEEE 12207:2026: https://ieeexplore.ieee.org/iel8/11481696/11481697/11481698.pdf
- ISO 1709:2018: https://www.iso.org/standard/68617.html ; NCSP summary: https://ncsp.llnl.gov/sites/ncsp/files/2023-12/iso1709_summary_issue3.pdf
- IAEA SSG-52: https://www.iaea.org/publications/13382/design-of-the-reactor-core-for-nuclear-power-plants
- IAEA SSR-3: https://www.iaea.org/publications/7024/safety-of-research-reactors
- IAEA SSG-22 (Rev. 1): https://www.iaea.org/publications/15080/use-of-a-graded-approach-in-the-application-of-the-safety-requirements-for-research-reactors
- IAEA SSG-27 (Rev. 1): https://www.iaea.org/publications/14883/criticality-safety-in-the-handling-of-fissile-material
- IAEA Glossary 2022: https://www.iaea.org/publications/15236/iaea-nuclear-safety-and-security-glossary
- NEA ICSBEP: https://www.oecd-nea.org/jcms/pl_20291/international-criticality-safety-benchmark-evaluation-project-icsbep-handbook
- NEA IRPhE: https://www.oecd-nea.org/tools/abstract/detail/nea-1765/
- NEA/NSC/WPNCS/DOC(2013)7: https://oecd-nea.org/science/wpncs/UACSA/publications/EGUACSASOAR1.pdf
- BIPM JCGM publications: https://www.bipm.org/en/committees/jc/jcgm/publications
- BIPM SI Brochure: https://www.bipm.org/en/publications/si-brochure
- SCALE 6.3.3 VADER (secondary, formula comparison): https://scale-manual.ornl.gov/6.3.3/vader.html
- LANL LA-UR-09-03136 (F.B. Brown, "A Review of Best Practices for Monte Carlo Criticality Calculations", ANS NCSD 2009): https://mcnpx.lanl.gov/pdf_files/TechReport_2009_LANL_LA-UR-09-03136_Brown.pdf — verified from the primary source (01.10.2026): §II.C source convergence (k and H_src plots); §III.C "1000s of neutrons/cycle … for all calculations"; §IV.A correlation between batches makes σ underestimated; §IV.B Table 2 local fission rates 1.7–4.7 times (mean 3.1), no marked bias observed for k-eff (§IV.C); §V "at least 5000 or more neutrons per cycle … for long production runs … a few hundred active cycles"
- LANL LA-UR-02-0878 (Mosteller): https://mcnpx.lanl.gov/pdf_files/TechReport_2002_LANL_LA-UR-02-0878_Mosteller.pdf
- mit-crpg/benchmarks: https://github.com/mit-crpg/benchmarks
