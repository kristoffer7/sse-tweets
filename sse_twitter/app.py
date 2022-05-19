import asyncio
import logging
import urllib.parse
from datetime import datetime, timezone

import uvicorn
from sse_starlette.sse import EventSourceResponse
from starlette.applications import Starlette
from starlette.endpoints import HTTPEndpoint
from starlette.requests import Request
from starlette.responses import HTMLResponse
from starlette.routing import Route

from sse_twitter import config
from sse_twitter.twitter_client import SearchEmptyError, TwitterClient

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class Home(HTTPEndpoint):
    async def get(self, request: Request):
        return HTMLResponse(
            """
            <!DOCTYPE html>
            <html>
            <head>
                <script src="https://unpkg.com/htmx.org@1.7.0"></script>
                <script src="https://unpkg.com/htmx.org@1.7.0/dist/ext/sse.js"></script>
                <link rel="shortcut icon" href="data:image/x-icon;," type="image/x-icon">
            </head>
            <body>
                <h1>Tweets over SSE</h1>

                <form hx-post="/search">
                <div hx-target="this" hx-swap="outerHTML">
                    <label>Search phrase</label>
                    <input type="text" class="form-control" name="searchPhrase">
                </div>
                <button class="btn btn-default">Submit</button>
                </form>
            </body>
            """
        )


class Search(HTTPEndpoint):
    async def post(self, request: Request):
        search_phrase = (await request.form())["searchPhrase"]
        now = datetime.now(timezone.utc)
        search_phrase_query_safe = urllib.parse.quote_plus(search_phrase)
        qs = f"q={search_phrase_query_safe}&start={int(now.timestamp())}"
        logger.debug(
            f"Search phrase: {search_phrase}, start time: {now}, query_string: {qs}"
        )
        return HTMLResponse(
            f"""
            <div hx-ext="sse"
                sse-connect="/events?{qs}"
                sse-swap="new_tweets"
                hx-trigger="changed"
                hx-target="#tgt"
                hx-swap="afterbegin"
            >
                <!-- FIXME: Sanitize search_phrase -->
                <p>Search: {search_phrase}<p>
                <div id="tgt" />
            </div>
            """
        )


CLIENT_SSE_RETRY_MS = 5000
CHECK_NEW_TWEETS_WAIT_TIME_SEC = 5.0


async def event_generator(request: Request):
    """Yields html formatted stream of tweets as requested until client
    disconnects"""
    try:
        logger.debug(f"{request.url=} {request.query_params=}")
        query = urllib.parse.unquote_plus(request.query_params["q"])
        start_time = datetime.fromtimestamp(int(request.query_params["start"]))
        start_time = start_time.replace(tzinfo=timezone.utc)
        logger.debug(
            f"Client: {request.client}, query: {query}, start_time: {start_time}"
        )
        twitter_client = TwitterClient(bearer_token=config.twitter_token)
        since_id = None
        while True:
            try:
                twitter_results = await twitter_client.search(
                    search_query=query, start_time=start_time, since_id=since_id
                )
                since_id = twitter_results.newest_id
                tweet_html = ""
                for tweet in twitter_results.tweets:
                    tweet_html += f"<p>{tweet.text}<p>"
                yield {
                    "event": "new_tweets",
                    "retry": CLIENT_SSE_RETRY_MS,
                    "data": tweet_html,
                }
            except SearchEmptyError:
                yield {
                    "event": "new_tweets",
                    "retry": CLIENT_SSE_RETRY_MS,
                    "data": "<p>No tweets found</p>",
                }
            await asyncio.sleep(CHECK_NEW_TWEETS_WAIT_TIME_SEC)
    except asyncio.CancelledError:
        logger.debug("Disconnected from client (via refresh/close)")


class Events(HTTPEndpoint):
    async def get(self, request: Request):
        generator = event_generator(request)
        return EventSourceResponse(generator)


routes = [
    Route("/", endpoint=Home),
    Route("/search", endpoint=Search),
    Route("/events", endpoint=Events),
]

app = Starlette(debug=True, routes=routes)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="debug")
