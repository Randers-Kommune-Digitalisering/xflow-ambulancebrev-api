import logging
import time
import requests
from typing import Dict, Tuple
from utils.api_client import APIClientWithAuthHeaders
from utils.config import SBSIP_URL

logger = logging.getLogger(__name__)


class SbsysAPIClient(APIClientWithAuthHeaders):
    _client_cache: Dict[Tuple[str, str, str, str], 'SbsysAPIClient'] = {}

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
        key = (client_id, client_secret, username, password)
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
                token_url = "https://" + token_url
            response = requests.post(token_url, headers=headers, data=payload, timeout=20)
            response.raise_for_status()
            data = response.json()
            self.access_token = data['access_token']
            self.access_token_expiry = time.time() + data['expires_in']
            return self.access_token
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
            response = self.api_client.post(path=path, json=payload)
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

    def journalize(self, file, sag_id):
        """
        Journalize a document by uploading a file and metadata.

        :param file: The file to be journalized.
        :param json: Metadata describing the document (JournaliserDokumentInputDtoV10).
        :return: API response.
        """
        url = f"{self.api_client.base_url}/dokument/journaliser"
        headers = self.api_client.get_auth_headers()
        files = {
            "file": file
        }
        data = {
            "json": {
                "SagID": sag_id,
                "beskrivelse": "Oplysningsbrev automatisk journaliseret fra X-Flow blanket udfyldt af medarbejderen."
            }
        }
        try:
            response = requests.post(url, headers=headers, files=files, data=data, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Journalize failed: {e}")
            return False
