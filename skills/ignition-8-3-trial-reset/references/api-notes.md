# API notes

The authentication header and documentation locations come from the [Ignition API documentation](https://www.docs.inductiveautomation.com/docs/8.3/platform/gateway/openapi). Token configuration is documented under [API keys](https://www.docs.inductiveautomation.com/docs/8.3/platform/security/api-keys).

The [licensing manual](https://docs.inductiveautomation.com/docs/8.3/platform/licensing-and-activation) describes renewable two-hour trials. Trial expiry can require clients to reconnect after renewal.

Verified against Ignition 8.3.9 on September 5, 2026:

- Authenticated `GET /data/api/v1/trial` returned a JSON object with `licenseMode`, `trialState`, `trialSecondsLeft`, and `expired`, plus emergency and development fields.
- After GET reported `expired: true` and `trialSecondsLeft: 0`, POST to the same route with that complete object as JSON returned HTTP 200.
- A subsequent GET returned `expired: false` and `trialSecondsLeft: 7199`.
- That installation's `/openapi.json` documented GET for this path but omitted POST. The script's reset body is based on the verified request, not a published POST schema.

Inspect the installed version before relying on this behavior elsewhere. Do not claim every 8.3 patch has been tested.
