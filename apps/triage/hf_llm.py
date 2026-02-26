import os
import json
from dotenv import load_dotenv
from huggingface_hub import InferenceClient

load_dotenv()
HF_TOKEN = os.getenv("HF_TOKEN")

# ✅ InferenceClient handles routing automatically
client = InferenceClient(
    model="Qwen/Qwen2.5-7B-Instruct",
    token=HF_TOKEN
)


def ask_llm(message):
    system_prompt = """You are a medical triage assistant. Extract clinical data from the patient message.
Return ONLY a raw JSON object. No explanation. No markdown. No code blocks.

Use this exact format:
{
  "primary_symptom": "",
  "secondary_symptoms": [],
  "severity": "mild/moderate/severe",
  "duration": "0_1_days/1_3_days/4_7_days/over_1_week"
}"""

    try:
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Patient message: {message}"}
            ],
            temperature=0.2,
            max_tokens=200
        )

        text = response.choices[0].message.content.strip()

        # Try direct parse
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Fallback: extract JSON block if model added surrounding text
            start = text.index("{")
            end = text.rindex("}") + 1
            return json.loads(text[start:end])

    except Exception as e:
        print(f"Error: {e}")
        return None