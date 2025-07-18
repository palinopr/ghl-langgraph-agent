# LangGraph Migration Cutover Plan

## Overview
This document outlines the step-by-step process for migrating from the Node.js implementation to the Python LangGraph implementation.

## Pre-Cutover Checklist

### 1. Testing Verification
- [ ] All unit tests passing
- [ ] Integration tests with GoHighLevel API verified
- [ ] Load testing completed (100+ concurrent messages)
- [ ] Agent routing logic verified
- [ ] Appointment booking flow tested end-to-end

### 2. Environment Setup
- [ ] Production environment variables configured
- [ ] Supabase database migrations applied
- [ ] API keys and tokens verified
- [ ] Webhook URLs updated in GoHighLevel

### 3. Monitoring Setup
- [ ] Logging configured and tested
- [ ] Error tracking (Sentry) configured
- [ ] Performance monitoring ready
- [ ] Alerts configured for failures

## Cutover Steps

### Phase 1: Parallel Running (Day 1-3)
1. **Deploy Python service** alongside existing Node.js service
2. **Configure load balancer** to send 10% traffic to Python service
3. **Monitor both services** for:
   - Response times
   - Error rates
   - Agent accuracy
   - Appointment booking success

### Phase 2: Gradual Migration (Day 4-7)
1. **Increase traffic** to Python service:
   - Day 4: 25%
   - Day 5: 50%
   - Day 6: 75%
   - Day 7: 90%

2. **Monitor key metrics**:
   ```sql
   -- Message processing success rate
   SELECT 
     COUNT(*) FILTER (WHERE status = 'completed') * 100.0 / COUNT(*) as success_rate,
     processed_by_agent,
     DATE(created_at) as date
   FROM message_queue
   WHERE created_at > NOW() - INTERVAL '7 days'
   GROUP BY processed_by_agent, DATE(created_at);

   -- Appointment booking rate
   SELECT 
     COUNT(*) FILTER (WHERE appointment_booked = true) * 100.0 / COUNT(*) as booking_rate,
     DATE(created_at) as date
   FROM message_queue
   WHERE created_at > NOW() - INTERVAL '7 days'
   GROUP BY DATE(created_at);
   ```

### Phase 3: Full Cutover (Day 8)
1. **Redirect all traffic** to Python service
2. **Keep Node.js service running** in standby mode
3. **Monitor closely** for 24 hours
4. **Quick rollback plan**: Update webhook URL in GoHighLevel if issues arise

### Phase 4: Decommission (Day 9-10)
1. **Verify all metrics** are stable
2. **Archive Node.js codebase**
3. **Update documentation**
4. **Remove Node.js deployment**

## Rollback Plan

### Immediate Rollback Triggers
- Error rate > 5%
- Response time > 3 seconds
- Agent routing failures > 10%
- Appointment booking failures

### Rollback Steps
1. **Update GoHighLevel webhook URL** to point back to Node.js service
2. **Verify traffic is flowing** to Node.js service
3. **Investigate Python service issues**
4. **Fix issues and retry migration**

## Success Criteria

### Performance Metrics
- Response time < 2 seconds (p95)
- Error rate < 1%
- Message processing success > 98%
- Agent routing accuracy > 95%

### Business Metrics
- Appointment booking rate maintained or improved
- Lead qualification rate maintained or improved
- Customer satisfaction maintained

## Communication Plan

### Stakeholders
- Development team
- Customer support team
- Sales team
- Management

### Communication Timeline
- **T-7 days**: Initial notification of migration
- **T-1 day**: Final reminder and schedule
- **T+0**: Migration start notification
- **T+8 hours**: Progress update
- **T+24 hours**: Completion notification

## Post-Migration Tasks

1. **Performance Optimization**
   - Analyze LangGraph execution traces
   - Optimize agent prompts
   - Fine-tune routing logic

2. **Documentation Update**
   - Update API documentation
   - Update runbooks
   - Create troubleshooting guide

3. **Training**
   - Train support team on new system
   - Create video walkthrough
   - Update knowledge base

## Emergency Contacts

- **Technical Lead**: [Contact Info]
- **DevOps Lead**: [Contact Info]
- **GoHighLevel Support**: [Contact Info]
- **On-Call Engineer**: [Contact Info]

## Appendix

### Environment Variables Migration
```bash
# Node.js -> Python mapping
OPENAI_API_KEY (same)
SUPABASE_URL (same)
SUPABASE_ANON_KEY (same)
GHL_API_TOKEN (same)
GHL_LOCATION_ID (same)
GHL_CALENDAR_ID (same)
GHL_ASSIGNED_USER_ID (same)
WEBHOOK_SECRET (new - add to GHL)
```

### Database Schema Changes
```sql
-- New columns added for LangGraph tracking
ALTER TABLE message_queue
ADD COLUMN IF NOT EXISTS langgraph_thread_id VARCHAR(255),
ADD COLUMN IF NOT EXISTS langgraph_run_id VARCHAR(255),
ADD COLUMN IF NOT EXISTS workflow_state JSONB;

-- Index for performance
CREATE INDEX IF NOT EXISTS idx_langgraph_thread 
ON message_queue(langgraph_thread_id) 
WHERE langgraph_thread_id IS NOT NULL;
```

### Monitoring Queries
```sql
-- Agent performance comparison
WITH agent_stats AS (
  SELECT 
    processed_by_agent,
    COUNT(*) as total_messages,
    AVG(EXTRACT(EPOCH FROM (updated_at - created_at))) as avg_response_time,
    COUNT(*) FILTER (WHERE status = 'completed') * 100.0 / COUNT(*) as success_rate
  FROM message_queue
  WHERE created_at > NOW() - INTERVAL '24 hours'
  GROUP BY processed_by_agent
)
SELECT * FROM agent_stats ORDER BY total_messages DESC;

-- Conversation flow analysis
SELECT 
  current_agent,
  next_agent,
  COUNT(*) as transition_count
FROM (
  SELECT 
    LAG(processed_by_agent) OVER (PARTITION BY contact_id ORDER BY created_at) as current_agent,
    processed_by_agent as next_agent
  FROM message_queue
  WHERE created_at > NOW() - INTERVAL '24 hours'
) transitions
WHERE current_agent IS NOT NULL
GROUP BY current_agent, next_agent
ORDER BY transition_count DESC;
```

## Sign-off

- [ ] Development Team Lead
- [ ] QA Lead
- [ ] Operations Lead
- [ ] Product Manager
- [ ] CTO/Technical Director