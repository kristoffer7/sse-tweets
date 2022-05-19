# sse-tweets

A very simple web server that hosts a HTMl page where user can search for tweets based on a search phrase, and receive real-time-updates.

## Resources used

- Official docs for [Starlette](https://www.starlette.io/), [htmx](https://htmx.org/), [starlette-sse](https://github.com/sysid/sse-starlette)
- https://github.com/twitterdev/Twitter-API-v2-sample-code/blob/main/Recent-Search/recent_search.py
- https://github.com/vlcinsky/fastapi-sse-htmx/
- Setting up a twitter dev account: https://developer.twitter.com/en/docs/apps/overview
- +++

## TODO (or "if time would have allowed")

- Research why htmx is causing a flood of new requests if SSE request throws an error
- Add tests
- Include request ID in logs, integrate better with Fly.io logging, remove SSE stdout data (`data: ...`)
- Differentiate event type on new tweets vs no new tweets
- Format tweet with author, timestamp
- Separate formatting from route logic

## Sessions

(time used)

1) 02h 15m
2) 04h 00m
