---
name: allen-bradley-structured-text
description: "Allen-Bradley Logix Structured Text programming skill. Use when asked to design, explain, review, troubleshoot, or provide Studio 5000 Structured Text examples for ControlLogix or CompactLogix PLC functions, routines, AOIs, sequences, state machines, equipment modules, queues, handshakes, alarms, interlocks, Produced/Consumed tags, or SCADA integration. Produces Logix-compatible tag contracts, scan-safe logic, code examples, fault behavior, and commissioning tests. Do not use for Siemens SCL, CODESYS, Beckhoff TwinCAT, or generic IEC 61131-3 code."
argument-hint: "Describe the PLC function, inputs/outputs, sequence, controller/revision, and failure behavior"
---

# Allen-Bradley Structured Text

Design implementation-ready Structured Text for Allen-Bradley ControlLogix and CompactLogix controllers in Studio 5000 Logix Designer. Explain how the function behaves across scans, provide the supporting tag contract, and make assumptions and unresolved hardware details explicit.

## Core Rules

**Default target:** Use revision-neutral Logix syntax and a program-scoped ST routine. Mark revision-specific instructions as `VERIFY`, and recommend an AOI only when repeated use and a stable interface justify one.

1. Target Rockwell Logix syntax and execution semantics, not generic IEC 61131-3 pseudocode.
2. Treat the word "function" as a behavior request. Recommend a routine, Add-On Instruction (AOI), equipment-phase/state routine, or simple inline block based on ownership and reuse.
3. Do not put `VAR`, `VAR_INPUT`, `VAR_OUTPUT`, `END_VAR`, `FUNCTION`, or `FUNCTION_BLOCK` declarations inside a Studio 5000 routine. List controller/program tags or AOI parameters separately.
4. Use `:=` for assignment, `=` and `<>` for comparisons, `AND`/`OR`/`NOT` for Boolean logic, and Logix-compatible `IF`, `CASE`, and `FOR` syntax.
5. Design for cyclic scan execution. Every latch, edge, timer, state transition, command, and acknowledgment must have explicit set and clear behavior.
6. Never assume that a one-scan pulse will cross a controller, network, or SCADA boundary reliably. Use a maintained request/acknowledge handshake or sequence counter for asynchronous systems.
7. Separate sequence logic from physical I/O mapping. Use descriptive internal tags and map module-defined tags in dedicated I/O routines.
8. Keep commands, status, configuration, and diagnostics distinct. Do not overload one tag with multiple meanings.
9. Provide deterministic behavior for invalid data, duplicate records, timeouts, communications loss, controller mode changes, first scan, and reset.
10. Do not present ordinary PLC logic as safety-rated. Safety functions require the correct GuardLogix controller, safety task, safety instructions, validated risk assessment, and site standards.

## Required Discovery

Before finalizing code, determine the following when they affect correctness:

- Controller family and catalog number: ControlLogix, CompactLogix, or GuardLogix.
- Studio 5000 major revision and controller firmware revision.
- Standard task or safety task; continuous, periodic, or event task; task period.
- Desired implementation unit: program routine, AOI, equipment phase, or controller routine.
- Signal ownership: which system writes each command, data field, status, and acknowledgment.
- I/O or communications path: local I/O, remote EtherNet/IP, MSG, Produced/Consumed tags, OPC UA, or SCADA tags.
- Existing UDTs, AOIs, naming conventions, status codes, alarm strategy, and program structure.
- Required startup, shutdown, abort, hold, reset, maintenance, and communications-loss behavior.
- Whether data must survive power loss, download, or SCADA outage; identify required retentive and PLC-resident data.
- Array capacities, valid ranges, string lengths, units, and producer/consumer update guarantees.

If details are missing, do not stall a conceptual example. State conservative assumptions, mark hardware/revision-dependent items as `VERIFY`, and identify exactly what must be confirmed before commissioning.

## Design Workflow

### 1. Define The Behavioral Contract

Restate the requested behavior as:

- Trigger or command.
- Preconditions and permissives.
- Ordered actions.
- Completion condition.
- Abort and fault conditions.
- Reset and retry behavior.
- Data owner for every exchanged value.

For cross-system handshakes, write the ownership sequence explicitly. Example:

1. PLC owns `OperationDataUpdated` and holds it high.
2. SCADA detects a new request and selects one waiting operation.
3. SCADA writes the complete payload and a validity/revision marker.
4. Receiving PLC logic validates and copies the payload to working tags.
5. Receiver owns `OperationDataAck` and holds it high after a successful copy.
6. Requesting PLC drops `OperationDataUpdated` after seeing the acknowledgment.
7. Receiver drops `OperationDataAck` after seeing the request low.

Flag contradictions such as both systems writing the same bit or the prose saying SCADA performs a step while the requested code is intended for the PLC.

