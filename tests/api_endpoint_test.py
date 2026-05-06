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
    monkeypatch.setattr(api_endpoints_module, 'TESTING', True)
    monkeypatch.setattr(api_endpoints_module, 'DRY_RUN', False)
    monkeypatch.setattr(api_endpoints_module, 'TEST_CPR_NUMBER', '0102030405')

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


@patch('api_endpoints.delta_client.search_cpr')
@patch('api_endpoints.delta_client.get_dq_number_search')
@patch('api_endpoints.sbsys_client.journalize')
@patch('api_endpoints.sbsys_client.get_personalesag')
@patch('api_endpoints.sbsys_client.get_delforloeb')
def test_journaliser_falls_back_to_client_cpr_when_delta_empty(
    mock_get_delforloeb,
    mock_get_personalesag,
    mock_journalize,
    mock_get_dq_number_search,
    mock_search_cpr,
    client,
    monkeypatch,
):
    monkeypatch.setattr(api_endpoints_module, 'TESTING', False)
    monkeypatch.setattr(api_endpoints_module, 'DRY_RUN', False)

    mock_get_dq_number_search.return_value = {'Query': 'dq1'}
    mock_search_cpr.return_value = []

    provided_cpr = '1111111111'
    mock_get_personalesag.return_value = [
        {
            'Id': 123,
            'Nummer': 'SAG-1',
            'SagsStatus': {'Id': api_endpoints_module.SBSYS_SAG_STATUS_ACTIVE_PROD},
        }
    ]
    mock_get_delforloeb.return_value = []
    mock_journalize.return_value = {'Filer': [{'ShortId': 7050}]}

    pdf_bytes = b'%PDF-1.4\n%\xe2\xe3\xcf\xd3\n1 0 obj\n<<>>\nendobj\n%%EOF\n'
    data_b64 = base64.b64encode(pdf_bytes).decode('ascii')

    response = client.post(
        '/api/journaliser',
        json={'user': 'Test User - dq1', 'cpr': provided_cpr, 'data': data_b64},
    )

    assert response.status_code == 200
    mock_get_dq_number_search.assert_called_once_with(dq_number='dq1')
    mock_search_cpr.assert_called_once_with(search_dict={'Query': 'dq1'})
    mock_get_personalesag.assert_called_once_with(cpr=provided_cpr)
    mock_journalize.assert_called_once()


@patch('api_endpoints.delta_client.search_cpr')
@patch('api_endpoints.delta_client.get_dq_number_search')
@patch('api_endpoints.sbsys_client.journalize')
@patch('api_endpoints.sbsys_client.get_personalesag')
@patch('api_endpoints.sbsys_client.get_delforloeb')
def test_journaliser_delta_cpr_overrides_client_cpr(
    mock_get_delforloeb,
    mock_get_personalesag,
    mock_journalize,
    mock_get_dq_number_search,
    mock_search_cpr,
    client,
    monkeypatch,
):
    monkeypatch.setattr(api_endpoints_module, 'TESTING', False)
    monkeypatch.setattr(api_endpoints_module, 'DRY_RUN', False)

    mock_get_dq_number_search.return_value = {'Query': 'dq1'}
    mock_search_cpr.return_value = [{'CPR': '2222222222'}]

    mock_get_personalesag.return_value = [
        {
            'Id': 123,
            'Nummer': 'SAG-1',
            'SagsStatus': {'Id': api_endpoints_module.SBSYS_SAG_STATUS_ACTIVE_PROD},
        }
    ]
    mock_get_delforloeb.return_value = []
    mock_journalize.return_value = {'Filer': [{'ShortId': 7050}]}

    pdf_bytes = b'%PDF-1.4\n%\xe2\xe3\xcf\xd3\n1 0 obj\n<<>>\nendobj\n%%EOF\n'
    data_b64 = base64.b64encode(pdf_bytes).decode('ascii')

    response = client.post(
        '/api/journaliser',
        json={'user': 'Test User - dq1', 'cpr': '1111111111', 'data': data_b64},
    )

    assert response.status_code == 200
    mock_get_personalesag.assert_called_once_with(cpr='2222222222')
    mock_journalize.assert_called_once()


@patch('api_endpoints.delta_client.search_cpr')
@patch('api_endpoints.delta_client.get_dq_number_search')
def test_journaliser_404_when_delta_empty_and_no_client_cpr(
    mock_get_dq_number_search,
    mock_search_cpr,
    client,
    monkeypatch,
):
    monkeypatch.setattr(api_endpoints_module, 'TESTING', False)
    monkeypatch.setattr(api_endpoints_module, 'DRY_RUN', False)

    mock_get_dq_number_search.return_value = {'Query': 'dq1'}
    mock_search_cpr.return_value = []

    pdf_bytes = b'%PDF-1.4\n%\xe2\xe3\xcf\xd3\n1 0 obj\n<<>>\nendobj\n%%EOF\n'
    data_b64 = base64.b64encode(pdf_bytes).decode('ascii')

    response = client.post('/api/journaliser', json={'user': 'Test User - dq1', 'data': data_b64})

    assert response.status_code == 404
    assert b'Could not determine CPR for user' in response.data
