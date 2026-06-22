"""
METAR Reader — Flask web application.

Accepts a Canadian ICAO airport code, fetches the current METAR
observation from the Nav Canada weather API, decodes it with
metar_decoder, and renders a plain-English weather report.
"""

import re

from flask import Flask, render_template, request
import requests

from metar_decoder import decode_metar

app = Flask(__name__)

# Nav Canada public weather API — returns the latest METAR for a given site.
# Query parameters: site=<ICAO code>, alpha=metar
NAVCANADA_API = 'https://plan.navcanada.ca/weather/api/alpha/'


def fetch_metar(station_code: str) -> tuple[str | None, str | None]:
    """Fetch the raw METAR text for a station from the Nav Canada API.

    Args:
        station_code: 3–4 character ICAO airport identifier (e.g. "CYYC").

    Returns:
        A (raw_text, error_message) tuple. On success, raw_text is the
        METAR string and error_message is None. On failure, raw_text is
        None and error_message describes what went wrong.
    """
    try:
        response = requests.get(
            NAVCANADA_API,
            params={'site': station_code, 'alpha': 'metar'},
            timeout=10,
            headers={'User-Agent': 'METAR-Reader/1.0'},
        )
        response.raise_for_status()
        data = response.json()

        # The API returns {"data": [...]} where each item may be a dict
        # with a "text" key or, in older responses, a plain string.
        items = data.get('data') or []
        for item in items:
            if isinstance(item, dict):
                text = item.get('text') or item.get('rawText') or item.get('raw')
                if text:
                    return text.strip(), None
            elif isinstance(item, str) and item.strip():
                return item.strip(), None

        return None, (
            f'No METAR data found for {station_code}. '
            'This service covers Canadian airports '
            '(ICAO codes starting with C, e.g. CYYC, CYYZ, CYVR).'
        )

    except requests.exceptions.Timeout:
        return None, 'The weather service timed out. Please try again.'
    except requests.exceptions.ConnectionError:
        return None, 'Could not reach the weather service. Check your internet connection.'
    except requests.exceptions.HTTPError as e:
        code = e.response.status_code
        if code == 404:
            return None, f'Station {station_code} was not found. Verify the ICAO code.'
        return None, f'Weather service returned HTTP {code}. Please try again.'
    except (ValueError, KeyError):
        return None, 'Received unexpected data from the weather service.'


@app.route('/', methods=['GET', 'POST'])
def index():
    """Render the main page.

    GET:  Display the search form.
    POST: Validate the submitted airport code, fetch the METAR, decode
          it, and pass the structured result to the template.
    """
    metar = None
    error = None
    station = ''

    if request.method == 'POST':
        station = request.form.get('station', '').strip().upper()

        if not station:
            error = 'Please enter an airport code.'
        elif not re.match(r'^[A-Z0-9]{3,4}$', station):
            error = 'Enter a 3–4 character ICAO airport code (letters/numbers only).'
        else:
            raw, error = fetch_metar(station)
            if raw:
                metar = decode_metar(raw)

    return render_template('index.html', metar=metar, error=error, station=station)


if __name__ == '__main__':
    app.run(debug=True)
