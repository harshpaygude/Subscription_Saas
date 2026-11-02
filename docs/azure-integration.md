# Microsoft Azure integration

UniSora supports Microsoft Entra authorization-code + PKCE and service-principal
connections, with an encrypted token cache, token refresh handling, ARM
subscription/resource client, and Cost Management query shape.
The standalone Azure development UI and its `X-Platform-User-ID` development
header are not used by UniSora.

## Configuration

Set these server-side in the active `backend ` environment. Existing
`MICROSOFT_CLIENT_ID`, `MICROSOFT_CLIENT_SECRET`, and `MICROSOFT_TENANT_ID`
are accepted as fallbacks:

```env
AZURE_CLIENT_ID=...
AZURE_CLIENT_SECRET=...
AZURE_TENANT=common
AZURE_REDIRECT_URI=http://127.0.0.1:8000/integrations/azure/oauth/callback
AZURE_SCOPES=https://management.azure.com/user_impersonation
AZURE_TOKEN_ENCRYPTION_KEY=<fernet-key>
FRONTEND_URL=http://127.0.0.1:3000
```

Register the exact callback URL in the Microsoft Entra app registration. The
encryption key must be stable across restarts and must never be committed.

## Flow

1. The signed-in UniSora user selects Microsoft Azure.
2. The user enters a Microsoft Entra tenant ID, application client ID, client secret, and optional subscription ID in the connection form.
3. The backend exchanges the service-principal credentials for an Azure management token and verifies subscription access.
4. Credentials and tokens are encrypted server-side; they never return to the browser.
5. UniSora discovers subscriptions, persists selected subscriptions, and exposes ARM resources and Cost Management data.

The OAuth route remains available for deployments that prefer delegated Microsoft
authorization.

Routes are organization/user scoped and return `REAUTH_REQUIRED` when the
refresh token is missing or revoked. Azure cost permission failures are shown as
unavailable rather than zero.
