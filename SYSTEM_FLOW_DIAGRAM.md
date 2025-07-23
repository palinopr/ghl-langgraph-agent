# LangGraph GHL Agent System Flow

## Complete System Architecture

```mermaid
graph TB
    %% Entry Point
    Webhook[Webhook Data] --> ThreadMapper[Thread ID Mapper]
    
    %% Thread Mapper
    ThreadMapper --> |Maps thread_id| Receptionist[Receptionist]
    
    %% Receptionist
    Receptionist --> |Loads GHL History| SmartRouter[Smart Router]
    
    %% Smart Router Decision
    SmartRouter --> |Score 0-4| Maria[Maria Agent]
    SmartRouter --> |Score 5-7| Carlos[Carlos Agent]
    SmartRouter --> |Score 8-10| Sofia[Sofia Agent]
    SmartRouter --> |Direct Response| Responder[Responder]
    
    %% Agent Escalations
    Maria --> |needs_escalation| SmartRouter
    Carlos --> |needs_escalation| SmartRouter
    Sofia --> |needs_escalation| SmartRouter
    
    %% All Agents to Responder
    Maria --> Responder
    Carlos --> Responder
    Sofia --> Responder
    
    %% Responder to End
    Responder --> |Sends Message| End[End]
    
    %% Styling
    classDef entry fill:#e1f5fe,stroke:#01579b,stroke-width:3px
    classDef router fill:#fff3e0,stroke:#e65100,stroke-width:3px
    classDef agent fill:#f3e5f5,stroke:#4a148c,stroke-width:3px
    classDef output fill:#e8f5e9,stroke:#1b5e20,stroke-width:3px
    
    class Webhook,ThreadMapper entry
    class SmartRouter router
    class Maria,Carlos,Sofia agent
    class Responder,End output
```

## Agent Details and Tools

```mermaid
graph LR
    %% Maria - Initial Contact Agent
    subgraph Maria [Maria - Initial Contact]
        M1[Score: 0-4]
        M2[Goal: Collect Info]
        M3[Language: Spanish]
        
        subgraph MariaTools [Maria's Tools]
            MT1[get_contact_details_with_task]
            MT2[escalate_to_router]
            MT3[update_contact_with_context]
            MT4[save_important_context]
            MT5[track_lead_progress]
        end
    end
    
    %% Carlos - Qualification Agent
    subgraph Carlos [Carlos - Qualification]
        C1[Score: 5-7]
        C2[Goal: Qualify & Demo Value]
        C3[Language: Spanish]
        
        subgraph CarlosTools [Carlos's Tools]
            CT1[get_contact_details_with_task]
            CT2[escalate_to_router]
            CT3[update_contact_with_context]
            CT4[save_important_context]
            CT5[track_lead_progress]
        end
    end
    
    %% Sofia - Appointment Agent
    subgraph Sofia [Sofia - Appointment Setting]
        S1[Score: 8-10]
        S2[Goal: Book Demo]
        S3[Language: Spanish]
        
        subgraph SofiaTools [Sofia's Tools]
            ST1[get_contact_details_with_task]
            ST2[update_contact_with_context]
            ST3[book_appointment_with_instructions]
            ST4[escalate_to_router]
            ST5[track_lead_progress]
        end
    end
```

## Data Flow and State

```mermaid
graph TD
    %% State Management
    subgraph State [Production State]
        S1[messages: List]
        S2[current_agent: str]
        S3[lead_score: int]
        S4[contact_id: str]
        S5[thread_id: str]
        S6[router_complete: bool]
        S7[needs_escalation: bool]
        S8[extracted_data: Dict]
        S9[next_agent: str]
        S10[agent_task: str]
    end
    
    %% GHL Integration
    subgraph GHL [GoHighLevel API]
        G1[get_contact]
        G2[update_contact]
        G3[add_contact_note]
        G4[send_message]
        G5[get_conversations]
        G6[get_conversation_messages]
    end
    
    %% Message Flow
    State --> |Read/Write| Agents[All Agents]
    Agents --> |API Calls| GHL
    GHL --> |Data| State
```

## Smart Router Logic

```mermaid
graph TD
    %% Router Decision Tree
    Message[Customer Message] --> Analyze[Analyze Message]
    
    Analyze --> Extract[Extract Data]
    Extract --> Score[Calculate Score]
    
    Score --> |Check Score| Decision{Score Range?}
    
    Decision --> |0-4| RouteM[Route to Maria]
    Decision --> |5-7| RouteC[Route to Carlos]
    Decision --> |8-10| RouteS[Route to Sofia]
    
    RouteM --> SetTask1[Task: Collect Info]
    RouteC --> SetTask2[Task: Qualify Lead]
    RouteS --> SetTask3[Task: Book Demo]
    
    %% Scoring Factors
    subgraph Scoring [Scoring Factors]
        F1[Has Name: +1]
        F2[Has Business: +2]
        F3[Has Budget: +2]
        F4[High Interest: +2]
        F5[Urgency: +1]
        F6[Contact Info: +1]
        F7[Ready to Buy: +1]
    end
```

## Tool Details

```mermaid
graph LR
    %% Tool Categories
    subgraph Contact [Contact Tools]
        T1[get_contact_details_with_task<br/>Get GHL contact info]
        T2[update_contact_with_context<br/>Update contact fields]
        T3[save_important_context<br/>Save notes to GHL]
    end
    
    subgraph Progress [Progress Tools]
        T4[track_lead_progress<br/>Track score changes]
        T5[escalate_to_router<br/>Transfer to different agent]
    end
    
    subgraph Appointment [Appointment Tools]
        T6[book_appointment_with_instructions<br/>Book demo appointments]
    end
    
    %% Tool Flow
    Agents[Agents] --> |Use| Contact
    Agents --> |Use| Progress
    Sofia --> |Use| Appointment
```

## Error Handling and Edge Cases

```mermaid
graph TD
    %% Error Scenarios
    Error[Error Occurs] --> Type{Error Type?}
    
    Type --> |API Error| Retry[Retry with Backoff]
    Type --> |Invalid State| Default[Use Default Values]
    Type --> |Tool Failure| Fallback[Return Error Message]
    
    Retry --> |Success| Continue[Continue Flow]
    Retry --> |Max Retries| LogError[Log Error & Continue]
    
    Default --> Continue
    Fallback --> Continue
    LogError --> Continue
```

## Key Features

1. **Thread Management**: Each conversation gets a unique thread_id for persistence
2. **Message Deduplication**: Prevents duplicate messages with case-insensitive comparison
3. **Smart Routing**: Automatic agent selection based on lead score
4. **Tool Tracking**: All tool usage logged to LangSmith
5. **Error Recovery**: Graceful handling of API failures
6. **State Persistence**: Memory checkpoint for conversation continuity

## Workflow Rules

- **Maria** (Score 0-4): Initial contact, information gathering
- **Carlos** (Score 5-7): Qualification and value demonstration  
- **Sofia** (Score 8-10): Demo booking and closing
- **Responder**: Sends all agent messages via WhatsApp
- **Smart Router**: Analyzes messages and routes based on lead score

## Integration Points

- **GoHighLevel**: CRM and messaging platform
- **LangSmith**: Debugging and monitoring
- **OpenAI**: LLM for agents
- **WhatsApp**: Communication channel