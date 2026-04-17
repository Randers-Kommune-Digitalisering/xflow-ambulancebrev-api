import json
import logging
import time
import requests
from utils.api_client import APIClientWithAuthHeaders
from utils.config import SBSIP_URL

logger = logging.getLogger(__name__)


class SbsysAPIClient(APIClientWithAuthHeaders):
    _client_cache: dict[tuple[str, str, str, str, str], 'SbsysAPIClient'] = {}

    def __init__(self, client_id, client_secret, username, password, url):
        super().__init__(url)
        self.client_id = client_id
        self.client_secret = client_secret
        self.username = username
        self.password = password
        self.access_token = None
        self.access_token_expiry = None
        self.refresh_token = None
        self.refresh_token_expiry = None

    @classmethod
    def get_client(cls, client_id, client_secret, username, password, url):
        key = (client_id, client_secret, username, password, url)
        if key in cls._client_cache:
            return cls._client_cache[key]
        client = cls(client_id, client_secret, username, password, url)
        cls._client_cache[key] = client
        return client

    def request_access_token(self):
        token_url = f"{SBSIP_URL}/auth/realms/sbsip/protocol/openid-connect/token"
        payload = {
            "grant_type": "password",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "username": self.username,
            "password": self.password
        }
        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }

        try:
            if not token_url.startswith("https://"):
                token_url = "https://" + token_url.removeprefix("http://")
            response = requests.post(token_url, headers=headers, data=payload, timeout=20)
            response.raise_for_status()
            data = response.json()
            self.access_token = data['access_token']
            self.access_token_expiry = time.time() + data['expires_in']
            return self.access_token

        except requests.exceptions.HTTPError as e:
            safe_payload = {
                **payload,
                "client_secret": "***" if payload.get("client_secret") else "",
                "password": "***" if payload.get("password") else "",
            }
            response = getattr(e, "response", None)
            if response is not None:
                body = response.text
                logger.error(
                    "Access token request failed (%s). url=%s payload=%s response_body=%s",
                    response.status_code,
                    response.url,
                    safe_payload,
                    body,
                )
            else:
                logger.error("Access token request failed: %s", e)
            return None

        except requests.exceptions.RequestException as e:
            logger.error(e)
            return None

    def get_auth_headers(self):
        if self.access_token and self.access_token_expiry and time.time() < self.access_token_expiry:
            return {'Authorization': f'Bearer {self.access_token}'}
        else:
            if self.request_access_token():
                return {'Authorization': f'Bearer {self.access_token}'}
            else:
                logger.error("Failed to obtain access token")
                return {}


class SbsysClient:
    def __init__(self, client_id, client_secret, username, password, url):
        self.api_client = SbsysAPIClient.get_client(client_id, client_secret, username, password, url)

    # TODO: add docstrings and type hints for get_personalesag
    def get_personalesag(self, cpr):
        path = "api/sag/search"
        if "-" not in cpr:
            cpr = cpr[:6] + "-" + cpr[6:]

        payload = {
            'PrimaerPerson': {
                'CprNummer': cpr
            },
            'SagsTyper': [
                {
                    'Navn': 'PersonaleSag'
                }
            ]
        }

        try:
            response = self.api_client._make_request("POST", path=path, json=payload)
            if not response:
                logger.warning("No response from SBSYS client")
                return False
            if not response['Results']:
                logger.warning("CPR not found in SBSYS")
                return None
            return response['Results']

        except Exception as e:
            logger.error(f"An error occurred while performing sag_get: {e}")
            return False

    # TODO: add docstrings and type hints for get_delforloeb
    def get_delforloeb(self, sag_id):
        path = f"api/delforloeb/sag/{sag_id}"
        try:
            response = self.api_client._make_request("GET", path=path)
            if not response:
                logger.warning("No response from SBSYS client")
                return False
            return response

        except Exception as e:
            logger.error(f"An error occurred while performing get_delforloeb: {e}")
            return False

    # TODO: add type hints for journalize
    def journalize(self, file, sag_id, delforloeb_id=None):
        """
        Journalize a document by uploading a file and metadata.

        :param file: The file to be journalized.
        :param sag_id: The ID of the sag to journalize the document under.
        :param delforloeb_id: Optional ID of the delforloeb to associate with the journalized document.
        :return: API response.
        """
        metadata = {  # JournaliserDokumentInputDtoV10
            "SagID": sag_id,
            "Beskrivelse": "Ambulancebrev automatisk journaliseret fra X-Flow blanket udfyldt af medarbejderen.",
            "OmfattetAfAktindsigt": True,
            "DokumentNavn": "Ambulancebrev",
        }

        if isinstance(file, (bytes, bytearray)):
            file_part = ("Ambulancebrev.pdf", file, "application/pdf")
        else:
            filename = getattr(file, "name", None) or "Ambulancebrev.pdf"
            file_part = (filename, file, "application/pdf")

        multipart = {
            "file": file_part,
            "json": (None, json.dumps(metadata, ensure_ascii=False), "application/json"),
        }

        try:
            response = self.api_client._make_request(
                "POST",
                path="api/dokument/journaliser" + (f"/{delforloeb_id}" if delforloeb_id else ""),
                files=multipart,
            )
            if not response:
                logger.warning("No response from SBSYS client")
                return False
            return response
        except Exception as e:
            logger.error(f"An error occurred while journalizing: {e}")
            return False
