# Ignition 8.1 Known Issues

Evidence reviewed 2026-09-05. Scope: reports explicitly tied to Ignition 8.1.40–8.1.53. Use only for an observed matching failure or an explicit version-compatibility question. Identify the Ignition patch and affected Designer/Workstation/browser environment; the runner's `0.3.x` version is separate.

Scan the index, then read the matching entry. A reported patch is not an exhaustive affected-version range. Vendor-confirmed means a shipped correction; user-confirmed means a reporter described success; proposed/unresolved means success was not established. Do not infer a patch from posting date or apply another installation's result as proof. Maintained 8.1 documentation is not a frozen specification for every patch.

## Contents

| Symptom / search terms | Reported patch | Section |
|---|---|---|
| `rootViewDefaultSize`, unable to get view config | 8.1.40, 8.1.42 | Designer Loading Race |
| Missing Perspective editor, Server 2012 | 8.1.42 | Designer Client Environment |
| Nested params not evaluated, `inputBehavior` | 8.1.45 report | Nested Parameter Workaround |
| Child starts with saved `tagPath` | 8.1.44 | Initial Tag Context |
| Pipe color bindings shift after reorder | 8.1.43, 8.1.44, 8.1.45 | Pipe Binding Assignments |
| Chrome memory error, Carousel | 8.1.42 | Browser Memory And Frozen Sessions |
| Existing sessions freeze, fresh sessions work | 8.1.45 | Browser Memory And Frozen Sessions |
| Script initialization deadlock | 8.1.46 | Scripting Regression |
| First style class fails | 8.1.47 | Stylesheet Syntax |
| Missing backfilled history, `Good_Backfill` | 8.1.50 | History Quality Filtering |
| Repeated Gateway Network disconnects | 8.1.52 | Gateway Network Disconnects |
| Explicit upgrade review: charts, clicks, docks | Target-dependent | Focused Upgrade Checks |

## Designer Loading Race

**Evidence:** reports on 8.1.40 and 8.1.42 include `rootViewDefaultSize` being undefined before “Unable to get the view config.” IA identified a loading race and shipped a correction in 8.1.44. Restarting Designer was a temporary user workaround, not the repair.

**Action:** match the full error sequence and build before changing the page. If an upgrade is in scope, evaluate the release containing the correction and verify that the affected view opens. Other view-config errors can have different causes; do not require every build task to reproduce this historical incident.

