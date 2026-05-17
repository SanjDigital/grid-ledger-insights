/**
 * useVerifiedEvents Hook
 * 
 * Currently returns mock verified events for dashboard panels.
 * 
 * TODO: Integrate with backend endpoint (to be created):
 * GET /api/owner/mills/{mill_id}/events?limit=N&offset=O
 * 
 * Event types: CYCLE_SEALED, CYCLE_DISPUTED, RECEIPT_RECORDED, VARIANCE_BREACH,
 *              GOVERNANCE_RECORD, ENFORCEMENT_ACTION, etc.
 */

import { useState, useEffect } from 'react';

export interface VerifiedEvent {
  event_id: string;
  event_type: string;
  timestamp: string; // ISO format
  mill_id: string;
  severity: 'INFO' | 'WARNING' | 'CRITICAL';
  description: string;
  kwh?: number;
  meteredKwh?: number;
  gridOutage?: boolean;
  cycleId?: number;
  variance?: number;
}

export interface UseVerifiedEventsReturn {
  events: VerifiedEvent[];
  loading: boolean;
  error: string | null;
}

/**
 * Mock events for development
 * TODO: Replace with backend fetch when endpoint is ready
 */
function getMockVerifiedEvents(millId: string): VerifiedEvent[] {
  const now = new Date();
  
  return [
    {
      event_id: `evt_${Date.now()}_1`,
      event_type: 'CYCLE_SEALED',
      timestamp: new Date(now.getTime() - 2 * 3600000).toISOString(),
      mill_id: millId,
      severity: 'INFO',
      description: 'Cycle #127 sealed: 59.9 kWh allocated',
      kwh: 59.9,
      cycleId: 127,
    },
    {
      event_id: `evt_${Date.now()}_2`,
      event_type: 'RECEIPT_RECORDED',
      timestamp: new Date(now.getTime() - 1.5 * 3600000).toISOString(),
      mill_id: millId,
      severity: 'INFO',
      description: 'Cash receipt recorded: 80,865 MWK (99.8% of expected)',
      variance: -0.2,
      cycleId: 127,
    },
    {
      event_id: `evt_${Date.now()}_3`,
      event_type: 'GOVERNANCE_RECORD',
      timestamp: new Date(now.getTime() - 1 * 3600000).toISOString(),
      mill_id: millId,
      severity: 'INFO',
      description: 'Mandate acknowledgment logged by operator',
    },
    {
      event_id: `evt_${Date.now()}_4`,
      event_type: 'CYCLE_SEALED',
      timestamp: new Date(now.getTime() - 0.5 * 3600000).toISOString(),
      mill_id: millId,
      severity: 'INFO',
      description: 'Cycle #128 sealed: 59.9 kWh allocated',
      kwh: 59.9,
      cycleId: 128,
    },
  ];
}

export function useVerifiedEvents(millId: string | null): UseVerifiedEventsReturn {
  const [events, setEvents] = useState<VerifiedEvent[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!millId) {
      setEvents([]);
      setError(null);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      // TODO: Replace with actual backend fetch when ready:
      // const response = await ownerApiClient.get<VerifiedEvent[]>(`/mills/${millId}/events?limit=50`);
      // setEvents(response.data);

      // For now, use mock data
      const mockEvents = getMockVerifiedEvents(millId);
      setEvents(mockEvents);
    } catch (err) {
      setError('Failed to fetch verified events');
      setEvents([]);
    } finally {
      setLoading(false);
    }
  }, [millId]);

  return { events, loading, error };
}

export default useVerifiedEvents;
