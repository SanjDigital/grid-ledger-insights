# TELEMETRY CONSENT GATE PROTOCOL V1.0

**Document ID:** GL-TCG-2026-05-27-V1.0
**Version:** 1.0 · May 2026  
**Authority:** GridLedger IP Ltd — Verification Infrastructure  
**Effective Date:** 27 May 2026  

---

## PURPOSE

The Telemetry Consent Gate is the **mandatory threshold** through which raw ESCOM data (or any third-party energy telemetry) transitions from private operational telemetry to public evidentiary infrastructure.

**Principle:** No raw data is committed to the public repository until explicit, witnessed, documented consent is obtained from the operator and/or account holder.

---

## REGULATORY FOUNDATION

- **Data Protection (Malawi) — Privacy Principles**  
- **GridLedger Certificate of Incorporation** — Verification Authority (ISIC 7490)  
- **Trust Anchor Repository Policy** — Public commitment requires explicit consent  

---

## CONSENT CATEGORIES

### Category 1: Operator/Account Holder Consent (Field-Obtainable)

**Definition:** Verbal consent from the operator or authorized account representative, documented with witness and signature during a site visit.

**Prerequisites:**
- Operator identity independently verified (ID document check)
- Physical site visit completed (Human Audit Checklist V1.0)
- Operator has read the Consent Declaration (verbally presented if literacy concerns exist)

**Execution:**
- Auditor presents the Consent Declaration (see Section F below)
- Operator verbally affirms consent
- Operator signs or applies thumbprint on witness form
- Auditor countersigns and dates
- Audio or video record taken if possible (optional but recommended)

**Boundary:** This consent applies to the **aggregated production data from this node only** for the purposes of impact verification and credit analysis. It does NOT grant consent for:
- Personal financial data disclosure
- Sharing of operator name with third parties without explicit request
- Use of operator identity in marketing or case studies without separate written agreement

**Retention:** Consent form archived to Trust Anchor; linked to operator record; retained indefinitely.

---

### Category 2: Sovereign/Third-Party Corroboration (For External Data Integration)

**Definition:** Consent obtained directly from a third-party data controller (ESCOM, Airtel Money, grid operator, etc.) to integrate their telemetry with GridLedger analysis.

**Prerequisites:**
- Formal data-sharing agreement in place
- Third-party confirmation that operator has authorized data sharing
- Data classification reviewed (confidential → institutional → public)

**Execution:**
- Legal/institutional data-sharing agreement signed
- Data controller explicitly consents to GridLedger's analytical use
- Data controller confirms no additional operator consent is required (or provides it directly)
- Data integration executed only after consent is formally logged

**Boundary:** Third-party consent does NOT override operator consent. If the operator revokes consent, the operator's SMS data is withdrawn; third-party corroboration (ESCOM, Airtel) remains as independent evidence.

**Retention:** Data-sharing agreement filed in legal register; consent log maintained.

---

### Category 3: Revocation Gate (Ongoing Boundary)

**Definition:** The operator may revoke consent to participation in GridLedger verification at any time.

**Procedure:**
1. Operator submits written notice to GridLedger (email, SMS, or registered letter)
2. GridLedger acknowledges receipt within 2 business days
3. **Effective Date of Revocation:** 30 days from receipt of notice (grace period for in-flight verification cycles)
4. After effective date:
   - New SMS data from this node is not ingested
   - Existing public archive entries are **flagged as revoked** but not deleted
   - Node is marked as INACTIVE in verification index
   - Financial partners are notified if node participates in active facility covenants

**Retention:** Revocation notice retained indefinitely; linked to operator record.

---

## SECTION A: FIELD CONSENT EXECUTION (Salima Node — 27 May 2026)

### A.1 — Pre-Visit Preparation

**Auditor Checklist:**
- [ ] Operator contact details confirmed: **Phone:** __________ **Preferred Language:** __________
- [ ] Consent Declaration printed (or prepared on tablet for digital signature)
- [ ] Witness form printed (or digital form with timestamp capability)
- [ ] Audio recording device tested and ready (if using)
- [ ] Identification materials ready for operator verification

### A.2 — On-Site Consent Procedure

**Step 1: Identity Verification (5 minutes)**
- Request operator's national ID or passport
- Verify name matches SMS registry
- Record ID number (do NOT photograph ID)
- Confirm: "Are you authorized to make decisions about this mill's participation in GridLedger?"

**Step 2: Consent Declaration Presentation (10 minutes)**
- Read or present the Consent Declaration (see Section B below)
- Use operator's preferred language (translation if needed)
- Allow operator to ask clarifying questions
- Auditor explains: "This agreement allows your production data to be used by financial partners, but it does NOT publish your personal information without your permission."

**Step 3: Consent Affirmation (2 minutes)**
- Auditor asks: "Do you authorize GridLedger to use your production data as described?"
- Operator verbally confirms: "Yes, I consent" or equivalent
- Auditor records: **Time of Consent:** __________ **Operator Response:** __________

**Step 4: Documentation (5 minutes)**
- Operator signs or applies thumbprint on Witness Form
- Auditor signs and dates immediately below
- Witness name: Auditor name and organization
- Consent form photograph or scan taken for archive

**Step 5: Confirmation Statement (2 minutes)**
- Auditor confirms back to operator: "Your data will be stored securely and used for credit verification. You can withdraw this consent at any time by sending written notice. Do you understand?"
- Operator affirms: "Yes"

**Total Time Required:** ~25 minutes

---

## SECTION B: CONSENT DECLARATION (Field Version)

---

