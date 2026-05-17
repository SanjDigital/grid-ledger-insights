/**
 * Institutional Services – GL-1 Mandate Logging & Audit Trail
 * 
 * Frontend API client for:
 * - Mandate submission & acknowledgment
 * - Friction analytics recording
 * - Discrepancy report submission
 * - Enforcement action logging
 * - Audit trail retrieval
 * 
 * All endpoints require X-API-Key header (set in apiClient.ts)
 */

import { institutionalApiClient } from './apiClient';
import { v4 as uuidv4 } from 'uuid';

// ============================================================================
// Session & Mandate ID Generators (for audit trail)
// ============================================================================

export function generateSessionId(): string {
  return `session_${uuidv4()}`;
}

export function generateMandateId(): string {
  return `mandate_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}

// ============================================================================
// Mandate Submission
// ============================================================================

export interface MandateSubmissionPayload {
  mandate_id: string;
  submitted_by: string;
  role: string;
  mandate_version_hash: string;
  acknowledgment_type: string;
  session_id: string;
  // GL-1 INSTITUTIONAL ACCOUNTABILITY FIELDS
  institution_name: string;
  authorisation_level: string;
  capital_range: string;
  mode_viewed: string;
}

export async function submitMandate(payload: MandateSubmissionPayload) {
  const response = await institutionalApiClient.post('/mandate-submission', payload);
  return response.data;
}

// ============================================================================
// Friction Analytics
// ============================================================================

export interface FrictionAnalyticsPayload {
  session_id: string;
  mandate_id: string;
  scroll_depth_pct: number;
  time_on_statement_ms: number;
  interaction_count: number;
  bypass_attempted?: boolean;
}

export async function recordFrictionAnalytics(payload: FrictionAnalyticsPayload) {
  const response = await institutionalApiClient.post('/friction-analytics', payload);
  return response.data;
}

// ============================================================================
// Discrepancy Reports
// ============================================================================

export interface DiscrepancyReportPayload {
  event_id: string;
  mill_id: string;
  reported_by: string;
  reason: string;
  details?: string;
}

export async function submitDiscrepancyReport(payload: DiscrepancyReportPayload) {
  const response = await institutionalApiClient.post('/discrepancy-reports', payload);
  return response.data;
}

export async function getDiscrepancyReports(
  millId?: string,
  status?: string,
  limit = 50,
  offset = 0
) {
  const params = new URLSearchParams();
  if (millId) params.append('mill_id', millId);
  if (status) params.append('status', status);
  params.append('limit', limit.toString());
  params.append('offset', offset.toString());

  const response = await institutionalApiClient.get(`/discrepancy-reports?${params}`);
  return response.data;
}

// ============================================================================
// Enforcement Actions
// ============================================================================

export interface EnforcementActionPayload {
  mill_id: string;
  cycle_id?: number;
  action_type: string;
  initiated_by: string;
  reason: string;
}

export async function recordEnforcementAction(payload: EnforcementActionPayload) {
  const response = await institutionalApiClient.post('/enforcement-actions', payload);
  return response.data;
}

export async function getEnforcementActions(
  millId?: string,
  actionType?: string,
  limit = 50,
  offset = 0
) {
  const params = new URLSearchParams();
  if (millId) params.append('mill_id', millId);
  if (actionType) params.append('action_type', actionType);
  params.append('limit', limit.toString());
  params.append('offset', offset.toString());

  const response = await institutionalApiClient.get(`/enforcement-actions?${params}`);
  return response.data;
}

// ============================================================================
// Audit Trail
// ============================================================================

export async function getFullAuditTrail(limit = 50, offset = 0) {
  const params = new URLSearchParams();
  params.append('limit', limit.toString());
  params.append('offset', offset.toString());

  const response = await institutionalApiClient.get(`/audit-trail?${params}`);
  return response.data;
}

export async function getAuditTrailForMill(millId: string, limit = 50, offset = 0) {
  const params = new URLSearchParams();
  params.append('mill_id', millId);
  params.append('limit', limit.toString());
  params.append('offset', offset.toString());

  const response = await institutionalApiClient.get(`/audit-trail?${params}`);
  return response.data;
}

export default {
  generateSessionId,
  generateMandateId,
  submitMandate,
  recordFrictionAnalytics,
  submitDiscrepancyReport,
  getDiscrepancyReports,
  recordEnforcementAction,
  getEnforcementActions,
  getFullAuditTrail,
  getAuditTrailForMill,
};
