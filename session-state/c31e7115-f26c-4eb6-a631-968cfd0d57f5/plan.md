# Echo IP Synchronization Follow-up

1. Complete: corrected the harness so an explicitly selected Echo-listed virtual adapter address is accepted.
2. Complete: updated the Echo setup and troubleshooting documentation to match Rockwell QA64164.
3. Complete: built the harness and verified that it selects the documented KM-TEST address.

The Echo 4.0.1437 controller runtime still fails to bind both the KM-TEST address and an active
Wi-Fi address after the documented repair and a Windows restart. This is an Echo runtime/install
fault, not a repository address-selection issue.
