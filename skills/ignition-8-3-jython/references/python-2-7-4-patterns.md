# Python 3 instinct to Jython 2.7.4 pattern

Use these patterns when a request, example, or draft is written with Python 3 assumptions. They are narrow starting points, not proof that the surrounding Ignition scope, import, Java overload, resource, or side effect is valid.

## Contents

- [Declare the target in generated code](#declare-the-target-in-generated-code)
- [Replace only the incompatible construct](#replace-only-the-incompatible-construct)
- [Use Python 2 module names on the fixed target](#use-python-2-module-names-on-the-fixed-target)
- [Normalize text once](#normalize-text-once)
- [Define numbers and iteration deliberately](#define-numbers-and-iteration-deliberately)
- [Define classes and defaults explicitly](#define-classes-and-defaults-explicitly)
- [Keep exception boundaries exact](#keep-exception-boundaries-exact)
- [Refuse unsupported dependency assumptions](#refuse-unsupported-dependency-assumptions)

## Declare the target in generated code

```python
# Target: Ignition 8.3.8 / Jython 2.7.4 (Python 2.7 semantics)
# Scope: <exact Gateway, Perspective, Vision, event, Web Dev, or Designer scope>
# Inputs: <types, units, null policy, size bounds>
# Effects: <reads/writes/messages/UI calls, or none>
# Completion: <what proves success>
# Failure/cleanup: <timeout, quality/error, cleanup, outcome-unknown policy>
```

Never copy `<...>` placeholders into production code.

## Replace only the incompatible construct

| Python 3 instinct | Jython 2.7.4 starting point | Boundary to verify |
|---|---|---|
| `f"{name}:{value}"` | `u"{0}:{1}".format(name, value)` | Normalize operands to `unicode` before formatting. |
| type annotations | docstring plus explicit validation | Validate exact accepted types, including the Python 2 `bool`/`int` relationship. |
| `@dataclass` | explicit new-style class inheriting `object` | Define constructor, defaults, equality, mutability, and serialization deliberately. |
| zero-argument `super()` | `super(CurrentClass, self)` | Preserve the actual class hierarchy. |
| `range(...)` as a lazy sequence | bounded `xrange(...)` for iteration | Use `range` only when an eager list is intended and bounded. |
| iterator-returning `map`/`filter`/`zip` | bounded explicit loop or deliberate eager result | Python 2 forms allocate lists; `map(None, ...)` can pad with `None`. |
| `pathlib` | `os.path` or a verified Java/Ignition path API | Preserve text encoding, path type, scope, and filesystem authorization. |
| `datetime.fromisoformat` | exact-format `datetime.datetime.strptime` | Define locale, time zone, full-input validation, DST policy, and epoch units. |
| `list.copy()` | `list(source)` | This is a shallow copy only. |
| dictionary union `left | right` | `merged = left.copy(); merged.update(right)` | Define precedence, accepted mapping types, and shallow-copy semantics. |
| `removeprefix`/`removesuffix` | non-empty `startswith`/`endswith` plus slicing | Normalize text type and define the empty-prefix policy. |
| `int.to_bytes`/`from_bytes` | fixed `struct.pack`/`unpack` format | Specify signedness, width, byte order, and range. |
| `math.prod` | bounded explicit multiplication loop | Define empty-input identity and accepted numeric types. |
| `math.isclose` | explicit finite-value tolerance comparison | Define relative/absolute tolerances and NaN/infinity policy. |
| `subprocess.run` | no automatic replacement | Prefer a scope-correct Ignition/Java API only after authorization, limits, and cleanup are proven. |
| `async def`/`await` | no syntax translation | Design ownership, result/error channel, deadline, cancellation, cleanup, and retry safety before selecting a verified Ignition/Java asynchronous API. |

Do not use a replacement merely because it appears in this table. Apply it only when its narrower contract matches the request.

## Use Python 2 module names on the fixed target

| Python 3 spelling to reject | Tested Python 2 spelling |
|---|---|
| `_thread` | `thread` |
| `configparser` | `ConfigParser` |
| `copyreg` | `copy_reg` |
| `http.client` | `httplib` |
| `queue` | `Queue` |
| `socketserver` | `SocketServer` |
| `urllib.parse` | `urlparse` |
| `urllib.request` | `urllib2` |
| `xmlrpc.client` | `xmlrpclib` |

Also use the tested Python 2 names `BaseHTTPServer`, `CGIHTTPServer`, `SimpleHTTPServer`, and `StringIO` when those exact APIs are required. Do not emit a Python 3-first fallback chain for this fixed Jython target. A separately installed compatibility package can alter availability, so discover and validate any non-baseline deployment explicitly.

## Normalize text once

Use `unicode` internally for human-readable text:

```python
# Target: Ignition 8.3.8 / Jython 2.7.4 (Python 2.7 semantics)
def require_unicode(value, encoding):
	if isinstance(value, unicode):
		return value
	if isinstance(value, str):
		return value.decode(encoding)
	raise TypeError("value must be str or unicode")
```

At a byte boundary, encode once with the protocol's named codec:

```python
# Target: Ignition 8.3.8 / Jython 2.7.4 (Python 2.7 semantics)
text_value = require_unicode(source_value, "utf-8")
wire_bytes = text_value.encode("utf-8")
```

Do not use `str(non_ascii_unicode)`, `unicode(non_ascii_bytes)`, mixed `str`/`unicode` concatenation, or `sys.setdefaultencoding` as conversion policy. Do not pre-encode for an Ignition or Java API that expects text.

## Define numbers and iteration deliberately

```python
# Target: Ignition 8.3.8 / Jython 2.7.4 (Python 2.7 semantics)
# Fractional result required.
ratio = float(part) / total

# Bounded lazy Python 2 iteration.
for index in xrange(item_count):
	process(index)

# Arbitrary-size integer accepted.
if not isinstance(value, (int, long)) or isinstance(value, bool):
	raise TypeError("value must be an integer, not bool")
```

Validate zero denominators, finite values, units, signs, and maximum counts separately. Do not assume Python 3 division or iterator behavior.

## Define classes and defaults explicitly

```python
# Target: Ignition 8.3.8 / Jython 2.7.4 (Python 2.7 semantics)
class Reading(object):
	def __init__(self, path, value=None):
		if not isinstance(path, basestring):
			raise TypeError("path must be str or unicode")
		self.path = path
		self.value = value


def append_reading(reading, values=None):
	if values is None:
		values = []
	values.append(reading)
	return values
```

Do not substitute a mutable default or infer dataclass-like equality, immutability, representation, or serialization.

## Keep exception boundaries exact

`except Exception as error` is valid Python 2.7 syntax. Catch only errors the boundary can classify and handle. A Java throwable can bypass a Python-only `except Exception`, so catch a verified Java exception class explicitly when that API contract requires it. Preserve control-flow and unexpected Java errors, and keep primary failure separate from cleanup failure.

Do not wrap import, initialization, and member use in one broad `except ImportError`. Import the exact module first, validate required members explicitly, and return a stable dependency error when the configured requirement is absent.

## Refuse unsupported dependency assumptions

Do not generate `pip`, `ensurepip`, CPython wheel, or C-extension installation instructions for the Gateway. Treat NumPy, pandas, dataclasses, modern backports, optional bridges, and JVM libraries as unavailable until the exact target scope proves the identifier, version, loader, members, and deployment contract. Prefer a verified pure-Python 2.7 dependency, a verified JVM library, or built-in Ignition functionality according to the task contract.
