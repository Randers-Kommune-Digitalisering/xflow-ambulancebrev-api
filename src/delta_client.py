import logging
import time
import requests

from utils.api_client import APIClientWithAuthHeaders

logger = logging.getLogger(__name__)


class DeltaAPIClient(APIClientWithAuthHeaders):
    _client_cache: dict[tuple[str, str, str, str, str], 'DeltaAPIClient'] = {}

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
            else:
                tmp_json_data['grant_type'] = 'client_credentials'

            now = time.time()

            response = requests.post(tmp_url, headers=tmp_headers, data=tmp_json_data, timeout=60)
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

    def get_cpr_by_dq_number(self, search_dict: dict | None = None) -> list[dict] | None:
        """
        Search for persons CPR in Delta based on the provided search dictionary.

        :param search_dict: All search parameters for Delta graph query. Generated via get_dq_number_search
        :return: A list of dicts with CPR only (e.g. [{"CPR": "..."}]) or None if no results found
        """
        if not search_dict:
            return None

        res = self.api_client._make_request(method="POST", path="api/object/graph-query", json=search_dict)
        if not res:
            raise ValueError("Intet svar fra Delta")

        graph_results = res.get("graphQueryResult") or []
        if not graph_results:
            return None

        instances = graph_results[0].get("instances") or []
        if not instances:
            return None

        people = []
        for instance in instances:
            relations = instance.get("typeRefs") or []
            person_target = next(
                (
                    rel.get("targetObject", {})
                    for rel in relations
                    if rel.get("userKey") == "APOS-Types-Engagement-TypeRelation-Person"
                ),
                None,
            )
            if not person_target:
                continue

            person_attrs = person_target.get("attributes") or []
            cpr = next(
                (
                    item.get("value")
                    for item in person_attrs
                    if item.get("userKey") == "APOS-Types-Person-Attribute-CPR"
                ),
                None,
            )

            if cpr:
                people.append({"CPR": cpr})

        return people

    def get_dq_number_search(self, dq_number: str) -> dict:
        """
        Generate a search dictionary for querying Delta by DQ number.

        :param dq_number: DQ number to search for.
        :return: A search dictionary for querying Delta by DQ number.
        """
        return {
            "graphQueries": [
                {
                    "computeAvailablePages": False,
                    "graphQuery": {
                        "structure": {
                            "alias": "employee",
                            "userKey": "APOS-Types-Engagement",
                            "relations": [
                                {
                                    "alias": "person",
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
                                }
                            ]
                        },
                        "criteria": {
                            "type": "AND",
                            "criteria": [
                                {
                                    "type": "MATCH",
                                    "operator": "EQUAL",
                                    "left": {"source": "DEFINITION", "alias": "employee.person.user.$userKey"},
                                    "right": {"source": "STATIC", "value": dq_number},
                                },
                                {
                                    "type": "MATCH",
                                    "operator": "EQUAL",
                                    "left": {"source": "DEFINITION", "alias": "employee.$state"},
                                    "right": {"source": "STATIC", "value": "STATE_ACTIVE"},
                                }
                            ]
                        },
                        "projection": {
                            "typeRelations": [
                                {
                                    "userKey": "APOS-Types-Engagement-TypeRelation-Person",
                                    "projection": {
                                        "attributes": ["APOS-Types-Person-Attribute-CPR"],
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
