"""
Unit tests for metar_decoder.py.

Each test passes a synthetic METAR string (or calls a helper directly)
and asserts on the decoded output — no network calls, no external deps.
"""

import pytest

from metar_decoder import (
    decode_metar,
    _parse_temp,
    _to_mph,
    _format_vis_sm,
    _decode_weather_group,
    _decode_sky,
    _dominant_sky,
    _degrees_to_compass,
)


# ── Mock METAR strings ───────────────────────────────────────────────────────

TYPICAL = 'METAR CYYC 231600Z 27015KT 15SM FEW030 BKN080 18/05 A3012 RMK SLP168'
CAVOK   = 'METAR CYYZ 231600Z 09010KT CAVOK 22/15 A2998'
STORM   = 'METAR CYVR 231600Z 18020G35KT 3SM TSRA BKN030CB 15/14 A2985'
WINTER  = 'METAR CYEG 231600Z 00000KT 1SM -SN OVC010 M05/M08 A2990'
VRB     = 'METAR CYQR 231600Z VRB03KT P6SM SKC 10/04 A3020'
NIL     = 'METAR CZXX 231600Z NIL'
FOG     = 'METAR CYWG 231600Z 01010KT 1/4SM FG OVC002 01/01 A3005'
AUTO    = 'METAR CYKA 231600Z AUTO 21008KT 9SM SCT040 14/06 A3015'
METRIC  = 'METAR EGLL 231600Z 24012KT 9000 -RA FEW015 SCT025 12/10 Q1008'
VARWIND = 'METAR CYYJ 231600Z 32010KT 270V360 15SM FEW025 16/08 A3005'


# ── Helper: _degrees_to_compass ──────────────────────────────────────────────

class TestDegreesToCompass:
    def test_north(self):
        assert _degrees_to_compass(0) == 'N'

    def test_east(self):
        assert _degrees_to_compass(90) == 'E'

    def test_south(self):
        assert _degrees_to_compass(180) == 'S'

    def test_west(self):
        assert _degrees_to_compass(270) == 'W'

    def test_northeast(self):
        assert _degrees_to_compass(45) == 'NE'

    def test_northwest(self):
        assert _degrees_to_compass(315) == 'NW'


# ── Helper: _parse_temp ──────────────────────────────────────────────────────

class TestParseTemp:
    def test_positive(self):
        assert _parse_temp('18') == 18

    def test_zero(self):
        assert _parse_temp('00') == 0

    def test_negative(self):
        assert _parse_temp('M05') == -5

    def test_negative_double_digit(self):
        assert _parse_temp('M22') == -22


# ── Helper: _to_mph ──────────────────────────────────────────────────────────

class TestToMph:
    def test_knots(self):
        assert _to_mph(10, 'KT') == round(10 * 1.15078)

    def test_mps(self):
        assert _to_mph(10, 'MPS') == round(10 * 2.23694)

    def test_kmh(self):
        assert _to_mph(16, 'KMH') == round(16 * 0.621371)

    def test_zero_speed(self):
        assert _to_mph(0, 'KT') == 0


# ── Helper: _format_vis_sm ───────────────────────────────────────────────────

class TestFormatVisSm:
    def test_more_than_10_miles(self):
        assert 'excellent' in _format_vis_sm(10)
        assert 'excellent' in _format_vis_sm(15)

    def test_good_visibility(self):
        result = _format_vis_sm(7)
        assert 'good' in result

    def test_moderate_visibility(self):
        result = _format_vis_sm(4)
        assert 'moderate' in result

    def test_reduced_visibility(self):
        result = _format_vis_sm(1.5)
        assert 'reduced' in result

    def test_poor_visibility_in_feet(self):
        result = _format_vis_sm(0.25)
        assert 'feet' in result
        assert 'poor' in result
        assert '1,320' in result  # 0.25 * 5280 = 1320 ft


# ── Helper: _decode_weather_group ────────────────────────────────────────────

class TestDecodeWeatherGroup:
    def test_rain(self):
        assert _decode_weather_group('RA') == 'rain'

    def test_heavy_rain(self):
        assert _decode_weather_group('+RA') == 'heavy rain'

    def test_light_snow(self):
        assert _decode_weather_group('-SN') == 'light snow'

    def test_thunderstorm_rain(self):
        assert _decode_weather_group('TSRA') == 'thunderstorm rain'

    def test_freezing_fog(self):
        assert _decode_weather_group('FZFG') == 'freezing fog'

    def test_shower_rain(self):
        assert _decode_weather_group('SHRA') == 'shower rain'

    def test_nearby_fog(self):
        assert _decode_weather_group('VCFG') == 'nearby fog'

    def test_heavy_thunderstorm_rain(self):
        assert _decode_weather_group('+TSRA') == 'heavy thunderstorm rain'

    def test_blowing_snow(self):
        assert _decode_weather_group('BLSN') == 'blowing snow'


