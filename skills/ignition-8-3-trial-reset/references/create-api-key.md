# Create an API key in the browser

Read this when no usable token is available for the intended Gateway. Use the host's available browser or computer-use tool and follow its operating instructions. Work from the current page's labels and controls; inspect the page again after navigation and saves. Do not assume fixed coordinates or fabricate browser API calls. If browser control is unavailable, guide the user through the same steps and resume after they finish.

## Offer to create the key

If the user has not already requested or approved key creation, ask: "I don't have an API key for this Gateway yet, and I need one to reset the trial. Would you like me to create one for you using computer use?" For API setup alone, say "connect to the Gateway API" instead of "reset the trial". Wait for an answer. If the user agrees, proceed with the browser workflow. If they decline, let them supply a token or complete setup themselves. Do not repeat the question when permission was already given.

## Find the Gateway and log in

Use the user's Gateway URL or an existing Gateway tab first. Otherwise, for a local installation, try `http://localhost:8088`. For Docker, inspect `docker ps` and use the published host port, such as `8188` in `8188->8088`. Confirm the Gateway name and 8.3 version before changing settings. If the address is unknown or ambiguous, ask: "Is your Ignition Gateway on this computer, or what URL do you use to open it?"

`localhost` refers to the machine running the browser or script. A browser on the user's computer and an agent running in a container or on another machine may need different addresses for the same Gateway. Confirm both reach the intended installation. Use HTTPS for a remote Gateway.

Open the Gateway and reuse its authenticated session. If login is required and the user has supplied a username and password for this Gateway, enter them through the browser tool and submit the login form. Do not repeat the credentials in messages, logs, or skill files. If credentials are unavailable, say: "I've opened the Gateway login page. I don't have your username or password, so please sign in there and I'll continue creating the API key." Resume once the authenticated page is visible. Let the user complete any MFA or other interactive login challenge. The account needs permission to edit security settings and create API keys. If the necessary controls are unavailable, ask for a suitably privileged login.

## Create the security level

1. Navigate to **Platform > Security > Levels**, which may appear as **Security Levels**.
2. Inspect existing levels. Reuse a level intended for this API integration if its permissions match the requested work. Otherwise select **Add Level** and name it, for example, `IgnitionAPI`. The name is a label, not a required literal.
3. Click away from the name field to commit the edit, then select **Save Changes**. Verify the new level appears in the saved tree. Record its full path for selection on the next pages.

## Assign Gateway permissions

Open **Platform > Security > General Settings** and locate the Gateway Access, Read, and Write permission selectors. For the read-and-reset workflow, configure the API security level for Gateway read and write access. These are broad Gateway permissions, not a trial-only permission.

Add the level without removing existing administrator access. Inspect each selector's "at least one" versus "all" matching rule. Adding a level to an "all" rule can exclude existing users and still leave the API key unable to connect. Preserve the existing access logic; if the rule cannot accommodate the new level without changing who has access, resolve that specific configuration with the user before saving.

If Gateway Access is already Public, leave it as configured. If restricted, ensure the API level has effective access. Never make Read or Write Public to get the key working. Write permission also grants Read, and Read grants Access, so separate selections may be redundant on the installed version.

Settings may save automatically. Check for a saved indicator or use the visible save control, then revisit the selectors to verify the intended level persisted.

## Create the token

1. Open **Platform > Security > API Keys** and select **Create API Key**.
2. Choose **Basic Token**, then **Next** if shown.
3. Enter a descriptive, unused name, such as `IgnitionTrialAgent`. It does not need to match the security level name.
4. Set **Require secure connections for API Keys** for the connection being used. For a local development Gateway accessed over loopback HTTP, turn it off for this key. For HTTPS or a remote Gateway, leave it on. Do not disable a Gateway-wide security setting as a substitute.
5. Select the security level configured above. Leave the required default Authenticated level selected.
6. Select **Create API Key** once. If the result is uncertain, inspect the page and key list before attempting another creation.

## Save the token before closing

The token appears only once. Capture its complete displayed value, including any name prefix and colon. Use the tool's supported secret handling to place it in the session environment or a secret store outside the skill. Do not echo it in the response, logs, or exported screenshots. If the tool cannot transfer it privately, leave the dialog open and ask the user to store it and load it through the masked PowerShell prompt in SKILL.md.

Only after storage succeeds, select **I have stored my API Key for future reference**, then **Done**. Verify the new key is listed and enabled. An existing key's secret cannot be recovered from the list. If its secret was lost, create a distinctly named replacement; do not delete a key that another service may use.

## Verify and continue

With `IGNITION_API_TOKEN` set in the execution environment, run from the skill directory:

```sh
python scripts/trial.py --gateway http://localhost:8088
```

Substitute the verified URL. This performs GET only. Confirm the response contains a boolean `expired` and numeric `trialSecondsLeft`. For 401/403, check the complete token, enabled state, assigned level, effective permissions, and HTTP/HTTPS setting before creating another key. A successful browser login alone does not verify API authentication.

Report the Gateway URL, key name, security level, and test outcome without the token. Resume the already requested trial action. Creating a key does not itself authorize a reset or a schedule when the user requested only API setup.

The workflow follows the [API key documentation](https://www.docs.inductiveautomation.com/docs/8.3/platform/security/api-keys), [Gateway permission definitions](https://www.docs.inductiveautomation.com/docs/8.3/platform/security/gateway-general-security-settings), and [security level documentation](https://www.docs.inductiveautomation.com/docs/8.3/platform/security/identity-provider-authentication-strategy/security-levels).
