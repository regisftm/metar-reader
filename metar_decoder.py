import re
from typing import Optional, Dict, Any, List


def _degrees_to_compass(degrees: int) -> str:
    directions = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE',
                  'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW']
    return directions[round(degrees / 22.5) % 16]


COMPASS_WORDS = {
    'N': 'north', 'NNE': 'north-northeast', 'NE': 'northeast',
    'ENE': 'east-northeast', 'E': 'east', 'ESE': 'east-southeast',
    'SE': 'southeast', 'SSE': 'south-southeast', 'S': 'south',
    'SSW': 'south-southwest', 'SW': 'southwest', 'WSW': 'west-southwest',
    'W': 'west', 'WNW': 'west-northwest', 'NW': 'northwest',
    'NNW': 'north-northwest',
}

WEATHER_DESCRIPTORS = {
    'MI': 'shallow', 'PR': 'partial', 'BC': 'patchy',
    'DR': 'drifting', 'BL': 'blowing', 'SH': 'shower',
    'TS': 'thunderstorm', 'FZ': 'freezing',
}

WEATHER_PHENOMENA = {
    'DZ': 'drizzle', 'RA': 'rain', 'SN': 'snow', 'SG': 'snow grains',
    'IC': 'ice crystals', 'PL': 'ice pellets', 'GR': 'hail',
    'GS': 'small hail', 'UP': 'unknown precipitation',
    'BR': 'mist', 'FG': 'fog', 'FU': 'smoke', 'VA': 'volcanic ash',
    'DU': 'dust', 'SA': 'sand', 'HZ': 'haze', 'PY': 'spray',
    'PO': 'dust/sand whirls', 'SQ': 'squalls', 'FC': 'funnel cloud',
    'SS': 'sandstorm', 'DS': 'dust storm',
}

SKY_COVERAGE = {
    'CLR': ('clear', 'clear'),
    'SKC': ('clear', 'clear'),
    'NSC': ('no significant clouds', 'clear'),
    'NCD': ('no clouds detected', 'clear'),
    'FEW': ('a few clouds', 'few'),
    'SCT': ('scattered clouds', 'scattered'),
    'BKN': ('broken clouds', 'broken'),
    'OVC': ('overcast', 'overcast'),
    'VV': ('sky obscured', 'obscured'),
}

SKY_SUMMARY = {
    'clear': 'Clear skies',
    'few': 'Mostly clear',
    'scattered': 'Partly cloudy',
    'broken': 'Mostly cloudy',
    'overcast': 'Overcast',
    'obscured': 'Sky obscured',
}

SKY_ICON = {
    'clear': '☀️',
    'few': '🌤️',
    'scattered': '⛅',
    'broken': '🌥️',
    'overcast': '☁️',
    'obscured': '🌫️',
}

COVERAGE_ORDER = ['obscured', 'overcast', 'broken', 'scattered', 'few', 'clear']


def _parse_temp(s: str) -> int:
    return -int(s[1:]) if s.startswith('M') else int(s)


def _to_mph(speed: int, unit: str) -> int:
    if unit == 'KT':
        return round(speed * 1.15078)
    if unit == 'MPS':
        return round(speed * 2.23694)
    return round(speed * 0.621371)  # KMH


def _format_vis_sm(miles: float) -> str:
    if miles >= 10:
        return f'More than 10 miles — excellent visibility'
    elif miles >= 6:
        return f'{miles:.0f} miles — good visibility'
    elif miles >= 3:
        return f'{miles:.1f} miles — moderate visibility'
    elif miles >= 1:
        return f'{miles:.1f} miles — reduced visibility'
    else:
        feet = int(miles * 5280)
        return f'{feet:,} feet — poor visibility'


def _decode_weather_group(token: str) -> str:
    parts = []
    t = token

    if t.startswith('+'):
        parts.append('heavy')
        t = t[1:]
    elif t.startswith('-'):
        parts.append('light')
        t = t[1:]
    elif t.startswith('VC'):
        parts.append('nearby')
        t = t[2:]

    for code, word in WEATHER_DESCRIPTORS.items():
        if t.startswith(code):
            parts.append(word)
            t = t[len(code):]
            break

    while t:
        matched = False
        for code, word in WEATHER_PHENOMENA.items():
            if t.startswith(code):
                parts.append(word)
                t = t[len(code):]
                matched = True
                break
        if not matched:
            parts.append(t)
            break

    return ' '.join(parts)


def _weather_icon(phenomena: List[str]) -> str:
    combined = ' '.join(phenomena).lower()
    if 'thunderstorm' in combined:
        return '⛈️'
    if 'snow' in combined or 'ice pellets' in combined or 'small hail' in combined or 'hail' in combined:
        return '🌨️'
    if 'rain' in combined or 'drizzle' in combined:
        return '🌧️'
    if 'fog' in combined or 'mist' in combined:
        return '🌫️'
    if 'smoke' in combined or 'haze' in combined or 'dust' in combined or 'sand' in combined:
        return '😶‍🌫️'
    return '🌦️'


