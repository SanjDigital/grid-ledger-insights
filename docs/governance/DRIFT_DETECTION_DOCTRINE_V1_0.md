DRIFT DETECTION DOCTRINE

Document: DRIFT_DETECTION_DOCTRINE_V1_0
Issuer: GridLedger IP Ltd — Verification Authority (ISIC 7490)
Status: Frozen — May 2026
Repository: github.com/SanjDigital/grid-ledger-insights
Vocabulary: Consistent with CANONICAL_TERMINOLOGY v1.2

Purpose

This doctrine establishes the governing observable, intercept logic, constitutional constraint, and failure definition for operational drift detection at energy-gated productive nodes. It is an internal governance document. It does not predict machine failure. It defines what the verification layer observes, what it reports, and what it does not infer.

1. The Governing Observable — Specific Energy Consumption (SEC)

Definition: Specific Energy Consumption (SEC) is the ratio of energy input to productive output at cycle resolution.
SEC = kWh consumed per cycle / kg output per cycle 
Or, where output is expressed as revenue proxy:
SEC = kWh consumed per cycle / MWK remitted per cycle 
SEC is the only variable that governs across all operational conditions at an energy-gated productive node because:

Energy consumption is always physically measurable

Production output is always economically measurable

All other signals (vibration, temperature, current draw) are explanatory variables that account for variance in SEC, not independent governing variables

SEC is a Layer 1 output. The GridLedger verification layer seals kWh and cash confirmation at cycle resolution. SEC is computable from those sealed fields without any additional inference.
The verification layer does not interpret SEC. It records the ratio. Interpretation belongs to the Layer 2 condition inference layer.

2. Baseline Establishment

Nabiwi Reference Baseline (March 2026, 31-day observation window):
ParameterValueMean SEC (kWh/cycle)59.9 kWhClean-cycle ratio0.93Observation window705 cyclesVariance bandEstablished from sealed production history 
The baseline is node-specific and established from sealed production history, not from external engineering standards. Each node establishes its own baseline from its own sealed record. No external calibration is imposed.
Baseline methodology: CUSUM (Cumulative Sum) control charting applied to the sealed cycle history. CUSUM detects gradual drift against a node-specific baseline and signals when accumulated deviation exceeds the control limit derived from the node's own variance band.

3. The Layer 2 Intercept Logic

The verification layer (Layer 1) produces sealed cycle records. The condition inference layer (Layer 2) is operated by the lender, the operator, or a separate technical service. Layer 2 reads the Layer 1 output. It does not modify it.
Layer 2 signal definitions (derived from sealed Layer 1 records):
Operational Deviation Signal:

SEC drift exceeds the node's established baseline envelope for 3 or more consecutive sealed cycles

Output: observational flag — not a diagnosis, not a prediction

Recipient: operator (as a maintenance prompt)

GridLedger statement: "SEC increased [X]% above baseline over [N] consecutive cycles. Output was stable. Energy input was rising."

Financial Review Signal:

SEC drift sustained beyond 7 or more consecutive sealed cycles with throughput stable or declining

Output: Layer 2 input for credit exposure review

Recipient: lender (as a risk signal for working capital review)

GridLedger statement: "Deviation from historical production envelope detected across [N] sealed cycles. Energy-to-output ratio is outside the node's calibrated baseline."

What the verification layer does not say:

"This motor is failing"

"Production will decline"

"This node is high risk"

"We predict breakdown"

"Credit exposure is increasing"

All of the above are Layer 2 inferences. The Layer 1 record supports them. It does not make them.

4. The Constitutional Constraint

Layer 3 cannot self-authorize truth.

Decision orchestration systems — whether human credit committees or autonomous capital deployment agents — cannot use their own outputs as verification inputs. The admissibility of any operational state claim depends on Layer 1 sealed physical evidence, not on Layer 3 inference or Layer 3 reported confidence.
This constraint is not a technology design preference. It is the structural safeguard that prevents recursive epistemic failure:

Without Layer 2 evidence constraints: execution systems become self-referential

Self-referential execution systems amplify their own assumptions

Capital deployment accelerates in proportion to synthetic operational confidence

Physical productive reality diverges from digitally-reported state

Capital misallocation compounds until physical failure makes the divergence undeniable