**GRIDLEDGER TELEMETRY PARTICIPATION AGREEMENT**

**Node:** Salima Road Maize Mill (Lilongwe, M1 Corridor)  
**Operator Name:** __________________ **Date:** __________

### Your Participation

Your mill sends production reports to GridLedger via SMS. These reports include:
- Date of production
- Quantity milled (kg or bags)
- Cash remitted
- Production duration

### What We Do

GridLedger analyzes these reports to verify that:
- Your production is real and recorded accurately
- The timing and amounts are consistent with your operational capability
- Any changes in production are explained by operational conditions (grid failures, maintenance, etc.)

### Who Uses This Data

Your data will be shared with:
- **Financial Partners** — banks and investors who provide funding for mills like yours
- **Research Partners** — universities and impact organizations studying energy access

### What They See

Financial partners see your **production data only** — not your name, personal information, or bank account details. They see:
- Your mill's ID (e.g., NABIWI)
- Your 30-day production totals
- Whether your production is consistent or variable

### What They Do NOT See

- Your personal name
- Your phone number
- Your SMS content beyond the production figures
- Your family's income or financial status
- Any personal banking or transfer information

### Your Rights

1. **You can say No.** This is voluntary. If you do not consent, your data will not be used.

2. **You can withdraw consent.** If you change your mind later, you can stop participating by sending written notice to GridLedger. Your old data remains available to financial partners, but no new data will be used.

3. **You can request proof.** You can ask GridLedger to show you how your data was used or calculated.

4. **You are protected.** GridLedger is a licensed verification authority. Your data is held securely and shared only under strict confidentiality agreements.

### This is NOT

- A credit application
- A financial review of your personal accounts
- A judgment of your personal honesty or trustworthiness
- An obligation to repay any debt

It is only a record of your mill's production performance, used to help financial partners understand your operational capability.

### Your Decision

**Do you authorize GridLedger to use your production data as described above?**

- [ ] **YES, I consent.** I authorize GridLedger to collect, analyze, and share my production data with financial partners and research organizations under the terms above.

- [ ] **NO, I do not consent.** I do not authorize use of my data beyond GridLedger's internal records.

**Operator Signature or Thumbprint:** __________________ **Date:** __________ **Time:** __________

**Auditor (Witness) Name:** __________________ **Signature:** __________________ **Date:** __________

**Organization:** GridLedger IP Ltd  
**Auditor Credentials:** [Title/Certification]

---

## SECTION C: REVOCATION PROCEDURE

### C.1 — Revocation Request Form

**To:** GridLedger IP Ltd, Verification Authority  
**From:** [Operator Name]  
**Date:** __________

I hereby revoke my consent for GridLedger to use production data from the following node:

**Node ID:** __________________ **Node Name:** __________________ **Phone/Contact:** __________

**Reason (optional):** ___________________________________________________________________

**Effective Date Requested:** [30 days from receipt recommended]

**Operator Signature:** __________________ **Date:** __________

---

### C.2 — Post-Revocation Actions

**GridLedger Response (within 5 business days):**

1. Acknowledge receipt of revocation notice
2. Confirm effective date (30-day grace period applies)
3. Provide confirmation number and archive reference
4. Explain impact on any active financial agreements

**Data Handling Post-Revocation:**

| Data Category | Action |
|---------------|--------|
| Historical data (before revocation date) | Retained but flagged REVOKED in index |
| New incoming data (after revocation date) | Not ingested; discarded immediately |
| Active facility covenants | Node marked INACTIVE; lender notified if material |
| Public reporting | Node removed from aggregated indices |

---

## SECTION D: COMPLIANCE LOG & AUDIT TRAIL

### D.1 — Consent Registry (Salima Node — 27 May 2026)

| Field | Status | Value |
|-------|--------|-------|
| **Operator Name** | DOCUMENTED | Thokozani Doreen Nambindo / Tuiweni Nambindo |
| **Site Visit Date** | SCHEDULED | [Field Execution Date] |
| **Auditor** | ASSIGNED | [Auditor Name] |
| **Consent Form Signed** | PENDING | Awaiting field execution |
| **Consent Effective Date** | PENDING | [Post-signature date] |
| **Consent Archive ID** | PENDING | [Generated post-execution] |
| **Data Ingestion Authorized** | FALSE | Awaiting consent completion |

### D.2 — Data Ingestion Gate

**Before consenting:**
- [ ] Raw SMS data held in quarantine (not ingested to public repo)
- [ ] Node marked as PENDING_CONSENT in system

**After consenting:**
- [ ] Consent logged to audit trail
- [ ] Node marked as ACTIVE in system
- [ ] Raw SMS data ingested to Trust Anchor (with consent reference)
- [ ] Verification cycles proceed as normal

**After revoking:**
- [ ] Revocation logged to audit trail
- [ ] Node marked as REVOKED in system
- [ ] New data held in quarantine
- [ ] Historical data flagged but retained

---

## APPENDIX: TRANSLATIONS & ADAPTATIONS

### Swahili Translation (for use in Tanzania, Kenya):

**HIFADHI YA DATA YA UZALISHAJI**

[If needed, provide Swahili consent form variant]

### Chichewa Translation (for Malawi):

**CHILOLEZO CHA KUGWIRITSA NTCHITO KWA DETA YA UZALISHAJI**

[If needed, provide Chichewa consent form variant]

---

**Status:** ACTIVE · Ready for field deployment  
**Effective Date:** 27 May 2026  
**Next Review Date:** 31 December 2026

*GridLedger IP Ltd — Verification Authority · ISIC 7490 · May 2026*
