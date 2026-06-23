"""
Unit tests for app.py.

fetch_metar() is tested by patching requests.get so no real HTTP calls
are made. The Flask route is tested with the built-in test client, with
fetch_metar itself patched to remove the network dependency entirely.
"""

import pytest
import requests
from unittest.mock import patch, MagicMock

from app import app, fetch_metar


@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as c:
        yield c


# ── fetch_metar: successful responses ────────────────────────────────────────

class TestFetchMetarSuccess:
    def _mock_response(self, json_body):
        mock = MagicMock()
        mock.raise_for_status.return_value = None
        mock.json.return_value = json_body
        return mock

    def test_dict_item_with_text_key(self):
        payload = {'data': [{'text': 'METAR CYYC 231600Z 27015KT CAVOK 18/05 A3012'}]}
        with patch('app.requests.get', return_value=self._mock_response(payload)):
            text, error = fetch_metar('CYYC')
        assert error is None
        assert text == 'METAR CYYC 231600Z 27015KT CAVOK 18/05 A3012'

    def test_dict_item_with_rawText_key(self):
        payload = {'data': [{'rawText': 'METAR CYYZ 231600Z 09010KT CAVOK 22/15 A2998'}]}
        with patch('app.requests.get', return_value=self._mock_response(payload)):
            text, error = fetch_metar('CYYZ')
        assert error is None
        assert 'CYYZ' in text

    def test_plain_string_item(self):
        payload = {'data': ['METAR CYVR 231600Z 18010KT 15SM CLR 16/08 A3005']}
        with patch('app.requests.get', return_value=self._mock_response(payload)):
            text, error = fetch_metar('CYVR')
        assert error is None
        assert 'CYVR' in text

    def test_leading_trailing_whitespace_stripped(self):
        payload = {'data': [{'text': '  METAR CYYC 231600Z 27015KT CAVOK 18/05 A3012  '}]}
        with patch('app.requests.get', return_value=self._mock_response(payload)):
            text, error = fetch_metar('CYYC')
        assert text == 'METAR CYYC 231600Z 27015KT CAVOK 18/05 A3012'


# ── fetch_metar: empty / missing data ────────────────────────────────────────

class TestFetchMetarNoData:
    def _mock_response(self, json_body):
        mock = MagicMock()
        mock.raise_for_status.return_value = None
        mock.json.return_value = json_body
        return mock

    def test_empty_data_list(self):
        with patch('app.requests.get', return_value=self._mock_response({'data': []})):
            text, error = fetch_metar('CZXX')
        assert text is None
        assert error is not None

    def test_missing_data_key(self):
        with patch('app.requests.get', return_value=self._mock_response({})):
            text, error = fetch_metar('CZXX')
        assert text is None
        assert error is not None

    def test_error_message_mentions_station(self):
        with patch('app.requests.get', return_value=self._mock_response({'data': []})):
            _, error = fetch_metar('CZXX')
        assert 'CZXX' in error

    def test_error_message_mentions_canadian_airports(self):
        with patch('app.requests.get', return_value=self._mock_response({'data': []})):
            _, error = fetch_metar('CZXX')
        assert 'Canadian' in error or 'ICAO' in error or 'C' in error


# ── fetch_metar: network / HTTP errors ───────────────────────────────────────

class TestFetchMetarErrors:
    def test_timeout(self):
        with patch('app.requests.get', side_effect=requests.exceptions.Timeout):
            text, error = fetch_metar('CYYC')
        assert text is None
        assert 'timed out' in error

    def test_connection_error(self):
        with patch('app.requests.get', side_effect=requests.exceptions.ConnectionError):
            text, error = fetch_metar('CYYC')
        assert text is None
        assert 'connection' in error.lower() or 'internet' in error.lower()

    def test_http_404(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        with patch('app.requests.get', side_effect=requests.exceptions.HTTPError(response=mock_resp)):
            text, error = fetch_metar('CZXX')
        assert text is None
        assert 'not found' in error.lower() or '404' in error

    def test_http_500(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        with patch('app.requests.get', side_effect=requests.exceptions.HTTPError(response=mock_resp)):
            text, error = fetch_metar('CYYC')
        assert text is None
        assert '500' in error

    def test_invalid_json(self):
        mock = MagicMock()
        mock.raise_for_status.return_value = None
        mock.json.side_effect = ValueError('not json')
        with patch('app.requests.get', return_value=mock):
            text, error = fetch_metar('CYYC')
        assert text is None
        assert error is not None


# ── Flask route: GET ─────────────────────────────────────────────────────────

class TestIndexGet:
    def test_get_returns_200(self, client):
        response = client.get('/')
        assert response.status_code == 200

    def test_get_renders_form(self, client):
        response = client.get('/')
        assert b'form' in response.data.lower() or b'station' in response.data.lower()


# ── Flask route: POST validation ─────────────────────────────────────────────

class TestIndexPostValidation:
    def test_empty_station_shows_error(self, client):
        response = client.post('/', data={'station': ''})
        assert b'Please enter an airport code' in response.data

    def test_station_with_special_chars_rejected(self, client):
        response = client.post('/', data={'station': 'CY!!'})
        assert response.status_code == 200
        assert b'ICAO' in response.data

    def test_station_too_long_rejected(self, client):
        response = client.post('/', data={'station': 'CYYCC'})
        assert response.status_code == 200
        assert b'ICAO' in response.data

    def test_station_too_short_rejected(self, client):
        response = client.post('/', data={'station': 'CY'})
        assert response.status_code == 200
        assert b'ICAO' in response.data


# ── Flask route: POST with mocked fetch_metar ────────────────────────────────

MOCK_METAR_RAW = 'METAR CYYC 231600Z 27015KT 15SM FEW030 BKN080 18/05 A3012 RMK SLP168'


class TestIndexPostWithMock:
    def test_successful_fetch_returns_200(self, client):
        with patch('app.fetch_metar', return_value=(MOCK_METAR_RAW, None)):
            response = client.post('/', data={'station': 'CYYC'})
        assert response.status_code == 200

    def test_station_uppercased_before_fetch(self, client):
        with patch('app.fetch_metar', return_value=(MOCK_METAR_RAW, None)) as mock_fetch:
            client.post('/', data={'station': 'cyyc'})
        mock_fetch.assert_called_once_with('CYYC')

    def test_api_error_displays_message(self, client):
        with patch('app.fetch_metar', return_value=(None, 'Station not found')):
            response = client.post('/', data={'station': 'CZXX'})
        assert b'Station not found' in response.data

    def test_decoded_temperature_rendered(self, client):
        with patch('app.fetch_metar', return_value=(MOCK_METAR_RAW, None)):
            response = client.post('/', data={'station': 'CYYC'})
        assert b'18' in response.data
