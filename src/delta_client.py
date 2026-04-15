import logging
import time
import requests
from typing import Dict, Tuple

from utils.api_client import APIClientWithAuthHeaders

logger = logging.getLogger(__name__)


class DeltaAPIClient(APIClientWithAuthHeaders):
    _client_cache: Dict[Tuple[str, str, str, str, str], 'DeltaAPIClient'] = {}

    def __init__(self, client_id, client_secret, url, auth_url, realm):
        super().__init__(url)
        self.client_id = client_id
        self.client_secret = client_secret
        self.auth_url = auth_url
        self.realm = realm
        self.access_token = None
        self.access_token_expiry = None
        self.refresh_token = None
        self.refresh_token_expiry = None

    @classmethod
    def get_client(cls, client_id, client_secret, url, auth_url, realm):
        key = (client_id, client_secret, url, auth_url, realm)
        if key in cls._client_cache:
            return cls._client_cache[key]
        client = cls(client_id, client_secret, url, auth_url, realm)
        cls._client_cache[key] = client
        return client

    def get_auth_headers(self):
        if self.client_id and self.client_secret:
            if not self.realm:
                raise ValueError('Realm is required for client_id and client_secret authentication')

            refresh_token = False

            if self.access_token:
                if self.access_token_expiry:
                    if time.time() < self.access_token_expiry:
                        return {'Authorization': f'Bearer {self.access_token}'}
                    else:
                        if self.refresh_token:
                            if self.refresh_token_expiry:
                                if time.time() < self.refresh_token_expiry:
                                    refresh_token = True

            tmp_base_url = self.auth_url or self.base_url
            tmp_url = f'{tmp_base_url}/realms/{self.realm}/protocol/openid-connect/token'

            tmp_headers = {
                'Content-Type': 'application/x-www-form-urlencoded'
            }

            tmp_json_data = {
                'client_id': self.client_id,
                'client_secret': self.client_secret
            }

            if refresh_token:
                tmp_json_data['grant_type'] = 'refresh_token'
                tmp_json_data['refresh_token'] = self.refresh_token
            # elif self.username and self.password:
            #     tmp_json_data['grant_type'] = 'password'
            #     tmp_json_data['username'] = self.username
            #     tmp_json_data['password'] = self.password
            else:
                tmp_json_data['grant_type'] = 'client_credentials'

            now = time.time()

            import requests

            response = requests.post(tmp_url, headers=tmp_headers, data=tmp_json_data)
            response.raise_for_status()
            data = response.json()

            self.access_token = data['access_token']
            self.access_token_expiry = now + data['expires_in']

            if 'refresh_token' in data:
                self.refresh_token = data['refresh_token']
                self.refresh_token_expiry = now + data['refresh_expires_in']

            return {'Authorization': f'Bearer {self.access_token}'}
        else:
            return {}

    def _make_request(self, method, path, **kwargs):
        return super()._make_request(method, path, **kwargs)
        
