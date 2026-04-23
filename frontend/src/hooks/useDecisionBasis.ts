import { useState, useEffect } from "react";

export interface DecisionBasisData {
  mill_id: string;
  trust_integrity_score: number;
  energy_accountability_ratio: number;
  reconciliation_variance_pct: number;
  fraud_risk_level: "LOW" | "MEDIUM" | "HIGH";
  effective_rate_per_kwh?: number;
  verified_throughput_kwh: number;
  risk_classification: string;
  financing_rate_adjustment_bps: number;
}

interface DecisionBasisState {
  data: DecisionBasisData | null;
  loading: boolean;
  error: Error | null;
}

/**
 * Hook to fetch pre-computed decision basis from backend.
 * Eliminates frontend duplication of EAR and Trust Score computation (Gap 6).
 * 
 * Single source of truth: Backend (trust_scorecard.py) computes all values.
 * Frontend consumes and displays only.
 */
export function useDecisionBasis(millId: string): DecisionBasisState {
  const [state, setState] = useState<DecisionBasisState>({
    data: null,
    loading: true,
    error: null,
  });

  useEffect(() => {
    if (!millId) {
      setState({ data: null, loading: false, error: null });
      return;
    }

    const fetchDecisionBasis = async () => {
      try {
        setState((prev) => ({ ...prev, loading: true, error: null }));

        // Backend endpoint returns pre-computed values
        const response = await fetch(`/api/v1/mills/${millId}/scorecard`);
        
        if (!response.ok) {
          throw new Error(`Failed to fetch decision basis: ${response.statusText}`);
        }

        const json = await response.json();

        // Extract relevant fields from the scorecard response
        const data: DecisionBasisData = {
          mill_id: json.metadata?.mill_id || millId,
          trust_integrity_score: json.kpis?.trust_integrity_score || 0,
          energy_accountability_ratio: json.kpis?.energy_accountability_ratio || 1.0,
          reconciliation_variance_pct: json.kpis?.reconciliation_variance_pct || 0,
          fraud_risk_level: json.kpis?.fraud_risk_level || "MEDIUM",
          effective_rate_per_kwh: json.decision_basis?.effective_rate_per_kwh,
          verified_throughput_kwh: json.kpis?.verified_throughput_kwh || 0,
          risk_classification: json.capital_impact?.risk_classification || "UNCLASSIFIED",
          financing_rate_adjustment_bps: json.capital_impact?.financing_rate_adjustment_bps || 0,
        };

        setState({
          data,
          loading: false,
          error: null,
        });
      } catch (err) {
        setState({
          data: null,
          loading: false,
          error: err instanceof Error ? err : new Error(String(err)),
        });
      }
    };

    fetchDecisionBasis();
  }, [millId]);

  return state;
}

/**
 * Fallback mock data for development/testing.
 * Use when backend is unavailable.
 */
export function getMockDecisionBasis(millId: string): DecisionBasisData {
  return {
    mill_id: millId,
    trust_integrity_score: 84,
    energy_accountability_ratio: 0.98,
    reconciliation_variance_pct: 2.1,
    fraud_risk_level: "LOW",
    effective_rate_per_kwh: 1350,
    verified_throughput_kwh: 4104,
    risk_classification: "COMMERCIAL",
    financing_rate_adjustment_bps: -300,
  };
}
