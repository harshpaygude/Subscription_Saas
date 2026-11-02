# Azure account setup

Microsoft identity is the sign-in authority. An Azure subscription is a billing/resource container. Microsoft Entra ID manages identities and app consent. Signing in does not itself grant subscription access.

1. Open [Microsoft Entra admin center](https://entra.microsoft.com/) and create an App registration.
2. For customer organizations choose multitenant organizational accounts; choose single-tenant for one organization. Personal Microsoft accounts are not assumed to have Azure subscriptions.
3. Add the Web redirect URI `http://localhost:8000/api/azure/oauth/callback` and the deployed HTTPS callback.
4. Create a server-side client secret or certificate. Never send it to the frontend.
5. Add delegated Azure Service Management `user_impersonation`. Admin consent may be required. This is distinct from Graph permissions and Azure RBAC.
6. Give the user read access to the subscriptions/resources. Cost queries may additionally require Cost Management Reader or billing-scope access.

Set `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`, `AZURE_TENANT`, `AZURE_REDIRECT_URI`, `AZURE_SCOPES`, and `AZURE_TOKEN_ENCRYPTION_KEY`. Generate the key with `Fernet.generate_key()` and store it in a secret manager. Loss of the key requires reauthorization. OAuth state is stored in the database and additionally bound to a short-lived HttpOnly SameSite cookie, so the callback must use the same browser.

Select **Connect Microsoft Azure** in the UI. The backend validates one-time state and PKCE, encrypts the token response, and discovers subscriptions. Empty results mean no accessible subscriptions. `AADSTS50011` means the redirect differs exactly; `AADSTS65001` means consent is missing; ARM 403 means missing RBAC/delegated access; cost 403 means missing billing access. See [authorization code flow](https://learn.microsoft.com/en-us/entra/identity-platform/v2-oauth2-auth-code-flow), [MSAL flows](https://learn.microsoft.com/en-us/entra/msal/msal-authentication-flows), [subscriptions](https://learn.microsoft.com/en-us/rest/api/resources/subscriptions/list), and [Cost Management](https://learn.microsoft.com/en-us/rest/api/cost-management/query/usage-by-scope).

## Local temporary-token testing

This is disabled by default and must never be enabled in production. Set `APP_ENV=development` and `ENABLE_MANUAL_AZURE_TOKEN_INPUT=true`, then set a local development identity through the dashboard. The token can be obtained from an authorized Azure CLI session with `az account get-access-token --resource https://management.azure.com/`; paste the short-lived value into the password-style field. It is held only in backend process memory, is not written to the database or browser storage, and must be cleared or re-entered after expiry. The backend still verifies access by calling Azure; it does not trust decoded token contents.
