# UniSora API Gateway

Single public HTTP ingress (Port `8000`). Handles CORS, correlation IDs, sliding-window rate limiting, edge JWT verification, internal HMAC identity header signing, downstream health aggregation, and declarative service routing. Contains zero business logic.
