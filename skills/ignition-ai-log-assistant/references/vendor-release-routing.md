# Vendor And Release Routing

Use this reference before making version-specific bug, fix, latest-version, or compatibility claims.

## General Rules

- Start from the live module inventory when available.
- Route only installed module IDs/names from `gatewayInfo.modules.modules[]`.
- Note when no Cirrus, Sepasoft, or third-party modules are present instead of implying those vendor sources apply to the current Gateway.
- Treat source routing, page reachability, and exact version/family matching as separate gates.
- If a routed page is unreachable or lacks the exact module version/family evidence, report missing current evidence and search additional official/vendor sources.
- Do not infer that no matching public bug or fix exists from one missing or unreachable page.

When Python is available and you have a saved `gatewayInfo` response or module-list JSON, use `scripts/route_module_sources.py <gatewayInfo-or-modules.json>` to build a deterministic IA/Cirrus/Sepasoft/unknown-vendor source-routing plan. Treat the output as a routing plan only: it does not fetch current pages or confirm a latest version, open bug, fix, or compatibility status.

## Inductive Automation

- Search official Ignition release notes: https://inductiveautomation.com/downloads/releasenotes
- Build the exact target-version release-note URL from the live parsed Ignition version, for example `/downloads/releasenotes/8.1.53`.
- Treat the release-note root/latest page as current context, not target-version confirmation.
- Check exact-version and later-version release notes for fixed issues that match the logger/module/symptom.
- Use Ignition 8.1 docs, IA support articles, IA forum threads, and IA Canny as supporting evidence.
- Do not rely on a central IA public known-bug database unless a current official source for that database is found; use official release notes and cited sources instead.

## Cirrus Link And MQTT Modules

- If module IDs/names suggest Cirrus Link, Chariot, MQTT Engine, MQTT Transmission, MQTT Distributor, MQTT Recorder, or related Cirrus modules, search Chariot/Cirrus Link Ignition 8.x-compatible release notes: https://docs.chariot.io/display/CLD80/Ignition%2B8.x%2BCompatible%2BRelease%2BNotes
- Match against the exact module family and version when the version is available.
- If `gatewayInfoModuleVersions` is absent or the runner only exposes module IDs/states, say that module versions were not captured and request module-version evidence before making version-specific claims.
- Use the installed `moduleVersion` block first.
- Inspect later Chariot/Cirrus version blocks only as possible later-fix evidence.
- Do not treat the top/latest block as installed-version evidence unless it equals the captured `moduleVersion`.
- When multiple Cirrus Link modules are present, compare their `moduleVersion` values first.
- Chariot docs state Cirrus Link module versions should match on an Ignition Gateway; flag mismatches and missing module-version evidence before version-specific bug matching.
- If IA release notes mention bundled Cirrus Link MQTT modules for Ignition Cloud Edition, treat that as platform/bundled-module context. For installed Cirrus module bug/fix matching, still use Chariot/Cirrus release notes and match by module family and `moduleVersion`.

## Sepasoft And MES Modules

- If module IDs/names suggest Sepasoft, MES Production, OEE Downtime, Batch Procedure, Track & Trace, SPC, Settings & Changeover, Document Management, Business Connector, Web Services, or Interface for SAP ERP, search Sepasoft Ignition 8.1 release notes and Sepasoft docs/download archive pages.
- Match the Sepasoft module family and `moduleVersion` first.
- Record Sepasoft's highest-tested and minimum-required Ignition versions when the page provides them.
- If the target Ignition version is newer than Sepasoft's highest-tested version, say compatibility evidence is not an exact target-version match and request current vendor support/release evidence before making version-specific bug claims.
- Do not treat IA platform release notes as the primary source for Sepasoft module fixes.

## Unknown Third-Party Modules

- Identify the vendor from module ID/name.
- Search official vendor release notes, docs, support KB, and forums.
- Mark source confidence.
- Vendor docs/release notes outrank forum anecdotes.
- Forum posts can still be useful leads when clearly labeled.
