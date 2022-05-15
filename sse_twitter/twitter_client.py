import dataclasses
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)


class SearchEmptyError(Exception):
    pass


@dataclasses.dataclass(frozen=True)
class Tweet:
    author_id: str
    created_at: datetime
    id: str
    text: str

    @classmethod
    def from_dict(cls, d: dict[str, Any]):
        return cls(
            author_id=d["author_id"],
            created_at=datetime.strptime(d["created_at"], "%Y-%m-%dT%H:%M:%S.%fZ"),
            id=d["id"],
            text=d["text"],
        )


@dataclasses.dataclass(frozen=True)
class SearchResult:
    result_count: int
    newest_id: str
    tweets: list[Tweet]
    next_token: Optional[str] = None

    @classmethod
    def from_result_dict(cls, res: dict[str, Any]):
        res_count = res["meta"]["result_count"]
        if not res_count:
            raise SearchEmptyError

        return cls(
            result_count=res_count,
            newest_id=res["meta"]["newest_id"],
            next_token=res["meta"].get("newest_token"),
            tweets=[Tweet.from_dict(d) for d in res["data"]],
        )


class TwitterClient:
    base_url = "https://api.twitter.com/2"
    user_agent = "v2RecentSearchPython"

    def __init__(self, bearer_token: str) -> None:
        self.bearer_token = bearer_token

    def _build_query_params(
        self,
        search_query: str,
        start_time: Optional[datetime] = None,
        since_id=None,
    ):
        # Optional params: start_time,end_time,since_id,until_id,max_results,next_token,
        # expansions,tweet.fields,media.fields,poll.fields,place.fields,user.fields
        query = {
            "query": search_query,
            "tweet.fields": "author_id,created_at",
        }
        # since_id will be prefered (if provided), else use start_time
        if start_time and not since_id:
            # API requirement: 'start_time' must be a minimum of 10 seconds
            # prior to the request time.
            prior_10_sec_now = datetime.now(timezone.utc) - timedelta(seconds=10)
            if start_time > prior_10_sec_now:
                start_time = prior_10_sec_now
            query["start_time"] = self.datetime_to_string(start_time)
        if since_id:
            query["since_id"] = since_id
        return query

    def _bearer_oauth(self, request):
        """
        Method required by bearer token authentication.
        """
        request.headers["Authorization"] = f"Bearer {self.bearer_token}"
        request.headers["User-Agent"] = self.user_agent
        return request

    async def search(
        self,
        search_query,
        start_time: Optional[datetime] = None,
        since_id=None,
    ) -> SearchResult:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/tweets/search/recent",
                auth=self._bearer_oauth,
                params=self._build_query_params(
                    search_query=search_query, start_time=start_time, since_id=since_id
                ),
            )
        if response.status_code != 200:
            raise Exception(response.status_code, response.text)
        return SearchResult.from_result_dict(response.json())

    @staticmethod
    def datetime_to_string(dt: datetime) -> str:
        return dt.isoformat(sep="T", timespec="seconds").removesuffix("+00:00") + "Z"
