# Full Debug Output - All 4 Traces

## Key Data From Each Trace

### TRACE 1: 1f0669c6-a989-67ec-a016-8f63b91f79c2
- **Message**: "Hola"
- **Thread ID**: d779d1e2-ee2c-458d-8ce6-8828d106ad7f
- **Contact**: L850LitpO3RGj0l504Vu (Jaime Ortiz)
- **Lead Score**: 1
- **Response**: "¡Hola! ¿Cómo te llamas?"
- **Extracted Data**: {"name": null, "business_type": null}
- **Time**: 4.78s
- **Child Runs**: responder, maria, supervisor, intelligence, receptionist

### TRACE 2: 1f0669c7-6120-6563-b484-e5ca2a2740d1  
- **Message**: "Jaime"
- **Thread ID**: 0dbc1c79-30eb-4a12-9509-dbd17eb0d4bd (DIFFERENT!)
- **Contact**: L850LitpO3RGj0l504Vu (Same contact)
- **Lead Score**: 2
- **Response**: "¡Hola Jaime! Me alegra que estés interesado en mejorar la automatización de WhatsApp para tu negocio. ¿Podrías decirme qué tipo de negocio tienes?"
- **Extracted Data**: {"name": "Jaime", "business_type": null}
- **Time**: 7.66s

### TRACE 3: 1f0669c8-709c-6207-9a9f-ac54af55789c
- **Message**: "Restaurante"  
- **Thread ID**: 3969eb20-54d1-41a9-a201-2da88df6a578 (DIFFERENT!)
- **Contact**: L850LitpO3RGj0l504Vu (Same contact)
- **Lead Score**: 4
- **Response**: "¡Hola! Gracias por contactarnos. ¿Podrías decirme el nombre de tu restaurante y un poco más sobre él?"
- **Extracted Data**: {"name": "Restaurante", "business_type": "restaurante"} (NAME WRONG!)
- **Time**: 6.50s

### TRACE 4: 1f0669c9-c860-6dac-9fd9-2f962b941a71
- **Message**: "Papas locas restaurant"
- **Thread ID**: c95ee525-421e-4810-8887-4bd2ce0e4746 (DIFFERENT!)
- **Contact**: L850LitpO3RGj0l504Vu (Same contact)
- **Lead Score**: 3 (DECREASED!)
- **Response**: "¡Hola! Gracias por compartir el nombre de tu restaurante, Papas Locas. ¿Podrías decirme tu nombre para dirigirme a ti de manera más personal?"
- **Extracted Data**: {"name": null, "business_type": "restaurant"} (LOST NAME!)
- **Time**: 6.92s

## Critical Issues Found

1. **Different Thread IDs** - Each message has different thread_id despite same contact
2. **No Conversation Memory** - Agent doesn't remember previous messages
3. **Data Loss** - Lost "Jaime" name in trace 4
4. **Wrong Extraction** - "Restaurante" extracted as name instead of business type
5. **Score Regression** - Score went from 4 to 3 despite more info

## Raw Execution Flow (All Traces)

Each trace follows same pattern:
```
receptionist → intelligence → supervisor → [agent] → responder
```

## Token Usage
- Trace 1: 816 tokens (806 prompt, 10 completion)
- Trace 2: 844 tokens (808 prompt, 36 completion)  
- Trace 3: 843 tokens (813 prompt, 30 completion)
- Trace 4: 853 tokens (814 prompt, 39 completion)

## All Child Run IDs

### Trace 1 Children:
- receptionist: c6edae57-5540-4565-bee8-cf07015e01da
- intelligence: 1ff5b29d-113f-43a0-99d3-5444df38548b
- supervisor: 583b5847-7818-4bad-a5ac-e1ba8ce5b060
- maria: 778588d7-11c4-43df-afb0-22500a40e209
- responder: b82723e9-cf31-4682-a099-e92f1bb645a2

### Trace 2 Children:
- receptionist: dc7c2a71-d6d1-4fbe-b536-b853d3ace8c9
- intelligence: b084d2cd-1341-4bdc-a7fc-2e5ec8c022fb
- supervisor: b087ace4-5696-4c62-b6a7-50b16ac66b38
- maria: ea3199ce-d182-4d24-9600-fbebe2d15569
- responder: b5d5eb14-a050-4272-8978-ce563d7a5e7c

### Trace 3 Children:
- receptionist: 8e2c5c87-35d8-46c4-baaa-a09f7fea2b10
- intelligence: 59c93ad2-f831-4ee2-bfdb-5bb8e8f34b7e
- supervisor: bd96a84f-e0f5-44e1-8b7a-60d5e7cf86e5
- maria: 3b4e6a49-2ffa-44e2-9241-1e22d2b35e81
- responder: 30c40adb-a26b-4e23-b5a0-c4dc4bb02b07

### Trace 4 Children:
- receptionist: 8a2b5d05-1dd6-467d-b85f-7e4c0f17b5e7
- intelligence: 436b0bb8-ffdb-46c7-ad3e-29e088c96c77
- supervisor: 14cf36e8-0dcb-4d93-a5f2-a6a965ecce38
- maria: 8b0ad9d8-ce77-43f8-ab5f-f96e4e9d5bb4
- responder: 0c18c36f-cd73-45c6-b625-6e0f2b3e47a9

## System Information
- LangGraph Version: 0.5.3
- API Version: 0.2.98
- Plan: Enterprise
- Git SHA: caf536db87d928ec31e9b26de82fbb27cf347ca2
- Python: 3.13.5
- LangChain Core: 0.3.69

## Supervisor Error (All Traces)
```
"error": "Missing required key(s) {'remaining_steps'} in state_schema"
```

The full debug output is available in `FULL_DEBUG_OUTPUT.txt` (2315 lines)