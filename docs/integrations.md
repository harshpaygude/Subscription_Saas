# UniSora integrations

## AWS identity model

The active integration accepts temporary or long-lived AWS access-key
credentials from the authenticated user, verifies them with STS
`GetCallerIdentity`, and then performs a read-only Cost Explorer request. STS
success proves the credentials identify an AWS principal; it does not prove
that Cost Explorer or Free Tier permissions are available.

### AWS promotional credits

UniSora retrieves promotional/free-tier account-plan data from AWS Free Tier's
`GetAccountPlanState` operation through the connected account. The required
permission is `freetier:GetAccountPlanState`; current AWS billing read-only
managed policies may include this permission. AWS returns the remaining credit
amount and plan expiration timestamp, but does not always return an original
promotional-credit amount, so UniSora leaves that field unavailable when AWS
does not provide it.

The backend preserves the raw expiration date and calculates signed calendar
days in UTC. The frontend recalculates display text from that raw date so it can
show “Expires today” and “Expired N days ago” accurately without stale text.
Cost Explorer spend and Free Tier credits are separate data sources.

Credentials are encrypted before persistence in the `connections` table using
the configured JWT secret as the existing application encryption key. A future
deployment should prefer IAM roles or a managed secret store and should rotate
any long-lived keys if they have been exposed.

## Local development

Backend (run from either the repository root or the active backend directory):

```bash
cd "backend "
source venv/bin/activate
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Frontend:

```bash
cd frontend
npm run dev -- --hostname 127.0.0.1 --port 3000
```

The authenticated, non-persisting verification endpoint is
`POST /integrations/aws/verify`. The normal connection endpoint runs the same
verification before storing the encrypted credentials.

## OpenAI API key integration

OpenAI is connected with an API key, which is different from a ChatGPT
subscription or password. The backend verifies the key with OpenAI's
read-only `GET https://api.openai.com/v1/models` operation before storing a
connection. A successful model-list request confirms this key can authenticate
to that endpoint; it does not grant or prove access to organization usage,
cost, or billing data.

OpenAI credentials use the existing encrypted provider-credential storage and
the server-side `JWT_SECRET_KEY` configuration. No additional OpenAI secret is
required in `.env`: the key is submitted over the authenticated API request,
then discarded by the frontend. Do not put an OpenAI key in frontend
configuration, browser storage, URLs, logs, or test fixtures containing real
secrets.

Available endpoints:

- `POST /integrations/openai/connections` — verify and create or update the
  authenticated user's OpenAI connection.
- `GET /integrations/openai/connections` — list sanitized connection status.
- `POST /integrations/openai/connections/{id}/test` — verify the encrypted key
  without returning it.
- `DELETE /integrations/openai/connections/{id}` — remove the connection.

### OpenAI usage and costs

The usage dashboard calls the organization-level OpenAI endpoints:

- `GET /v1/organization/usage/completions` with UTC Unix-second boundaries,
  daily buckets, model/project grouping, and cursor pagination.
- `GET /v1/organization/costs` with UTC Unix-second boundaries, daily buckets,
  project grouping, and cursor pagination.

These endpoints may require an OpenAI organization administrator key or
equivalent organization usage/cost access. A key can successfully authenticate
to `/v1/models` and still be unable to read organization analytics. UniSora
shows that as an authorization/unavailable state rather than reporting zero.
Usage and reported API costs are not ChatGPT Plus, Pro, or other ChatGPT
subscription charges. The current implementation queries on dashboard load or
when the user presses Refresh; it does not persist raw usage payloads or run a
background synchronization job.

## Capability matrix (current backend)

| Provider | Authentication | Backend endpoints | Verification | Data/actions | Status |
|---|---|---|---|---|---|
| AWS | Account credentials (STS) | `/integrations/aws/*` | STS identity plus Cost Explorer and Free Tier checks | Account identity, month-to-date spend, promotional credits/expiration, refresh, disconnect | Supported; requires `freetier:GetAccountPlanState` for credits |
| OpenAI | Encrypted API key | `/integrations/openai/*` | `/v1/models`; usage/cost calls when organization permissions allow | API usage, reported costs, model breakdown, test, refresh, disconnect | Credit expiration not applicable; usage/cost may require organization access |
| Gemini | Encrypted API key | `/integrations/gemini/*` | Gemini `models` list endpoint | Model availability, test, disconnect; usage link to AI Studio | Implemented; historical usage/cost API is not exposed by the Gemini API-key connector |
| Microsoft Azure | Microsoft Entra OAuth + PKCE | `/integrations/azure/*` | Microsoft token exchange, ARM subscription discovery, token refresh | Subscription selection, ARM resources, Azure Cost Management, refresh, disconnect | Credit balance not available in current connector; cost data requires billing permissions |
| Google Cloud | OAuth/workload identity | None | None | None | Coming Soon |
| GitHub | OAuth/PAT | None | None | None | Coming Soon |
| Slack | OAuth | None | None | None | Coming Soon |
| Microsoft 365 | OAuth | None | None | None | Coming Soon |
| Claude, Google Workspace, GitLab, Stripe | Provider-specific | None | None | None | Coming Soon |

The catalog only presents a connect action for providers with a verified
backend connector. Connection order is centralized in the frontend registry:
verified active connections, available disconnected providers, attention states
(error/expired), then unsupported providers. The backend remains the source of
truth for connection status.

## Settings capability

Account display name and password changes are backed by `/auth/me` (PATCH) and
`/auth/change-password`. Organization name, email, and role are read-only in
the current API. Theme preference is stored by the existing local preference
mechanism. Notification preferences, MFA, and active-session management are
not yet exposed by the backend and are explicitly labelled unsupported.
