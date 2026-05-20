from typing import Any

import httpx

from .errors import StripeAPIError


class LocalStripeClient:
    def __init__(self, base_url: str, api_key: str):
        self._base_url = base_url
        self._http = httpx.AsyncClient(
            base_url=base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10.0,
        )

    async def get(self, path: str, params: dict | None = None) -> dict:
        try:
            r = await self._http.get(path, params=params)
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            raise StripeAPIError(
                503, f"localstripe unreachable at {self._base_url}: {e}", "network"
            )
        return self._handle(r)

    async def post(self, path: str, form: dict) -> dict:
        try:
            r = await self._http.post(path, data=_flatten(form))
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            raise StripeAPIError(
                503, f"localstripe unreachable at {self._base_url}: {e}", "network"
            )
        return self._handle(r)

    async def aclose(self) -> None:
        await self._http.aclose()

    @staticmethod
    def _handle(r: httpx.Response) -> dict:
        if r.status_code >= 400:
            try:
                err = r.json().get("error", {})
            except Exception:
                err = {"message": r.text or "unknown error"}
            raise StripeAPIError(
                r.status_code,
                err.get("message", "unknown error"),
                err.get("code") or err.get("type"),
            )
        return r.json()


def _flatten(form: dict) -> dict[str, Any]:
    # Stripe-style form encoding: {"metadata": {"k": "v"}} -> {"metadata[k]": "v"}
    out: dict[str, Any] = {}
    for k, v in form.items():
        if isinstance(v, dict):
            for sub_k, sub_v in v.items():
                out[f"{k}[{sub_k}]"] = sub_v
        else:
            out[k] = v
    return out
