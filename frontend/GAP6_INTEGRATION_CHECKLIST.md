# Gap 6 Refactor - Integration Checklist

## Deploy Instructions

### Step 1: Backup Current Files
```bash
cd frontend
cp src/lib/forensic-engine.ts src/lib/forensic-engine.ts.backup
cp src/pages/Index.tsx src/pages/Index.tsx.backup
```

### Step 2: Install Refactored Code
```bash
# Copy new files into place
cp src/lib/forensic-engine-refactored.ts src/lib/forensic-engine.ts
cp src/pages/Index-refactored.tsx src/pages/Index.tsx
```

### Step 3: Verify API Configuration
Ensure backend API is available at:
```
GET /api/v1/mills/{mill_id}/scorecard
```

Update `.env` if needed:
```
VITE_API_BASE_URL=http://localhost:8000
```

### Step 4: Test Hook Integration
```bash
# Test development server
npm run dev

# Verify in browser console:
# 1. Open Index page
# 2. Check Network tab for GET /api/v1/mills/.../scorecard calls
# 3. Verify AuditPanel displays trust_score and ear values
```

### Step 5: Validate Values Match
**Test Case: Compare API vs Frontend Display**

1. Call backend directly:
```bash
curl http://localhost:8000/api/v1/mills/mill-1/scorecard
```

2. Note `kpis.trust_integrity_score` and `kpis.energy_accountability_ratio`

3. Open frontend at same mill → verify AuditPanel displays matching values

4. ✅ If values match → Gap 6 fixed!

### Step 6: Run Tests
```bash
npm test

# Critical tests:
- useDecisionBasis hook returns correct data
- computeForensics with API data produces deterministic results
- AuditPanel displays API values (not computed locally)
```

### Step 7: Rollback (if needed)
```bash
# Revert to backup
cp src/lib/forensic-engine.ts.backup src/lib/forensic-engine.ts
cp src/pages/Index.tsx.backup src/pages/Index.tsx
```

---

## Success Criteria

✅ **All must pass**:

- [ ] API endpoint `/api/v1/mills/{mill_id}/scorecard` is accessible
- [ ] `useDecisionBasis` hook fetches data without errors
- [ ] AuditPanel displays EAR and Trust Score from API (not computed)
- [ ] Per-event forensics (SEC, breaches) still computed correctly
- [ ] Authority alignment stack renders correctly
- [ ] No console errors or warnings
- [ ] Frontend/backend values match for same mill
- [ ] Variance override demo still works

---

## Troubleshooting

### Issue: API returns 404
**Solution**: Verify backend is running and mill_id is valid
```bash
curl http://localhost:8000/api/v1/mills/mill-1/scorecard
```

### Issue: Hook shows "loading" forever
**Solution**: Check browser Network tab for failed requests
- CORS issues? Enable CORS on backend
- API down? Start backend: `python main.py`

### Issue: Values don't match between API and frontend
**Solution**: Clear browser cache and verify mock data fallback isn't being used
```javascript
// In browser console:
localStorage.clear();
location.reload();
```

### Issue: TypeScript errors
**Solution**: Verify `DecisionBasisData` interface matches backend response
```bash
npm run type-check
```

---

## Performance Notes

- Hook caches decision basis per mill_id
- API calls triggered only on mill change
- Fallback to mock data if API unavailable (graceful degradation)
- Per-event forensics remain locally computed (O(n) where n = event count)

---

## Monitoring

After deployment, monitor:

1. **API Response Time**: `GET /api/v1/mills/{mill_id}/scorecard` should be < 100ms
2. **Error Rate**: Track hook failures in error logging
3. **Data Divergence**: Alert if frontend value ≠ API value
4. **User Reports**: Any display discrepancies?

---

## Rollback Plan

If critical issues found:

1. **Immediate**: Revert files from backup
2. **Root Cause**: Identify mismatch (API vs frontend)
3. **Patch**: Fix in backend or frontend as appropriate
4. **Redeploy**: After verification

---

## Questions?

See full documentation: `FORENSIC_ENGINE_REFACTOR_GAP6.md`

