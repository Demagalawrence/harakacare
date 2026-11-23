# 🎤 HarakaCare AI Triage — Live Demo Script

**Goal:** Demonstrate the AI conversational triage flow end-to-end.

**Current status note:** OpenAI credits are currently exhausted (`429 no credits`), so the
conversational AI automatically uses its built-in deterministic NLP + fallback engine —
which is fully functional and clinically safe. The demo below works **right now**.

---

## Prerequisites (running)

- Backend: `http://127.0.0.1:8000` (Django dev server)
- Frontend: `http://localhost:3000` → visit **`/chat`**
- Health check: `GET http://127.0.0.1:8000/health-check/` → `"ready": true`

---

## Demo Flow 1: Non-Emergency — "I have a fever and headache"

| Step | User types | AI response (stage) | What happens |
|---|---|---|---|
| 1 | `hi` | Welcome + disclaimer + start (`symptoms`) | Conversation starts, `conversation_id` issued |
| 2 | `I have a fever and headache for 2 days` | Smart follow-up questions (age, sex, duration) (`followup`) | Symptom text saved to `patient_data.complaint_text` |
| 3 | `I am a 30 year old female, symptoms for 3 days now` | Assessment guidance (`assessment`) | Flow ends → case reference produced |

**Expected API responses:**

```json
// Step 1
{ "message": "🏥 Welcome to HarakaCare Medical Triage! ...", "stage": "symptoms", "conversation_id": "PT-XXXX" }

// Step 2
{ "stage": "followup", "patient_data": { "complaint_text": "I have a fever and headache for 2 days" } }

// Step 3
{ "stage": "assessment", ... }
```

---

## Demo Flow 2: Emergency — Chest Pain + Difficulty Breathing (SAFETY OVERRIDE)

| Step | User types | AI response (stage) | Safety engine |
|---|---|---|---|
| 4 | `I have chest pain and difficulty breathing` | **`EMERGENCY: Danger signs detected. Seek immediate medical attention...`** (`emergency`) | `safety_level: emergency`, red flags override AI |

**Safety guarantee to highlight in the demo:**

```json
{
  "stage": "emergency",
  "safety": {
    "safety_level": "emergency",
    "requires_human_review": true,
    "reasoning": "Safety rules triggered: Severe Breathing Difficulty",
    "recommended_action": "EMERGENCY: Immediate medical care required. Go to nearest hospital."
  }
}
```

> 🚨 **Key talking point:** No matter what the AI says, the **deterministic Clinical Safety Engine always overrides** the AI when red flags are detected. Emergency red flags are **never** downgraded.

---

## Demo Talking Points (AI Course Project)

1. **Natural language understanding** — patient says *"I have a fever and headache for 2 days"* → structured `patient_data` extracted.
2. **Conversational stages** — `symptoms → followup → consent → assessment → emergency`.
3. **Safety-first design** — AI collects symptoms; safety engine decides emergencies.
4. **AI limitations** — AI is decision *support*, never diagnosis/prescription; clinician review required.
5. **ML + rules** — ML risk classifier + rule-based fallback with red-flag override.
6. **Consent & privacy** — patient consent required before clinical data use.

---

## Quick Commands

```bash
# Backend
py manage.py runserver 127.0.0.1:8000 --settings=harakacare.settings.development

# Frontend
cd frontend && npx react-scripts start   # http://localhost:3000/chat

# Health
curl http://127.0.0.1:8000/health-check/
```

---

## Sample API Calls (for live demo)

```bash
# Start conversation
curl -X POST http://127.0.0.1:8000/api/v1/triage/chat/ \
  -H "Content-Type: application/json" \
  -d '{"message": "hi"}'

# Continue
curl -X POST http://127.0.0.1:8000/api/v1/triage/chat/ \
  -H "Content-Type: application/json" \
  -d '{
    "message": "I have a fever and headache for 2 days",
    "conversation_id": "PT-XXXX",
    "context": {"stage": "symptoms", "patient_data": {}}
  }'
```
