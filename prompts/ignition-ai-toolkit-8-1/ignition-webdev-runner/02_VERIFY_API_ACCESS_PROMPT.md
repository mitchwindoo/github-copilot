# Verify Ignition Web Dev Runner Access

Replace the three bracketed values, then copy the complete prompt into your AI agent.

```text
Check the health of my Ignition Web Dev runner and give me a quick summary of what its API can do.

Gateway URL: <PASTE_GATEWAY_URL>
Host project: <PASTE_PROJECT_NAME>
Runner endpoint: <PASTE_GATEWAY_URL>/system/webdev/<PASTE_PROJECT_NAME>/llmImport
Runner token: <PASTE_RUNNER_TOKEN>

POST the health request to the runner endpoint. Tell me whether the gateway is reachable and healthy, report the runner and stack versions, and summarize the API's main capabilities in no more than 8 bullets. If the connection fails, report the endpoint, HTTP status, and response body so I can troubleshoot it.
```
