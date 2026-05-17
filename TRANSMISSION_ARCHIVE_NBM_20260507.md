# TRANSMISSION ARCHIVE — GridLedger IP Ltd
## NBM Development Bank Technical Submission
**7 May 2026 · 18:45 UTC**

---

## SUBMISSION METADATA

| Field | Value |
|---|---|
| **Submission ID** | NBM-GDL-20260507-001 |
| **Recipient** | NBM Development Bank – Risk Desk |
| **Submitter** | GridLedger IP Ltd (Sanjani Mwambaghi, Director) |
| **Timestamp (UTC)** | 2026-05-07T18:45:00Z |
| **Version** | Final (v1.0) |
| **Status** | FROZEN – No revisions without version increment |

---

## TRANSMITTED ARTIFACTS

### 1. Architecture Statement (May 2026)
- **Filename:** `ARCHITECTURE_STATEMENT_MAY_2026.md`
- **SHA256:** `d92fa940ec2af6b83e22266ccc5e6f4316f4d36bc1ffb2b6a95b7ee8f93a7218`
- **Size:** 12,847 bytes
- **Purpose:** Technical foundation defining operational/verification split, Chain of Custody model, Seal Invalidity criteria, integrity guarantees, honest limits, data sovereignty position, failure domain taxonomy

### 2. Integrity Proof (May 2026)
- **Filename:** `INTEGRITY_PROOF_MAY_2026.md`
- **SHA256:** `ca2a783127b56d76b8b54729ef51e6d47d00bb5baca2ed1d0f8d6e182a7e1128`
- **Size:** 9,456 bytes
- **Purpose:** Reproducible demonstration that database mutation does not propagate to externally anchored seal chain; witnessed evidence of Architecture Statement claims

### 3. Auditor's Toolkit (Simulation & Verification Script)
- **Filename:** `integrity_proof_sim.py`
- **SHA256:** `6dacda48e22422cafd1e55c84d03140e62cc55d9235434587566b7e870671760`
- **Language:** Python 3.9+
- **Dependencies:** hashlib (stdlib), json (stdlib), pathlib (stdlib), uuid (stdlib)
- **Purpose:** Open-source verification script that any party can execute independently to validate seal chain integrity; demonstrates independent replayability

### 4. Transmission Cover Letter
- **Filename:** `NBM_TECHNICAL_SUBMISSION_MAY_2026.md`
- **SHA256:** (computed separately)
- **Purpose:** Formal introduction, artifact summary, dependencies/limitations disclosure, file integrity references, invitation to technical review

---

## INSTITUTIONAL DISCIPLINE RECORD

This transmission implements the institutional discipline described in the Architecture Statement itself:

✅ **Version Freezing:** All transmitted files are final (v1.0). Any future revision increments version number and generates new hashes.

✅ **File Integrity Verification:** SHA256 hashes provided enable recipient to confirm files are bit-identical to submitted versions.

✅ **Timestamp Anchoring:** UTC timestamp records exact moment of transmission. No claim to prior dates.

✅ **No Silent Edits:** Commitment that transmitted versions remain unchanged. All modifications tracked via version control.

✅ **Immutable Archive:** This record is the institutional commitment to the transmitted state.

---

## VERIFICATION PROCEDURE (For NBM)

To confirm file integrity:

```bash
# Linux/macOS
sha256sum ARCHITECTURE_STATEMENT_MAY_2026.md
sha256sum INTEGRITY_PROOF_MAY_2026.md
sha256sum integrity_proof_sim.py

# Windows PowerShell
(Get-FileHash "ARCHITECTURE_STATEMENT_MAY_2026.md" -Algorithm SHA256).Hash
(Get-FileHash "INTEGRITY_PROOF_MAY_2026.md" -Algorithm SHA256).Hash
(Get-FileHash "integrity_proof_sim.py" -Algorithm SHA256).Hash
```

Expected hashes:
```
d92fa940ec2af6b83e22266ccc5e6f4316f4d36bc1ffb2b6a95b7ee8f93a7218  ARCHITECTURE_STATEMENT_MAY_2026.md
ca2a783127b56d76b8b54729ef51e6d47d00bb5baca2ed1d0f8d6e182a7e1128  INTEGRITY_PROOF_MAY_2026.md
6dacda48e22422cafd1e55c84d03140e62cc55d9235434587566b7e870671760  integrity_proof_sim.py
```

If hashes match: files are bit-identical to transmitted versions.
If hashes diverge: files have been modified since transmission.

---

## NEXT STEPS (Per GridLedger Protocol)

1. **Transmission Confirmation:** NBM acknowledges receipt of this submission
2. **Technical Review Window:** NBM conducts independent review (no timeline specified)
3. **Technical Engagement (Optional):** If questions arise, GridLedger available for structured technical session
4. **Decision Point:** NBM determines whether architecture meets internal evidentiary standards
5. **Outcome:** Partnership exploratory conversation (if NBM assesses architecture meets standards) or conclusion of review (if not)

No decision timeline is imposed. No urgency is suggested. This is a technical submission, not a pitch.

---

## OPERATIONAL CONTEXT

**Backend System Status:**
- ✅ FastAPI + Uvicorn running on localhost:8000
- ✅ SQLite database initialized with 29 tables (4 GL-1 institutional governance tables)
- ✅ 8 institutional API endpoints operational
- ✅ Test cycle created and sealed (INTEGRITY-TEST-6C73B9F7)
- ✅ Seal verification passed before and after database corruption

**Frontend System Status:**
- ⏳ React + Vite code ready (grid-ledger-insights-main directory)
- ⏳ npm dependencies blocked by network registry access (parallel issue, non-blocking for technical review)
- ⏳ Will complete when npm registry accessible

**Documentation Status:**
- ✅ Architecture Statement (institutional due diligence)
- ✅ Integrity Proof (witnessed demonstration)
- ✅ Auditor's Toolkit (reproducible verification)
- ✅ Engineering decision gates stored in repository memory
- ✅ All Phase 1 deliverables complete

---

## ARCHIVE CUSTODIAN

**GridLedger IP Ltd**  
Lingadzi House, Area 40/31  
Lilongwe, Malawi  
ISIC 7490 – Verification Authority

**Contact:** Sanjani Mwambaghi, Director

---

*Transmission Archive · GridLedger IP Ltd · 7 May 2026 · 18:45 UTC*
*Status: FROZEN · Version: v1.0 · Final*