def _decode_sky(token: str) -> Dict:
    m = re.match(r'^(VV|CLR|SKC|NSC|NCD|FEW|SCT|BKN|OVC)(\d{3})?(CB|TCU)?$', token)
    if not m:
        return {'raw': token, 'description': token, 'coverage': 'unknown'}

    code = m.group(1)
    height_code = m.group(2)
    cloud_type = m.group(3)

    desc, level = SKY_COVERAGE.get(code, (code, 'unknown'))
    height_ft = int(height_code) * 100 if height_code else None

    text = desc.capitalize()
    if height_ft is not None:
        text += f' at {height_ft:,} ft'
    if cloud_type == 'CB':
        text += ' (cumulonimbus — storm clouds)'
    elif cloud_type == 'TCU':
        text += ' (towering cumulus)'

    return {'raw': token, 'description': text, 'coverage': level, 'height_ft': height_ft}


def _dominant_sky(sky_conditions: List[Dict]) -> str:
    if not sky_conditions:
        return 'unknown'
    worst = 'clear'
    for sky in sky_conditions:
        cov = sky.get('coverage', 'clear')
        if cov in COVERAGE_ORDER:
            if COVERAGE_ORDER.index(cov) < COVERAGE_ORDER.index(worst):
                worst = cov
    return worst


