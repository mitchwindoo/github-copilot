#!/usr/bin/env python3
"""Conservative structural preflight for Ignition 8.3 tag-import JSON."""

import argparse
import json
import math
import re
from pathlib import Path


TAG_TYPES = {"AtomicTag", "Folder", "UdtInstance", "UdtType"}
VALUE_SOURCES = {"db", "derived", "expr", "memory", "opc", "reference"}
DATA_TYPES = {
    "Int1", "Int2", "Int4", "Int8", "Float4", "Float8", "Boolean",
    "String", "DateTime", "Text", "Int1Array", "Int2Array", "Int4Array",
    "Int8Array", "Float4Array", "Float8Array", "BooleanArray", "StringArray",
    "DateTimeArray", "ByteArray", "DataSet", "Document",
}
SCALE_MODES = {"Off", "Linear", "SquareRoot", "ExponentialFilter", "BitInversion"}
CLAMP_MODES = {"No_Clamp", "Clamp_Low", "Clamp_High", "Clamp_Both"}
QUERY_TYPES = {"Select", "Update", "AutoDetect"}
EXECUTION_MODES = {"EventDriven", "FixedRate", "TagGroupRate"}
HISTORY_DEADBAND_STYLES = {"Auto", "Analog_Compressed", "Discrete"}
DEADBAND_MODES = {"Absolute", "Percent", "Off"}
SAMPLE_MODES = {"OnChange", "Periodic", "TagGroup"}
TIME_UNITS = {"MS", "SEC", "MIN", "HOUR", "DAY", "WEEK", "MONTH", "YEAR"}
ALARM_MODES = {
    "Equality", "Inequality", "AboveValue", "BelowValue", "BetweenValues",
    "OutsideValues", "OutOfEngRange", "BadQuality", "AnyChange", "Bit",
    "OnCondition", "WhenTrue", "WhenFalse",
}
ALARM_PRIORITIES = {"Diagnostic", "Low", "Medium", "High", "Critical"}
ACK_MODES = {"Unused", "Auto", "Manual"}
ALARM_STANDARD_PROPERTIES = {
    "name", "enabled", "priority", "timestampSource", "label", "displayPath",
    "ackMode", "notes", "ackNotesReqd", "shelvingAllowed", "mode", "setpointA",
    "inclusiveA", "setpointB", "inclusiveB", "anyChange", "bitOnZero",
    "bitPosition", "activeCondition", "deadband", "deadbandMode",
    "timeOnDelaySeconds", "timeOffDelaySeconds", "activePipeline", "clearPipeline",
    "ackPipeline", "voip.customMessage", "CustomEmailSubject", "CustomEmailMessage",
    "CustomSmsMessage",
}
ASSOCIATED_DATA_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,63}$")
EVENT_IDS = {
    "qualityChanged", "valueChanged", "qualifiedValueChanged",
    "alarmActive", "alarmCleared", "alarmAcked",
}
QUALIFIED_VALUE_CHANGE_TYPES = {"VALUE", "QUALITY", "TIMESTAMP"}
PERMISSION_TYPES = {"AnyOf", "AllOf"}
ARRAY_DATA_TYPES = {
    "Int1Array", "Int2Array", "Int4Array", "Int8Array", "Float4Array",
    "Float8Array", "BooleanArray", "StringArray", "DateTimeArray", "ByteArray",
}
INTEGER_ARRAY_RANGES = {
    "Int1Array": (-128, 127),
    "ByteArray": (-128, 127),
    "Int2Array": (-32768, 32767),
    "Int4Array": (-2147483648, 2147483647),
    "Int8Array": (-9223372036854775808, 9223372036854775807),
}
INTEGER_DATA_TYPE_RANGES = {
    "Int1": (-128, 127),
    "Int2": (-32768, 32767),
    "Int4": (-2147483648, 2147483647),
    "Int8": (-9223372036854775808, 9223372036854775807),
}
DATASET_COLUMN_TYPES = {
    "java.lang.String", "java.lang.Byte", "java.lang.Short",
    "java.lang.Integer", "java.lang.Long", "java.lang.Float",
    "java.lang.Double", "java.lang.Boolean", "java.util.Date",
}
DATASET_INTEGER_RANGES = {
    "java.lang.Byte": (-128, 127),
    "java.lang.Short": (-32768, 32767),
    "java.lang.Integer": (-2147483648, 2147483647),
    "java.lang.Long": (-9223372036854775808, 9223372036854775807),
}
PARAMETER_DATA_TYPES = {"String", "Integer", "Float", "Boolean", "Int4", "Float4", "Float8"}


def guards_current_value_before_numeric_conversion(script):
    conversion = re.search(
        r"\b(?:int|long|float)\s*\(\s*currentValue\s*\.\s*value\s*\)", script
    )
    if conversion is None:
        return True
    prefix = script[:conversion.start()]
    positive_guard = re.search(
        r"currentValue\s*\.\s*value\s+is\s+not\s+None", prefix
    )
    early_return_guard = re.search(
        r"if[^\n:]*currentValue\s*\.\s*value\s+is\s+None[^\n:]*:\s*\r?\n[ \t]+return\b",
        prefix,
    )
    return bool(positive_guard or early_return_guard)


