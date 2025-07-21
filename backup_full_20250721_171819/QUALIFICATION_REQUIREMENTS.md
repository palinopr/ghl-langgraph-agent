# 🎯 Qualification Requirements for Appointments

## Main Goal: Book Appointments ONLY with Qualified Leads

Based on the n8n workflow, appointments require:

### ✅ Mandatory Requirements (ALL must be met):
1. **Name** - Full name of the contact
2. **Email** - For sending Google Meet link  
3. **Budget $300+/month** - Confirmed and agreed to

### 🚫 What NOT to Do:
- NEVER book appointments without email
- NEVER mention dates/times without all requirements
- NEVER say "déjame revisar mi calendario" without qualification
- NEVER route to Sofia without budget confirmation

### 🔄 Proper Flow:

1. **Intelligence Layer** (Automatic)
   - Extracts name, business, budget from Spanish text
   - Scores lead 1-10
   - Never decreases score

2. **Supervisor** (Router)
   - Checks qualification status
   - Routes based on score AND requirements:
     - Score 6+ WITH all requirements → Sofia
     - Score 5-7 OR missing requirements → Carlos  
     - Score 1-4 → Maria

3. **Carlos** (Qualifier)
   - Primary job: Confirm $300+ budget
   - "Trabajo con presupuestos desde $300/mes, ¿te funciona?"
   - If "sí" → Mark qualified → Route to Sofia
   - If "no" → Polite closure

4. **Sofia** (Appointment Setter)
   - ONLY books if has name + email + $300+ budget
   - Uses calendar tools to check availability
   - Sends confirmation with Google Meet link

### 📊 Example Scenarios:

**Scenario 1: Qualified Lead**
- User: "Soy Jaime, tengo un restaurante"
- Carlos: "¿Trabajas con presupuestos desde $300/mes?"
- User: "Sí"
- Carlos: "Perfecto, te paso con Sofia"
- Sofia: "Jaime, necesito tu email para el link"
- User: "jaime@restaurant.com"
- Sofia: [CHECKS CALENDAR] "Tengo martes 10am o jueves 3pm"

**Scenario 2: Missing Budget**
- User: "Quiero agendar una cita"
- Score: 8/10 (high intent)
- Supervisor: Routes to Carlos (not Sofia) because no budget
- Carlos: Must qualify budget first

**Scenario 3: Complete Info**
- Extracted: Name ✓, Email ✓, Budget $300+ ✓
- Score: 7/10
- Supervisor: Routes directly to Sofia
- Sofia: Books appointment immediately

### 🛠️ Implementation Status:
- ✅ Intelligence layer extracts all info
- ✅ Supervisor checks qualification
- ✅ Carlos focuses on $300+ budget
- ✅ Sofia validates before booking
- ✅ Responder sends confirmations

This ensures QUALITY over QUANTITY - only qualified appointments!