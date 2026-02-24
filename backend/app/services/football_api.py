from typing import Any
import httpx

from app.config import get_settings
from app.utils.rate_limiter import TokenBucketRateLimiter
from app.utils.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)

# Shared rate limiter: football-data.org free tier = 10 req/min
_rate_limiter = TokenBucketRateLimiter(rate=10, period=60.0)


class FootballDataClient:
    """Async httpx client for football-data.org API v4."""

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=settings.football_data_base_url,
                headers={"X-Auth-Token": settings.football_data_api_key},
                timeout=30.0,
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def _get(self, path: str, params: dict | None = None) -> dict[str, Any]:
        await _rate_limiter.acquire()
        url = path if params is None else f"{path}"
        response = await self.client.get(url, params=params)
        response.raise_for_status()
        return response.json()

    async def get_competitions(self) -> dict[str, Any]:
        return await self._get("/competitions")

    async def get_standings(self, competition_code: str) -> dict[str, Any]:
        return await self._get(f"/competitions/{competition_code}/standings")

    async def get_matches(
        self,
        competition_code: str,
        season: int | None = None,
        status: str | None = None,
        matchday: int | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {}
        if season is not None:
            params["season"] = season
        if status:
            params["status"] = status
        if matchday is not None:
            params["matchday"] = matchday
        if date_from:
            params["dateFrom"] = date_from
        if date_to:
            params["dateTo"] = date_to
        return await self._get(f"/competitions/{competition_code}/matches", params=params)

    async def get_teams(self, competition_code: str, season: int | None = None) -> dict[str, Any]:
        params = {}
        if season is not None:
            params["season"] = season
        return await self._get(f"/competitions/{competition_code}/teams", params=params)

    async def get_match(self, match_id: int) -> dict[str, Any]:
        return await self._get(f"/matches/{match_id}")