def validate_integer(value, minimum, maximum, location, errors):
    if isinstance(value, bool) or not isinstance(value, int):
        errors.append(f"{location}: expected JSON integer")
    elif value < minimum or value > maximum:
        errors.append(f"{location}: integer outside [{minimum}, {maximum}]")


def validate_dataset_cell(value, column_type, location, errors):
    if value is None:
        return
    if column_type == "java.lang.String":
        if not isinstance(value, str):
            errors.append(f"{location}: expected string or null for {column_type}")
    elif column_type in DATASET_INTEGER_RANGES:
        validate_integer(value, *DATASET_INTEGER_RANGES[column_type], location, errors)
    elif column_type in {"java.lang.Float", "java.lang.Double"}:
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            errors.append(f"{location}: expected finite JSON number or null for {column_type}")
    elif column_type == "java.lang.Boolean":
        if not isinstance(value, bool):
            errors.append(f"{location}: expected boolean or null for {column_type}")
    elif column_type == "java.util.Date":
        if isinstance(value, bool) or not isinstance(value, int):
            errors.append(f"{location}: expected epoch-millisecond JSON integer or null for {column_type}")


def validate_dataset_value(value, location, errors):
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            errors.append(f"{location}: encoded DataSet value must be valid JSON")
            return
    if not isinstance(value, dict):
        errors.append(f"{location}: DataSet value must be an object or an encoded object string")
        return
    unexpected = set(value) - {"columns", "rows"}
    if unexpected:
        errors.append(f"{location}: unexpected DataSet keys {sorted(unexpected)}")
    columns = value.get("columns")
    rows = value.get("rows")
    if not isinstance(columns, list):
        errors.append(f"{location}.columns: expected array of name/type objects")
        return
    if not isinstance(rows, list):
        errors.append(f"{location}.rows: expected array of row arrays")
        return
    column_types = []
    seen = set()
    for index, column in enumerate(columns):
        column_location = f"{location}.columns[{index}]"
        if not isinstance(column, dict):
            errors.append(f"{column_location}: expected object with name and type")
            column_types.append(None)
            continue
        unexpected_column = set(column) - {"name", "type"}
        if unexpected_column:
            errors.append(f"{column_location}: unexpected keys {sorted(unexpected_column)}")
        name = column.get("name")
        column_type = column.get("type")
        if not isinstance(name, str) or not name:
            errors.append(f"{column_location}.name: expected nonempty string")
        elif name in seen:
            errors.append(f"{column_location}.name: duplicate column {name!r}")
        else:
            seen.add(name)
        if column_type not in DATASET_COLUMN_TYPES:
            errors.append(f"{column_location}.type: expected one of {sorted(DATASET_COLUMN_TYPES)}")
            column_types.append(None)
        else:
            column_types.append(column_type)
    for row_index, row in enumerate(rows):
        row_location = f"{location}.rows[{row_index}]"
        if not isinstance(row, list):
            errors.append(f"{row_location}: expected array; preserve one-row nesting during JSON generation")
            continue
        if len(row) != len(columns):
            errors.append(f"{row_location}: expected {len(columns)} cells, found {len(row)}")
            continue
        for column_index, (cell, column_type) in enumerate(zip(row, column_types)):
            if column_type is not None:
                validate_dataset_cell(cell, column_type, f"{row_location}[{column_index}]", errors)


