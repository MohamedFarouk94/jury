from .. import exceptions as exc
from ..models import Policy


class PoliciesResource:
    def __init__(self, transport):
        self._transport = transport

    def create(self, name: str, description: str = None) -> Policy:
        resp = self._transport.request(
            "POST", "/policies/", json={"name": name, "description": description}
        )
        # The create endpoint doesn't echo back `rules` (there are none yet),
        # so this response is already a complete, valid Policy payload.
        data = resp.json()
        data.setdefault("rules", [])
        return Policy._from_api(data, self._transport)

    def get(self, name: str) -> Policy:
        """
        Fetch a policy by name. Policy names are unique per user, so this is a
        safe primary key from the SDK's point of view even though the backend
        only exposes id-based lookup. Costs two round trips (list, then get-by-id)
        since there's no dedicated by-name endpoint yet.
        """
        resp = self._transport.request("GET", "/policies/")
        match = next((p for p in resp.json() if p["name"] == name), None)
        if match is None:
            raise exc.NotFoundError(f"No policy named '{name}' was found.")

        full = self._transport.request("GET", f"/policies/{match['id']}")
        return Policy._from_api(full.json(), self._transport)

    def list(self) -> list:
        """
        Return all of the current user's policies, fully loaded with rules.
        Note: this issues one request per policy in addition to the initial
        listing request, so it's O(n) round trips for n policies -- fine at
        the scale this tool is used at today, but worth knowing if you have a
        very large number of policies.
        """
        resp = self._transport.request("GET", "/policies/")
        policies = []
        for summary in resp.json():
            full = self._transport.request("GET", f"/policies/{summary['id']}")
            policies.append(Policy._from_api(full.json(), self._transport))
        return policies