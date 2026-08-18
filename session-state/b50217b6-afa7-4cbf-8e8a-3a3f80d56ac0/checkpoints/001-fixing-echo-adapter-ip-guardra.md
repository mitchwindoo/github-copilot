<overview>
The user asked to add guardrails to the FactoryTalk Logix Echo test setup tooling so that a second Echo controller/adapter configuration never collides with a PLC/controller Echo already has running: it must reuse the NIC Echo is already using, and pick another IP already configured on that NIC that Echo isn't using — not a synthesized free IP on the subnet. If IP assignment fails, the fix is to restart the FactoryTalk Logix Echo Service and Message Broker and retry. Mid-implementation, the user corrected a core misunderstanding: Echo can only bind to IPv4 addresses **already assigned to a NIC** in Windows — it cannot use an arbitrary free address on the subnet that was never added to the adapter — so the "next available IP" logic needed to be replaced with "next existing-but-unused adapter address" logic. This correction is currently being implemented.
</overview>

<history>
1. User requested guardrails: detect the NIC an already-configured Echo PLC is using, pick the next available IP on that NIC, and never collide with an existing config; also handle the "restart Echo Message Broker/Service and retry" fix for failed IP assignment.
   - Explored repo structure: found `docs/runbooks/setup-echo-adapter.ps1`, `docs/testing/logix-echo-setup.md`, `tests/harness/LogixEchoHarness/EchoChassis.cs`, `Program.cs`, `.github/instructions/test-harness.instructions.md`, `docs/runbooks/troubleshooting.md`.
   - Inspected live machine: found FactoryTalk Logix Echo Message Broker and Service running, `Ethernet` adapter already had 5 IPs (192.168.127.5-9) configured — this is the live Echo NIC.
   - Discovered the original script's critical flaw: it called `Remove-NetIPAddress` to wipe ALL existing IPs off the adapter before assigning the new one — this would break any controller already using those addresses.
   - Rewrote `docs/runbooks/setup-echo-adapter.ps1`:
     - Added `-RestartEchoServices` switch and a `Restart-EchoServices` function (stops Service then Broker, starts Broker then Service, per Rockwell guidance).
     - Added auto-detection of the adapter already hosting the previously-saved `ACS_LOGIX_ECHO_IP`.
     - Added `Get-EchoAssignedAddresses` (calls new harness command) and (at the time) `Get-NextAvailableIPv4` to compute next free subnet IP — **this was the part later found to be wrong**.
     - Changed adapter configuration to only ADD the new IP via `New-NetIPAddress`, never removing existing addresses.
     - Added automatic retry-after-Echo-restart if `New-NetIPAddress` fails.
   - Added new C# harness capability: `EchoChassis.ListAssignedAddressesAsync()` (queries all chassis/controllers via `IServiceApiClientV2` for their bound IPv4 addresses) and wired up a new `echo-list-addresses` CLI command in `Program.cs`, plus updated the `Usage()` text.
   - Fixed a compile error (`IPAddress` object vs `string` mismatch — needed `.ToString()`).
   - Built the harness successfully (`dotnet build` succeeded after fix; there's a pre-existing, unrelated `NU1603` package-version warning-as-error on this machine which was bypassed only for local verification, not fixed/changed).
   - Ran `dotnet run -- echo-list-addresses` against the live Echo service — succeeded, returned no addresses (no chassis currently active).
   - Verified PowerShell script parses without syntax errors via `[System.Management.Automation.Language.Parser]::ParseFile`.
   - Updated documentation: `docs/testing/logix-echo-setup.md` (added guardrail description, restart-and-retry guidance), `docs/runbooks/troubleshooting.md` (added troubleshooting entries), `.github/instructions/test-harness.instructions.md` (noted new guardrail behavior).
   - Attempted to actually run the script live against the `Ethernet` adapter — failed because the current PowerShell session was not elevated (not admin), so live adapter mutation could not be tested end-to-end.
   - Delivered a summary of work to the user.

2. User corrected: "the echo device can only be configured onto an IP address already associated with a NIC, we aren't looking for a free IP on the subnet, we are looking for another IP configured on the NIC that echo is not using."
   - Currently mid-fix: replacing the "synthesize next free subnet IP" logic (`Get-NextAvailableIPv4`) with a new `Select-UnusedAdapterAddress` function that filters `$existingAdapterIPs` (addresses already configured on the NIC) down to those not in `$echoAssigned` (addresses Echo already has bound to a controller), returning the first such address, or `$null` if all existing NIC addresses are already claimed by Echo.
   - Replaced `Get-NextAvailableIPv4` function definition with `Select-UnusedAdapterAddress`.
   - Rewrote the "Prompt for IP address if not provided" block: now suggests an existing-but-Echo-unused address from the adapter (or, if none exists, warns the operator that a new address must be manually added to the NIC and prompts for one on the same subnet).
   - Updated validation logic in both the interactive and `-IPAddress` (explicit param) code paths to check against `$echoAssigned` only (not a broader `$inUseAddresses` combining adapter + Echo, since reusing an adapter address not claimed by Echo is now the desired/expected case).
   - Added `$addressAlreadyOnAdapter = $existingAdapterIPs -contains $IPAddress` flag after IP selection, intended to let the "configure the adapter" step skip `New-NetIPAddress` when the address is already present on the NIC (this part is not yet fully wired in — see Next Steps).
   - Was in the process of viewing/updating the "Configure the adapter" block (`Add-EchoAdapterAddress` function and its try/catch) to conditionally skip adding the IP when `$addressAlreadyOnAdapter` is true, when the conversation was compacted.
</history>

<work_done>
Files updated:
- `docs/runbooks/setup-echo-adapter.ps1`: Fully reworked guardrail script.
  - Added `-RestartEchoServices` switch param and `Restart-EchoServices` function.
  - Added adapter auto-detection based on previously saved `ACS_LOGIX_ECHO_IP`.
  - Added `Get-EchoAssignedAddresses` (calls harness `echo-list-addresses`).
  - Replaced `Get-NextAvailableIPv4` (WRONG: synthesized free subnet IPs) with `Select-UnusedAdapterAddress` (CORRECT: filters existing adapter IPs down to those Echo isn't using).
  - Rewrote IP-selection prompt/validation blocks (interactive and explicit `-IPAddress` param paths) to use the corrected selection logic and validate only against `$echoAssigned`, not adapter-existing addresses.
  - Added `$addressAlreadyOnAdapter` flag (**not yet consumed** — the adapter-configuration block below it still unconditionally calls `New-NetIPAddress`, which needs updating).
  - Adapter configuration no longer removes existing IPs (kept from earlier work); still needs the conditional skip-if-already-present logic added.
  - Updated header comment-based help (`.SYNOPSIS`/`.DESCRIPTION`) already reflects "pick address already on adapter" model in most places but should be double-checked against the final logic once done.
- `tests/harness/LogixEchoHarness/EchoChassis.cs`: Added `ListAssignedAddressesAsync()` static method (near end of class, before `SelectControllerNetwork`). Fixed `IPAddress` → `string` conversion bug via `.ToString()`.
- `tests/harness/LogixEchoHarness/Program.cs`: Added `echo-list-addresses` case in `Main`'s switch, added `EchoListAddressesAsync()` private method, updated `Usage()` text to list the new command.
- `docs/testing/logix-echo-setup.md`: Added guardrail description section and restart-and-retry guidance (written before the user's correction — **may need revision** to reflect "pick unused adapter address" instead of "next available subnet IP"; not yet updated post-correction).
- `docs/runbooks/troubleshooting.md`: Added two troubleshooting entries about the guardrail rejecting addresses and the restart-and-retry flow (also written pre-correction, **may need revision**).
- `.github/instructions/test-harness.instructions.md`: Added a paragraph describing the new guardrail behavior (also pre-correction, **may need revision**).

Verification performed:
- PowerShell syntax validated via `Parser::ParseFile` — no errors (as of pre-correction version; needs re-validation after latest edits).
- C# harness built successfully with `dotnet build` (bypassing an unrelated pre-existing `NU1603` warning-as-error via `/p:NoWarn=NU1603 /p:TreatWarningsAsErrors=false` — this was NOT a permanent fix, just for local verification; the `.csproj` was not modified).
- `dotnet run -- echo-list-addresses` executed successfully against the live Echo service, returned no addresses (expected, since no chassis was active).
- Live adapter mutation via the script could NOT be tested — current shell is not elevated/admin.

Current state / issues:
- The script edit is **incomplete**: `Select-UnusedAdapterAddress` and the IP-selection prompt/validation were updated, but the subsequent "Configure the adapter" block (around what was originally lines ~405-450, containing `Add-EchoAdapterAddress` and its try/catch) still unconditionally calls `New-NetIPAddress`, which will fail or be redundant when the address is already present on the adapter (the common/expected case now). This needs to be fixed next.
- Documentation files (`logix-echo-setup.md`, `troubleshooting.md`, `test-harness.instructions.md`) describe the OLD "next available subnet IP" behavior in places and need to be revised to match the corrected "existing but Echo-unused adapter address" model.
- PowerShell syntax has not been re-validated since the latest edits (in progress at compaction time).
- No live end-to-end test of the corrected script has been performed (no admin shell available).
</work_done>

<technical_details>
- **Core correction**: FactoryTalk Logix Echo's `IServiceApiClientV2.ListAvailableEthernetAddresses()` only enumerates IPv4 addresses that Windows has ALREADY assigned to a NIC — Echo does not create or use arbitrary "next free" addresses on a subnet. Therefore the guardrail must select among the adapter's existing configured addresses (filtering out loopback/link-local and whatever Echo already has bound to a live controller), not synthesize a new host address like `.2`, `.3`, etc.
- If no unused address exists on the adapter (all are claimed by existing Echo controllers), a NEW address genuinely does need to be added to the NIC (via `New-NetIPAddress`) — this is a legitimate fallback path, but distinct from the "guardrail default" path of just picking an existing free one.
- The live test machine's `Ethernet` adapter (`Realtek PCIe GbE Family Controller`) already has 5 static IPs configured: 192.168.127.5, .6, .7, .8, .9 — this is the real Echo-configured NIC on this machine, discovered via `Get-NetIPAddress`.
- FactoryTalk Logix Echo services on this machine: `FactoryTalk Logix Echo Message Broker` (no dependencies) and `FactoryTalk Logix Echo Service` (depends on Message Broker) — both `Automatic` start type, running. Correct restart order: stop Service, then Broker; start Broker, then Service (dependency order).
- Restart fix path (per user's original instructions and existing `troubleshooting.md` entry): "if a controller fails to set its IP address... restart Echo after confirming the address is present." Implemented as automatic retry-once-after-restart in the script, plus an explicit `-RestartEchoServices` switch to force it proactively.
- Harness structure: `EchoChassis.cs` binds to the Rockwell `IServiceApiClientV2` (EchoSDK) — the repo's custom instructions call this "one of only two files in this repository that bind to a Rockwell SDK," so changes here are treated carefully. New method reads `ChassisData`/`ControllerData` via `ListChassis()` → `ListControllers(chassisGuid)` → `controller.IPConfigurationData.Address` (an `IPAddress` object, not `string` — caused a compile error, fixed with `.ToString()`).
- `Program.cs` exit codes are load-bearing: 0 = passed, 1 = test failure, 2 = infrastructure failure. The new `echo-list-addresses` command returns `ExitPassed` (0) always (informational listing, not a test).
- Pre-existing, unrelated build issue: local machine has `RockwellAutomation.LogixDesigner.CSClient` resolved to `2.2.1109` but `.csproj` pins `>= 2.1.974`, triggering `NU1603` warning-as-error. This is a local package source/version mismatch and was NOT fixed as part of this task (out of scope; per `TreatWarningsAsErrors=true` in the `.csproj`, itself intentional per repo conventions) — only bypassed locally to verify the new code compiles.
- The `docs/runbooks/setup-echo-adapter.ps1` script locates the harness executable via `Get-ChildItem` relative to `$PSScriptRoot\..\..\tests\harness`, filtering for `LogixEchoHarness.exe`, to invoke `echo-list-addresses`. If the harness isn't built or Echo is unreachable, `Get-EchoAssignedAddresses` returns `$null` and the script falls back with a warning (degrades gracefully rather than failing hard).
- Repo custom instructions (`.github/instructions/*.md`) apply per-path: `l5x-source.instructions.md` (src/**), `rag-tooling.instructions.md` (tools/**), `structured-text.instructions.md` (src ST files), `test-harness.instructions.md` (tests/**), `change-control.instructions.md` (changes/**, workflows). None of these blocked the current PowerShell/C# work directly but were reviewed for context.
- No admin PowerShell session is available in this environment/session, so the adapter-mutation logic in the script has only been unit-tested logically (dot-sourced helper function tests) and never run end-to-end against a real NIC.
</technical_details>

<important_files>
- `C:\Users\MitchellLandreth\Git-Local\AB-Logix-CI-CD\docs\runbooks\setup-echo-adapter.ps1`
  - The primary guardrail script being corrected; central to this entire task.
  - Currently mid-edit: `Select-UnusedAdapterAddress` function added, IP-prompt/validation logic corrected, but the adapter-configuration block (`Add-EchoAdapterAddress` call site) still needs to be made conditional on `$addressAlreadyOnAdapter` so it doesn't try to re-add an address that's already there.
  - Key sections: `Restart-EchoServices` function (~line 89), `Get-EchoAssignedAddresses` function (~line 145), `Select-UnusedAdapterAddress` function (replacing old `Get-NextAvailableIPv4`), adapter auto-detection block (~line 200s), IP-address selection/prompt block (~line 305-400s, just edited), "Configure the adapter" block with `Add-EchoAdapterAddress` (still needs updating — was ~line 405-450 before latest edit, line numbers now shifted).
- `C:\Users\MitchellLandreth\Git-Local\AB-Logix-CI-CD\tests\harness\LogixEchoHarness\EchoChassis.cs`
  - New `ListAssignedAddressesAsync()` static method added (queries live Echo chassis/controller addresses). This is what the PowerShell script relies on to know which adapter addresses Echo already has claimed.
  - Fixed compile bug: `controller.IPConfigurationData?.Address` is an `IPAddress` object, needed `.ToString()`.
- `C:\Users\MitchellLandreth\Git-Local\AB-Logix-CI-CD\tests\harness\LogixEchoHarness\Program.cs`
  - Added `echo-list-addresses` CLI command (`EchoListAddressesAsync()` method + switch case + usage text). This is the CLI surface the PowerShell script shells out to.
- `C:\Users\MitchellLandreth\Git-Local\AB-Logix-CI-CD\docs\testing\logix-echo-setup.md`
  - Documentation describing Echo setup/guardrails; updated with pre-correction language about "next available IP" that likely needs revision to "next unused adapter address."
- `C:\Users\MitchellLandreth\Git-Local\AB-Logix-CI-CD\docs\runbooks\troubleshooting.md`
  - Added troubleshooting entries referencing the guardrail and restart fix; may need wording tweaks post-correction (references to "reused address" logic should be double-checked but the core troubleshooting fix guidance — restart Message Broker/Service — remains accurate and unaffected by the correction).
- `C:\Users\MitchellLandreth\Git-Local\AB-Logix-CI-CD\.github\instructions\test-harness.instructions.md`
  - Added a paragraph on the guardrail; likely needs minor wording revision to match "existing adapter address" model instead of "next available address."
</important_files>

<next_steps>
Remaining work:
1. **Finish fixing `setup-echo-adapter.ps1`'s adapter-configuration block**: Update the `Add-EchoAdapterAddress`/try-catch section to check `$addressAlreadyOnAdapter` — if true, skip `New-NetIPAddress` entirely (the address is already there; just ensure the adapter is enabled) and go straight to setting `ACS_LOGIX_ECHO_IP`; if false, proceed with adding the new address as before (with the existing restart-and-retry-on-failure fallback).
2. **Update the summary/status messages** near the end of the script (the "Configuration Summary" block) to reflect whether the address was newly added vs. already present.
3. **Re-validate PowerShell syntax** via `[System.Management.Automation.Language.Parser]::ParseFile` after these edits.
4. **Re-run the C# build** (already succeeded before, should still be fine since C# wasn't touched in this latest round, but worth a quick re-check) — no changes needed unless further harness changes are made.
5. **Revise documentation** (`docs/testing/logix-echo-setup.md`, `docs/runbooks/troubleshooting.md`, `.github/instructions/test-harness.instructions.md`) to replace "next available IP on the subnet" language with "next existing adapter address Echo isn't using" to match the corrected behavior.
6. **Attempt final validation**: re-run the dot-sourced logic test for `Select-UnusedAdapterAddress` (similar to the earlier `Get-NextAvailableIPv4` unit test) to confirm it correctly picks e.g. `.6` when `.5` is Echo-assigned and `.6`-`.9` are free-on-adapter-but-Echo-unused, given the real adapter state (192.168.127.5-9).
7. Note to user: full end-to-end live testing of adapter IP assignment still cannot be performed in this session due to lack of an elevated/admin PowerShell shell; this should be flagged as untested when work is delivered.

Immediate next action: continue editing the "Configure the adapter" block in `setup-echo-adapter.ps1` to consume `$addressAlreadyOnAdapter` and skip redundant `New-NetIPAddress` calls, then re-validate syntax.
</next_steps>