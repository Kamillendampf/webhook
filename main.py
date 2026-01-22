import logging
import re
from typing import Optional

import httpx
from fastapi import FastAPI, Request

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)
app = FastAPI()

INVALID = {"message": "Contact not valid"}

# Because there is only this one product supported by the task
PRODUCT_NAME = "Solaranlagen"

#Questions
Q_ROOF_TYPE = "Welche Dachform haben Sie auf Ihrem Haus?"
Q_CONSUMPTION = "Wie hoch schätzen Sie ihren Stromverbrauch?"
Q_OWNER = "Sind Sie Eigentümer der Immobilie?"
Q_PROPERTY_TYPE = "Wo möchten Sie die Solaranlage installieren?"
Q_ROOF_AGE = "Wie alt ist Ihr Dach?"
Q_ROOF_AREA = "Dachfläche"
Q_ROOF_MATERIAL = "Dachmaterial"
Q_ORIENTATION = "Dachausrichtung"
Q_STORAGE = "Stromspeicher gewünscht"

#Number Validation
_FIRST_NUMBER_RE = re.compile(r"(\d+(?:[.,]\d+)?)")

FAKE_CUSTOMER_TOKEN = 'FakeCustomerToken'
URL = 'https://contactapi.static.fyi/lead/receive/fake/haerle/'

def _clean(text: str) -> str:
    return text.strip()


def _as_numeric(s: str) -> Optional[str]:
    s = _clean(s)
    if not s:
        return None
    if s.isdigit():
        s = s.replace(".", "").replace(",", ".")
        return s
    return None


def _split_street_housnumber(street_number: str):
    s = (_clean(street_number) or "")
    if not s:
        return "", None
    parts = s.split()
    if len(parts) >= 2 and re.match(r"^\d", parts[-1]):
        return " ".join(parts[:-1]), parts[-1]
    return s, None


def _normalize_property_type(property_type: str) -> str:
    allowed = {
        "Einfamilienhaus", "Zweifamilienhaus", "Mehrfamilienhaus", "Firmengebäude", "Freilandfläche",
        "Garage", "Carport", "Scheune/Landwirtschaft", "Lagerhalle", "Industrie"
    }
    raw = _clean(property_type).lower()
    if not raw:
        return ""

    if raw in allowed:
        return raw

    if "hallen" in raw or "hallenbauten" in raw or "gewerbeobjekt" in raw:
        return "Lagerhalle"
    if "firma" in raw or "büro" in raw:
        return "Firmengebäude"
    if "industrie" in raw:
        return "Industrie"
    if "ein" in raw and "zwei" in raw:
        return "Einfamilienhaus"

    return ""

def _normalize_roof_age(v: str) -> Optional[str]:
    raw = _clean(v)
    s = raw.lower()
    if not s:
        return None

    # wenn schon "offiziell" geliefert wird
    if raw in {"Erst in Planung", "Gerade erst gebaut", "Jünger als 30 Jahre", "Älter als 30 Jahre"}:
        return raw

    # Beispiele aus deinem Input
    if "nach 1990" in s:
        return "Jünger als 30 Jahre"
    if "vor 1990" in s:
        return "Älter als 30 Jahre"
    if "fast neu" in s or s == "neu":
        return "Gerade erst gebaut"

    return None

def _normalize_roof_material(v: str) -> Optional[str]:
    raw = _clean(v)
    s = raw.lower()
    if not s:
        return None


    if s == "blech":
        return "Blech/Trapezblech"
    if s == "dachziegel":
        return "Dachziegel"


    return raw

def _normalize_orientation(v: str) -> Optional[str]:
    raw = _clean(v)
    if not raw:
        return None


    mapping = {
        "sued": "Süd",
        "süd": "Süd",
        "sued-ost": "Süd-Ost",
        "sued-west": "Süd-West",
    }
    key = raw.lower().replace(" ", "")
    return mapping.get(key, raw)

def _yes_no_storage(v: str) -> Optional[str]:
    s = _clean(v).lower()
    if not s:
        return None
    if s in {"ja", "true", "1", "yes", "y"}:
        return "Ja"
    if s in {"nein", "false", "0", "no", "n"}:
        return "Nein"
    if "nicht sicher" in s or "unsicher" in s:
        return "Noch nicht sicher"
    # falls es schon korrekt ist
    if v in {"Ja", "Nein", "Noch nicht sicher"}:
        return v
    return None