def validate_complex_value(data_type, value, location, errors):
    if data_type in INTEGER_DATA_TYPE_RANGES:
        if isinstance(value, dict):
            validate_binding(value, location, errors)
        else:
            validate_integer(value, *INTEGER_DATA_TYPE_RANGES[data_type], location, errors)
    elif data_type in {"Float4", "Float8"}:
        if isinstance(value, dict):
            validate_binding(value, location, errors)
        elif isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            errors.append(f"{location}: expected finite JSON number")
    elif data_type == "Boolean":
        if isinstance(value, dict):
            validate_binding(value, location, errors)
        elif not isinstance(value, bool):
            errors.append(f"{location}: expected JSON boolean")
    elif data_type == "String":
        if isinstance(value, dict):
            validate_binding(value, location, errors)
        elif not isinstance(value, str):
            errors.append(f"{location}: expected JSON string")
    elif data_type == "DateTime":
        if isinstance(value, dict):
            if not validate_binding(value, location, errors):
                errors.append(f"{location}: expected epoch-millisecond JSON integer or property-binding object")
        elif isinstance(value, bool) or not isinstance(value, int):
            errors.append(f"{location}: expected epoch-millisecond JSON integer; ISO strings are not the verified scalar import shape")
    elif data_type in ARRAY_DATA_TYPES:
        if not isinstance(value, list):
            errors.append(f"{location}: {data_type} requires a JSON array; scalar input silently normalized to null in live testing")
            return
        for index, item in enumerate(value):
            item_location = f"{location}[{index}]"
            if data_type in INTEGER_ARRAY_RANGES:
                validate_integer(item, *INTEGER_ARRAY_RANGES[data_type], item_location, errors)
            elif data_type in {"Float4Array", "Float8Array"}:
                if isinstance(item, bool) or not isinstance(item, (int, float)) or not math.isfinite(item):
                    errors.append(f"{item_location}: expected finite JSON number")
            elif data_type == "BooleanArray" and not isinstance(item, bool):
                errors.append(f"{item_location}: expected boolean")
            elif data_type == "StringArray" and not isinstance(item, str):
                errors.append(f"{item_location}: expected string")
            elif data_type == "DateTimeArray" and (isinstance(item, bool) or not isinstance(item, int)):
                errors.append(f"{item_location}: expected epoch-millisecond JSON integer; ISO strings normalized to null")
    elif data_type == "DataSet":
        validate_dataset_value(value, location, errors)
    elif data_type == "Text" and not isinstance(value, str):
        errors.append(f"{location}: Text value should be an explicit JSON string; other scalars are coerced")


def validate_security_level_node(value, location, errors):
    if not isinstance(value, dict):
        errors.append(f"{location}: expected security-level object")
        return
    unexpected = set(value) - {"name", "children"}
    if unexpected:
        errors.append(f"{location}: unexpected keys {sorted(unexpected)}")
    name = value.get("name")
    if not isinstance(name, str) or not name.strip():
        errors.append(f"{location}.name: expected nonempty security-level name")
    elif name == "Public":
        errors.append(f"{location}.name: omit the permission property for Public; do not add a Public wrapper")
    children = value.get("children")
    if not isinstance(children, list):
        errors.append(f"{location}.children: expected array; preserve one-element arrays during JSON generation")
        return
    seen = set()
    for index, child in enumerate(children):
        validate_security_level_node(child, f"{location}.children[{index}]", errors)
        if isinstance(child, dict) and isinstance(child.get("name"), str):
            if child["name"] in seen:
                errors.append(f"{location}.children[{index}].name: duplicate sibling {child['name']!r}")
            seen.add(child["name"])


def validate_permissions(value, location, errors):
    if not isinstance(value, dict):
        errors.append(f"{location}: expected object with type and securityLevels")
        return
    unexpected = set(value) - {"type", "securityLevels"}
    if unexpected:
        errors.append(f"{location}: unexpected keys {sorted(unexpected)}")
    permission_type = value.get("type")
    if permission_type not in PERMISSION_TYPES:
        errors.append(f"{location}.type: expected exact AnyOf or AllOf")
    levels = value.get("securityLevels")
    if not isinstance(levels, list):
        errors.append(
            f"{location}.securityLevels: expected array; PowerShell helper output can silently unwrap a one-element array"
        )
        return
    if not levels:
        errors.append(f"{location}.securityLevels: expected nonempty array; omit the permission property for Public")
        return
    seen = set()
    for index, level in enumerate(levels):
        validate_security_level_node(level, f"{location}.securityLevels[{index}]", errors)
        if isinstance(level, dict) and isinstance(level.get("name"), str):
            if level["name"] in seen:
                errors.append(f"{location}.securityLevels[{index}].name: duplicate root {level['name']!r}")
            seen.add(level["name"])


def validate_binding(value, location, errors):
    if not isinstance(value, dict):
        return False
    if not isinstance(value.get("bindType"), str) or not value["bindType"].strip():
        errors.append(f"{location}.bindType: expected nonempty string")
    if not isinstance(value.get("binding"), str) or not value["binding"].strip():
        errors.append(f"{location}.binding: expected nonempty string")
    return True


def validate_number_or_binding(value, location, errors):
    if isinstance(value, bool):
        errors.append(f"{location}: expected number or property-binding object")
    elif isinstance(value, (int, float)):
        return
    elif not validate_binding(value, location, errors):
        errors.append(f"{location}: expected number or property-binding object")


def validate_alarm_expression_binding(value, location, errors):
    """Validate the distinct JSON shape used by bindable alarm properties."""
    if not isinstance(value, dict):
        return False
    unexpected = set(value) - {"bindType", "value"}
    if unexpected:
        errors.append(f"{location}: unexpected keys {sorted(unexpected)}; alarm expressions use bindType/value")
    if value.get("bindType") != "Expression":
        errors.append(f"{location}.bindType: expected exact alarm binding type 'Expression'")
    if not isinstance(value.get("value"), str) or not value["value"].strip():
        errors.append(f"{location}.value: expected nonempty alarm expression")
    return True