# ── Helper: _decode_sky ──────────────────────────────────────────────────────

class TestDecodeSky:
    def test_clear(self):
        result = _decode_sky('CLR')
        assert result['coverage'] == 'clear'
        assert result['height_ft'] is None

    def test_few_clouds_with_height(self):
        result = _decode_sky('FEW020')
        assert result['coverage'] == 'few'
        assert result['height_ft'] == 2000

    def test_scattered_clouds(self):
        result = _decode_sky('SCT040')
        assert result['coverage'] == 'scattered'
        assert result['height_ft'] == 4000

    def test_broken_clouds(self):
        result = _decode_sky('BKN080')
        assert result['coverage'] == 'broken'
        assert result['height_ft'] == 8000

    def test_overcast(self):
        result = _decode_sky('OVC010')
        assert result['coverage'] == 'overcast'
        assert result['height_ft'] == 1000

    def test_cumulonimbus(self):
        result = _decode_sky('BKN030CB')
        assert result['coverage'] == 'broken'
        assert 'cumulonimbus' in result['description']

    def test_towering_cumulus(self):
        result = _decode_sky('FEW025TCU')
        assert 'towering cumulus' in result['description']

    def test_sky_obscured(self):
        result = _decode_sky('VV005')
        assert result['coverage'] == 'obscured'
        assert result['height_ft'] == 500

    def test_invalid_token(self):
        result = _decode_sky('INVALID')
        assert result['coverage'] == 'unknown'


# ── Helper: _dominant_sky ────────────────────────────────────────────────────

class TestDominantSky:
    def test_empty_list(self):
        assert _dominant_sky([]) == 'unknown'

    def test_single_clear(self):
        assert _dominant_sky([{'coverage': 'clear'}]) == 'clear'

    def test_broken_beats_scattered(self):
        skies = [{'coverage': 'scattered'}, {'coverage': 'broken'}]
        assert _dominant_sky(skies) == 'broken'

    def test_overcast_beats_all(self):
        skies = [{'coverage': 'few'}, {'coverage': 'scattered'}, {'coverage': 'overcast'}]
        assert _dominant_sky(skies) == 'overcast'

    def test_obscured_is_worst(self):
        skies = [{'coverage': 'overcast'}, {'coverage': 'obscured'}]
        assert _dominant_sky(skies) == 'obscured'


# ── decode_metar: typical clear-day observation ──────────────────────────────

class TestDecodeMetarTypical:
    def setup_method(self):
        self.result = decode_metar(TYPICAL)

    def test_station(self):
        assert self.result['station'] == 'CYYC'

    def test_time(self):
        assert self.result['time'] == '16:00 UTC'

    def test_wind_speed_mph(self):
        assert self.result['wind_speed_mph'] == round(15 * 1.15078)

    def test_wind_direction_contains_west(self):
        assert 'west' in self.result['wind_direction']

    def test_wind_text_present(self):
        assert self.result['wind'] is not None
        assert 'mph' in self.result['wind']

    def test_visibility(self):
        assert 'excellent' in self.result['visibility']

    def test_temperature_c(self):
        assert self.result['temperature_c'] == 18

    def test_temperature_f(self):
        assert self.result['temperature_f'] == round(18 * 9 / 5 + 32)

    def test_dewpoint_c(self):
        assert self.result['dewpoint_c'] == 5

    def test_altimeter_inhg(self):
        assert self.result['altimeter'] == '30.12 inHg'

    def test_remarks(self):
        assert self.result['remarks'] == 'SLP168'

    def test_sky_layer_count(self):
        assert len(self.result['sky']) == 2

    def test_dominant_sky_is_broken(self):
        assert self.result['sky_summary'] == 'Mostly cloudy'

    def test_no_weather_phenomena(self):
        assert self.result['weather'] == []

    def test_summary_includes_temperature(self):
        assert '18°C' in self.result['summary']

    def test_auto_is_false(self):
        assert self.result['auto'] is False


# ── decode_metar: CAVOK ──────────────────────────────────────────────────────

class TestDecodeMetarCAVOK:
    def setup_method(self):
        self.result = decode_metar(CAVOK)

    def test_visibility_excellent(self):
        assert 'excellent' in self.result['visibility']

    def test_sky_summary_clear(self):
        assert self.result['sky_summary'] == 'Clear skies'

    def test_no_weather_phenomena(self):
        assert self.result['weather'] == []

    def test_altimeter_inhg(self):
        assert self.result['altimeter'] == '29.98 inHg'


