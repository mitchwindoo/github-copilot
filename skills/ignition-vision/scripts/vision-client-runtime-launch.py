"""Launch a classic-auth Vision Client with credentials supplied only by environment.

Run this script with the Ignition-bundled Jython jar and launchclient.jar on the
Java classpath. The normal desktop BootstrapSwing entry point does not accept
username/password JVM properties. Launcher.startLauncherInitial(user, pass)
places the credentials in Ignition's in-memory launcher attributes instead.
"""

import json
import re

from java.io import File, FileOutputStream, OutputStreamWriter
from java.lang import Runnable, String, System, Thread
from java.security import MessageDigest
from javax.swing import JFrame, SwingUtilities

from com.inductiveautomation.ignition.client.launch import FrameAppListener
from com.inductiveautomation.ignition.client.launch import LaunchParent
from com.inductiveautomation.ignition.client.launch import Launcher
from com.inductiveautomation.ignition.client.launch import LauncherParent
from com.inductiveautomation.ignition.client.launch import LaunchSpec
from com.inductiveautomation.ignition.client.launch import RootPaneAppListener


USERNAME_ENV = "IGNITION_VISION_USERNAME"
PASSWORD_ENV = "IGNITION_VISION_PASSWORD"
DIAGNOSTIC_FILE_ENV = "IGNITION_VISION_DIAGNOSTIC_FILE"
MAX_DIAGNOSTIC_TEXT = 500
DIAGNOSTIC_SCHEMA_VERSION = 2


def _safe_text(value):
    text = unicode(value or "")
    text = re.sub(
        r"(?i)\b(password|passwd|token|secret|api[_-]?key)\b\s*[:=]\s*[^\s,;]+",
        r"\1=<redacted>",
        text,
    )
    if len(text) > MAX_DIAGNOSTIC_TEXT:
        return text[:MAX_DIAGNOSTIC_TEXT] + "<truncated>"
    return text


def _sha256_text(value):
    digest = MessageDigest.getInstance("SHA-256").digest(String(unicode(value or "")).getBytes("UTF-8"))
    return "".join(["%02x" % (item & 0xFF) for item in digest])


def _type_name(value):
    if value is None:
        return None
    try:
        name = getattr(value.__class__, "__name__", None)
        if name:
            return unicode(name)
    except Exception:
        pass
    return _safe_text(type(value))


def _write_diagnostic(path, value):
    target = File(path)
    parent = target.getParentFile()
    if parent is not None:
        parent.mkdirs()
    writer = OutputStreamWriter(FileOutputStream(target), "UTF-8")
    try:
        writer.write(json.dumps(value, indent=2, sort_keys=True) + "\n")
        writer.flush()
    finally:
        writer.close()


def _write_diagnostic_stage(stage, details=None):
    path = System.getenv(DIAGNOSTIC_FILE_ENV) or ""
    if not path:
        return
    report = {
        "schemaVersion": DIAGNOSTIC_SCHEMA_VERSION,
        "capturedAtEpochMillis": System.currentTimeMillis(),
        "stage": stage,
        "scriptConfigAvailable": False,
        "handlers": [],
        "readinessTimeline": [],
    }
    if details:
        report.update(details)
    _write_diagnostic(path, report)


def _handler_records(config):
    records = []
    handler_map = config.getMessageHandlerScripts()
    if handler_map is not None:
        for entry in handler_map.entrySet():
            key = entry.getKey()
            script = unicode(entry.getValue() or "")
            permissions = key.getPermissions()
            records.append(
                {
                    "name": unicode(key.getName() or ""),
                    "enabled": bool(key.isEnabled()),
                    "threadType": unicode(key.getThreadType() or ""),
                    "permissionsMode": (
                        "unrestricted" if permissions is None else "explicit-list"
                    ),
                    "permissionsNull": permissions is None,
                    "permissionCount": permissions.size() if permissions is not None else 0,
                    "scriptChars": len(script),
                    "scriptSha256": _sha256_text(script),
                    "hasHandleMessageEntrypoint": bool(
                        re.search(r"(?m)^def handleMessage\(payload\):\s*$", script)
                    ),
                }
            )
    records.sort(key=lambda item: (item["name"], item["threadType"], item["scriptSha256"]))
    return records


