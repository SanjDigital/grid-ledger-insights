"""Quick test of PXE engine."""

from backend.policy_execution_engine import (
    PolicyExecutionEngine,
    PXEInput,
    BreachFlags,
    MillState,
    EARTier,
)

pxe = PolicyExecutionEngine()

example_input = PXEInput(
    mill_id="NABIWI_MKWINDA",
    timestamp="2026-03-29T10:00:00Z",
    trust_score=89.0,
    reconciliation_score=88.0,
    consistency_score=100.0,
    governance_score=95.0,
    ear=0.88,
    ear_tier=EARTier.TIER_3,
    dce=1250.0,
    risk_penalty=0.1,
    mill_state=MillState.VERIFIED,
    breach_flags=BreachFlags(),
    event_metadata_hash="0xabc123def456",
    policy_id="STANDARD_COMMERCIAL",
)

print("Executing PXE...")
cao = pxe.execute(example_input)
print(f"Mill: {cao.mill_id}")
print(f"Decision: {cao.credit_decision}")
print(f"Advance Rate: {cao.advance_rate}")
print(f"Capital State: {cao.capital_state}")
print(f"Input Hash: {cao.input_hash}")
print(f"Policy Hash: {cao.policy_hash}")
print("✅ PXE executed successfully")