def decode_metar(raw_text: str) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        'raw': raw_text.strip(),
        'station': None,
        'time': None,
        'auto': False,
        'wind': None,
        'wind_speed_mph': None,
        'wind_gust_mph': None,
        'wind_direction': None,
        'visibility': None,
        'weather': [],
        'sky': [],
        'sky_summary': 'Unknown',
        'sky_icon': '☁️',
        'temperature_c': None,
        'temperature_f': None,
        'dewpoint_c': None,
        'dewpoint_f': None,
        'altimeter': None,
        'remarks': None,
        'summary': None,
        'summary_icon': '🌡️',
    }

    tokens = raw_text.strip().split()
    idx = 0

    if idx < len(tokens) and tokens[idx] in ('METAR', 'SPECI'):
        idx += 1

    # Station ID
    if idx < len(tokens) and re.match(r'^[A-Z0-9]{3,4}$', tokens[idx]):
        result['station'] = tokens[idx]
        idx += 1

    # Timestamp DDHHmmZ
    if idx < len(tokens):
        m = re.match(r'^(\d{2})(\d{2})(\d{2})Z$', tokens[idx])
        if m:
            day, hour, minute = int(m.group(1)), int(m.group(2)), int(m.group(3))
            result['time'] = f'{hour:02d}:{minute:02d} UTC'
            result['time_day'] = day
            result['time_utc_hour'] = hour
            result['time_utc_minute'] = minute
            idx += 1

    # AUTO / COR
    while idx < len(tokens) and tokens[idx] in ('AUTO', 'COR', 'NIL'):
        if tokens[idx] == 'AUTO':
            result['auto'] = True
        if tokens[idx] == 'NIL':
            result['summary'] = 'No observation available (NIL report).'
            return result
        idx += 1

    # Wind: dddssKT or VRBssKT or dddssGggKT
    if idx < len(tokens):
        m = re.match(r'^(VRB|\d{3})(\d{2,3})(G(\d{2,3}))?(KT|MPS|KMH)$', tokens[idx])
        if m:
            direction_raw = m.group(1)
            speed = int(m.group(2))
            gust = int(m.group(4)) if m.group(4) else None
            unit = m.group(5)
            speed_mph = _to_mph(speed, unit)
            gust_mph = _to_mph(gust, unit) if gust else None
            result['wind_speed_mph'] = speed_mph
            result['wind_gust_mph'] = gust_mph

            if direction_raw == 'VRB':
                result['wind_direction'] = 'variable direction'
                dir_text = 'from a variable direction'
            elif speed == 0:
                result['wind_direction'] = 'calm'
                dir_text = None
            else:
                deg = int(direction_raw)
                compass = _degrees_to_compass(deg)
                direction_word = COMPASS_WORDS.get(compass, compass)
                result['wind_direction'] = direction_word
                dir_text = f'from the {direction_word} ({deg}°)'

            if speed == 0:
                result['wind'] = 'Calm — no wind'
            elif gust:
                result['wind'] = f'Wind {dir_text}, {speed_mph} mph, gusting to {gust_mph} mph'
            else:
                result['wind'] = f'Wind {dir_text}, {speed_mph} mph'

            idx += 1

            # Variable direction range: dddVddd
            if idx < len(tokens) and re.match(r'^\d{3}V\d{3}$', tokens[idx]):
                vm = re.match(r'^(\d{3})V(\d{3})$', tokens[idx])
                low = COMPASS_WORDS.get(_degrees_to_compass(int(vm.group(1))), '')
                high = COMPASS_WORDS.get(_degrees_to_compass(int(vm.group(2))), '')
                result['wind'] += f', varying between {low} and {high}'
                idx += 1

    # CAVOK
    if idx < len(tokens) and tokens[idx] == 'CAVOK':
        result['visibility'] = 'More than 10 km — excellent visibility'
        result['sky'] = [{'raw': 'CAVOK', 'description': 'No significant clouds below 5,000 ft', 'coverage': 'clear'}]
        result['sky_summary'] = 'Clear skies'
        result['sky_icon'] = SKY_ICON.get('clear', '☀️')
        idx += 1
    else:
        # Visibility
        if idx < len(tokens):
            token = tokens[idx]
            vis_miles = None

            if token == 'P6SM':
                result['visibility'] = 'More than 6 miles — excellent visibility'
                idx += 1
            elif re.match(r'^\d+SM$', token):
                vis_miles = int(re.match(r'^(\d+)SM$', token).group(1))
                result['visibility'] = _format_vis_sm(vis_miles)
                idx += 1
            elif re.match(r'^\d+/\d+SM$', token):
                pm = re.match(r'^(\d+)/(\d+)SM$', token)
                vis_miles = int(pm.group(1)) / int(pm.group(2))
                result['visibility'] = _format_vis_sm(vis_miles)
                idx += 1
            elif (re.match(r'^\d+$', token)
                  and idx + 1 < len(tokens)
                  and re.match(r'^\d+/\d+SM$', tokens[idx + 1])):
                whole = int(token)
                pm = re.match(r'^(\d+)/(\d+)SM$', tokens[idx + 1])
                vis_miles = whole + int(pm.group(1)) / int(pm.group(2))
                result['visibility'] = _format_vis_sm(vis_miles)
                idx += 2
            elif token == '9999':
                result['visibility'] = 'More than 10 km — excellent visibility'
                idx += 1
            elif re.match(r'^\d{4}$', token):
                vis_m = int(token)
                if vis_m >= 9999:
                    result['visibility'] = 'More than 10 km — excellent visibility'
                elif vis_m >= 5000:
                    result['visibility'] = f'{vis_m / 1000:.1f} km — good visibility'
                elif vis_m >= 1000:
                    result['visibility'] = f'{vis_m / 1000:.1f} km — reduced visibility'
                else:
                    result['visibility'] = f'{vis_m} m — very poor visibility'
                idx += 1

        # Present weather
        wx_re = re.compile(
            r'^(\+|-|VC)?(MI|PR|BC|DR|BL|SH|TS|FZ)?'
            r'(DZ|RA|SN|SG|IC|PL|GR|GS|UP|BR|FG|FU|VA|DU|SA|HZ|PY|PO|SQ|FC|SS|DS)+'
            r'$'
        )
        while idx < len(tokens) and wx_re.match(tokens[idx]):
            result['weather'].append(_decode_weather_group(tokens[idx]))
            idx += 1

        # Sky conditions
        sky_re = re.compile(r'^(VV|CLR|SKC|NSC|NCD|FEW|SCT|BKN|OVC)(\d{3})?(CB|TCU)?$')
        while idx < len(tokens) and sky_re.match(tokens[idx]):
            result['sky'].append(_decode_sky(tokens[idx]))
            idx += 1

        dominant = _dominant_sky(result['sky'])
        result['sky_summary'] = SKY_SUMMARY.get(dominant, 'Variable cloudiness')
        result['sky_icon'] = SKY_ICON.get(dominant, '☁️')

    # Temperature / Dew point
    if idx < len(tokens):
        m = re.match(r'^(M?\d+)/(M?\d+)$', tokens[idx])
        if m:
            temp_c = _parse_temp(m.group(1))
            dew_c = _parse_temp(m.group(2))
            result['temperature_c'] = temp_c
            result['temperature_f'] = round(temp_c * 9 / 5 + 32)
            result['dewpoint_c'] = dew_c
            result['dewpoint_f'] = round(dew_c * 9 / 5 + 32)
            idx += 1

    # Altimeter
    if idx < len(tokens):
        m_a = re.match(r'^A(\d{4})$', tokens[idx])
        m_q = re.match(r'^Q(\d{4})$', tokens[idx])
        if m_a:
            result['altimeter'] = f'{int(m_a.group(1)) / 100:.2f} inHg'
            idx += 1
        elif m_q:
            result['altimeter'] = f'{m_q.group(1)} hPa'
            idx += 1

    # Remarks
    if idx < len(tokens) and tokens[idx] == 'RMK':
        result['remarks'] = ' '.join(tokens[idx + 1:])

    # Override sky icon if weather phenomena present
    if result['weather']:
        result['sky_icon'] = _weather_icon(result['weather'])

    result['summary'] = _build_summary(result)
    return result


def _build_summary(r: Dict) -> str:
    parts = []

    sky = r.get('sky_summary', '')
    if sky and sky != 'Unknown':
        parts.append(sky)

    wx = r.get('weather', [])
    if wx:
        parts.append('with ' + ', '.join(wx))

    temp_c = r.get('temperature_c')
    temp_f = r.get('temperature_f')
    if temp_c is not None:
        parts.append(f'{temp_c}°C ({temp_f}°F)')

    wind = r.get('wind')
    if wind:
        parts.append(wind[0].lower() + wind[1:])

    vis = r.get('visibility')
    if vis:
        parts.append(f'visibility {vis[0].lower() + vis[1:]}')

    return ', '.join(parts) if parts else 'Weather observation decoded successfully.'
