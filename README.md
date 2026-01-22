# Webhook1 Developer Setup Guide

This project is a FastAPI-based webhook handler for processing solar panel leads.

## Prerequisites

- **Python 3.9+**
- **pip** (Python package installer)

## Installation

1.  **Clone the repository** (if you haven't already):
    ```bash
    git clone https://github.com/Kamillendampf/webhook
    cd Webhook1
    ```

2.  **Create and activate a virtual environment**:
    ```bash
    # Create the virtual environment
    python -m venv .venv
    
    # Activate on Windows
    .venv\Scripts\activate
    
    # Activate on MacOS/Linux
    source .venv/bin/activate
    ```

3.  **Install dependencies**:
    ```bash
    pip install fastapi uvicorn httpx
    ```
    
    *Optional: If you need to freeze dependencies later, run `pip freeze > requirements.txt`.*

## Running the Application

Start the local server using Uvicorn:

```bash
uvicorn main:app --reload
```

The server will be available at [http://127.0.0.1:8000](http://127.0.0.1:8000).

## Usage

### Webhook Endpoint

- **URL**: `/webhook`
- **Method**: `POST`
- **Content-Type**: `application/json`

### Example Request Body

```json
{
  "questions": {
    "Welche Dachform haben Sie auf Ihrem Haus?": "Satteldach",
    "Wie hoch schätzen Sie ihren Stromverbrauch?": "3500",
    "Sind Sie Eigentümer der Immobilie?": "Ja",
    "Wo möchten Sie die Solaranlage installieren?": "Einfamilienhaus",
    "Wie alt ist Ihr Dach?": "nach 1990",
    "Dachfläche": "60",
    "Dachmaterial": "Dachziegel",
    "Dachausrichtung": "Süd"
  },
  "zipcode": "66111",
  "city": "Saarbrücken",
  "first_name": "Test",
  "last_name": "User",
  "email": "test@example.com",
  "phone": "015112345678",
  "street": "Hauptstraße 10"
}
```

### Validation Logic

The application includes specific validation rules (see `_validate_body` in `main.py`):
1.  **Zipcode**: Must start with "66".
2.  **Owner**: Must answer "Ja" to "Sind Sie Eigentümer der Immobilie?".

If these conditions are not met, the webhook returns `{"message": "Contact not valid"}`.

## External Services

- The application sends processed leads to an external API (`https://contactapi.static.fyi/lead/receive/fake/haerle/`).
- `ngrok` is included in the project directory, potentially for exposing the local server to the internet.


