# Native Vision Serialization And Gateway-Common Transcode

## Contents

- [Safety boundary](#safety-boundary)
- [Target-version round trip](#target-version-round-trip)
- [Preferred bounds and nested layout](#preferred-bounds-and-nested-layout)
- [Parsed expression bindings](#parsed-expression-bindings)
- [Numeric labels, state indicators, and meters](#numeric-labels-state-indicators-and-meters)
- [Custom bounded drawing scripts](#custom-bounded-drawing-scripts)
- [Deterministic package construction](#deterministic-package-construction)
- [Gateway-common binary transcode](#gateway-common-binary-transcode)
- [Jython module-size control](#jython-module-size-control)
- [Verification checklist](#verification-checklist)

## Safety Boundary

Use native serialization only with jars from the exact target Ignition/Vision patch. Prefer a Designer export when possible. Never edit unknown binary offsets or assume a payload from another patch will deserialize correctly.

Gateway-common binary transcode is a bounded read-only inspection technique. It can expose structural XML-like evidence when Vision client classes are unavailable in Gateway scope, but it does not execute bindings/scripts, initialize a client, or prove pixels.

## Target-Version Round Trip

For generated native windows/templates:

1. Discover the exact target Java, IA Jython, core common/client/designer, and Vision common/client/designer jars.
2. Initialize the matching XML serializer and deserializer defaults.
3. Construct components with target classes and deliberate Java types.
4. Apply the complete final layout/binding/component specification.
5. Serialize once.
6. Deserialize the serialized bytes.
7. Assert resource identity, component classes/order, bounds, layout constraints, bindings, datasets/types, and important bean properties.
8. Serialize the deserialized object again when deterministic bytes are required.
9. Package only the declared resource files with deterministic entry names/timestamps.
10. Import through the external runner's dry-run and state-guarded lifecycle.

Do not normalize fields unless the resource contract explicitly identifies them as nondeterministic and safe to normalize.

## Preferred Bounds And Nested Layout

Swing `setBounds` alone is insufficient for native Vision layout. Apply the intended design rectangle through Vision layout APIs and preserve named anchor/layout flags.

```jython
from java.awt import Rectangle
from java.lang import Boolean
from com.inductiveautomation.factorypmi.application.components.util import FPMILayout

design_bounds = Rectangle(20, 70, 320, 180)
component.setBounds(design_bounds)
component.setPreferredSize(design_bounds.getSize())
FPMILayout.setPreferredBounds(component, design_bounds)
component.putClientProperty('fpmi.lc', Boolean.TRUE)
```

Use the actual target API names available in the installed jars. Reapply the final complete layout after fonts, icons, and other properties that can influence preferred size. Store nested child rectangles relative to the immediate parent.

After deserialization, assert preferred bounds, runtime/design bounds, layout constraint/anchor values, and the expected Boolean type—not only truthiness.

## Parsed Expression Bindings

Do not serialize only expression text. Parse with the target expression parser and create fully qualified tag listeners:

```jython
from java.lang import String
from com.inductiveautomation.factorypmi.application.binding import ExpressionPropertyAdapter
from com.inductiveautomation.ignition.common.expressions import BoundTagExpression
from com.inductiveautomation.ignition.common.expressions import DefaultFunctionFactory
from com.inductiveautomation.ignition.common.expressions import ExpressionParseContext
from com.inductiveautomation.ignition.common.expressions import TagListener
from com.inductiveautomation.ignition.common.expressions.parsing import ELParserHarness

class VisionExpressionParseContext(ExpressionParseContext):
    def createBoundExpression(self, path):
        value = str(path).strip()
        if not value.startswith('[') or ']' not in value:
            raise ValueError('Only fully qualified tags are allowed: ' + repr(value))
        listener = TagListener()
        listener.setTagPath(value)
        expression = BoundTagExpression()
        expression.setTagListenerDelegate(listener)
        return expression

    def getFunctionFactory(self):
        return DefaultFunctionFactory.getSharedInstance()

source = "if({[Provider]Area/Unit/State} = 'Running', 'READY', 'BLOCKED')"
parsed = ELParserHarness().parse(source, VisionExpressionParseContext())
adapter = ExpressionPropertyAdapter()
adapter.setTarget(target)
adapter.setTargetPropertyName('text')
adapter.setValueClass(String)
adapter.setExpressionSource(source)
adapter.setExpression(parsed)
controller.setPropertyAdapter(target, 'text', adapter)
```

Match the value class and every branch to the real source/target type. After the final round trip, assert adapter class, source, parsed expression, value class, and every bound tag path. Runtime Good quality and the expected value are separate external checks.

Before importing an expression-bound resource, inspect both serialized initialization layers:

- the `ExpressionPropertyAdapter` initial `QualifiedValue`; and
- every nested `BoundTagExpression` listener's initial tag `QualifiedValue`.

Treat a missing, explicit-null, unresolved, wrong-class, or incomplete result as unsafe for Designer attachment. A live tag read with Good quality does not prove these serialized initial values exist. An expression can therefore pass static reference and dependency checks yet still throw during Designer binding initialization.

## Numeric Labels, State Indicators, And Meters

Center a numeric label explicitly:

```jython
from javax.swing import SwingConstants

numeric_label.setHorizontalAlignment(SwingConstants.CENTER)
numeric_label.setVerticalAlignment(SwingConstants.CENTER)
```

Reapply final bounds/preferred bounds after setting the font, units, number format, and alignment.

Configure the actual process range and ticks on a native meter:

```jython
meter.setOverallLow(0.0)
meter.setOverallHigh(105.0)
meter.setTickSize(15.0)
meter.setTicks(True)
meter.setTickLabelFormat('0')
```

Configure the angle/extent, colors, and intervals deliberately. Prefer the native meter when it communicates the scale accurately.

For a multi-state indicator, initialize the state dataset explicitly when the component does not provide one. Include every required state and the fields expected by the target component, including text, foreground/background/border, and animation values. Ensure the selected text is readable and centered when intended.

Use ordinary `java.awt.Color` objects in generated resources rather than look-and-feel resource subclasses.

## Custom Bounded Drawing Scripts

Use a custom dial only when the native meter cannot satisfy the presentation. Keep the bound numeric value separate and update only known primitives from a filtered event:

```jython
if event.propertyName == 'value':
    import math

    try:
        value = float(event.newValue)
    except Exception:
        value = 0.0
    value = min(105.0, max(0.0, value))
    angle = math.radians(225.0 - (value / 105.0) * 270.0)
    center_x = 160.0
    center_y = 150.0
    radius = 95.0
    tip_x = center_x + radius * math.cos(angle)
    tip_y = center_y - radius * math.sin(angle)
    needle = event.source.parent.getComponent('Needle')
    needle.setBounds(
        int(round(min(center_x, tip_x))),
        int(round(min(center_y, tip_y))),
        max(2, int(round(abs(tip_x - center_x)))),
        max(2, int(round(abs(tip_y - center_y))))
    )
```

This script must not accept caller-selected components/methods or write application tags. Validate its endpoint/state through a fixed bounded bridge and validate pixels through a native screenshot.

## Deterministic Package Construction

- Use stable ZIP entry ordering and timestamps.
- Include only `resource.json` and the payload/thumbnail files declared for the resource.
- Reject duplicate normalized paths, traversal, prefix escape, and undeclared files.
- Preserve resource scope and attributes.
- Build twice from clean output directories when byte determinism is required and compare package/payload hashes.
- Keep generation outputs and evidence internal. Ship only portable customer helpers explicitly routed by the skill.

## Gateway-Common Binary Transcode

A bounded transcode may use Gateway-common serializer classes, proxy handlers, and a capped class-alias map to convert a native Vision payload into inspectable structure without loading Vision client classes into Gateway scope.

Require:

- an exact resource/payload state hash;
- target format/version recognition;
- strict input and output byte caps;
- capped discovered aliases and proxy handlers;
- closed temporary classloaders/streams;
- explicit transcode scope and warnings;
- fallback to bounded format/class/token/marker evidence when transcode fails.

Do not expose arbitrary class loading, object methods, reflection targets, or script execution. Do not use the transcode result as a writer or pixel claim.

A Designer-saved binary-v2 resource can require class aliases and proxy handlers that are available to the Gateway-common transcode but not to a direct standalone `XMLDeserializer`, even when Vision client/designer delegates are present. Do not classify the resource as corrupt from that direct failure alone. Run the target-version alias-aware transcode twice, require identical output hashes, and then apply the bounded structural classifier to the transcoded bytes.

Designer saves can also serialize the current values of bound display properties. Raw payload and transcoded XML hashes may therefore change while hierarchy, layout, bindings, and expression sources remain identical. Keep the new raw hash as evidence, compare an allowlisted semantic projection, and require the initialization-safety classifier before accepting a new pin. Never auto-accept an unexplained hash change.

## Jython Module-Size Control

Large generated Jython can exceed JVM method limits even when the syntax is valid.

- Keep the outer entry point and action dispatcher small.
- Split ordinary code into modules.
- Put large deterministic action groups behind a tested lazy loader only when a single self-contained resource is required.
- Avoid constructing one enormous dictionary/list literal in the outer module.
- Compile the readable source, direct Web Dev wrapper, and every decoded/generated group with the installed IA Jython runtime.
- After code generation, assert exact import statements and resolve them in the matching Vision client classloader. Broad chained text substitutions can create nonexistent Java symbols while leaving the Jython source syntactically valid.
- Treat a compile/load failure as a stop condition; preserve the prior working resource and use the guarded rollback path.

## Verification Checklist

- Exact target jars and versions recorded.
- Serializer and deserializer defaults initialized.
- Final bytes deserialize successfully.
- Logical identity, manifest, scope, and declared files match.
- Preferred bounds, nested coordinates, layout constraints, and Boolean types survive.
- Parsed expressions retain listeners and value classes.
- Every expression adapter and nested bound-tag listener has a complete, non-null initial `QualifiedValue` before Designer attachment.
- Alias-aware binary transcode is deterministic, and any accepted raw-hash change has an explicit semantic diff.
- Datasets retain column names and Java types.
- Primitive bean settings are applied through valid target calls.
- Custom scripts are filtered, bounded, and side-effect explicit.
- Clean deterministic build comparison passes where required.
- External import, dependency, runtime, log, and screenshot validation is handed to `ignition-vision`.