### 2. Choose The Logix Structure

Use this decision table:

| Need | Preferred structure |
|---|---|
| One machine-specific sequence | Program-scoped ST routine |
| Repeated encapsulated behavior with a stable interface | AOI |
| Reusable data only | UDT plus routine; a UDT has no behavior |
| Physical input/output normalization | Dedicated I/O mapping routines |
| Multi-step equipment behavior | Explicit `DINT` state machine in a periodic task |
| Controller-to-controller cyclic data | Produced/Consumed UDT with connection sizing verified |
| Infrequent explicit transfer | MSG with `.EN`, `.DN`, `.ER`, timeout, and retry handling |

Avoid AOIs when the behavior is unique, requires frequent online modification, hides too much troubleshooting context, or would need unsafe shared-state side effects.

### 3. Define Tags And Data Types

Provide a table before the code with:

| Tag | Scope | Type | Owner | Direction | Initial value | Description |
|---|---|---|---|---|---|---|

For queues, define an entry UDT and queue metadata separately. A typical operation entry may contain:

- Identity: `JobId`, `OperationId`, `JobNumber`, `Revision`, `PartNumber`, `SerialNumber`.
- Routing: `OperationCode`, `OperationSequence`, `AssignedResourceId`.
- State: `Status`, `Valid`, `DataRevision`, `ErrorCode`.
- Time: timestamps only when the time source, representation, and synchronization strategy are defined.

Prefer numeric IDs and bounded fixed fields for PLC transfer. Avoid duplicating long business strings in the PLC unless operators or outage recovery genuinely need them. Define status values as named constants or a documented `DINT` map, for example `0 = Empty`, `10 = WaitingForData`, `20 = Ready`, `30 = InProcess`, `40 = Complete`, and `900 = Faulted`.

Do not rely on tag order or undocumented UDT layout across Produced/Consumed connections. Keep matching UDT definitions and verify connection size and firmware constraints in Studio 5000.

### 4. Design Scan-Safe Logic

For each code block, check:

- Is this condition level-triggered or edge-triggered?
- Can the action repeat every scan, and is repetition safe?
- Which tag remembers prior state?
- Which state owns each output?
- What clears each output and latched fault?
- Can two records be selected in one scan?
- Can source data change while it is being copied?
- What happens if the request disappears early?
- What happens after a download or transition to Run?

Use a state machine for multi-scan behavior. Reserve state ranges so normal steps, completion, and faults are easy to diagnose. Set outputs by state or assign safe defaults before state logic; do not leave output values dependent on stale execution paths.

### 5. Generate The Structured Text

Code must include:

- A separate required-tag/AOI-parameter table.
- Descriptive names consistent with the user's project style.
- Numbered step comments for significant blocks.
- Explicit bounds checks before array access.
- Explicit status and error codes.
- No unexplained magic numbers.
- No hardware-specific module members unless the exact module and project mapping are known.
- A note for every instruction or signature that must be verified against the user's Studio 5000 revision.

Use this baseline style:

```st
// Step 1: Detect a new maintained request.
RequestRise := Request AND NOT RequestPrevious;
RequestPrevious := Request;

// Step 2: Execute one deterministic state transition per scan.
CASE State OF
    0:
        Acknowledge := 0;
        ErrorCode := 0;

        IF RequestRise THEN
            State := 10;
        END_IF;

    10:
        IF PayloadValid THEN
            State := 20;
        ELSE
            ErrorCode := 101;
            State := 900;
        END_IF;

    20:
        Acknowledge := 1;

        IF NOT Request THEN
            Acknowledge := 0;
            State := 0;
        END_IF;

    900:
        Acknowledge := 0;

        IF Reset AND NOT Request THEN
            ErrorCode := 0;
            State := 0;
        END_IF;

    ELSE
        Acknowledge := 0;
        ErrorCode := 999;
        State := 900;
END_CASE;
```

This is a pattern, not a complete implementation. Payload copying, consistency checks, timeout logic, and exact reset policy must match the contract.

### 6. Explain Operation Across Scans

After the code, describe at least:

- The idle scan.
- The request scan.
- Each processing state.
- The acknowledgment scan.
- Request release and return to idle.
- Invalid-data, timeout, communications-loss, and reset paths.

Use a short transition table:

| Current state | Condition | Action | Next state |
|---|---|---|---|

### 7. Provide Commissioning Checks

Always include tests for:

1. Normal request and acknowledgment.
2. Request held high for many scans; action occurs once.
3. Request removed before completion.
4. No matching queue entry.
5. Multiple matching queue entries.
6. Invalid resource, index, status, or payload revision.
7. Queue at zero entries and maximum capacity.
8. Communications loss before, during, and after transfer.
9. Timeout, reset, and retry.
10. Power cycle, download, Program-to-Run transition, and first scan.
11. Maintenance/fault event while an operation is assigned or active.
12. SCADA outage with only the PLC-resident recovery dataset available.

