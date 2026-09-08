# Ignition Vision 8.3.8 Environment Gate

Before version-sensitive work, obtain environment identity from at least two independent supported surfaces and require all available values to agree:

- Gateway semantic version: `8.3.8`
- Gateway build: `b2026071409`
- Vision module ID: `com.inductiveautomation.vision`
- Vision module version: `12.3.8.2026071409`

Hash the decisive installation or module artifacts when filesystem access is an approved part of the workflow. Record the live values rather than inferring them from a project export, Designer title, local folder name, or user-supplied version string.

Stop before version-sensitive mutation when:

- a required identity value is unavailable;
- independent surfaces disagree;
- the Vision module is missing;
- the Gateway is another Ignition version or build;
- the result could come from stale local metadata.

Capability discovery and project identity remain separate gates. Exact platform identity does not prove that a particular API route, project, resource format, component, or workflow is available.

## Validated Fresh-Client Runtime

One fixed, freshly launched Vision Client on this exact environment reported:

- Java `17.0.19`;
- implementation `Jython`;
- Jython version `[2, 7, 4]`;
- Python version text beginning with `2.7.4`;
- script scope flags `12`.

The observation used one fixed Client Event Script handler and a server-owned temporary String tag. The Gateway verified the exact Client session and delivery status, required the handler's bounded JSON schema and request identity, observed Good configure/write/delete qualities, and proved the temporary tag root absent afterward.

Use this as a version-specific Client baseline only. It does not prove Designer or Gateway script scope, arbitrary Client launches, another Java vendor/build, arbitrary libraries, threading behavior, or a future Ignition build. Re-observe the target process when any of those details matter.

## Keep Build, Origin, and License Separate

Do not infer configuration provenance or license entitlement from the current Gateway build:

- A clean 8.3.8 configuration and one migrated from the legacy `config.idb` model can run the same 8.3.8 binaries.
- A successful `config.idb` migration proves legacy-configuration history, but it does not prove the exact source Gateway patch unless that version is independently recorded.
- Trial, activated, and expired license behavior require their own live evidence. An absent effective-license record or blank platform edition does not authorize guessing an edition.

Use a fail-closed origin such as `upgraded-legacy-config-prior-version-unqualified` when migration is proven but the exact prior version is not. Preserve the migration record’s digest and summary rather than copying configuration values into customer evidence.