def validate_parameter_literal(data_type, value, location, errors):
    if data_type == "String":
        if not isinstance(value, str):
            errors.append(f"{location}: String parameter requires a JSON string")
    elif data_type == "Boolean":
        if not isinstance(value, bool):
            errors.append(f"{location}: Boolean parameter requires a JSON boolean")
    elif data_type in {"Integer", "Int4"}:
        if isinstance(value, bool) or not isinstance(value, int):
            errors.append(f"{location}: {data_type} parameter requires a JSON integer")
    elif data_type in {"Float", "Float4", "Float8"}:
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            errors.append(f"{location}: {data_type} parameter requires a finite JSON number")


def validate_parameters(parameters, tag_type, location, errors):
    if not isinstance(parameters, dict):
        errors.append(f"{location}: expected object")
        return
    for name, parameter in parameters.items():
        parameter_location = f"{location}.{name}"
        if not isinstance(name, str) or not name:
            errors.append(f"{parameter_location}: expected nonempty parameter name")
        if tag_type == "UdtType":
            if not isinstance(parameter, dict):
                errors.append(f"{parameter_location}: UdtType parameters require dataType/value objects")
                continue
            unexpected = set(parameter) - {"dataType", "value"}
            if unexpected:
                errors.append(f"{parameter_location}: unexpected keys {sorted(unexpected)}")
            data_type = parameter.get("dataType")
            if data_type not in PARAMETER_DATA_TYPES:
                errors.append(f"{parameter_location}.dataType: expected a supported UDT parameter type")
            if "value" not in parameter:
                errors.append(f"{parameter_location}.value: required for a UDT definition parameter")
            elif data_type in PARAMETER_DATA_TYPES:
                validate_parameter_literal(data_type, parameter["value"], f"{parameter_location}.value", errors)
            continue
        if tag_type != "UdtInstance":
            continue
        if isinstance(parameter, str) and ("{" in parameter or "}" in parameter):
            errors.append(
                f"{parameter_location}: plain brace text remains literal; use a typed dataType/value parameter-binding wrapper"
            )
            continue
        if not isinstance(parameter, dict):
            continue
        if "bindType" in parameter or "binding" in parameter:
            errors.append(
                f"{parameter_location}: raw binding objects infer unreliable metadata; wrap the binding in dataType/value"
            )
            validate_binding(parameter, parameter_location, errors)
            continue
        unexpected = set(parameter) - {"dataType", "value"}
        if unexpected:
            errors.append(f"{parameter_location}: unexpected keys {sorted(unexpected)}")
        data_type = parameter.get("dataType")
        if data_type not in PARAMETER_DATA_TYPES:
            errors.append(f"{parameter_location}.dataType: expected a supported UDT parameter type")
        if "value" not in parameter:
            errors.append(f"{parameter_location}.value: required in a typed instance parameter wrapper")
            continue
        value = parameter["value"]
        if isinstance(value, dict):
            unexpected_binding = set(value) - {"bindType", "binding"}
            if unexpected_binding:
                errors.append(f"{parameter_location}.value: unexpected binding keys {sorted(unexpected_binding)}")
            if value.get("bindType") != "parameter":
                errors.append(f"{parameter_location}.value.bindType: expected exact lowercase 'parameter'")
            binding = value.get("binding")
            if not isinstance(binding, str) or not binding.strip():
                errors.append(f"{parameter_location}.value.binding: expected nonempty parent-parameter binding text")
        elif data_type in PARAMETER_DATA_TYPES:
            validate_parameter_literal(data_type, value, f"{parameter_location}.value", errors)


