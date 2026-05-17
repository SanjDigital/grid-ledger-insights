/**
 * useDecisionBasis Hook
 * 
 * Fetches allocation decision basis from /api/owner/mill/{mill_id}/decision
 * Provides:
 * - One-shot fetch on mount (no polling)
 * - Manual refresh with audit timestamp
 * - Error handling with graceful fallback
 * 
 * Returns DecisionBasis + metadata for institutional audit trail
 */

import { useState, useEffect, useCallback } from 'react';
import { ownerApiClient, handleApiError } from '@/services/apiClient';

export interface DecisionBasis {
  cycle_state: string;
  cycle_elapsed_hours: number | null;
  trust_score: number;
  last_cycle_adherence: number;
  last_cycle_lag_hours: number;
  next_advance_rate: number;
  capital_at_risk: string; // Decimal as string
  time_weighted_risk: string; // Decimal as string
  time_to_missing_hours: number | null;
  time_to_lock_hours: number | null;
  simulated_allocation_kwh: string;
  simulated_expected_revenue: string;
  exposure_used: string;
  exposure_limit: string;
  effective_rate_per_kwh: string | null;
}

export interface UseDecisionBasisReturn {
  data: DecisionBasis | null;
  loading: boolean;
  error: string | null;
  lastRefreshAt: string | null; // ISO timestamp for audit trail
  refresh: () => Promise<void>;
}

export function useDecisionBasis(millId: string): UseDecisionBasisReturn {
  const [data, setData] = useState<DecisionBasis | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastRefreshAt, setLastRefreshAt] = useState<string | null>(null);

  const fetchDecision = useCallback(async () => {
    if (!millId) {
      setData(null);
      setError(null);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await ownerApiClient.get<DecisionBasis>(
        `/mill/${millId}/decision`
      );
      setData(response.data);
      setLastRefreshAt(new Date().toISOString());
    } catch (err) {
      const errorMsg = handleApiError(err, `Failed to fetch decision for ${millId}`);
      setError(errorMsg);
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [millId]);

  // Fetch on mount + when millId changes
  useEffect(() => {
    fetchDecision();
  }, [millId, fetchDecision]);

  const refresh = useCallback(async () => {
    await fetchDecision();
  }, [fetchDecision]);

  return {
    data,
    loading,
    error,
    lastRefreshAt,
    refresh,
  };
}