class DeltaClient:
    def __init__(self, url, auth_url, realm, client_id, client_secret):
        self.api_client = DeltaAPIClient.get_client(client_id, client_secret, url, auth_url, realm)

    def search(self, search_dict: dict | None = None) -> list[dict] | None:
        """
        Search for persons in Delta based on the provided search dictionary.

        :param search_dict: All search parameters for Delta graph query. Generated via get_dq_number_search
        :return: A list of dictionaries with person information (name, email, phone, mobile, department, DQ-number) or None if no results found
        """
        if search_dict:
            res = self.api_client._make_request(method='POST', path='api/object/graph-query', json=search_dict)

            if res:
                res = res.get('graphQueryResult', [])
            else:
                raise ValueError('Intet svar fra Delta')

            if len(res) > 0:
                instances = res[0].get('instances', [])
                if len(instances) < 1:
                    return None
                else:
                    people = []
                    for e in instances:
                        attributes = e.get('attributes', [])

                        email = next((item.get('value', '-') for item in attributes if item['userKey'] == 'APOS-Types-Engagement-Attribute-Email'), '-')
                        mobile = next((item.get('value', '-') for item in attributes if item['userKey'] == 'APOS-Types-Engagement-Attribute-Mobile'), '-')
                        phone = next((item.get('value', '-') for item in attributes if item['userKey'] == 'APOS-Types-Engagement-Attribute-Phone'), '-')

                        relations = e.get('typeRefs', [])
                        department = next((item.get('targetObject', {}).get('identity', {}).get('name', '-') for item in relations if item['userKey'] == 'APOS-Types-Engagement-TypeRelation-AdmUnit'), '-')
                        name = next((item.get('targetObject', {}).get('attributes', [{}])[0].get('value', '-') for item in relations if item['userKey'] == 'APOS-Types-Engagement-TypeRelation-Person'), '-')

                        incoming_type_relations = next((item.get('targetObject', {}).get('inTypeRefs', None) for item in relations if item['userKey'] == 'APOS-Types-Engagement-TypeRelation-Person'), None)
                        if incoming_type_relations:
                            user = incoming_type_relations[0].get('targetObject', {}).get('identity', {}).get('name', '-')
                        else:
                            user = '-'

                        person = {
                            'Navn': name,
                            'E-mail': email,
                            'Telefon': phone,
                            'Mobil': mobile,
                            'Afdeling': department,
                            'DQ-nummer': user
                        }

                        for key, value in person.items():
                            if not value:
                                person[key] = '-'

                        people.append(person)

                    return people

    def get_dq_number_search(self, dq_number: str) -> dict | None:
        """
        Generate a search dictionary for querying Delta by DQ number. Logs the search action in the database.

        :param dq_number: DQ number to search for
        :param user: User information dictionary containing 'username' and 'email' keys
        :return: A search dictionary for querying Delta by DQ number if user is provided, otherwise None.
        """
        return {
            "graphQueries": [
                {
                    "computeAvailablePages": False,
                    "graphQuery": {
                        "structure": {
                            "alias": "employee",
                            "userKey": "APOS-Types-Engagement",
                            "attributes": [
                                {
                                    "alias": "email",
                                    "userKey": "APOS-Types-Engagement-Attribute-Email"
                                },
                                {
                                    "alias": "phone",
                                    "userKey": "APOS-Types-Engagement-Attribute-Phone"
                                },
                                {
                                    "alias": "mobile",
                                    "userKey": "APOS-Types-Engagement-Attribute-Mobile"
                                }
                            ],
                            "relations": [
                                {
                                    "alias": "person",
                                    "title": "APOS-Types-Engagement-TypeRelation-Person",
                                    "userKey": "APOS-Types-Engagement-TypeRelation-Person",
                                    "typeUserKey": "APOS-Types-Person",
                                    "direction": "OUT",
                                    "relations": [
                                        {
                                            "alias": "user",
                                            "userKey": "APOS-Types-User-TypeRelation-Person",
                                            "typeUserKey": "APOS-Types-User",
                                            "direction": "IN"
                                        }
                                    ]
                                },
                                {
                                    "alias": "unit",
                                    "title": "APOS-Types-Engagement-TypeRelation-AdmUnit",
                                    "userKey": "APOS-Types-Engagement-TypeRelation-AdmUnit",
                                    "typeUserKey": "APOS-Types-AdministrativeUnit",
                                    "direction": "OUT"
                                }
                            ]
                        },
                        "criteria": {
                            "type": "AND",
                            "criteria": [
                                {
                                    "type": "MATCH",
                                    "operator": "EQUAL",
                                    "left": {
                                        "source": "DEFINITION",
                                        "alias": "employee.person.user.$userKey"
                                    },
                                    "right": {
                                        "source": "STATIC",
                                        "value": dq_number
                                    }
                                },
                                {
                                    "type": "MATCH",
                                    "operator": "EQUAL",
                                    "left": {
                                        "source": "DEFINITION",
                                        "alias": "employee.$state"
                                    },
                                    "right": {
                                        "source": "STATIC",
                                        "value": "STATE_ACTIVE"
                                    }
                                }
                            ]
                        },
                        "projection": {
                            "identity": True,
                            "state": True,
                            "attributes": [
                                "APOS-Types-Engagement-Attribute-Mobile",
                                "APOS-Types-Engagement-Attribute-Phone",
                                "APOS-Types-Engagement-Attribute-Email"
                            ],
                            "typeRelations": [
                                {
                                    "userKey": "APOS-Types-Engagement-TypeRelation-Person",
                                    "projection": {
                                        "state": True,
                                        "attributes": [
                                            "APOS-Types-Person-Attribute-SurnameAndName"
                                        ],
                                        "incomingTypeRelations": [
                                            {
                                                "userKey": "APOS-Types-User-TypeRelation-Person",
                                                "projection": {
                                                    "identity": True
                                                }
                                            }
                                        ]
                                    }
                                },
                                {
                                    "userKey": "APOS-Types-Engagement-TypeRelation-AdmUnit",
                                    "projection": {
                                        "identity": True
                                    }
                                }
                            ]
                        }
                    },
                    "validDate": "NOW",
                    "limit": 1
                }
            ]
        }