def _manager_diagnostics(fpmi_app, loader, fpmi_class):
    result = {
        "messageReceiverAvailable": False,
        "messageHandlerManagerAvailable": False,
        "managerHandlerNames": [],
        "scriptDiagnosticCount": 0,
        "scriptDiagnostics": [],
        "scriptExecutionReportCount": 0,
        "scriptExecutionReports": [],
    }
    receiver_field = fpmi_class.getDeclaredField("messageReceiver")
    receiver_field.setAccessible(True)
    receiver = receiver_field.get(fpmi_app)
    if receiver is None:
        return result
    result["messageReceiverAvailable"] = True
    receiver_class = loader.loadClass(
        "com.inductiveautomation.factorypmi.application.script.ScriptMessageReceiver"
    )
    manager_field = receiver_class.getDeclaredField("manager")
    manager_field.setAccessible(True)
    manager = manager_field.get(receiver)
    if manager is None:
        return result
    result["messageHandlerManagerAvailable"] = True
    manager_class = loader.loadClass(
        "com.inductiveautomation.ignition.common.script.message.MessageHandlerManager"
    )
    handlers_field = manager_class.getDeclaredField("handlersMap")
    handlers_field.setAccessible(True)
    handlers = handlers_field.get(manager)
    if handlers is not None:
        names = []
        for key in handlers.keySet():
            if hasattr(key, "getName"):
                names.append(unicode(key.getName() or ""))
            else:
                names.append(unicode(key or ""))
        result["managerHandlerNames"] = sorted(names)
    diagnostics = manager.getScriptDiagnostics()
    if diagnostics is not None:
        result["scriptDiagnosticCount"] = diagnostics.size()
        result["scriptDiagnostics"] = [
            {
                "class": _type_name(item),
                "summary": _safe_text(item),
            }
            for item in list(diagnostics)[:20]
        ]
    reports = manager.getScriptExecutionReports()
    if reports is not None:
        result["scriptExecutionReportCount"] = reports.size()
        result["scriptExecutionReports"] = [
            {
                "class": _type_name(item),
                "summary": _safe_text(item),
            }
            for item in list(reports)[:20]
        ]
    return result


def _diagnostic_manager_ready(report):
    manager = report.get("manager") or {}
    configured = set(
        [item.get("name", "") for item in report.get("handlers", []) if item.get("name")]
    )
    registered = set(manager.get("managerHandlerNames", []))
    return bool(
        report.get("scriptConfigAvailable")
        and manager.get("messageReceiverAvailable")
        and manager.get("messageHandlerManagerAvailable")
        and configured.issubset(registered)
    )


def _capture_client_diagnostics(parent, context, attempt):
    report = {
        "schemaVersion": DIAGNOSTIC_SCHEMA_VERSION,
        "capturedAtEpochMillis": System.currentTimeMillis(),
        "attempt": attempt,
        "launcherAppClass": _type_name(parent.app),
        "launcherContextClass": _type_name(context),
        "scriptConfigAvailable": False,
        "handlers": [],
    }
    try:
        loader = Thread.currentThread().getContextClassLoader()
        if loader is None:
            raise RuntimeError("Vision client context classloader is unavailable")
        fpmi_class = loader.loadClass("com.inductiveautomation.factorypmi.application.FPMIApp")
        get_instance = fpmi_class.getMethod("getInstance", [])
        fpmi_app = get_instance.invoke(None, [])
        report["fpmiAppAvailable"] = fpmi_app is not None
        if fpmi_app is None:
            return report
        config = fpmi_app.getScriptConfig()
        report["scriptConfigAvailable"] = config is not None
        if config is None:
            return report
        report["scriptConfigClass"] = _type_name(config)
        report["handlers"] = _handler_records(config)
        try:
            report["manager"] = _manager_diagnostics(fpmi_app, loader, fpmi_class)
            report["handlerManagerReady"] = _diagnostic_manager_ready(report)
        except Exception as exc:
            report["managerDiagnosticError"] = _safe_text(repr(exc))
    except Exception as exc:
        report["captureError"] = _safe_text(repr(exc))
    return report


def _timeline_record(report):
    manager = report.get("manager") or {}
    handlers = report.get("handlers") or []
    return {
        "attempt": report.get("attempt"),
        "capturedAtEpochMillis": report.get("capturedAtEpochMillis"),
        "scriptConfigAvailable": bool(report.get("scriptConfigAvailable")),
        "handlerNames": sorted(
            [item.get("name", "") for item in handlers if item.get("name")]
        ),
        "unrestrictedHandlerNames": sorted(
            [
                item.get("name", "")
                for item in handlers
                if item.get("name") and item.get("permissionsNull") is True
            ]
        ),
        "messageReceiverAvailable": bool(manager.get("messageReceiverAvailable")),
        "messageHandlerManagerAvailable": bool(
            manager.get("messageHandlerManagerAvailable")
        ),
        "managerHandlerNames": sorted(manager.get("managerHandlerNames", [])),
        "handlerManagerReady": bool(report.get("handlerManagerReady")),
        "captureError": report.get("captureError"),
        "managerDiagnosticError": report.get("managerDiagnosticError"),
    }