Sources: [8.1.40 report](https://forum.inductiveautomation.com/t/i-cannot-open-pages-in-perspective-sometimes/91111), [8.1.42 reports and IA diagnosis](https://forum.inductiveautomation.com/t/help-unable-to-get-the-view-config/85469), [8.1.44 release notes](https://inductiveautomation.com/downloads/releasenotes/8.1.44).

## Designer Client Environment

**Evidence:** a user on 8.1.42 / Windows Server 2012 could run browser pages but could not use the Perspective editor; another client worked. IA identified unsupported Chromium/OS compatibility. A completed OS upgrade was not reported.

**Action:** inspect the affected client's supported environment before rewriting project resources or reinstalling the Gateway. Workstation's 8.1.44 browser changes and Windows 10 / Server 2016 minimums are separate guidance, not proof that an Ignition upgrade alone repairs this Designer installation.

Sources: [Report and IA diagnosis](https://forum.inductiveautomation.com/t/designer-project-menus-not-appearing/92849), [8.1.44 Workstation changes](https://inductiveautomation.com/downloads/releasenotes/8.1.44).

## Nested Parameter Workaround

**Evidence:** an explicit 8.1.45 complaint appears in a nested Embedded View parameter discussion. A different participant reported no recurrence after an IA-support suggestion to change the lowest-level view's `inputBehavior` from `replace` to `merge`; that successful participant's patch was unspecified.

**Action:** reproduce the affected parameter handoff. Consider `merge` only if retaining omitted default keys fits the input contract; confirm cold load and relevant equipment switching. It is a reported workaround, not a confirmed 8.1.45 fix. `after-parent` is not a universal substitute. Use the page-behavior reference for the semantics when needed.

Source: [Discussion and qualified workaround](https://forum.inductiveautomation.com/t/perspective-nested-embedded-views/85342).

## Initial Tag Context

**Evidence:** an 8.1.44 report describes a child initially using its saved design-time `tagPath` before the parent binding arrives, including with `after-parent`. No solution was confirmed.

**Action:** inspect initial provider/equipment context and guard commands until that context is valid. Inert saved defaults and initialization checks are proposed safeguards; verify the actual first target in the reproduction rather than claiming a vendor fix.

Source: [Saved tag-path report](https://forum.inductiveautomation.com/t/perspectives-embedded-view-params/99072).

## Pipe Binding Assignments

**Evidence:** participants reported color bindings shifting after pipe z-order or structural edits on 8.1.43, 8.1.44, and 8.1.45. No in-range fix was verified. Later 8.3 replies do not establish an 8.1 resolution.

**Action:** preserve the normal resource backup/drift protections, reopen the changed view, and verify pipe-to-tag assignments against known states alongside the existing geometry check. Limit corrections to the affected mappings; do not claim a patch remedy without matching evidence.

Source: [Pipe-binding discussion](https://forum.inductiveautomation.com/t/bug-pipe-bindings-does-not-follow-the-pipe-if-the-z-order-of-pipes-is-changed/101896).

## Browser Memory And Frozen Sessions

**Evidence:** an 8.1.42 Chrome out-of-memory report involved a lazy-loaded Carousel rotating every 30 seconds and explicitly did not use fade. Root cause remained unresolved. An 8.1.45 Citrix/Edge report described frozen existing sessions while fresh sessions worked; that original case also remained unresolved.

**Action:** capture the affected browser's error/memory evidence and corresponding Gateway state. Treat JVM used heap and OS process memory as different measurements. Narrow the failing page/component first. A prolonged comparison or static-versus-Carousel experiment is appropriate only if required by this incident's investigation and authorized scope.

Do not prescribe a fade change, memory increase, NIC change, or whole-UDT-binding rewrite from these reports. The freeze thread's later NIC result had no exact patch; a separate binding result was on 8.3.0-rc1.

Sources: [Carousel memory report](https://forum.inductiveautomation.com/t/memory-error-perspective-client-session-in-chrome-browser/101903), [Mixed-version freeze discussion](https://forum.inductiveautomation.com/t/recurring-intermittent-perspective-freeze/111904).

## Scripting Regression

**Evidence:** IA withdrew 8.1.46 after a script-initialization change could cause a rare deadlock. 8.1.47 reverted the change. This is a vendor-confirmed rollback. The 8.1.47 release notes also carry forward improvements from 8.1.46; not every listed item originated in 8.1.47.

**Action:** for a matching scripting failure, record the build and initialization evidence. If version remediation is authorized, evaluate the supported release containing the rollback and verify affected scripting/page behavior. The host-builder must not silently upgrade Ignition as part of an ordinary page build.

Sources: [IA withdrawal and rollback announcement](https://forum.inductiveautomation.com/t/8-1-46-pulled-8-1-47-emergency-release/102920), [8.1.47 notes](https://inductiveautomation.com/downloads/releasenotes/8.1.47), [Release history](https://docs.inductiveautomation.com/docs/8.1/new-in-this-version).

## Stylesheet Syntax

**Evidence:** an 8.1.47 user reported a failing first style class and a dummy-class workaround. The accepted resolution was removing an extra `}` from `stylesheet.css`; another installation on the same patch had not reproduced it.

**Action:** inspect stylesheet syntax and the applied browser rule. Correct the actual syntax issue when present and verify the intended style. Do not preserve a disposable first class as the fix or assume a platform defect from the symptom alone.

Source: [User-confirmed CSS correction](https://forum.inductiveautomation.com/t/first-style-does-not-work/115377).

## History Quality Filtering

**Evidence:** an 8.1.50 report describes stored backfilled values excluded by `queryTagHistory` with `ignoreBadQuality=True`, involving `Good_Backfill` code 203. A tall-query/filter/reshape workaround was proposed; a PowerChart repair was not confirmed.

**Action:** compare stored-data evidence and query quality-filter settings before diagnosing a rendering delay. Keep the existing historian evidence requirements. A replacement query/filter needs verification against the required quality semantics; do not claim it repairs PowerChart or lower quality requirements just to draw a chart.

Source: [Backfill query discussion](https://forum.inductiveautomation.com/t/querytaghistory-with-good-backfill/113220).

## Gateway Network Disconnects

**Evidence:** a production 8.1.52 report matched IGN-15463, frequent Gateway Network disconnects associated with a Jetty update. A matching vendor correction shipped in 8.1.53 on March 24, 2026. No same-site successful retest was reported.

**Action:** match the connection symptom/build before attributing it to page complexity. If version remediation is in scope, evaluate the release containing the fix and verify the affected remote-data/reconnection path. The historical support-provided JAR is not the default repair instruction. A page-building task does not authorize Gateway upgrades or infrastructure changes.

Sources: [Incident and IA response](https://forum.inductiveautomation.com/t/ign-15463-backport-gan-connections-frequently-disconnect-related-to-12-0-27-jetty-upgrade/114205), [8.1.53 shipped correction](https://inductiveautomation.com/downloads/releasenotes/8.1.53).

## Focused Upgrade Checks

Use this section only when the task includes a version change or the relevant feature fails. 8.1.48 notes identify fixes for backgrounded XY Chart updates, chart scrolling, Coordinate Container percent behavior, duplicate clicks, and Workstation secondary-monitor placement. 8.1.53 includes an `alterDock` persistence correction.

Select checks for the features actually used and the symptom being addressed. These release notes do not require a full upgrade matrix, device lab, or repeated regression suite for every new visualization. Once the relevant behavior and the skill's normal delivery checks pass, finish the requested work.

Sources: [8.1.48 notes](https://inductiveautomation.com/downloads/releasenotes/8.1.48), [8.1.53 notes](https://inductiveautomation.com/downloads/releasenotes/8.1.53).
