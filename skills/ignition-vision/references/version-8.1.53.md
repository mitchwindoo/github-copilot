# Ignition 8.1.53 Compatibility Baseline

## Contents

- [Scope](#scope)
- [Resource names and metadata](#resource-names-and-metadata)
- [Vision serialization and layout](#vision-serialization-and-layout)
- [Bindings, components, and Java types](#bindings-components-and-java-types)
- [Client launch and diagnostics](#client-launch-and-diagnostics)
- [Porting to another 8.1 release](#porting-to-another-81-release)

## Scope

Use this reference for actionable cautions when the target is Ignition `8.1.53`. Treat patch-level private classes, serializer behavior, bean setters, and launch libraries as version-specific. Re-run installed-runtime compilation, serialization round trips, fresh-client validation, and screenshot/log checks for a different patch version.

## Resource Names And Metadata

- Validate every slash-delimited project-resource segment with the installed Gateway through `projectResourceNameValidate`.
- A directory that Windows can create may still be an illegal Ignition resource name. Characters such as `+` can fail the installed resource-name validator.
- Require `allPathsLegal:true` before import or relocation.
- Preserve `resource.json` scope, attributes, declared files, and resource identity.
- Do not rename a native Vision resource by editing only its directory. Use a supported relocation flow that rewrites structured window identity and checks dependencies.

## Vision Serialization And Layout

- Use only the target-version Ignition and Vision jars for native serialization.
- Initialize the matching serializer and deserializer defaults.
- Deserialize the final bytes again before packaging.
- Preserve root design size, component bounds, preferred bounds, layout constraints, anchor flags, nested local coordinates, and the expected Boolean layout fields.
- Do not hand-author primitive Java class signatures inside serialized XML. Invoke primitive bean setters in executable Jython or use the target serializer.
- Treat Gateway-common binary transcode as bounded structural inspection. It does not execute the resource or prove pixels.
- Do not byte-patch opaque native payloads.

## Bindings, Components, And Java Types

- Build native expression adapters from a parsed expression and fully qualified tag listeners; expression text alone is insufficient.
- Preserve declared Java dataset column types, especially for charts, schedules, dates, colors, and booleans.
- Use `java.lang.Boolean` deliberately when a Java API requires it. Avoid truthiness coercion of strings.
- Vision numeric labels can remain right-aligned even when their bounds are wide; set horizontal alignment explicitly.
- Configure a native meter's declared low/high range and ticks when the process scale differs from 0–100.
- Initialize multi-state component datasets explicitly when the selected state would otherwise render blank.
- Use ordinary `java.awt.Color` values in generated resources.

## Client Launch And Diagnostics

- A classic-auth launcher can keep credentials in process environment/in-memory launcher attributes. Do not place usernames or passwords in command-line properties, saved scripts, logs, or evidence.
- Match the Java, Jython, core client, launch client, and Vision client jars to the target Gateway.
- Install fixed Client Event Script handlers before starting a fresh client; an already-running client may hold stale project script configuration.
- Vision Client logs are in the client JVM. Use an approved fixed client-log bridge; Gateway log queries are separate, and no desktop fallback is part of this skill.
- For visual validation, capture the native root at the actual client size and inspect the pixels in addition to font-metric text-fit records.

## Porting To Another 8.1 Release

Before reusing a serializer, launcher, handler, or private class on another patch:

1. Discover the installed versions and jar paths.
2. Compile the outer Jython and every generated/lazy-loaded payload with the installed IA Jython runtime.
3. Serialize and deserialize a minimal representative resource.
4. Verify component classes, bean properties, dataset types, layout state, and resource metadata.
5. Import through dry-run and state-guarded apply in a disposable project/resource scope.
6. Start a fresh client and validate runtime state, focused logs, and pixels.
7. Promote the change only after the new target evidence is recorded internally.