def validate_node(node, location, errors, parent_tag_type=None):
    if not isinstance(node, dict):
        errors.append(f"{location}: expected object")
        return
    name = node.get("name")
    if not isinstance(name, str) or not name or len(name) >= 256:
        errors.append(f"{location}.name: expected nonempty string shorter than 256 characters")
    tag_type = node.get("tagType")
    if tag_type not in TAG_TYPES:
        errors.append(f"{location}.tagType: expected one of {sorted(TAG_TYPES)}")
    if tag_type == "UdtInstance":
        type_id = node.get("typeId")
        is_inherited_member_stub = type_id is None and parent_tag_type == "UdtInstance"
        if not is_inherited_member_stub and (
            not isinstance(type_id, str)
            or not type_id.strip()
            or type_id.startswith(("/", "["))
            or ".." in type_id.replace("\\", "/").split("/")
        ):
            errors.append(f"{location}.typeId: UdtInstance requires a nonempty relative typeId string")
    if tag_type == "UdtType" and node.get("typeId") is not None:
        type_id = node.get("typeId")
        if (
            not isinstance(type_id, str)
            or not type_id.strip()
            or type_id.startswith(("/", "["))
            or ".." in type_id.replace("\\", "/").split("/")
        ):
            errors.append(f"{location}.typeId: derived UDT requires a nonempty relative typeId string")
    value_source = node.get("valueSource")
    if value_source is not None and value_source not in VALUE_SOURCES:
        errors.append(f"{location}.valueSource: expected one of {sorted(VALUE_SOURCES)}")
    if value_source == "expr":
        expression = node.get("expression")
        if not isinstance(expression, str) or not expression.strip():
            errors.append(f"{location}.expression: expression-source member requires nonempty string text")
    data_type = node.get("dataType")
    if data_type is not None and data_type not in DATA_TYPES:
        errors.append(f"{location}.dataType: expected one of the Ignition 8.3 JSON data-type names")
    if data_type in DATA_TYPES and "value" in node:
        validate_complex_value(data_type, node["value"], f"{location}.value", errors)
    if "readOnly" in node and not isinstance(node["readOnly"], bool):
        errors.append(f"{location}.readOnly: expected boolean")
    for property_name in ("readPermissions", "writePermissions"):
        if property_name in node:
            validate_permissions(node[property_name], f"{location}.{property_name}", errors)
    scale_mode = node.get("scaleMode")
    if scale_mode is not None and scale_mode not in SCALE_MODES:
        errors.append(f"{location}.scaleMode: expected one of {sorted(SCALE_MODES)}")
    clamp_mode = node.get("clampMode")
    if clamp_mode is not None and clamp_mode not in CLAMP_MODES:
        errors.append(f"{location}.clampMode: expected one of {sorted(CLAMP_MODES)}")
    eng_limit_mode = node.get("engLimitMode")
    if eng_limit_mode is not None and eng_limit_mode not in CLAMP_MODES:
        errors.append(f"{location}.engLimitMode: expected one of {sorted(CLAMP_MODES)}")
    for property_name in ("rawLow", "rawHigh", "scaledLow", "scaledHigh", "engLow", "engHigh"):
        if property_name in node:
            validate_number_or_binding(node[property_name], f"{location}.{property_name}", errors)
    if value_source == "derived":
        source_path = node.get("sourceTagPath")
        if isinstance(source_path, str):
            if not source_path.strip():
                errors.append(f"{location}.sourceTagPath: expected nonempty string or property-binding object")
            elif "{" in source_path or "}" in source_path:
                errors.append(
                    f"{location}.sourceTagPath: plain parameter text remains literal; use a property-binding object"
                )
        elif not validate_binding(source_path, f"{location}.sourceTagPath", errors):
            errors.append(f"{location}.sourceTagPath: expected nonempty string or property-binding object")
        getter = node.get("deriveExpressionGetter")
        if not isinstance(getter, str) or not getter.strip():
            errors.append(f"{location}.deriveExpressionGetter: derived member requires a nonempty expression")
        setter = node.get("deriveExpressionSetter")
        if setter is not None and (not isinstance(setter, str) or not setter.strip()):
            errors.append(f"{location}.deriveExpressionSetter: expected nonempty expression when present")
        preserve_timestamp = node.get("preserveSourceTimestamp")
        if preserve_timestamp is not None and not isinstance(preserve_timestamp, bool):
            errors.append(f"{location}.preserveSourceTimestamp: expected boolean")
    if value_source == "db":
        datasource = node.get("datasource")
        if not isinstance(datasource, str) or not datasource.strip():
            errors.append(f"{location}.datasource: database-query member requires a nonempty datasource")
        query = node.get("query")
        if isinstance(query, str):
            if not query.strip():
                errors.append(f"{location}.query: expected nonempty SQL text")
        elif not validate_binding(query, f"{location}.query", errors):
            errors.append(f"{location}.query: expected SQL string or property-binding object")
        query_type = node.get("queryType")
        if query_type is not None and query_type not in QUERY_TYPES:
            errors.append(f"{location}.queryType: expected one of {sorted(QUERY_TYPES)}")
        execution_mode = node.get("executionMode")
        if execution_mode is not None and execution_mode not in EXECUTION_MODES:
            errors.append(f"{location}.executionMode: expected one of {sorted(EXECUTION_MODES)}")
        if execution_mode == "FixedRate":
            execution_rate = node.get("executionRate")
            if (
                isinstance(execution_rate, bool)
                or not isinstance(execution_rate, (int, float))
                or execution_rate <= 0
            ):
                errors.append(f"{location}.executionRate: FixedRate requires a positive number")
    history_enabled = node.get("historyEnabled")
    if history_enabled is not None and not isinstance(history_enabled, bool):
        errors.append(f"{location}.historyEnabled: expected boolean")
    history_provider = node.get("historyProvider")
    if history_provider is not None:
        if isinstance(history_provider, str):
            if not history_provider.strip():
                errors.append(f"{location}.historyProvider: expected nonempty string or property-binding object")
            elif "{" in history_provider or "}" in history_provider:
                errors.append(
                    f"{location}.historyProvider: plain parameter text remains literal; use a property-binding object"
                )
        elif not validate_binding(history_provider, f"{location}.historyProvider", errors):
            errors.append(f"{location}.historyProvider: expected nonempty string or property-binding object")
    elif history_enabled is True:
        errors.append(f"{location}.historyProvider: history-enabled member requires a provider")
    history_style = node.get("historicalDeadbandStyle")
    if history_style is not None and history_style not in HISTORY_DEADBAND_STYLES:
        errors.append(f"{location}.historicalDeadbandStyle: expected one of {sorted(HISTORY_DEADBAND_STYLES)}")
    history_deadband_mode = node.get("historicalDeadbandMode")
    if history_deadband_mode is not None and history_deadband_mode not in DEADBAND_MODES:
        errors.append(f"{location}.historicalDeadbandMode: expected one of {sorted(DEADBAND_MODES)}")
    if "historicalDeadband" in node:
        validate_number_or_binding(node["historicalDeadband"], f"{location}.historicalDeadband", errors)
    sample_mode = node.get("sampleMode")
    if sample_mode is not None and sample_mode not in SAMPLE_MODES:
        errors.append(f"{location}.sampleMode: expected one of {sorted(SAMPLE_MODES)}")
    if "historySampleRate" in node:
        sample_rate = node["historySampleRate"]
        if isinstance(sample_rate, bool):
            errors.append(f"{location}.historySampleRate: expected positive number or property-binding object")
        elif isinstance(sample_rate, (int, float)):
            if sample_rate <= 0:
                errors.append(f"{location}.historySampleRate: expected positive number or property-binding object")
        elif not validate_binding(sample_rate, f"{location}.historySampleRate", errors):
            errors.append(f"{location}.historySampleRate: expected positive number or property-binding object")
    if sample_mode == "Periodic" and "historySampleRate" not in node:
        errors.append(f"{location}.historySampleRate: Periodic requires a positive rate or property-binding object")
    if sample_mode == "Periodic" and "historySampleRateUnits" not in node:
        errors.append(f"{location}.historySampleRateUnits: Periodic requires explicit units")
    for property_name in ("historySampleRateUnits", "historyTimeDeadbandUnits", "historyMaxAgeUnits"):
        unit = node.get(property_name)
        if unit is not None and unit not in TIME_UNITS:
            errors.append(f"{location}.{property_name}: expected one of {sorted(TIME_UNITS)}")
    history_tag_group = node.get("historyTagGroup")
    if sample_mode == "TagGroup" and (not isinstance(history_tag_group, str) or not history_tag_group.strip()):
        errors.append(f"{location}.historyTagGroup: TagGroup requires a nonempty tag-group path")
    for property_name in ("historyTimeDeadband", "historyMaxAge"):
        if property_name in node:
            value = node[property_name]
            if isinstance(value, bool):
                errors.append(f"{location}.{property_name}: expected nonnegative number or property-binding object")
            elif isinstance(value, (int, float)):
                if value < 0:
                    errors.append(f"{location}.{property_name}: expected nonnegative number or property-binding object")
            elif not validate_binding(value, f"{location}.{property_name}", errors):
                errors.append(f"{location}.{property_name}: expected nonnegative number or property-binding object")
    alarm_eval_enabled = node.get("alarmEvalEnabled")
    if alarm_eval_enabled is not None and not isinstance(alarm_eval_enabled, bool):
        errors.append(f"{location}.alarmEvalEnabled: expected boolean")
    parameters = node.get("parameters")
    if parameters is not None:
        validate_parameters(parameters, tag_type, f"{location}.parameters", errors)
    tags = node.get("tags")
    if tags is not None:
        if not isinstance(tags, list):
            errors.append(f"{location}.tags: expected array")
        else:
            seen = set()
            for index, child in enumerate(tags):
                validate_node(child, f"{location}.tags[{index}]", errors, tag_type)
                if isinstance(child, dict) and isinstance(child.get("name"), str):
                    if child["name"] in seen:
                        errors.append(f"{location}.tags[{index}].name: duplicate sibling {child['name']!r}")
                    seen.add(child["name"])
    alarms = node.get("alarms")
    if alarms is not None:
        if not isinstance(alarms, list):
            errors.append(f"{location}.alarms: expected array")
        else:
            seen_alarm_names = set()
            one_setpoint_modes = {"Equality", "Inequality", "AboveValue", "BelowValue"}
            two_setpoint_modes = {"BetweenValues", "OutsideValues"}
            for index, alarm in enumerate(alarms):
                alarm_location = f"{location}.alarms[{index}]"
                if not isinstance(alarm, dict):
                    errors.append(f"{alarm_location}: expected object")
                    continue
                alarm_name = alarm.get("name")
                if not isinstance(alarm_name, str) or not alarm_name.strip() or "/" in alarm_name:
                    errors.append(f"{alarm_location}.name: expected nonempty name without '/'")
                elif alarm_name in seen_alarm_names:
                    errors.append(f"{alarm_location}.name: duplicate alarm {alarm_name!r}")
                else:
                    seen_alarm_names.add(alarm_name)
                mode = alarm.get("mode")
                if mode not in ALARM_MODES:
                    errors.append(f"{alarm_location}.mode: expected one of {sorted(ALARM_MODES)}")
                priority = alarm.get("priority")
                if priority is not None:
                    if isinstance(priority, dict):
                        validate_alarm_expression_binding(priority, f"{alarm_location}.priority", errors)
                    elif priority not in ALARM_PRIORITIES:
                        errors.append(f"{alarm_location}.priority: expected one of {sorted(ALARM_PRIORITIES)} or an alarm-expression binding")
                ack_mode = alarm.get("ackMode")
                if ack_mode is not None and ack_mode not in ACK_MODES:
                    errors.append(f"{alarm_location}.ackMode: expected one of {sorted(ACK_MODES)}")
                if "enabled" in alarm:
                    enabled = alarm["enabled"]
                    if isinstance(enabled, dict):
                        validate_alarm_expression_binding(enabled, f"{alarm_location}.enabled", errors)
                    elif not isinstance(enabled, bool):
                        errors.append(f"{alarm_location}.enabled: expected boolean or alarm-expression binding")
                for property_name in ("inclusiveA", "inclusiveB", "anyChange", "bitOnZero", "ackNotesReqd", "shelvingAllowed"):
                    if property_name in alarm and not isinstance(alarm[property_name], bool):
                        errors.append(f"{alarm_location}.{property_name}: expected boolean")
                for property_name in ("setpointA", "setpointB"):
                    if property_name in alarm:
                        value = alarm[property_name]
                        if isinstance(value, dict):
                            validate_alarm_expression_binding(value, f"{alarm_location}.{property_name}", errors)
                        elif isinstance(value, bool) or not isinstance(value, (int, float)):
                            errors.append(f"{alarm_location}.{property_name}: expected JSON number or alarm-expression binding")
                for property_name in ("deadband", "timeOnDelaySeconds", "timeOffDelaySeconds"):
                    if property_name in alarm:
                        value = alarm[property_name]
                        if isinstance(value, bool) or not isinstance(value, (int, float)):
                            errors.append(f"{alarm_location}.{property_name}: expected concrete JSON number")
                        elif value < 0:
                            errors.append(f"{alarm_location}.{property_name}: expected nonnegative number")
                if mode in one_setpoint_modes and "setpointA" not in alarm:
                    errors.append(f"{alarm_location}.setpointA: {mode} requires a number or alarm-expression binding")
                if mode in two_setpoint_modes:
                    for property_name in ("setpointA", "setpointB"):
                        if property_name not in alarm:
                            errors.append(f"{alarm_location}.{property_name}: {mode} requires two numeric or alarm-expression setpoints")
                if "activeCondition" in alarm:
                    active_condition = alarm["activeCondition"]
                    if isinstance(active_condition, dict):
                        validate_alarm_expression_binding(active_condition, f"{alarm_location}.activeCondition", errors)
                    elif not isinstance(active_condition, bool):
                        errors.append(f"{alarm_location}.activeCondition: expected boolean or alarm-expression binding")
                elif mode == "OnCondition":
                    errors.append(f"{alarm_location}.activeCondition: OnCondition requires a boolean or alarm-expression binding")
                for property_name in ("label", "displayPath"):
                    if property_name in alarm:
                        value = alarm[property_name]
                        if isinstance(value, dict):
                            validate_alarm_expression_binding(value, f"{alarm_location}.{property_name}", errors)
                        elif not isinstance(value, str):
                            errors.append(f"{alarm_location}.{property_name}: expected string or alarm-expression binding")
                for property_name, value in alarm.items():
                    if property_name in ALARM_STANDARD_PROPERTIES:
                        continue
                    associated_location = f"{alarm_location}.{property_name}"
                    if not ASSOCIATED_DATA_NAME.fullmatch(property_name):
                        errors.append(
                            f"{associated_location}: associated-data name must be a portable identifier of 1-64 characters"
                        )
                    if isinstance(value, dict):
                        validate_alarm_expression_binding(value, associated_location, errors)
                    elif not isinstance(value, str):
                        errors.append(f"{associated_location}: expected string or alarm-expression binding")
                if mode == "Bit":
                    bit_position = alarm.get("bitPosition")
                    if isinstance(bit_position, bool) or not isinstance(bit_position, int) or bit_position < 0:
                        errors.append(f"{alarm_location}.bitPosition: Bit requires a nonnegative integer")
                if mode == "OutOfEngRange" and ("engLow" not in node or "engHigh" not in node):
                    errors.append(f"{alarm_location}.mode: OutOfEngRange requires member engLow and engHigh")
                alarm_deadband_mode = alarm.get("deadbandMode")
                if alarm_deadband_mode is not None and alarm_deadband_mode not in DEADBAND_MODES:
                    errors.append(f"{alarm_location}.deadbandMode: expected one of {sorted(DEADBAND_MODES)}")
                elif alarm_deadband_mode == "Percent":
                    errors.append(
                        f"{alarm_location}.deadbandMode: Percent persisted but did not clear in the verified 8.3.8 runtime; require target-specific proof or use Absolute"
                    )
    scripts = node.get("eventScripts")
    if scripts is not None:
        if not isinstance(scripts, list):
            errors.append(f"{location}.eventScripts: expected array")
        else:
            seen_event_ids = set()
            for index, event in enumerate(scripts):
                event_location = f"{location}.eventScripts[{index}]"
                if not isinstance(event, dict):
                    errors.append(f"{event_location}: expected event-script object")
                    continue
                unexpected = set(event) - {"eventid", "script", "enabled", "changeTypes"}
                if unexpected:
                    errors.append(f"{event_location}: unexpected keys {sorted(unexpected)}")
                event_id = event.get("eventid")
                if event_id not in EVENT_IDS:
                    errors.append(f"{event_location}.eventid: unsupported event")
                elif event_id in seen_event_ids:
                    errors.append(f"{event_location}.eventid: duplicate event {event_id!r}")
                else:
                    seen_event_ids.add(event_id)
                if "enabled" in event and not isinstance(event["enabled"], bool):
                    errors.append(f"{event_location}.enabled: expected boolean")
                change_types = event.get("changeTypes")
                if event_id == "qualifiedValueChanged":
                    if not isinstance(change_types, list) or not change_types:
                        errors.append(
                            f"{event_location}.changeTypes: qualifiedValueChanged requires a nonempty array chosen from {sorted(QUALIFIED_VALUE_CHANGE_TYPES)}"
                        )
                    else:
                        invalid_change_types = [
                            change_type for change_type in change_types
                            if not isinstance(change_type, str)
                            or change_type not in QUALIFIED_VALUE_CHANGE_TYPES
                        ]
                        if invalid_change_types:
                            errors.append(
                                f"{event_location}.changeTypes: unsupported values {invalid_change_types}; use uppercase VALUE, QUALITY, and/or TIMESTAMP"
                            )
                        string_change_types = [
                            change_type for change_type in change_types
                            if isinstance(change_type, str)
                        ]
                        if len(string_change_types) != len(set(string_change_types)):
                            errors.append(f"{event_location}.changeTypes: duplicate trigger")
                elif "changeTypes" in event:
                    errors.append(
                        f"{event_location}.changeTypes: only qualifiedValueChanged accepts changeTypes"
                    )
                script = event.get("script")
                if not isinstance(script, str) or not script.strip():
                    errors.append(f"{event_location}.script: expected nonempty string")
                else:
                    unindented = [
                        line_number
                        for line_number, line in enumerate(script.splitlines(), 1)
                        if line.strip() and line[0] not in " \t"
                    ]
                    if unindented:
                        errors.append(
                            f"{event_location}.script: every nonblank line must be indented inside the generated event function; unindented lines {unindented}"
                        )
                    if re.search(r"\btagPath\s*\.\s*getParentPath\s*\(", script):
                        errors.append(
                            f"{event_location}.script: tagPath is unicode text in the verified 8.3 runtime; use str(tagPath).rsplit('/', 1)[0], not getParentPath()"
                        )
                    if re.search(r"\balarmEvent\s*\.\s*getEventId\s*\(", script):
                        errors.append(
                            f"{event_location}.script: the verified AlarmEvent UUID method is getId(), not getEventId()"
                        )
                    if re.search(
                        r"\bsystem\s*\.\s*tag\s*\.\s*writeBlocking\s*\(\s*\[\s*\]\s*,\s*\[\s*\]\s*\)",
                        script,
                    ):
                        errors.append(
                            f"{event_location}.script: branch around an empty selection; do not call system.tag.writeBlocking([], [])"
                        )
                    if (
                        node.get("valueSource") == "expr"
                        and event_id == "valueChanged"
                        and re.search(r"\b(?:int|long|float)\s*\(\s*currentValue\s*\.\s*value\s*\)", script)
                        and not guards_current_value_before_numeric_conversion(script)
                    ):
                        errors.append(
                            f"{event_location}.script: expression-backed valueChanged callbacks can receive currentValue.value=None with initialChange false; guard None before numeric conversion with a positive check or early return"
                        )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("payload", type=Path)
    args = parser.parse_args()
    try:
        with args.payload.open("r", encoding="utf-8") as stream:
            payload = json.load(stream)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        print(json.dumps({"ok": False, "errors": [f"root: invalid JSON: {error}"]}, indent=2))
        raise SystemExit(1)
    errors = []
    if not isinstance(payload, dict):
        errors.append("root: official Ignition 8.3 tag import requires one JSON object; wrap siblings in Folder.tags")
    else:
        validate_node(payload, "root", errors)
    if errors:
        print(json.dumps({"ok": False, "errors": errors}, indent=2))
        raise SystemExit(1)
    print(json.dumps({"ok": True, "rootCount": 1}, indent=2))


if __name__ == "__main__":
    main()
