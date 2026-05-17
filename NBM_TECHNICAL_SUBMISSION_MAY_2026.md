**GRIDLEDGER IP LTD**  
Verification Authority · ISIC 7490  
Lingadzi House, Area 40/31, Lilongwe, Malawi  

7 May 2026  

**To:** NBM Development Bank – Risk Desk  
**Subject:** Technical Submission: GridLedger Verification Architecture – Independent Replayability & Integrity Assessment  

---

This transmission provides materials to support an independent technical review of the GridLedger verification architecture. Its purpose is to enable NBM's Risk Desk to assess the system's reproducibility guarantees, operational failure boundaries, and integrity detection mechanisms without relying on any claim made by GridLedger.

No proposal for funding, partnership, or commercial relationship is made in this submission.

**Attached Artifacts**

| # | Document | Purpose |
|---|----------|---------|
| 1 | Architecture Statement (May 2026) | Defines the operational/verification split; Chain of Custody model; formal definition of Seal Invalidity; integrity guarantees; honest‑limits disclosure; data sovereignty position; failure‑domain taxonomy. |
| 2 | Integrity Proof (May 2026) | Reproducible demonstration that alteration of the operational database does not invalidate sealed cycle history. Includes a simulation script that any party can execute against the public trust anchor. |
| 3 | Auditor's Toolkit | Dependency‑light Python script that fetches raw cycle events from the public GitHub repository, recomputes Merkle roots, and compares the results to the published seal chain. No access to GridLedger's servers is required. |

**Verification Architecture Statement**

Sealed cycle records and Merkle roots can be independently recomputed from raw source inputs external to GridLedger's operational infrastructure. The Integrity Proof demonstrates that alteration of the operational database does not propagate to the externally anchored seal chain, and that the resulting mismatch is detectable by independent recomputation. No capacity is claimed beyond what can be independently verified.

**Dependencies & Limitations (Disclosed)**

- ESCOM prepaid token system (external utility record)
- Airtel Money transaction confirmation (mobile network‑dependent)
- Operator‑submitted meter open/close readings (subject to adversarial input risk, mitigated by statistical detection and planned Phase 2 clamp sensors)
- 72‑hour worst‑case detection window for missing remittance cycles
- Conditional enforcement decisions currently retain a degree of lender discretion; full deterministic capital enforcement awaits the Lender Policy Module

Certain mitigation components described in the Architecture Statement remain under phased implementation and are identified accordingly. These limitations are detailed in the Architecture Statement (Section VIII) and are stated upfront. No capacity is claimed beyond what can be independently verified.

**File Integrity References (SHA256)**

```
Architecture Statement:  d92fa940ec2af6b83e22266ccc5e6f4316f4d36bc1ffb2b6a95b7ee8f93a7218
Integrity Proof:         ca2a783127b56d76b8b54729ef51e6d47d00bb5baca2ed1d0f8d6e182a7e1128
Auditor's Toolkit:       6dacda48e22422cafd1e55c84d03140e62cc55d9235434587566b7e870671760
```

The above hashes are provided so that NBM can confirm the received files match the versions referenced in this submission. The exact transmitted files will be archived and timestamped. No silent edits will be made to transmitted versions; any future revision will carry a new version designation.

**Invitation**

The attached materials are provided to support independent technical review of the verification architecture and its replayability assumptions under adverse operational conditions. GridLedger is not asking for a decision on adoption or partnership. We are asking whether the architecture, as documented and demonstrated, would meet the evidentiary standards NBM applies to new verification technologies entering its risk assessment pipeline.

I am available to answer technical questions in writing or in a structured technical session — not a pitch, but a review — at NBM's convenience.

Regards,

**Sanjani Mwambaghi**  
Director, GridLedger IP Ltd  
Verification Authority (ISIC 7490)

---

**Transmission Archive Information**

- **Submission ID:** NBM-GDL-20260507-001
- **Timestamp (UTC):** 2026-05-07T18:45:00Z
- **Submitter:** GridLedger IP Ltd
- **Recipient:** NBM Development Bank – Risk Desk
- **Version:** Final (v1.0)
- **Status:** Frozen (no revisions without version increment)
