<div align="center">

# 🩺 AarogyaTriage

**A local-first, multimodal triage system for rural Indian healthcare.**

Nurses capture. AI prepares. Doctors decide.

Built for **Hackathon BPUT 2026**

[Architecture](#-architecture) · [Setup](#-getting-started) · [API](#-api-reference) · [Compliance](#-compliance)

</div>

---

## The Problem

A nurse at a Primary Health Centre in rural Odisha sees **60+ patients a day**. She has **2 minutes per patient**. She speaks Odia. The doctor speaks English. Lab reports come on paper. The internet drops every 20 minutes.

Triage today is informal — whoever shouts loudest gets seen first. Critical cases wait. Stable cases crowd the queue.

## The Solution

**AarogyaTriage is built for that nurse.**

She speaks symptoms in Odia. The system:

- Transcribes them (Sarvam AI)
- Extracts lab values from a photographed report (OCR)
- Describes a wound from a photo (Vision AI)
- Asks 5 targeted follow-up questions in her language (Groq LLaMA 3.1)
- Calculates a MEWS score and assigns priority P1–P4
- Hands the doctor a fully prepared case — in under **5 minutes**

No cloud dependency. No internet needed for core triage. Just a laptop.

---

## ✦ Capabilities

<table>
<tr>
<td width="50%" valign="top">

**🧑‍⚕️ Nurse Intake**
- Voice input in Odia, Hindi, English
- Lab report OCR (Hb · WBC · Platelets · Glucose)
- Wound / rash photo analysis
- AI-generated follow-up questions
- Live vitals with abnormality highlighting

</td>
<td width="50%" valign="top">

**👨‍⚕️ Doctor Workflow**
- Single-screen case review
- AI summary + reasoning shown
- Four actions: OPD · Chemist · ICU · Refer
- Priority override with audit reason
- Real-time queue sorted by urgency

</td>
</tr>
<tr>
<td width="50%" valign="top">

**🧠 Triage Engine**
- MEWS score from vitals
- Priority P1 → P4
- Load-balanced doctor assignment
- Emergency bypass (5-second alert)
- Referral navigator

</td>
<td width="50%" valign="top">

**🌐 System-Level**
- Local-first (SQLite, zero setup)
- Offline sync endpoint
- HL7 FHIR R4 export
- Full audit log
- Role-based access (5 roles)

</td>
</tr>
</table>

---

## 🏗️ Architecture

```mermaid
flowchart LR
    N([🧑‍⚕️ Nurse]) -->|Voice · Lab · Photo · Vitals| AI[🧠 AI Engine]
    AI -->|P1–P4 · Doctor| D([👨‍⚕️ Doctor])
    D --> A{⚖️}
    A -->|Standard| O1[🏥 OPD]
    A -->|Prescribe| O2[💊 Chemist]
    A -->|Critical| O3[🚑 ICU]
    A -->|Complex| O4[📤 Refer DH]
    AI -.->|🚨 P1| E([⚡ Alert 5s])
    E -.-> D

    classDef n fill:#0d9488,color:#fff,stroke:#0f766e,stroke-width:2px
    classDef a fill:#7c3aed,color:#fff,stroke:#6d28d9,stroke-width:2px
    classDef d fill:#2563eb,color:#fff,stroke:#1e40af,stroke-width:2px
    classDef o fill:#10b981,color:#fff,stroke:#047857,stroke-width:2px
    classDef e fill:#dc2626,color:#fff,stroke:#7f1d1d,stroke-width:2px
    class N n
    class AI a
    class D d
    class O1,O2,O3,O4 o
    class E e
