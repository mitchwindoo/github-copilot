# Bounded scale and concurrent writers

## Import one object

The official JSON import accepted one root object, not a document-root array. For many siblings, import a Folder object:

```json
{
  "name": "AreaA",
  "tagType": "Folder",
  "tags": [
    {"name": "Pump-001", "tagType": "UdtInstance", "typeId": "Equipment/Pump"},
    {"name": "Pump-002", "tagType": "UdtInstance", "typeId": "Equipment/Pump"}
  ]
}
```

On the verified build, `successCount` included the Folder and each child. A folder with 100 instances returned 101 successes.

## Conservative measured defaults

Two clean lab runs used 1, 10, and 100 instances with ten members each. These are operating defaults, not Gateway maximums:

- default runtime read batch: 32 paths;
- largest verified read batch: 64 paths, the action's enforced maximum;
- default browse cap: 100 rows;
- largest available browse cap: 500 rows;
- require `complete: true` and `truncated: false` before treating a browse as complete.

At 100 instances, the tested import payload was about 15 KB, the recursive export about 159 KB, import about 26 ms, settle about 32 ms, and 64-path read about 22 ms in one run. Do not copy these timings as a service-level objective. Measure the target.

Before each larger stage, sample official system-performance gauges and thread counts. Stop before the next stage when a caller-approved CPU, heap, blocked-thread, latency, response-size, or timeout threshold is crossed. The tested harness used conservative 75% CPU/heap and more than two blocked threads as stop conditions. Recalibrate for the environment.

The live `currentGauges` response exposed `cpu`, `heapMemory`, and `maxMemory`, although its OpenAPI schema listed a different memory field. Inspect the actual response and calculate heap ratio only when a valid maximum is present.

## Serialize configuration writes

Use a lock keyed at least by provider plus the owning grouped parent. Broaden the key when the storage mapping is uncertain.

In two clean runs, ten synchronized same-property `MergeOverwrite` races produced:

- HTTP and semantic success for both clients in every round;
- six final values from the left client and four from the right;
- no response that identified which value would remain.

Therefore, semantic success from both requests does not prove both intentions survived. Never run same-property configuration writes concurrently.

Concurrent updates to different properties on one definition, different definitions in one folder, and definitions in different folders all survived the tested rounds. Preserve this only as an observation. Continue serializing writes that can touch the same grouped parent because the official import route has no signature precondition and the test is not a platform-level atomicity guarantee.

After any suspected collision, export the complete owning folder, hash it, compare every sibling semantically, and read affected instances. If a request times out, classify the mutation as unknown and inventory before retrying.