For online testing, recommend forcing or simulation only under the site's approved commissioning and lockout/tagout procedures. Clearly identify outputs that must be inhibited or simulated.

## Queue And SCADA Handshake Pattern

When the request resembles an operation queue synchronized between SCADA and a cell PLC, use this pattern unless project requirements dictate otherwise.

### Required Supporting Tags

```text
OperationDataUpdated       BOOL    Request owned by the producing system
OperationDataAck           BOOL    Acknowledgment owned by the receiving system
OperationDataUpdatedPrev   BOOL    Previous-scan storage
QueueSyncState             DINT    Diagnostic sequence state
QueueSyncError             DINT    Stable diagnostic code
QueueCount                 DINT    Valid entry count, clamped to array capacity
QueueIndex                 DINT    Loop index
SelectedQueueIndex         DINT    Selected record, -1 when none
WaitingEntryFound          BOOL    Selection result
PayloadValid               BOOL    Complete payload validation result
PayloadRevision            DINT    Monotonic consistency marker
PayloadRevisionCopied      DINT    Revision copied to working data
```

### Deterministic Queue Selection

```st
// Step 1: Initialize the selection result before scanning the queue.
WaitingEntryFound := 0;
SelectedQueueIndex := -1;

// Step 2: Scan only the valid portion of the bounded array.
IF (QueueCount > 0) AND (QueueCount <= QueueCapacity) THEN
    FOR QueueIndex := 0 TO QueueCount - 1 DO
        IF (NOT WaitingEntryFound)
            AND (OperationQueue[QueueIndex].Status = StatusWaitingForData) THEN
            WaitingEntryFound := 1;
            SelectedQueueIndex := QueueIndex;
        END_IF;
    END_FOR;
ELSE
    QueueSyncError := 110;
END_IF;
```

If more than one waiting entry is illegal, count matches and fault instead of silently selecting the first. If priority matters, define a stable sort/selection rule such as lowest operation sequence, oldest accepted timestamp, or explicit PLC queue order.

### Data Consistency

For multi-field payloads shared asynchronously, do not acknowledge a partial update. Use one of these contracts:

- Copy a Produced/Consumed UDT only after a monotonic revision marker is stable across consecutive reads.
- Write `Valid := 0`, update all fields, update `DataRevision`, then write `Valid := 1`; receiver validates and copies before acknowledging.
- Use a command sequence number and echo it as the acknowledgment instead of relying only on Boolean edges.

When possible, prefer a sequence number because it distinguishes a new transaction after restarts and exposes missed or duplicate requests.

## Maintenance And Re-Evaluation

Treat maintenance as a state and routing input, not merely a user-interface flag. Define:

- Who asserts and clears maintenance.
- Whether CNC fault or tool-carousel access asserts it automatically.
- Whether an active operation may finish, must hold, or must abort.
- Whether queued operations are unassigned, rerouted, or left assigned but blocked.
- How SCADA learns that queue evaluation is required.
- How stale commands and acknowledgments are cleared after recovery.

Do not reassign an operation that is already physically in process without an explicit recovery policy. Preserve `JobId` and `OperationId` at the cell for traceability and outage recovery.

## Response Format

Use this order whenever generating or reviewing a PLC function:

1. **Function Summary**: purpose, trigger, completion, and ownership.
2. **Assumptions / VERIFY Items**: missing controller, revision, task, communications, or safety details.
3. **Recommended Structure**: routine, AOI, UDT, state machine, and task placement.
4. **Tag Contract**: names, scopes, types, owners, directions, defaults, and descriptions.
5. **Status And Fault Map**: named states and error codes.
6. **Structured Text**: paste-oriented Logix code with numbered step comments.
7. **Scan Behavior**: state-transition table and handshake timing.
8. **Failure Handling**: timeout, communications loss, invalid data, reset, and first scan.
9. **Commissioning Tests**: normal, boundary, interruption, maintenance, and outage cases.
10. **Open Decisions**: only unresolved choices that materially affect implementation.

## Review Checklist

Before presenting the result, verify:

- The syntax is for Logix Designer, with no generic IEC declaration block in routine code.
- Every tag used by the code appears in the tag contract or is clearly an existing project tag.
- Array indexes are checked before use.
- Every output, acknowledgment, latch, state, and fault has a clear reset path.
- Repeated execution across scans cannot duplicate a one-time action.
- Request and acknowledgment ownership is unambiguous.
- Multi-field data cannot be acknowledged while partially updated.
- State and error values are documented and externally diagnosable.
- Maintenance and communications-loss behavior are explicit.
- Safety-related limitations are stated.
- Revision-dependent instruction signatures are marked for verification rather than invented.