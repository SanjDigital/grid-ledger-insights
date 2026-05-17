/**
 * API Client Configuration
 * 
 * Centralized axios instance for all backend communication.
 * Enforces X-API-Key header; fails if VITE_API_KEY not configured.
 * 
 * Environment variables:
 * - VITE_API_URL: Backend base URL (default: http://localhost:8000)
 * - VITE_API_KEY: API key for institutional endpoints (required)
 */

import axios, { AxiosInstance } from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const API_KEY = import.meta.env.VITE_API_KEY;

if (!API_KEY) {
  console.warn(
    '[GRIDLEDGER] VITE_API_KEY not configured. Backend requests will fail. See .env.example'
  );
}

/**
 * Owner App API Client
 * For allocation decisions, decision feed, capital controls
 */
export const ownerApiClient: AxiosInstance = axios.create({
  baseURL: `${API_URL}/api/owner`,
  headers: {
    'Content-Type': 'application/json',
    ...(API_KEY ? { 'X-API-Key': API_KEY } : {}),
  },
});

/**
 * Institutional API Client
 * For mandate logging, friction analytics, audit trail
 */
export const institutionalApiClient: AxiosInstance = axios.create({
  baseURL: `${API_URL}/api/institutional`,
  headers: {
    'Content-Type': 'application/json',
    ...(API_KEY ? { 'X-API-Key': API_KEY } : {}),
  },
});

/**
 * Generic Reports API Client
 * For mill status, performance, credit metrics
 */
export const reportsApiClient: AxiosInstance = axios.create({
  baseURL: `${API_URL}/api/v1`,
  headers: {
    'Content-Type': 'application/json',
    ...(API_KEY ? { 'X-API-Key': API_KEY } : {}),
  },
});

/**
 * Error handler for API requests
 * Logs errors and provides user-friendly messages
 */
export function handleApiError(error: any, context: string = 'API request'): string {
  if (!API_KEY) {
    return `${context}: API key not configured. See .env.example`;
  }
  
  if (axios.isAxiosError(error)) {
    if (error.response?.status === 401) {
      return `${context}: Authentication failed. Check VITE_API_KEY.`;
    }
    if (error.response?.status === 404) {
      return `${context}: Resource not found.`;
    }
    if (error.response?.status === 500) {
      return `${context}: Backend error. Please try again.`;
    }
    return `${context}: ${error.message}`;
  }
  
  return `${context}: ${error.message || 'Unknown error'}`;
}

export default { ownerApiClient, institutionalApiClient, reportsApiClient };
