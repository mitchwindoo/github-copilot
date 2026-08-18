## Plan

1. [done] Audit local prerequisites and repo configuration for Python/.NET/RAG/harness tools.
2. [done] Set up workspace Python environment and install project extras.
3. [done] Validate Python tooling (logix tests, plan validation, RAG index/query/probe).
4. [done] Validate .NET harness restore/build prerequisites and detect missing Rockwell SDK packages.
5. [done] Report readiness status with exact remaining manual Windows-only requirements.
6. [in progress] Troubleshoot Echo/LDSDK handshake for the lift-station test run.
   - Controller creation race fixed by adopting the existing controller after the first IP-sync failure.
   - Remaining blocker is `RxE_COMM_DTLERROR` from `LogixProject.GoOnlineAsync()` after the comm path is set.
   - Echo reports the controller as enabled, fault-free, `ControllerStatusOK`, and `RemoteProgram`,
     but every LDSDK mode/download call still fails at the FactoryTalk Linx layer.
