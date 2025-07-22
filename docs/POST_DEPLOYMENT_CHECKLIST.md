# POST_DEPLOYMENT_CHECKLIST.md

## 🚀 Post-Deployment Verification Checklist

### Deployment Information
- **Commit Hash**: `4a961a6799a175f6be27f224779dc9ea7bebb8e2`
- **Branch**: `main`
- **Deployment Method**: Git push to main (auto-deploy)
- **Expected Deployment Time**: 5-10 minutes
- **Deployment Tracking**: Check LangSmith dashboard

### 🔍 First 5 Things to Check Post-Deployment

1. **LangSmith Dashboard**
   - Navigate to: https://smith.langchain.com
   - Check "Last Updated" timestamp
   - Verify deployment status shows "Success"
   - Confirm version matches commit hash

2. **Health Endpoints**
   ```bash
   # Check basic health
   curl https://YOUR-DEPLOYMENT-URL/health
   # Expected: {"status": "healthy"}
   
   # Check metrics
   curl https://YOUR-DEPLOYMENT-URL/metrics
   # Expected: Performance metrics
   
   # Check simple alive
   curl https://YOUR-DEPLOYMENT-URL/ok
   # Expected: "ok"
   ```

3. **Webhook Test**
   ```bash
   # Test with simple message
   curl -X POST https://YOUR-DEPLOYMENT-URL/webhook/message \
     -H "Content-Type: application/json" \
     -d '{
       "contactId": "test-deploy-001",
       "body": "Hola, tengo un restaurante",
       "type": "SMS",
       "locationId": "sHFG9Rw6BdGh6d6bfMqG"
     }'
   ```

4. **LangSmith Traces**
   - Check for new traces post-deployment
   - Verify no errors in initial traces
   - Confirm agents are routing correctly
   - Check lead scoring is working

5. **Memory Usage**
   - Monitor initial memory consumption
   - Should be around 44MB based on tests
   - Check for any memory leaks in first hour

### 🧪 Quick Smoke Tests

1. **Test Lead Scoring**
   ```bash
   # Low score test (should go to Maria)
   curl -X POST https://YOUR-DEPLOYMENT-URL/webhook/message \
     -H "Content-Type: application/json" \
     -d '{"contactId": "smoke-test-1", "body": "Hola"}'
   ```

2. **Test Business Extraction**
   ```bash
   # Should extract "restaurante" and score 3-4
   curl -X POST https://YOUR-DEPLOYMENT-URL/webhook/message \
     -H "Content-Type: application/json" \
     -d '{"contactId": "smoke-test-2", "body": "Tengo un restaurante"}'
   ```

3. **Test Agent Routing**
   ```bash
   # High score test (should go to Sofia)
   curl -X POST https://YOUR-DEPLOYMENT-URL/webhook/message \
     -H "Content-Type: application/json" \
     -d '{
       "contactId": "smoke-test-3",
       "body": "Mi nombre es Juan, tengo un restaurante y mi presupuesto es $500 al mes"
     }'
   ```

### 🔄 Rollback Procedure

If critical issues are detected:

1. **Immediate Rollback**
   ```bash
   # Revert to previous commit
   git revert HEAD
   git push origin main
   ```

2. **Alternative: Deploy Previous Version**
   - Update `langgraph.json` version to previous
   - Push to trigger redeployment

3. **Emergency Contacts**
   - Check LangSmith support if deployment platform issues
   - Monitor error logs in LangSmith traces

### ⏱️ Monitoring Timeline

- **0-5 minutes**: Deployment in progress
- **5-10 minutes**: Initial smoke tests
- **10-30 minutes**: Monitor for errors
- **30-60 minutes**: Check performance metrics
- **1-2 hours**: Verify stable operation

### 📊 Success Criteria

- [ ] All health endpoints return 200 OK
- [ ] Webhook processes test messages
- [ ] Correct agent routing based on scores
- [ ] No errors in LangSmith traces
- [ ] Memory usage stable (~44MB)
- [ ] Response times < 3 seconds

### 🚨 Red Flags

Watch for these warning signs:
- Memory usage > 100MB
- Response times > 5 seconds
- Errors in traces mentioning:
  - "Unknown node"
  - "State validation failed"
  - "Import error"
  - "Circular reference"

### 📝 Post-Deployment Notes

Document any observations here:
- Actual deployment time: ___________
- First successful trace ID: ___________
- Any warnings noticed: ___________
- Performance observations: ___________