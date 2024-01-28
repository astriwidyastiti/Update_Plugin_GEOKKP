import json

from .networkaccessmanager import NetworkAccessManager, DEFAULT_MAX_REDIRECTS

BASE_URL = "http://10.20.22.90:5001/spatialapi"

DEFAULT_HEADER = {b"Content-Type": b"application/json"}

REQUEST_KWARGS = {"endpoint", "method", "body", "headers", "redirections", "blocking"}


class API:
    def __init__(self, base_url=BASE_URL, *args, **kwargs):
        self._base_url = base_url
        self._client = NetworkAccessManager(*args, **kwargs)

    def _build_url(self, endpoint):
        return f"{self._base_url}/{endpoint}"

    @staticmethod
    def build_api_payload(payload):
        print("api payload", payload)
        return json.dumps(payload).encode("utf8")

    def request(
        self,
        endpoint,
        method="POST",
        body=None,
        headers=DEFAULT_HEADER,
        redirections=DEFAULT_MAX_REDIRECTS,
        blocking=True,
    ):
        request_url = self._build_url(endpoint)
        request_body = self.build_api_payload(body)
        (response, content) = self._client.request(
            url=request_url,
            method=method,
            body=request_body,
            headers=headers,
            redirections=redirections,
            blocking=blocking,
        )
        if blocking:
            return response
        else:
            return self._client


def api(endpoint, base_url=BASE_URL, method="POST", **client_config):
    def decorator(function):
        def wrapper(*args, **kwargs):
            client = API(base_url=base_url, **client_config)
            payload = function(*args, **kwargs)
            request_config = {}
            for kwarg in kwargs:
                if kwarg in REQUEST_KWARGS:
                    request_config[kwarg] = kwargs[kwarg]
            response = client.request(
                endpoint=endpoint, method=method, body=payload, **request_config
            )
            return response

        return wrapper

    return decorator
