import os
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import swisseph as swe
from openai import OpenAI
import requests
from dotenv import load_dotenv
import pytz

# ============================================================
# LOGGING AKTIVIEREN
# ============================================================
logging.basicConfig(level=logging.DEBUG)
print("🚀 STELLARIS Backend startet...")

# ============================================================
# 1. .env LADEN
# ============================================================
load_dotenv()

print(f"🔑 API Key geladen? {'Ja' if os.getenv('DEEPSEEK_API_KEY') else 'Nein'}")
print(f"🔑 Erste 10 Zeichen: {os.getenv('DEEPSEEK_API_KEY')[:10] if os.getenv('DEEPSEEK_API_KEY') else 'Nicht gefunden'}")

# ============================================================
# 2. DEEPSEEK KONFIGURATION
# ============================================================
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
if not DEEPSEEK_API_KEY:
    raise ValueError("❌ DEEPSEEK_API_KEY fehlt in .env")

try:
    client = OpenAI(
        api_key=DEEPSEEK_API_KEY,
        base_url="https://api.deepseek.com/v1"
    )
    print("✅ DeepSeek-Client initialisiert")
except Exception as e:
    print(f"❌ Fehler bei DeepSeek-Client: {e}")
    raise

LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-chat")
print(f"🤖 Modell: {LLM_MODEL}")

# Ephemeriden-Pfad
ephe_path = os.getenv("SE_EPHE_PATH", "./ephe")
print(f"📁 Ephemeriden-Pfad: {ephe_path}")
swe.set_ephe_path(ephe_path)