class _DiagnosticCapture(Runnable):
    def __init__(self, parent, context, path):
        self.parent = parent
        self.context = context
        self.path = path

    def run(self):
        report = {}
        timeline = []
        for attempt in range(1, 61):
            report = _capture_client_diagnostics(self.parent, self.context, attempt)
            timeline.append(_timeline_record(report))
            report["readinessTimeline"] = list(timeline)
            _write_diagnostic(self.path, report)
            if report.get("handlerManagerReady"):
                break
            Thread.sleep(1000)


def _start_diagnostic_capture(parent, context):
    path = System.getenv(DIAGNOSTIC_FILE_ENV) or ""
    if not path or parent.diagnostics_started:
        return
    parent.diagnostics_started = True
    thread = Thread(_DiagnosticCapture(parent, context, path), "VisionClientBootstrapDiagnostic")
    loader = Thread.currentThread().getContextClassLoader()
    if loader is not None:
        thread.setContextClassLoader(loader)
    thread.setDaemon(True)
    thread.start()


class _UiCall(Runnable):
    def __init__(self, function):
        self.function = function

    def run(self):
        self.function()


def _on_edt(function):
    if SwingUtilities.isEventDispatchThread():
        function()
    else:
        SwingUtilities.invokeAndWait(_UiCall(function))


class RuntimeLauncherParent(LauncherParent, LaunchParent):
    def __init__(self):
        self.launcher = None
        self.app = None
        self.frame = None
        self.splash_frame = None
        self.diagnostics_started = False

    def getLaunchProperty(self, property_name):
        return System.getProperty(property_name)

    def showSplash(self, splash):
        _write_diagnostic_stage("showSplash")

        def show():
            if self.splash_frame is not None:
                self.splash_frame.dispose()
            frame = JFrame("Ignition Vision Client")
            frame.setUndecorated(True)
            frame.setContentPane(splash)
            frame.pack()
            frame.setLocationRelativeTo(None)
            frame.setVisible(True)
            self.splash_frame = frame

        _on_edt(show)

    def handleError(self, message):
        # Do not echo launcher arguments, attributes, or credentials.
        _write_diagnostic_stage("handleError", {"message": _safe_text(message)})
        System.err.println("Vision client launcher reported an error.")

    def isFullScreen(self):
        return False

    def getRootPaneContainer(self):
        return self.frame

    def setContent(self, context, app):
        self.app = app
        _write_diagnostic_stage(
            "setContent",
            {
                "launcherAppClass": _type_name(app),
                "launcherContextClass": _type_name(context),
            },
        )

        def install():
            if self.splash_frame is not None:
                self.splash_frame.dispose()
                self.splash_frame = None
            if self.frame is None:
                frame = JFrame(app.getFrameTitle())
                frame.setSize(app.getInitialFrameSize())
                frame.setLocationRelativeTo(None)
                if app.isStartMaximized():
                    frame.setExtendedState(JFrame.MAXIMIZED_BOTH)
                self.frame = frame
                RootPaneAppListener.install(frame, app)
                FrameAppListener.install(frame, app)
            self.frame.setVisible(True)

        _on_edt(install)
        _start_diagnostic_capture(self, context)

    def getLaunchFlavor(self):
        return LaunchParent.LaunchFlavor.JWS_WINDOWED

    def restart(self, gateway_addresses, project_name, scope, user_object):
        if self.app is not None:
            self.app.shutdown()
        previous = self.launcher.getLastSpec()
        spec = LaunchSpec(
            previous.getMainClass(),
            System.currentTimeMillis(),
            gateway_addresses,
            previous.getPlatformEdition(),
            previous.getEdgeFlags(),
            project_name,
            scope,
            user_object,
        )
        self.launcher.startLauncher(spec)


def main():
    username = System.getenv(USERNAME_ENV) or ""
    password = System.getenv(PASSWORD_ENV) or ""
    if not username or not password:
        raise RuntimeError("Vision credentials must be supplied through environment variables")
    _write_diagnostic_stage("launcherScriptStarted")
    parent = RuntimeLauncherParent()
    parent.launcher = Launcher(parent, parent)
    _write_diagnostic_stage("launcherCreated")
    # This overload writes sso-username/sso-password only to the launcher's
    # in-memory attribute map. Neither value is placed on the Java command line.
    parent.launcher.startLauncherInitial(username, password)
    _write_diagnostic_stage("startLauncherInitialReturned")
    return parent


RUNTIME_LAUNCHER_PARENT = main()