# ── decode_metar: thunderstorm with gusts ────────────────────────────────────

class TestDecodeMetarThunderstorm:
    def setup_method(self):
        self.result = decode_metar(STORM)

    def test_gust_parsed(self):
        assert self.result['wind_gust_mph'] == round(35 * 1.15078)

    def test_wind_text_includes_gusting(self):
        assert 'gusting' in self.result['wind']

    def test_thunderstorm_in_weather(self):
        assert any('thunderstorm' in w for w in self.result['weather'])

    def test_rain_in_weather(self):
        assert any('rain' in w for w in self.result['weather'])

    def test_storm_icon(self):
        assert self.result['sky_icon'] == '⛈️'

    def test_cumulonimbus_in_sky_description(self):
        assert any('cumulonimbus' in s['description'] for s in self.result['sky'])


# ── decode_metar: winter / negative temps / calm / snow ─────────────────────

class TestDecodeMetarWinter:
    def setup_method(self):
        self.result = decode_metar(WINTER)

    def test_calm_wind(self):
        assert self.result['wind'] == 'Calm — no wind'
        assert self.result['wind_direction'] == 'calm'

    def test_negative_temperature(self):
        assert self.result['temperature_c'] == -5

    def test_negative_dewpoint(self):
        assert self.result['dewpoint_c'] == -8

    def test_snow_in_weather(self):
        assert any('snow' in w for w in self.result['weather'])

    def test_light_snow(self):
        assert any('light' in w for w in self.result['weather'])

    def test_reduced_visibility(self):
        assert 'reduced' in self.result['visibility']

    def test_overcast_sky(self):
        assert self.result['sky_summary'] == 'Overcast'

    def test_snow_icon(self):
        assert self.result['sky_icon'] == '🌨️'


# ── decode_metar: variable wind ──────────────────────────────────────────────

class TestDecodeMetarVariableWind:
    def setup_method(self):
        self.result = decode_metar(VRB)

    def test_wind_direction_variable(self):
        assert self.result['wind_direction'] == 'variable direction'

    def test_clear_sky(self):
        assert self.result['sky_summary'] == 'Clear skies'

    def test_p6sm_excellent_visibility(self):
        assert 'excellent' in self.result['visibility']


# ── decode_metar: variable wind range (dddVddd) ──────────────────────────────

class TestDecodeMetarVariableRange:
    def setup_method(self):
        self.result = decode_metar(VARWIND)

    def test_variable_range_appended_to_wind(self):
        assert 'varying between' in self.result['wind']

    def test_wind_speed_parsed(self):
        assert self.result['wind_speed_mph'] == round(10 * 1.15078)


# ── decode_metar: NIL report ─────────────────────────────────────────────────

class TestDecodeMetarNIL:
    def test_nil_summary(self):
        result = decode_metar(NIL)
        assert result['summary'] == 'No observation available (NIL report).'

    def test_nil_returns_early_no_wind(self):
        result = decode_metar(NIL)
        assert result['wind'] is None


# ── decode_metar: fog / fractional visibility ────────────────────────────────

class TestDecodeMetarFog:
    def setup_method(self):
        self.result = decode_metar(FOG)

    def test_fractional_visibility_in_feet(self):
        assert 'feet' in self.result['visibility']
        assert 'poor' in self.result['visibility']

    def test_fog_in_weather(self):
        assert any('fog' in w for w in self.result['weather'])

    def test_fog_icon(self):
        assert self.result['sky_icon'] == '🌫️'

    def test_overcast_low_ceiling(self):
        assert self.result['sky'][0]['height_ft'] == 200


# ── decode_metar: AUTO flag ──────────────────────────────────────────────────

class TestDecodeMetarAuto:
    def test_auto_flag_set(self):
        result = decode_metar(AUTO)
        assert result['auto'] is True

    def test_auto_station_still_parsed(self):
        result = decode_metar(AUTO)
        assert result['station'] == 'CYKA'


# ── decode_metar: metric visibility (ICAO format) ────────────────────────────

class TestDecodeMetarMetric:
    def setup_method(self):
        self.result = decode_metar(METRIC)

    def test_metric_visibility_km(self):
        assert 'km' in self.result['visibility']
        assert '9.0' in self.result['visibility']

    def test_qnh_hpa(self):
        assert self.result['altimeter'] == '1008 hPa'

    def test_light_rain_detected(self):
        assert any('rain' in w for w in self.result['weather'])
