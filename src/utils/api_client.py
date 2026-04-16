import logging
from abc import ABC, abstractmethod
from collections.abc import Callable
import requests

logger = logging.getLogger(__name__)


# Abstract base api client class
class APIClientWithAuthHeaders(ABC):
    def __init__(self, base_url):
        self.base_url = base_url

    @abstractmethod
    def get_auth_headers(self):
        pass  # pragma: no cover

    def _make_request(self, method, path, **kwargs):
        if isinstance(method, str):
            method_name = method.strip().lower()
            resolved: Callable[..., requests.Response] | None = getattr(requests, method_name, None)
            if not callable(resolved):
                logger.error(f"Unsupported HTTP method: {method!r}")
                return None
            method = resolved

        try:
            headers = self.get_auth_headers()
        except Exception as e:
            logger.error(f"Error obtaining auth headers: {e}")
            return None

        if headers:
            if path.startswith("http://") or path.startswith("https://"):
                url = path
            else:
                url = f"{self.base_url.rstrip('/')}/{path.lstrip('/')}"

            try:
                response = method(url, headers=headers, **kwargs)

                try:
                    response.raise_for_status()
                except requests.exceptions.HTTPError as e:
                    resp = getattr(e, "response", None) or response
                    body = (getattr(resp, "text", "") or "").strip()
                    if not body:
                        body = "<empty>"
                    elif len(body) > 4000:
                        body = body[:4000] + "...(truncated)"

                    logger.error(
                        "Request failed (%s) for url: %s response_body=%s",
                        getattr(resp, "status_code", "unknown"),
                        getattr(resp, "url", url),
                        body,
                    )
                    return None

                try:
                    return response.json()

                except requests.exceptions.JSONDecodeError:
                    if not response.content:
                        return b''
                    return response.content

            except requests.exceptions.RequestException as e:
                logger.error(f"Request failed: {e}")
                return None
        else:
            logger.error("Failed to get auth headers")
            return None

    def get(self, path, params=None, **kwargs):
        return self._make_request(requests.get, path, params=params, **kwargs)

    def post(self, path, data=None, json=None, **kwargs):
        return self._make_request(requests.post, path, data=data, json=json, **kwargs)

    def post_upload(self, path, data=None, files=None):
        return self._make_request(requests.post, path, data=data, files=files)

    def put(self, path, data=None, json=None, **kwargs):
        return self._make_request(requests.put, path, data=data, json=json, **kwargs)

    def delete(self, path, **kwargs):
        return self._make_request(requests.delete, path, **kwargs)