The architectural response is not fraud detection or anomaly scoring. It is physical truth enforcement at the admissibility boundary: no capital action is authorised against an operational state that cannot be anchored to sealed physical evidence.
Note: Enforcement — token gating, revenue lock, advance rate adjustment — is a Layer 3 function performed by the lender through the Capital Action Object. Layer 2 produces the evidence constraint. Layer 3 acts on it. These are distinct functions and must not be conflated.

5. The Failure Mode Definition

Truth latency exceeding execution latency produces systematic capital misallocation.

This is the governing failure condition. It is technologically neutral, economically measurable, and operationally testable. It applies wherever:

Capital deployment velocity exceeds the velocity at which physical productive state can be independently verified

Operational state claims are accepted on the basis of system-reported data without independent physical grounding

Execution systems are permitted to authorise transactions against their own inferences

The failure mode is not fraud. It is not error. It is structural divergence between energetic input and productive truth, compounded by unconstrained execution velocity.

6. The Operational Anchor — Salima Road Motor Failure

The Salima Road node (Lilongwe, M1 Corridor, May 2026) presents the operational instantiation of this doctrine.
Observed state:

One of two motors burnt — rewindable failure

Repair cost: MWK 1.3–1.6 million

Downtime: pending repair

Working capital financing: blocked by price constraint

What sealed SEC records would have shown (had telemetry been active):

Rising kWh per cycle with stable throughput target → energy not converting to output

Cash receipt gaps → operator under financial stress (maintenance deferred)

SEC deviation accumulating across cycles before physical failure

The sealed record would have shown the cash receipt gap before the SEC drift — confirming that financial stress preceded mechanical degradation. This is the causality reversal that distinguishes GridLedger's combined financial-physical record from a purely physical sensor system. Finance determines physics in this environment, not the other way around. A purely physical sensor system cannot detect this.
The doctrine applied:

Operational Deviation Signal: triggered at 3+ consecutive cycles of SEC drift

Financial Review Signal: triggered at 7+ cycles with concurrent throughput stability

No prediction made. No cause inferred. Sealed deviation reported.

Lender reviews credit exposure. Operator receives maintenance prompt.

Intervention cost: MWK 200–300k (preventive service call)

Versus observed outcome: MWK 1.3–1.6M rewind + two weeks downtime

The doctrine does not promise prevention. It makes the observable deviation available for external decision-making before threshold failure.

7. Phase 1 Identity — Correct Scope

This doctrine is grounded in the current admissible dataset:

705 sealed cycles, Nabiwi node, M1 Corridor, Malawi

Baseline SEC: 59.9 kWh/cycle

Observation window: March 2026

Phase 1 claim (the only claim the current dataset supports):

Replayable operational drift detection for infrastructure-constrained productive assets.

This claim is defensible, demonstrable, evidence-backed, and institutionally legible. It does not require extension beyond the sealed production history currently in the corpus.
The doctrine scales when the dataset scales. Not before.

8. What This Doctrine Is Not

This doctrine is not:

A predictive maintenance system

An AI scoring engine

A credit rating methodology

A physical failure prediction model

A machine-economy epistemic framework

It is an operational governance standard for detecting and reporting SEC drift at sealed cycle resolution, within a verification architecture that enforces physical truth as a precondition for capital action.

9. Empirical Verification

The CUSUM detection methodology was verified against the Nabiwi 705-cycle sealed dataset. Two drift periods were planted and detected:
ParameterValueBaseline SEC (mean)59.9 kWh/cycleBaseline SEC (std)Computed from first 10 cyclesCUSUM allowance (K)0.5 σControl limit (H)5.0 σDetection confirmed — Operational Deviation SignalCycles 120–124 (5-cycle drift window)Detection confirmed — Financial Review SignalCycles 450–460 (11-cycle drift window) 
Both signals were detected within the defined thresholds (3+ cycles for operational deviation, 7+ cycles for financial review). The CUSUM parameters are node-calibrated from the Nabiwi baseline and are not imposed from external engineering standards.
Verification status: Empirically confirmed. Methodology and thresholds are frozen at these parameters for the Nabiwi node. Recalibration is required for each new node onboarded, using that node's own sealed production history as the baseline.
"The seal is the moat. The repository is the proof. The governance version is the constitutional memory."
GridLedger IP Ltd — Verification Authority
ISIC Rev. 4, Section M, Division 74, Class 7490 | May 2026
