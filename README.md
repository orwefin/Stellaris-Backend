# Stellaris-Backend
STELLARIS – Astrologisches Backend mit KI &amp; Swiss Ephemeris. Generiert mehrsprachige Horoskope (DE, EN, FR, ES, IT, PT und später mehr).

1. STELLARIS – Dein persönliches Horoskop

Ein digitales Observatorium – astrologische Berechnungen, KI-generierte Texte und mehrsprachige Horoskope in sechs Sprachen.

Wichtige Voraussetzungen:
![AGPL-3.0](https://img.shields.io/badge/License-AGPL--3.0-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)](https://fastapi.tiangolo.com)


2. Über STELLARIS

STELLARIS ist ein astrologisches Backend, das personalisierte Horoskope auf Basis der Swiss Ephemeris berechnet und mit KI in poetische, mehrsprachige Texte umwandelt.

Unterstützte Sprachen:
-  Deutsch
-  English
-  Français
-  Español
-  Italiano
-  Português



3. Funktionen

- Astrologische Berechnungen – Planetenpositionen, Häuser, Aspekte mit Swiss Ephemeris
- Mehrsprachig – Antworten in sechs Sprachen
- KI-generierte Horoskope – poetische, präzise Texte per KI
- Verschiedene Horoskope auch kompinierbar
- Planetenrad-Visualisierung – interaktives Rad im Frontend
- Spenden-Integration – einfache Unterstützung über Ko-fi


4. Technologie

| Komponente  | Technologie |
|-------------|-------------|
| Backend     | FastAPI (Python) |
| Astrologie  | pyswisseph (Swiss Ephemeris) |
| KI          | API OpenAI-kompatibel |
| Frontend    | HTML, CSS, JavaScript (eigenständig) |
| Lizenz      | AGPL-3.0 |


5. Installation

  1. Repository klonen

bash:
git clone https://github.com/orwefin/stellaris-backend.git
cd stellaris-backend


6. Anpassung der main.py


import os
from openai import OpenAI

# OpenAI-kompatible API konfigurieren
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")

if not OPENAI_API_KEY:
    raise ValueError("❌ OPENAI_API_KEY fehlt in .env")

client = OpenAI(
    api_key=OPENAI_API_KEY,
    base_url=OPENAI_BASE_URL
)

LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
