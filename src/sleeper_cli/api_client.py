from typing import Any

import requests

SLEEPER_API_BASE_URL = "https://api.sleeper.app/v1"


class SleeperApiClient:
    def _fetch_data(self, relative_url: str) -> dict[str, Any]:
        return requests.get(f"{SLEEPER_API_BASE_URL}/{relative_url}").json()


class SleeperNflApiClient(SleeperApiClient):
    def fetch_players(self) -> dict[int, dict[str, Any]]:
        return self._fetch_data("players/nfl")


class SleeperLeagueApiClient(SleeperApiClient):
    def __init__(self, league_id: str) -> None:
        self.league_id = league_id

    def fetch_matchups(self, week: int) -> tuple[int, list[dict[str, Any]]]:
        return week, self._fetch_data(f"matchups/{week}")

    def fetch_rosters_by_id(self) -> dict[str, Any]:
        return {roster["roster_id"]: roster for roster in self._fetch_data("rosters")}

    def fetch_users_by_id(self) -> dict[str, Any]:
        return {user["user_id"]: user for user in self._fetch_data("users")}

    def _fetch_data(self, relative_url: str) -> dict[str, Any]:
        return super()._fetch_data(f"league/{self.league_id}/{relative_url}")