def _lead_mapper(body) -> dict[str, any]:
    street_number = _split_street_housnumber(body.get("street"))
    lead: dict[str, any] = {
        "first_name": body.get("first_name"),
        "last_name": body.get("last_name"),
        "email": body.get("email"),
        "phone": re.sub(r"[^\d+]", "", (body.get("phone") or "")),
        "street": street_number[0] or None,
        "housnumber": street_number[1] or None,
        "postcode": _clean(str(body.get("zipcode"))),
        "city": body.get("city"),
        "country": "de",
    }

    lead = {k: v for k, v in lead.items() if v not in (None, "", [])}
    return lead


def _product_mapper():
    return {'name': PRODUCT_NAME}


def _lead_attribut_mapper(questions):
    lead_attributs = {}
    if Q_ROOF_TYPE in questions:
        roof_type = _clean(questions[Q_ROOF_TYPE])
        if roof_type:
            lead_attributs['solar_roof_type'] = roof_type

    if Q_CONSUMPTION in questions:
        consumption = _clean(questions[Q_CONSUMPTION])
        if consumption:
            lead_attributs['solar_energy_consumption'] = consumption

    if Q_OWNER in questions:
        lead_attributs['owner'] = "Ja"  # It`s not necessary to normalize because there are only house owners allowed

    if Q_PROPERTY_TYPE in questions:
        prob = _normalize_property_type(questions[Q_PROPERTY_TYPE])
        if prob:
            lead_attributs['solar_property_type'] = prob

    if Q_ROOF_AGE in questions:
        age =  _normalize_roof_age(questions.get(Q_ROOF_AGE))
        if age:
            lead_attributs['solar_roof_age'] = age

    if Q_ROOF_AREA in questions:
        area = _as_numeric(questions.get(Q_ROOF_AREA))
        if area is not None:
            lead_attributs["solar_area"] = area

    if Q_ROOF_MATERIAL in questions:
        material = _normalize_roof_material(questions.get(Q_ROOF_MATERIAL))
        if material:
            lead_attributs["solar_roof_material"] = material

    if Q_ORIENTATION in questions:
        orientation = _normalize_orientation(questions.get(Q_ORIENTATION))
        if orientation:
            lead_attributs["solar_south_location"] = orientation

    if Q_STORAGE in questions:
        storage = _yes_no_storage(questions.get(Q_STORAGE))
        if storage:
            lead_attributs["solar_power_storage"] = storage

    return lead_attributs

def _build_response(body):
    return {
        'lead' : _lead_mapper(body),
        'product' : _product_mapper(),
        'lead_attributes' : _lead_attribut_mapper(body),
    }

def _validate_body(res_body: dict) -> bool:
    questions = res_body['questions']
    if _clean(res_body['zipcode']).startswith("66") and (
            'Sind Sie Eigentümer der Immobilie?' in questions and _clean(questions[
                                                                             'Sind Sie Eigentümer der Immobilie?']) in [
                "Ja", "ja" "True", "true"]):
        logging.info("Contact is valid: %s", res_body)
        return True
    else:
        logging.info("Contact is invalid: %s", res_body)
    return False

async def send_response(body):
    headers = {
        "Authorization": f"Bearer {FAKE_CUSTOMER_TOKEN}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=5000) as client:
        resp = await client.post(url=URL, json=body, headers=headers)

        if resp.status_code >= 400:
            logging.error( f"Customer API Fehler: {resp.status_code} - {resp.text}")
        else:
            logging.info("Customer was successfully created")

@app.post("/webhook")
async def webhook(request: Request):

    
    leads = []
    res_body = await request.json()

    # validat single leads or multiple leads request
    if type(res_body) == dict:
        length = 1
    else:
        length = len(res_body)

    if length == 1:
        if _validate_body(res_body):
            leads = _build_response(body=res_body)
            await send_response(leads)
        else:
            return INVALID
    else:
        for element in res_body:
            if _validate_body(element):
                leads.append(_build_response(body=element))
            await send_response(leads)

