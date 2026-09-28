import re


class PIIService:
    @staticmethod
    def extract_names(text: str) -> list:
        """Extract real names for the doctor's dashboard."""
        if not text:
            return []
        names = []

        # Hindi: "मेरा नाम X Y है"
        hindi_stops = r'(?=\s+(?:है|हूँ|हूं|था|थी|का|की|के|आपका|आपकी|मेरा|मेरी|और|मुझे|मैं)\b|[।\.\?\!]|$)'
        for match in re.finditer(
            r'(?:मेरा\s+नाम|नाम)\s+([\u0900-\u097F]+(?:\s+[\u0900-\u097F]+){0,3})' + hindi_stops,
            text
        ):
            names.append(match.group(1).strip())

        # English
        for match in re.finditer(
            r'\b(?:My\s+name\s+is|I\s+am|I\'m)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,4})',
            text,
            flags=re.IGNORECASE
        ):
            names.append(match.group(1).strip())

        for match in re.finditer(
            r'\b(?:Patient\s+Name|Name)[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,4})',
            text
        ):
            names.append(match.group(1).strip())

        for match in re.finditer(
            r'\b(?:Mr|Mrs|Ms|Dr|Shri|Smt|Sri)\.?\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3})',
            text
        ):
            names.append(match.group(1).strip())

        seen = set()
        unique = []
        for n in names:
            key = n.strip().lower()
            if key and key not in seen:
                seen.add(key)
                unique.append(n.strip())
        return unique

    @staticmethod
    def redact(text: str) -> str:
        """
        Redact IDs, phones, emails — but KEEP names visible.
        Runs safely even if called multiple times.
        """
        if not text:
            return text

        # Skip if already processed
        if "[ABHA_ID_REDACTED]" in text and "[NAME_REDACTED]" not in text:
            # Still check other patterns
            pass

        # ABHA ID (only redact once)
        text = re.sub(r'\b\d{2}-\d{4}-\d{4}-\d{4}\b', '[ABHA_ID_REDACTED]', text)

        # Aadhaar
        text = re.sub(r'\b\d{4}\s?\d{4}\s?\d{4}\b', '[AADHAAR_REDACTED]', text)

        # Phone
        text = re.sub(r'\b[6-9]\d{9}\b', '[PHONE_REDACTED]', text)

        # Email
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