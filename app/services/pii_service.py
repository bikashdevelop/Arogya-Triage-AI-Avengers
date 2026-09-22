import re


class PIIService:
    @staticmethod
    def redact(text: str) -> str:
        if not text:
            return text

        # ---------- ENGLISH NAME PATTERNS ----------
        # "My name is X Y" → "My name is [NAME_REDACTED]"
        text = re.sub(
            r'\b(My\s+name\s+is|I\s+am|I\'m)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            r'\1 [NAME_REDACTED]',
            text,
            flags=re.IGNORECASE
        )

        # "Name: X Y" / "Patient Name: X Y"
        text = re.sub(
            r'(Patient\s+Name|Name)[:\s]+[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*',
            r'\1: [NAME_REDACTED]',
            text,
            flags=re.IGNORECASE
        )

        # Names with English titles (Mr./Mrs./Dr.)
        text = re.sub(
            r'\b(Mr|Mrs|Ms|Dr|Shri|Smt|Sri)\.?\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*',
            '[NAME_REDACTED]',
            text
        )

        # ---------- HINDI NAME PATTERNS ----------
        # "मेरा नाम X है" → "मेरा नाम [NAME_REDACTED] है"
        text = re.sub(
            r'(मेरा\s+नाम|मेरा\s+नाम\s+है)\s+[\u0900-\u097F]+(?:\s+[\u0900-\u097F]+)*',
            r'मेरा नाम [NAME_REDACTED]',
            text
        )

        # "नाम: X" / "रोगी का नाम: X"
        text = re.sub(
            r'(नाम|रोगी\s+का\s+नाम)[:\s]+[\u0900-\u097F]+(?:\s+[\u0900-\u097F]+)*',
            r'\1: [NAME_REDACTED]',
            text
        )

        # ---------- IDENTIFIERS ----------
        # ABHA ID (XX-XXXX-XXXX-XXXX)
        text = re.sub(r'\b\d{2}-\d{4}-\d{4}-\d{4}\b', '[ABHA_ID_REDACTED]', text)

        # Aadhaar (12 digits)
        text = re.sub(r'\b\d{4}\s?\d{4}\s?\d{4}\b', '[AADHAAR_REDACTED]', text)

        # Indian phone numbers (10 digits)
        text = re.sub(r'\b[6-9]\d{9}\b', '[PHONE_REDACTED]', text)

        # Emails
        text = re.sub(
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            '[EMAIL_REDACTED]',
            text
        )

        # UHID / MRN
        text = re.sub(
            r'\b(UHID|MRN)\b[:\s]*[A-Z0-9-]{6,15}',
            r'\1: [ID_REDACTED]',
            text,
            flags=re.IGNORECASE
        )

        return text