import hashlib

def generate_patient_token(phone: str) -> str:
    phone = phone.replace("+", "").strip()
    return "PT-" + hashlib.sha256(phone.encode()).hexdigest()[:16]