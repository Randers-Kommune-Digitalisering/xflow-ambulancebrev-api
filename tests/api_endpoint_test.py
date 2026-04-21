import base64

import pytest

from unittest.mock import patch

from main import create_app
import api_endpoints as api_endpoints_module


@pytest.fixture()
def app():
    app = create_app()
    app.config.update({
        "TESTING": True,
    })
    yield app


@pytest.fixture()
def client(app):
    return app.test_client()


@patch('api_endpoints.sbsys_client.journalize')
@patch('api_endpoints.sbsys_client.get_personalesag')
@patch('api_endpoints.sbsys_client.get_delforloeb')
def test_journaliser_success(mock_get_delforloeb, mock_get_personalesag, mock_journalize, client, monkeypatch):
    mock_get_personalesag.return_value = [
        {
            'Id': 123,
            'Nummer': 'SAG-1',
            'SagsStatus': {'Id': api_endpoints_module.SBSYS_SAG_STATUS_ACTIVE_TEST},
        }
    ]
    mock_get_delforloeb.return_value = []
    mock_journalize.return_value = {'Filer': [{'ShortId': 7050}]}

    pdf_bytes = b'%PDF-1.4\n%\xe2\xe3\xcf\xd3\n1 0 obj\n<<>>\nendobj\n%%EOF\n'
    data_b64 = base64.b64encode(pdf_bytes).decode('ascii')

    response = client.post('/api/journaliser', json={'user': 'Test User - dq1', 'data': data_b64})

    assert response.status_code == 200
    assert b'Document journalized successfully' in response.data
    mock_journalize.assert_called_once()


def test_journaliser_missing_fields(client):
    response = client.post('/api/journaliser', json={'user': 'Test User - dq1'})
    assert response.status_code == 400
    assert b"Invalid payload: 'user' and 'data' fields are required." == response.data


def test_journaliser_invalid_base64(client):
    response = client.post('/api/journaliser', json={'user': 'Test User - dq1', 'data': 'not-base64@@@'})
    assert response.status_code == 400
    assert response.data == b'Invalid PDF data: expected base64-encoded PDF.'


def test_journaliser_invalid_pdf_bytes(client):
    data_b64 = base64.b64encode(b'hello').decode('ascii')
    response = client.post('/api/journaliser', json={'user': 'Test User - dq1', 'data': data_b64})
    assert response.status_code == 400
    assert response.data == b'Invalid PDF data.'
