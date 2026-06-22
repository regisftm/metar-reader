# ✈️ METAR Reader

A Flask web application that turns cryptic aviation weather reports (METARs) into plain-English summaries anyone can understand.

Type in a Canadian airport code and get back a friendly weather snapshot:
> *Mostly cloudy with light rain, 9°C (48°F), wind from the northwest at 15 mph gusting to 23 mph, visibility more than 10 miles.*

---

## What is a METAR?

A METAR (Meteorological Aerodrome Report) is a standardized weather observation issued every hour by airports around the world. They look like this:

```
METAR CYYC 221400Z 32013G20KT 20SM -RA BKN017 OVC050 09/06 A3015 RMK SC7SC1 SLP232=
```

This application decodes every token — wind direction and speed, visibility, sky coverage, temperature, dew point, and pressure — and presents it in a format that requires no aviation knowledge to read.

---

## Features

- **Live data** — fetches the most recent observation directly from the Nav Canada weather API
- **Full METAR decode** — wind (with gusts), visibility, sky layers, present weather (rain, snow, fog, etc.), temperature & dew point, and altimeter setting
- **Dual time display** — shows observation time in both UTC and your browser's local timezone
- **Clean card layout** — at-a-glance weather tiles plus a collapsible raw METAR string for reference
- **Graceful error handling** — clear messages for invalid codes, network errors, or stations with no data

---

## Requirements

- Python 3.10 or newer
- pip

---

## Installation

**1. Clone the repository**

```bash
git clone https://github.com/regisftm/metar-reader.git
cd metar-reader
```

**2. Create and activate a virtual environment**

```bash
python3 -m venv .venv
source .venv/bin/activate      # macOS / Linux
.venv\Scripts\activate         # Windows
```

**3. Install dependencies**

```bash
pip install -r requirements.txt
```

---

## Running the App

```bash
python app.py
```

Then open [http://127.0.0.1:5000](http://127.0.0.1:5000) in your browser.

---

## Usage

1. Enter a **4-letter ICAO airport code** in the search bar (e.g. `CYYC`, `CYYZ`, `CYVR`).
2. Press **Get Weather**.
3. Read the decoded weather report.

> **Note:** This app uses the Nav Canada weather API, which covers **Canadian airports only** — ICAO codes that begin with the letter `C`.

### Common Canadian airport codes

| Code | Airport |
|------|---------|
| CYYC | Calgary International |
| CYYZ | Toronto Pearson International |
| CYVR | Vancouver International |
| CYUL | Montréal-Trudeau International |
| CYOW | Ottawa Macdonald–Cartier International |
| CYWG | Winnipeg James Armstrong Richardson International |
| CYEG | Edmonton International |
| CYQB | Québec City Jean Lesage International |

---

## Project Structure

```
metar-reader/
├── app.py              # Flask routes and Nav Canada API integration
├── metar_decoder.py    # METAR string parser and plain-English generator
├── requirements.txt    # Python dependencies
└── templates/
    └── index.html      # Single-page UI with embedded CSS
```

---

## Data Source

Weather data is provided by [Nav Canada](https://www.navcanada.ca/) via their public aviation weather API. This application is intended for informational and educational purposes only — **not for operational flight planning or navigation**.

---

## License

MIT License — see [LICENSE](LICENSE) for details.
