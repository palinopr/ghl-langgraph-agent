# Workflow Tracing & Visualization Plan

## Goal
Create our own tracing system to understand workflow behavior BEFORE implementing changes, making it easier to debug and plan improvements.

## The Plan: 3 Components

### 1. **Workflow Simulator** 🧪
Test how the workflow will behave with different inputs WITHOUT hitting real APIs

```python
# Example usage:
simulator = WorkflowSimulator()
result = simulator.simulate(
    message="Quiero agendar una cita",
    current_score=0,
    business_type="restaurant"
)
# Shows: receptionist → intelligence (score:8) → supervisor → sofia → responder
```

### 2. **Visual Flow Tracer** 📊
Generate visual diagrams showing the path through your workflow

```python
# Creates an HTML file with interactive flow diagram
tracer = VisualTracer()
tracer.trace_conversation([
    "Hola",
    "Mi nombre es Juan",
    "Tengo un restaurante", 
    "Necesito automatización"
])
# Output: workflow_trace.html with visual flow
```

### 3. **Conversation Replayer** 🔄
Replay real conversations to see what happened step-by-step

```python
# Load a real conversation and replay it
replayer = ConversationReplayer()
replayer.load_from_ghl(contact_id="z49hFQn0DxOX5sInJg60")
replayer.replay_with_traces()
# Shows each step, decision, and state change
```

## Implementation Plan

### Phase 1: Workflow Simulator (2 hours)
**Purpose**: Test changes without deploying

**Features**:
- Mock GHL responses
- Simulate scoring logic
- Show routing decisions
- Predict agent responses
- No API calls needed

**Files to create**:
- `app/debug/workflow_simulator.py`
- `app/debug/mock_data.py`
- `test_simulator.py`

### Phase 2: Visual Flow Tracer (3 hours)
**Purpose**: See the flow visually

**Features**:
- Generate Mermaid diagrams
- Show decision points
- Highlight current step
- Export as HTML/PNG
- Interactive navigation

**Files to create**:
- `app/debug/visual_tracer.py`
- `app/debug/flow_renderer.py`
- `templates/trace_viewer.html`

### Phase 3: Conversation Replayer (2 hours)
**Purpose**: Debug real conversations

**Features**:
- Load from GHL
- Step through each node
- Show state at each step
- Identify where issues occurred
- Export trace for sharing

**Files to create**:
- `app/debug/conversation_replayer.py`
- `app/debug/state_inspector.py`
- `replay_conversation.py`

## Benefits

### Before Implementation
1. **Test Ideas**: "What if we change the scoring threshold?"
2. **Predict Impact**: "How will this affect routing?"
3. **Catch Issues**: "This would create a loop!"

### During Development
1. **Verify Logic**: "Is the score calculation correct?"
2. **Test Edge Cases**: "What if budget is mentioned twice?"
3. **Compare Versions**: "Old vs new behavior"

### After Deployment
1. **Debug Issues**: "Why did it route to Carlos?"
2. **Analyze Patterns**: "Sofia handles 60% of conversations"
3. **Optimize Flow**: "Remove this redundant step"

## Example Outputs

### 1. Simulator Output
```
=== WORKFLOW SIMULATION ===
Input: "Hola, necesito ayuda con WhatsApp para mi restaurante"

STEP 1: Receptionist
- Loaded contact info ✓
- Loaded 10 previous messages ✓
- Loaded custom fields ✓

STEP 2: Intelligence Analysis
- Extracted: business_type = "restaurante"
- Extracted: intent = "ayuda con WhatsApp"
- Previous score: 3
- New score: 5 (+2 for clear intent)

STEP 3: Supervisor
- Score: 5 → Route to Carlos
- Context: "Customer needs WhatsApp help for restaurant"

STEP 4: Carlos Response
- "¡Hola! Me alegra que estés interesado en automatizar 
   WhatsApp para tu restaurante. ¿Cuántos clientes manejas?"

STEP 5: Responder
- Delay: 2.3s (human-like timing)
- Message sent ✓
```

### 2. Visual Trace (Mermaid)
```mermaid
graph TD
    A[Webhook: "Hola"] --> B[Receptionist]
    B --> C[Intelligence: Score 2]
    C --> D[Supervisor]
    D --> E[Maria: Low Score]
    E --> F[Responder]
    
    style C fill:#f9f,stroke:#333,stroke-width:2px
    style E fill:#bbf,stroke:#333,stroke-width:2px
```

### 3. Replay Analysis
```
CONVERSATION REPLAY: Contact z49hFQn0DxOX5sInJg60
Date: 2024-01-15 14:30:00

[14:30:01] Customer: "Necesito agendar"
[14:30:02] >> Receptionist loads data (487ms)
[14:30:03] >> Intelligence: score 8 (high intent)
[14:30:03] >> Supervisor routes to Sofia
[14:30:05] >> Sofia offers appointments
[14:30:07] >> Responder sends (2.1s delay)
[14:30:07] Sofia: "¡Perfecto! Tengo estos horarios..."

[14:31:15] Customer: "El martes a las 2"
[14:31:16] >> Receptionist (312ms)
[14:31:17] >> Intelligence: maintains score 8
[14:31:17] >> Supervisor: continue with Sofia
[14:31:19] >> Sofia books appointment ✓
[14:31:21] >> GHL API: appointment created
[14:31:23] >> Responder sends confirmation
```

## Quick Start Commands

```bash
# 1. Test a message flow
python simulate_workflow.py "Hola, necesito automatización"

# 2. Visualize a conversation
python visualize_flow.py --contact-id z49hFQn0DxOX5sInJg60

# 3. Debug a specific issue
python replay_conversation.py --contact-id z49hFQn0DxOX5sInJg60 --step-by-step

# 4. Compare before/after a change
python compare_workflows.py --before v1 --after v2 --message "Tengo un restaurante"
```

## Why This Helps

1. **No More Guessing**: See exactly what will happen
2. **Faster Development**: Test without deploying
3. **Better Debugging**: Replay real issues
4. **Clear Communication**: Show stakeholders the flow
5. **Confidence**: Know your changes work before pushing

## Next Steps

1. Choose which component to build first
2. I'll implement it with full code
3. You can test workflows before making changes
4. Debug production issues easily
5. Share traces with team/support

Which component would be most helpful to start with?
- **Simulator**: Test changes safely
- **Visual Tracer**: See the flow
- **Replayer**: Debug real conversations