/**
 * Quick Backend API Verification Script
 * Run this from terminal to confirm Step 0 endpoints are responding
 * 
 * Prerequisites:
 * - Backend running: python -m uvicorn backend.main:app --reload --workers 1
 * - curl installed
 * 
 * Usage:
 *   node verify_backend_api.js
 */

const API_URL = process.env.API_URL || 'http://localhost:8000';
const API_KEY = process.env.API_KEY || 'letmein123';

const endpoints = [
  {
    name: 'Mandate Submission (POST)',
    method: 'POST',
    path: '/api/institutional/mandate-submission',
    payload: {
      mandate_id: `test_mandate_${Date.now()}`,
      submitted_by: 'NABIWI_01',
      role: 'operator',
      mandate_version_hash: 'sha256_abc123',
      acknowledgment_type: 'full_acceptance',
      session_id: `session_${Date.now()}`
    }
  },
  {
    name: 'Audit Trail (GET)',
    method: 'GET',
    path: '/api/institutional/audit-trail/mill/NABIWI_01'
  },
  {
    name: 'Decision Basis (GET)',
    method: 'GET',
    path: '/api/owner/mill/NABIWI_01/decision'
  }
];

async function testEndpoint(endpoint) {
  console.log(`\n[TEST] ${endpoint.name}`);
  console.log(`  ${endpoint.method} ${endpoint.path}`);

  try {
    const options = {
      method: endpoint.method,
      headers: {
        'X-API-Key': API_KEY,
        'Content-Type': 'application/json'
      }
    };

    if (endpoint.payload) {
      options.body = JSON.stringify(endpoint.payload);
    }

    const response = await fetch(`${API_URL}${endpoint.path}`, options);
    const data = await response.json();

    if (response.ok) {
      console.log(`  [OK] Status: ${response.status}`);
      console.log(`  Data: ${JSON.stringify(data).substring(0, 100)}...`);
      return true;
    } else {
      console.log(`  [FAIL] Status: ${response.status}`);
      console.log(`  Error: ${JSON.stringify(data)}`);
      return false;
    }
  } catch (error) {
    console.log(`  [FAIL] ${error.message}`);
    return false;
  }
}

async function runTests() {
  console.log('========================================');
  console.log('GridLedger Backend API Verification');
  console.log(`Base URL: ${API_URL}`);
  console.log('========================================');

  let passed = 0;
  let failed = 0;

  for (const endpoint of endpoints) {
    const result = await testEndpoint(endpoint);
    if (result) passed++;
    else failed++;
  }

  console.log('\n========================================');
  console.log(`Results: ${passed} PASS, ${failed} FAIL`);
  console.log('========================================');

  process.exit(failed > 0 ? 1 : 0);
}

runTests();