# ============================================================
# 3. FASTAPI + CORS
# ============================================================
app = FastAPI(title="STELLARIS Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
print("✅ CORS konfiguriert")

# ============================================================
# 4. DATENMODELLE
# ============================================================
class PartnerInput(BaseModel):
    name: str
    birth_date: str
    birth_time: str
    birth_city: str
    gender: Optional[str] = ""

class HoroscopeRequest(BaseModel):
    name: str
    birth_date: str
    birth_time: str
    birth_city: str
    timezone: str
    target_date: Optional[str] = None
    gender: Optional[str] = "Frau"
    horoscope_types: List[str]
    partners: Optional[List[PartnerInput]] = []
    language: str = "de"

class HoroscopeResponse(BaseModel):
    horoscope: str
    sun_sign: Optional[str] = None
    moon_sign: Optional[str] = None
    ascendant: Optional[str] = None
    birth_city: Optional[str] = None
    planets: Optional[Dict[str, float]] = None
    sex_partner_positions: Optional[List[Dict]] = None

# ============================================================
# 5. ASTROLOGISCHE HILFSFUNKTIONEN (mehrsprachig)
# ============================================================
# Sternzeichen – Übersetzungen
ZODIAC_NAMES = {
    "de": ["Widder", "Stier", "Zwillinge", "Krebs", "Löwe", "Jungfrau", "Waage", "Skorpion", "Schütze", "Steinbock", "Wassermann", "Fische"],
    "en": ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"],
    "fr": ["Bélier", "Taureau", "Gémeaux", "Cancer", "Lion", "Vierge", "Balance", "Scorpion", "Sagittaire", "Capricorne", "Verseau", "Poissons"],
    "es": ["Aries", "Tauro", "Géminis", "Cáncer", "Leo", "Virgo", "Libra", "Escorpio", "Sagitario", "Capricornio", "Acuario", "Piscis"],
    "it": ["Ariete", "Toro", "Gemelli", "Cancro", "Leone", "Vergine", "Bilancia", "Scorpione", "Sagittario", "Capricorno", "Acquario", "Pesci"],
    "pt": ["Áries", "Touro", "Gêmeos", "Câncer", "Leão", "Virgem", "Libra", "Escorpião", "Sagitário", "Capricórnio", "Aquário", "Peixes"]
}

# Hausbedeutungen – Übersetzungen
HOUSE_MEANINGS = {
    "de": {
        1: "Selbstbild und Persönlichkeit",
        2: "Werte, Besitz und Selbstwert",
        3: "Kommunikation, Geschwister und kurze Reisen",
        4: "Familie, Zuhause und innere Sicherheit",
        5: "Kreativität, Liebe und Vergnügen",
        6: "Gesundheit, Arbeit und tägliche Routinen",
        7: "Partnerschaften und Beziehungen",
        8: "Transformation, Intimität und gemeinsame Ressourcen",
        9: "Philosophie, Fernreisen und Bildung",
        10: "Karriere, öffentliches Ansehen und Lebensziel",
        11: "Freundschaften, Netzwerke und Ziele",
        12: "Spiritualität, Unterbewusstsein und Loslassen"
    },
    "en": {
        1: "Self-image and personality",
        2: "Values, possessions and self-worth",
        3: "Communication, siblings and short trips",
        4: "Family, home and inner security",
        5: "Creativity, love and pleasure",
        6: "Health, work and daily routines",
        7: "Partnerships and relationships",
        8: "Transformation, intimacy and shared resources",
        9: "Philosophy, long journeys and education",
        10: "Career, public image and life goal",
        11: "Friendships, networks and goals",
        12: "Spirituality, subconscious and letting go"
    },
    "fr": {
        1: "Image de soi et personnalité",
        2: "Valeurs, possessions et estime de soi",
        3: "Communication, frères/sœurs et courts voyages",
        4: "Famille, foyer et sécurité intérieure",
        5: "Créativité, amour et plaisir",
        6: "Santé, travail et routines quotidiennes",
        7: "Partenariats et relations",
        8: "Transformation, intimité et ressources partagées",
        9: "Philosophie, voyages lointains et éducation",
        10: "Carrière, image publique et objectif de vie",
        11: "Amitiés, réseaux et objectifs",
        12: "Spiritualité, subconscient et lâcher-prise"
    },
    "es": {
        1: "Autoimagen y personalidad",
        2: "Valores, posesiones y autoestima",
        3: "Comunicación, hermanos y viajes cortos",
        4: "Familia, hogar y seguridad interior",
        5: "Creatividad, amor y placer",
        6: "Salud, trabajo y rutinas diarias",
        7: "Asociaciones y relaciones",
        8: "Transformación, intimidad y recursos compartidos",
        9: "Filosofía, viajes largos y educación",
        10: "Carrera, imagen pública y objetivo de vida",
        11: "Amistades, redes y metas",
        12: "Espiritualidad, subconsciente y dejar ir"
    },
    "it": {
        1: "Immagine di sé e personalità",
        2: "Valori, possedimenti e autostima",
        3: "Comunicazione, fratelli/sorelle e viaggi brevi",
        4: "Famiglia, casa e sicurezza interiore",
        5: "Creatività, amore e piacere",
        6: "Salute, lavoro e routine quotidiane",
        7: "Collaborazioni e relazioni",
        8: "Trasformazione, intimità e risorse condivise",
        9: "Filosofia, viaggi lunghi e istruzione",
        10: "Carriera, immagine pubblica e obiettivo di vita",
        11: "Amicizie, reti e obiettivi",
        12: "Spiritualità, subconscio e lasciar andare"
    },
    "pt": {
        1: "Autoimagem e personalidade",
        2: "Valores, posses e autoestima",
        3: "Comunicação, irmãos e viagens curtas",
        4: "Família, lar e segurança interior",
        5: "Criatividade, amor e prazer",
        6: "Saúde, trabalho e rotinas diárias",
        7: "Parcerias e relacionamentos",
        8: "Transformação, intimidade e recursos compartilhados",
        9: "Filosofia, viagens longas e educação",
        10: "Carreira, imagem pública e objetivo de vida",
        11: "Amizades, redes e metas",
        12: "Espiritualidade, subconsciente e deixar ir"
    }
}

def get_zodiac_sign(deg: float, lang: str = "de") -> str:
    idx = int(deg // 30) % 12
    names = ZODIAC_NAMES.get(lang, ZODIAC_NAMES["de"])
    return names[idx]

def calc_planet_positions(jd: float) -> Dict[str, float]:
    planets = {
        "Sonne": swe.SUN,
        "Mond": swe.MOON,
        "Merkur": swe.MERCURY,
        "Venus": swe.VENUS,
        "Mars": swe.MARS,
        "Jupiter": swe.JUPITER,
        "Saturn": swe.SATURN,
        "Uranus": swe.URANUS,
        "Neptun": swe.NEPTUNE,
        "Pluto": swe.PLUTO,
    }
    result = {}
    for name, id_ in planets.items():
        try:
            pos, _ = swe.calc_ut(jd, id_)
            result[name] = pos[0]  # Längengrad in Grad
        except Exception as e:
            print(f"⚠️ Fehler bei Planet {name}: {e}")
            result[name] = 0.0
    return result

def get_house_positions(jd: float, lat: float, lng: float) -> List[float]:
    try:
        houses = swe.houses(jd, lat, lng, b'P')
        return houses[0]  # Spitzen der 12 Häuser
    except Exception as e:
        print(f"⚠️ Fehler bei Häuserberechnung: {e}")
        return [0.0] * 12

def calc_aspects(planet_positions: Dict[str, float]) -> List[Dict]:
    aspects = []
    planets = list(planet_positions.keys())
    for i in range(len(planets)):
        for j in range(i+1, len(planets)):
            p1 = planets[i]
            p2 = planets[j]
            diff = abs(planet_positions[p1] - planet_positions[p2]) % 360
            diff = min(diff, 360 - diff)
            orb = 8.0
            if diff <= orb:
                aspect = "Konjunktion"
            elif abs(diff - 60) <= orb:
                aspect = "Sextil"
            elif abs(diff - 90) <= orb:
                aspect = "Quadrat"
            elif abs(diff - 120) <= orb:
                aspect = "Trigon"
            elif abs(diff - 180) <= orb:
                aspect = "Opposition"
            else:
                continue
            aspects.append({
                "planet1": p1,
                "planet2": p2,
                "aspect": aspect,
                "orb": diff
            })
    return aspects

def get_coordinates(city: str) -> tuple:
    url = "https://nominatim.openstreetmap.org/search"
    params = {"q": city, "format": "json", "limit": 1}
    headers = {"User-Agent": "STELLARIS/1.0"}
    try:
        print(f"🔍 Suche Koordinaten für: {city}")
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        if resp.status_code != 200:
            raise HTTPException(400, f"Stadt '{city}' nicht gefunden.")
        data = resp.json()
        if not data:
            raise HTTPException(400, f"Stadt '{city}' nicht gefunden.")
        lat = float(data[0]["lat"])
        lon = float(data[0]["lon"])
        print(f"📍 Koordinaten: {lat}, {lon}")
        return lat, lon
    except requests.exceptions.Timeout:
        raise HTTPException(408, "Zeitüberschreitung bei der Koordinatenabfrage")
    except Exception as e:
        raise HTTPException(500, f"Fehler bei der Koordinatenabfrage: {str(e)}")

# ============================================================
# 6. PROMPT-ERSTELLUNG (mehrsprachig, verbessert)
# ============================================================
# System-Prompts je nach Sprache
SYSTEM_PROMPTS = {
    "de": "Du bist ein erfahrener Astrologe, der einfühlsame und präzise Horoskope verfasst.",
    "en": "You are an experienced astrologer who writes empathetic and precise horoscopes.",
    "fr": "Vous êtes un astrologue expérimenté qui rédige des horoscopes empathiques et précis.",
    "es": "Eres un astrólogo experimentado que escribe horóscopos empáticos y precisos.",
    "it": "Sei un astrologo esperto che scrive oroscopi empatici e precisi.",
    "pt": "Você é um astrólogo experiente que escreve horóscopos empáticos e precisos."
}

# Übersetzungen der acht Bausteine (wie gehabt)
PROMPT_SECTIONS = {
    "de": {
        "intro": "Bitte strukturiere deine Antwort genau nach diesen 8 Punkten:",
        "1": "**Einführung & Ausblick** – allgemeine Stimmung, roter Faden für den Tag / die Woche.",
        "2": "**Die aktivierten Häuser** – welche Häuser heute besonders angesprochen werden und was das für den Alltag bedeutet.",
        "3": "**Aktuelle Transite & Energien** – welche Planeten-Aspekte wirken und wie sie emotional, mental und physisch spürbar sind.",
        "4": "**Tageszeitliche Aufgaben** – konkrete Fokuszeiten: Vormittag, Nachmittag, Abend – was sollte unbedingt angepackt werden?",
        "5": "**Besondere Chancen (Opportunities)** – welche einmaligen Gelegenheiten bieten sich heute?",
        "6": "**Ein Zitat von Rumi** – thematisch passend zum Horoskop.",
        "7": "**Persönliche Wünsche** – eine liebevolle, persönliche Botschaft für die Person.",
        "8": "**Fazit & ermutigender Satz** – ein prägnanter Merksatz für den Tag / die Woche.",
        "style": "Verwende eine warme, poetische und gleichzeitig präzise Sprache. Formatiere die Überschriften mit **##** für die Hauptpunkte und **###** für Unterpunkte. Hebe wichtige Begriffe mit **fett** hervor."
    },
    "en": {
        "intro": "Please structure your answer exactly according to these 8 points:",
        "1": "**Introduction & Outlook** – general mood, the common thread for the day / week.",
        "2": "**The activated houses** – which houses are particularly addressed today and what this means for everyday life.",
        "3": "**Current transits & energies** – which planetary aspects are active and how they are felt emotionally, mentally and physically.",
        "4": "**Daily tasks** – specific focus times: morning, afternoon, evening – what should definitely be tackled?",
        "5": "**Special opportunities** – what unique opportunities are available today?",
        "6": "**A quote from Rumi** – thematically fitting for the horoscope.",
        "7": "**Personal wishes** – a loving, personal message for the person.",
        "8": "**Conclusion & encouraging sentence** – a concise motto for the day / week.",
        "style": "Use a warm, poetic and precise language. Format headings with **##** for main points and **###** for sub-points. Highlight important terms with **bold**."
    },
    "fr": {
        "intro": "Veuillez structurer votre réponse exactement selon ces 8 points :",
        "1": "**Introduction & perspectives** – humeur générale, fil conducteur du jour / de la semaine.",
        "2": "**Les maisons activées** – quelles maisons sont particulièrement sollicitées aujourd'hui et ce que cela signifie pour la vie quotidienne.",
        "3": "**Transits & énergies actuels** – quels aspects planétaires sont actifs et comment ils se font sentir émotionnellement, mentalement et physiquement.",
        "4": "**Tâches quotidiennes** – moments de concentration concrets : matin, après-midi, soir – que faut-il absolument aborder ?",
        "5": "**Opportunités particulières** – quelles opportunités uniques s'offrent aujourd'hui ?",
        "6": "**Une citation de Rumi** – en accord avec le thème de l'horoscope.",
        "7": "**Vœux personnels** – un message affectueux et personnalisé pour la personne.",
        "8": "**Conclusion & phrase encourageante** – une devise concise pour le jour / la semaine.",
        "style": "Utilisez un langage chaleureux, poétique et précis. Formatez les titres avec **##** pour les points principaux et **###** pour les sous-points. Mettez les termes importants en **gras**."
    },
    "es": {
        "intro": "Por favor, estructura tu respuesta exactamente según estos 8 puntos:",
        "1": "**Introducción y perspectivas** – estado de ánimo general, hilo conductor del día / semana.",
        "2": "**Las casas activadas** – qué casas se ven especialmente afectadas hoy y qué significa para la vida cotidiana.",
        "3": "**Tránsitos y energías actuales** – qué aspectos planetarios están activos y cómo se sienten emocional, mental y físicamente.",
        "4": "**Tareas diarias** – momentos de enfoque concretos: mañana, tarde, noche – ¿qué se debe abordar sin falta?",
        "5": "**Oportunidades especiales** – ¿qué oportunidades únicas se presentan hoy?",
        "6": "**Una cita de Rumi** – que encaje temáticamente con el horóscopo.",
        "7": "**Deseos personales** – un mensaje cariñoso y personal para la persona.",
        "8": "**Conclusión y frase alentadora** – un lema conciso para el día / semana.",
        "style": "Utiliza un lenguaje cálido, poético y preciso. Formatea los títulos con **##** para los puntos principales y **###** para los subpuntos. Resalta los términos importantes con **negrita**."
    },
    "it": {
        "intro": "Per favore, struttura la tua risposta esattamente secondo questi 8 punti:",
        "1": "**Introduzione e prospettive** – umore generale, filo conduttore del giorno / settimana.",
        "2": "**Le case attivate** – quali case sono particolarmente coinvolte oggi e cosa significa per la vita quotidiana.",
        "3": "**Transiti ed energie attuali** – quali aspetti planetari sono attivi e come si manifestano a livello emotivo, mentale e fisico.",
        "4": "**Compiti quotidiani** – momenti di concentrazione specifici: mattina, pomeriggio, sera – cosa va assolutamente affrontato?",
        "5": "**Opportunità speciali** – quali opportunità uniche si offrono oggi?",
        "6": "**Una citazione di Rumi** – tematicamente appropriata per l'oroscopo.",
        "7": "**Desideri personali** – un messaggio affettuoso e personalizzato per la persona.",
        "8": "**Conclusione e frase incoraggiante** – un motto conciso per il giorno / settimana.",
        "style": "Usa un linguaggio caldo, poetico e preciso. Formatta i titoli con **##** per i punti principali e **###** per i sottopunti. Evidenzia i termini importanti con **grassetto**."
    },
    "pt": {
        "intro": "Por favor, estruture sua resposta exatamente de acordo com estes 8 pontos:",
        "1": "**Introdução e perspectivas** – humor geral, fio condutor do dia / semana.",
        "2": "**As casas ativadas** – quais casas são particularmente abordadas hoje e o que isso significa para o dia a dia.",
        "3": "**Trânsitos e energias atuais** – quais aspectos planetários estão ativos e como são sentidos emocional, mental e fisicamente.",
        "4": "**Tarefas diárias** – momentos de foco específicos: manhã, tarde, noite – o que deve ser abordado sem falta?",
        "5": "**Oportunidades especiais** – quais oportunidades únicas surgem hoje?",
        "6": "**Uma citação de Rumi** – tematicamente adequada para o horóscopo.",
        "7": "**Desejos pessoais** – uma mensagem carinhosa e personalizada para a pessoa.",
        "8": "**Conclusão e frase encorajadora** – um lema conciso para o dia / semana.",
        "style": "Use uma linguagem calorosa, poética e precisa. Formate os títulos com **##** para os pontos principais e **###** para os subpontos. Destaque termos importantes com **negrito**."
    }
}

# Übersetzungen für allgemeine Prompt-Teile
PROMPT_PHRASES = {
    "de": {
        "houses": "Häuser:",
        "aspects": "Wichtige Aspekte:",
        "no_aspects": "Keine starken Aspekte heute.",
        "create": "Erstelle ein detailliertes {type_name} für {name} ({gender}) mit folgenden astrologischen Daten:",
        "sun": "Sonnenzeichen:",
        "moon": "Mondzeichen:",
        "asc": "Aszendent:",
        "birthplace": "Geburtsort:",
        "valid": "Gültig für:",
        "partner": "Partner:",
        "synastry_hint": "Berücksichtige die synastrischen Einflüsse in der Lesung."
    },
    "en": {
        "houses": "Houses:",
        "aspects": "Important aspects:",
        "no_aspects": "No strong aspects today.",
        "create": "Create a detailed {type_name} for {name} ({gender}) with the following astrological data:",
        "sun": "Sun sign:",
        "moon": "Moon sign:",
        "asc": "Ascendant:",
        "birthplace": "Place of birth:",
        "valid": "Valid for:",
        "partner": "Partner:",
        "synastry_hint": "Consider the synastry influences in the reading."
    },
    "fr": {
        "houses": "Maisons :",
        "aspects": "Aspects importants :",
        "no_aspects": "Pas d'aspects forts aujourd'hui.",
        "create": "Créez un {type_name} détaillé pour {name} ({gender}) avec les données astrologiques suivantes :",
        "sun": "Signe solaire :",
        "moon": "Signe lunaire :",
        "asc": "Ascendant :",
        "birthplace": "Lieu de naissance :",
        "valid": "Valable pour :",
        "partner": "Partenaire :",
        "synastry_hint": "Tenez compte des influences de synastrie dans la lecture."
    },
    "es": {
        "houses": "Casas:",
        "aspects": "Aspectos importantes:",
        "no_aspects": "No hay aspectos fuertes hoy.",
        "create": "Crea un {type_name} detallado para {name} ({gender}) con los siguientes datos astrológicos:",
        "sun": "Signo solar:",
        "moon": "Signo lunar:",
        "asc": "Ascendente:",
        "birthplace": "Lugar de nacimiento:",
        "valid": "Válido para:",
        "partner": "Pareja:",
        "synastry_hint": "Considera las influencias de sinastría en la lectura."
    },
    "it": {
        "houses": "Case:",
        "aspects": "Aspetti importanti:",
        "no_aspects": "Nessun aspetto forte oggi.",
        "create": "Crea un {type_name} dettagliato per {name} ({gender}) con i seguenti dati astrologici:",
        "sun": "Segno solare:",
        "moon": "Segno lunare:",
        "asc": "Ascendente:",
        "birthplace": "Luogo di nascita:",
        "valid": "Valido per:",
        "partner": "Partner:",
        "synastry_hint": "Considera le influenze di sinastria nella lettura."
    },
    "pt": {
        "houses": "Casas:",
        "aspects": "Aspectos importantes:",
        "no_aspects": "Nenhum aspecto forte hoje.",
        "create": "Crie um {type_name} detalhado para {name} ({gender}) com os seguintes dados astrológicos:",
        "sun": "Signo solar:",
        "moon": "Signo lunar:",
        "asc": "Ascendente:",
        "birthplace": "Local de nascimento:",
        "valid": "Válido para:",
        "partner": "Parceiro:",
        "synastry_hint": "Considere as influências de sinastria na leitura."
    }
}

def build_prompt(
    name: str,
    sun: str,
    moon: str,
    asc: str,
    birth_city: str,
    target_date: str,
    gender: str,
    houses: List[float],
    aspects: List[Dict],
    planets: Dict[str, float],
    horoscope_type: str,
    partner_name: Optional[str] = None,
    language: str = "de"
) -> str:
    print(f"🌐 Sprache für Prompt: {language}")

    # Hole die Übersetzungen für diese Sprache
    phrases = PROMPT_PHRASES.get(language, PROMPT_PHRASES["de"])
    house_meanings = HOUSE_MEANINGS.get(language, HOUSE_MEANINGS["de"])

    # Hauszeilen (mit übersetzten Bedeutungen)
    house_lines = []
    for i, deg in enumerate(houses, start=1):
        if i <= 12:
            sign = get_zodiac_sign(deg, language)
            meaning = house_meanings.get(i, "")
            house_lines.append(f"🏠 {i}. {phrases['houses']} ({meaning}): {sign} {deg:.1f}°")

    # Aspektzeilen (Aspektnamen bleiben auf Deutsch, da astrologische Fachbegriffe)
    aspect_lines = []
    for asp in aspects:
        aspect_lines.append(f"• {asp['planet1']} {asp['aspect']} {asp['planet2']} (Orb: {asp['orb']:.1f}°)")

    type_names = {
        "daily": "Tageshoroskop",
        "weekly": "Wochenhoroskop",
        "love": "Liebeshoroskop",
        "career": "Karrierehoroskop",
        "health": "Gesundheitshoroskop",
        "spiritual": "Spirituelles Horoskop",
        "sex": "Sex-Horoskop",
        "synastry": "Partnerhoroskop (Synastrie)"
    }
    # Übersetze den Horoskop-Typ-Namen in die Zielsprache (einfache Fallback-Lösung)
    type_name = type_names.get(horoscope_type, horoscope_type)

    # Sprachinstruktion
    language_instructions = {
        "de": "Antworte auf Deutsch.",
        "en": "Answer in English.",
        "fr": "Réponds en français.",
        "es": "Responde en español.",
        "it": "Rispondi in italiano.",
        "pt": "Responda em português."
    }
    lang_instruction = language_instructions.get(language, "Antworte auf Deutsch.")

    # Baue den Prompt – komplett in der Zielsprache
    prompt_parts = [
        lang_instruction,
        "",
        phrases["create"].format(type_name=type_name, name=name, gender=gender),
        f"- {phrases['sun']} {sun}",
        f"- {phrases['moon']} {moon}",
        f"- {phrases['asc']} {asc}",
        f"- {phrases['birthplace']} {birth_city}",
        f"- {phrases['valid']} {target_date}",
        "",
        phrases["houses"],
        "\n".join(house_lines),
        "",
        phrases["aspects"],
        "\n".join(aspect_lines) if aspect_lines else phrases["no_aspects"]
    ]

    if partner_name:
        prompt_parts.append(f"\n{phrases['partner']} {partner_name}")
        prompt_parts.append(phrases["synastry_hint"])

    # Die acht Punkte (aus den Übersetzungen)
    lang_texts = PROMPT_SECTIONS.get(language, PROMPT_SECTIONS["de"])
    prompt_parts.append("")
    prompt_parts.append(lang_texts["intro"])
    prompt_parts.append("1. " + lang_texts["1"])
    prompt_parts.append("2. " + lang_texts["2"])
    prompt_parts.append("3. " + lang_texts["3"])
    prompt_parts.append("4. " + lang_texts["4"])
    prompt_parts.append("5. " + lang_texts["5"])
    prompt_parts.append("6. " + lang_texts["6"])
    prompt_parts.append("7. " + lang_texts["7"])
    prompt_parts.append("8. " + lang_texts["8"])
    prompt_parts.append(lang_texts["style"])
    prompt_parts.append("")
    prompt_parts.append(lang_instruction)

    return "\n".join(prompt_parts)

# ============================================================
# 7. HAUPT-ENDPOINT (mit korrigierter Astrologie-Berechnung)
# ============================================================
@app.post("/api/horoscope", response_model=HoroscopeResponse)
async def generate_horoscope(request: HoroscopeRequest):
    try:
        print(f"\n📥 Anfrage für {request.name}, Typ: {request.horoscope_types}")
        print(f"🌐 Gewünschte Sprache: {request.language}")

        # Ziel-Datum
        if request.target_date:
            target_date = request.target_date
        else:
            target_date = datetime.now().strftime("%Y-%m-%d")
        print(f"📅 Ziel-Datum: {target_date}")

        # ----- GEBURTSZEIT IN UTC UMRECHNEN (KORREKT) -----
        timezone_str = request.timezone
        try:
            tz = pytz.timezone(timezone_str)
        except pytz.UnknownTimeZoneError:
            raise HTTPException(400, f"Unbekannte Zeitzone: {timezone_str}")

        birth_date_str = request.birth_date
        birth_time_str = request.birth_time

        # Lokale Zeit als naive datetime erzeugen
        local_dt = datetime.strptime(f"{birth_date_str} {birth_time_str}", "%Y-%m-%d %H:%M")
        # Zeit als lokale Zeit markieren (ohne Umrechnung)
        local_dt = tz.localize(local_dt, is_dst=None)
        # In UTC umwandeln
        utc_dt = local_dt.astimezone(pytz.UTC)

        print(f"🕒 Lokale Zeit (eingegeben): {local_dt.strftime('%Y-%m-%d %H:%M %Z')}")
        print(f"🕒 UTC-Zeit (für Ephemeride): {utc_dt.strftime('%Y-%m-%d %H:%M UTC')}")

        # JD für UTC berechnen
        jd_birth = swe.julday(utc_dt.year, utc_dt.month, utc_dt.day,
                              utc_dt.hour + utc_dt.minute/60.0 + utc_dt.second/3600.0)
        print(f"📅 JD (UTC): {jd_birth}")

        # ----- KOORDINATEN -----
        lat, lon = get_coordinates(request.birth_city)

        # ----- ZIEL-JD (für Transite, wenn target_date gesetzt) -----
        target_dt = datetime.strptime(target_date, "%Y-%m-%d")
        jd_target = swe.julday(target_dt.year, target_dt.month, target_dt.day, 0.0)
        print(f"🎯 Ziel-JD: {jd_target}")

        # ----- PLANETENPOSITIONEN ZUM GEBURTSZEITPUNKT (für Sonne/Mond) -----
        # Wir berechnen die Planeten für den Geburtszeitpunkt (JD_birth)
        # Für Sonne und Mond nehmen wir die Position zum Geburtszeitpunkt.
        # Die Transite werden später mit jd_target berechnet.
        birth_planets = calc_planet_positions(jd_birth)
        sun_deg = birth_planets.get("Sonne", 0.0)
        moon_deg = birth_planets.get("Mond", 0.0)

        # ----- HÄUSER UND ASZENDENT (zum Geburtszeitpunkt) -----
        houses = get_house_positions(jd_birth, lat, lon)
        asc_deg = houses[0] if houses else 0.0

        # ----- STERNZEICHEN IN DER GEWÜNSCHTEN SPRACHE -----
        sun_sign = get_zodiac_sign(sun_deg, request.language)
        moon_sign = get_zodiac_sign(moon_deg, request.language)
        asc_sign = get_zodiac_sign(asc_deg, request.language)

        print(f"☀️ Sonne: {sun_sign} ({sun_deg:.2f}°)")
        print(f"🌙 Mond: {moon_sign} ({moon_deg:.2f}°)")
        print(f"⬆️ Aszendent: {asc_sign} ({asc_deg:.2f}°)")

        # ----- TRANSIENTE PLANETEN FÜR DAS ZIEL-DATUM (für Aspekte) -----
        target_planets = calc_planet_positions(jd_target)
        aspects = calc_aspects(target_planets)
        print(f"🔮 Aspekte: {len(aspects)} gefunden")

        horoscope_parts = []
        sex_positions_data = []

        # System-Prompt in der gewünschten Sprache
        system_prompt = SYSTEM_PROMPTS.get(request.language, SYSTEM_PROMPTS["de"])

        for htype in request.horoscope_types:
            print(f"🔮 Generiere {htype}...")
            
            if htype in ["daily", "weekly", "love", "career", "health", "spiritual"]:
                prompt = build_prompt(
                    name=request.name,
                    sun=sun_sign,
                    moon=moon_sign,
                    asc=asc_sign,
                    birth_city=request.birth_city,
                    target_date=target_date,
                    gender=request.gender,
                    houses=houses,
                    aspects=aspects,
                    planets=target_planets,   # Für Transite verwenden wir die Ziel-Planeten
                    horoscope_type=htype,
                    language=request.language
                )
                print(f"📝 Prompt erstellt ({len(prompt)} Zeichen)")
                
                try:
                    print(f"🤖 Rufe DeepSeek auf...")
                    response = client.chat.completions.create(
                        model=LLM_MODEL,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.7,
                        max_tokens=3500
                    )
                    text = response.choices[0].message.content
                    horoscope_parts.append(f"## {htype.upper()}\n{text}")
                    print(f"✅ {htype} generiert ({len(text)} Zeichen)")
                except Exception as e:
                    print(f"❌ Fehler bei DeepSeek ({htype}): {str(e)}")
                    raise HTTPException(500, f"DeepSeek-Fehler bei {htype}: {str(e)}")

            elif htype == "sex" and request.partners:
                print(f"🔥 Generiere Sex-Horoskop für {len(request.partners)} Partner")
                # Hier könnte später die Sex-Logik eingefügt werden
                pass

            elif htype == "synastry" and request.partners:
                print(f"👥 Generiere Synastrie für {len(request.partners)} Partner")
                # Hier könnte später die Synastrie-Logik eingefügt werden
                pass

        full_horoscope = "\n\n---\n\n".join(horoscope_parts)
        print("✅ Horoskop erfolgreich erstellt")
        
        return HoroscopeResponse(
            horoscope=full_horoscope,
            sun_sign=sun_sign,
            moon_sign=moon_sign,
            ascendant=asc_sign,
            birth_city=request.birth_city,
            planets=target_planets,  # Für das Planetenrad im Frontend (Transite)
            sex_partner_positions=sex_positions_data if sex_positions_data else None
        )

    except HTTPException as e:
        print(f"❌ HTTP-Fehler: {e.detail}")
        raise e
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"❌ UNERWARTETER FEHLER:\n{error_detail}")
        raise HTTPException(500, detail=f"{str(e)}\n\n{error_detail}")

# ============================================================
# 8. START
# ============================================================
if __name__ == "__main__":
    import uvicorn
    print("🚀 Starte Server auf http://0.0.0.0:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)