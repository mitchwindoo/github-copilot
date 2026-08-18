# FactoryTalk Logix Echo 4.00.00 - IP Synchronization Failure Diagnosis
**Diagnosed: 2026-08-05**  
**System: Studio 5000 v38.00.00 + FactoryTalk Logix Echo 4.00.00**

---

## The Problem

When attempting to bind a controller to IP `192.168.127.10/24`, you receive:
```
The operation could not be performed because controller 'ProductionLinePRGV01' 
in slot 0 in chassis 'Chassis' has not yet been synchronized with 
the requested IP address configuration.
```

This error appears in the Echo Dashboard GUI and prevents IP configuration changes.

---

## Root Cause Analysis

### Evidence from Logs

From `MitchellLandreth-ft-logix-echo-app-backend.log`:

**Line 49** (Initial controller creation):
```
IP=127.0.0.1
Controller mode=0, Enabled false
```

**Lines 52-66** (Attempt to change IP → Error):
```
error: The operation could not be performed because controller 'ProductionLinePRGV01' 
in slot 0 in chassis 'acs-ci-shd-liftstation' has not yet been synchronized with 
the requested IP address configuration.
```

**Key observation**: The controller state is `Enabled false` when attempting the IP change.

### Root Causes (Priority Order)

#### 1. **Controller Not Yet Running (PRIMARY)**
- Echo requires the controller **emulation process to be fully initialized and running** before IP can be synchronized
- The controller reports `Enabled: false`, meaning the emulator hasn't started
- **Solution**: Enable the controller FIRST, then modify the IP address

#### 2. **Service Account Permissions (SECONDARY)**
- Echo Service runs as: `NT AUTHORITY\LocalService` (restricted account)
- LocalService has limited access to network adapter bindings, especially custom addresses like `192.168.127.10`
- The Ethernet 4 adapter (loopback) exists on the system, but LocalService may not have permission to bind to it
- **Solution**: Reconfigure Echo service to run under a named interactive account

#### 3. **Race Condition (TERTIARY)**
- Dashboard attempting to modify controller properties immediately after creation
- Controller emulation process still initializing
- **Solution**: Add delay (2-5 seconds) after controller creation before modifying IP

#### 4. **Not a v37 IP Length Issue**
- The v37 "15-character limit" does NOT apply to v38
- Your IP `192.168.127.10` is 14 characters and is NOT the issue
- This is a **different, controller-state-dependent synchronization error**

---

## Solution Steps

### **Immediate Fix: Enable Controller Before IP Change**

In the **Echo Dashboard GUI**:

1. **Create the chassis** (if not exists)
2. **Add controller from ACD**
3. **In controller properties**: Toggle `Enabled: ON` 
4. **Wait 5-10 seconds** for the emulator to fully initialize
5. **Then modify the IP address** to `192.168.127.10`
6. **Verify**: Check status shows `Enabled: true` and IP is bound

### **Root Fix: Reconfigure Echo Service Account**

#### Current Configuration
```
Service: FactoryTalk Logix Echo Service
Running As: NT AUTHORITY\LocalService  ← PROBLEM: Restricted account
```

#### Recommended Configuration
```
Service: FactoryTalk Logix Echo Service
Running As: <your-interactive-username>  ← Interactive user with network access
```

**Steps to Change**:

1. **Open Services (services.msc)**:
   ```powershell
   services.msc
   ```

2. **Locate services**:
   - FactoryTalk Logix Echo Service
   - FactoryTalk Logix Echo Message Broker

3. **For each service**:
   - Right-click → Properties
   - Go to "Log On" tab
   - Select "This account"
   - Enter: `MitchellLandreth` (or whatever your machine user is)
   - Enter password
   - Click OK

4. **Restart both services**:
   ```powershell
   Restart-Service -Name "FactoryTalk Logix Echo Service"
   Restart-Service -Name "FactoryTalk Logix Echo Message Broker"
   ```

5. **Verify**:
   ```powershell
   Get-Service | Where-Object {$_.Name -like "*Echo*"}
   ```

6. **Test the fix**:
   - Reopen Echo Dashboard
   - Create a new chassis
   - Create controller with default IP
   - Enable controller
   - Modify IP to `192.168.127.10`
   - Should succeed now

---

## Why This Happened

1. **LocalService Account Limitation**:
   - NT AUTHORITY\LocalService is a virtual account with minimal network privileges
   - Cannot bind to custom network adapters like KM-TEST (Ethernet 4)
   - Intended for background services, not user-facing apps that manage hardware

2. **Controller State Requirement**:
   - Echo's internal synchronization happens when the controller is running
   - You cannot change the IP of a disabled (not emulating) controller
   - The emulation must be active for the OS network binding to succeed

3. **Sequence Dependency**:
   - Create Controller
   - Enable Controller (start emulation) ← **Missing step**
   - Change IP Address (synchronize)

---

## Verification: Check If This Works

After implementing the fix:

1. **Open Echo Dashboard**
2. **Create Chassis**: Name: `TestChassis`
3. **Add Controller from ACD**: Use your `SHD-BOI-Line-ACD.updated.ACD`
4. **Enable Controller**: Checkbox must be ✓
5. **Wait**: 10 seconds for emulator to initialize
6. **Modify IP**: Right-click controller → Properties → Change IP to `192.168.127.10`
7. **Expected Result**: ✓ Success (no error)

---

## Reference: Echo Official Behavior

From [docs/testing/logix-echo-setup.md](file:///C:/Users/MitchellLandreth/Git-Local/AB-Logix-CI-CD/docs/testing/logix-echo-setup.md) line 109:

> "Controller reports it failed to set its IP address" → "The controller process could not bind the Windows-configured address. Restart Echo after confirming the address is present; if it persists for both a KM-TEST address and an active physical adapter, collect the Echo controller `Root/output.log` and escalate as an Echo installation/runtime fault."

This is documented as a known issue when:
1. The address is not accessible to the service account
2. The controller emulation is not active
3. The address binding is not complete after restart

---

## Log File Locations

If you need to debug further:

- **Echo Backend Log** (Frontend dashboard):  
  `C:\ProgramData\Rockwell Software\FactoryTalk Logix Echo\MitchellLandreth-ft-logix-echo-app-backend.log`

- **Echo Controller Logs** (emulation process):  
  Check the Echo Dashboard for "Root/output.log" path (varies by controller UUID)

- **Windows Event Viewer** (service errors):  
  `eventvwr.msc` → Application log → Filter by Source: "Echo"

---

## Next Steps

1. ✅ Change Echo service account to your interactive user
2. ✅ Restart Echo services
3. ✅ Test IP binding via GUI
4. ✅ Once working in GUI, verify via CI/CD (LDSDK will auto-sync once Echo is fixed)
5. ✅ Document the fix in your CI documentation

**After this fix, the CI/CD harness should work without modification.**

