# EA-005 — OUTAGE vs. CYCLE LOG CO-OCCURRENCE (NABIWI NODE)

**Source:** SMS production corpus (3,754 production messages) vs. outage messages
**Method:** Temporal proximity mapping (outage message within ±48 hours of production report)
**Output:** Observational co-occurrence record. No causal attribution.

## Aggregated Co-occurrence by Year
| Year | Outage Messages | Production Reports | Co-occurrence Rate |
|------|-----------------|--------------------|-------------------|
| 2026 | 41 | 324 | ~65% |
| 2025 | 278 | 1,438 | ~70% |
| 2024 | 175 | 1,300 | ~55% |
| 2023 | 41 | 623 | Moderate |

## Observational Patterns
- Outage messages frequently appear within the same 24-hour window as partial production reports (e.g., Open 60 → Close 20).
- Multi-day outage language ("dzulo mpaka pano") correlates with missing or delayed production reports.
- Clean cycles (no proximate outage) show tighter clustering around full expected runs.

## Replayability
All source messages are timestamped and preserved in the SMS corpus. Co-occurrence can be independently verified by reprocessing the raw SMS logs.

*Filed as EA-005. No causal interpretation. Observational record only.*
