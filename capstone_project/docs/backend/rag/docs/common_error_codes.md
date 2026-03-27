# Common Error Codes

## VPN Errors

**Error 422: Authentication Timeout**
- Close AnyConnect
- Wait 30 seconds
- Reopen and reconnect
- Respond to MFA within 60 seconds

**Error 412: Precondition Failed**
- Install Windows updates
- Ensure antivirus is running
- Enable firewall
- Restart and retry

## Windows Errors

**0x80070005: Access Denied**
- Run as Administrator
- Check file permissions
- Run Windows Update Troubleshooter

**0x80004005: Unspecified Error**
- Clear Windows Update cache
- Restart and retry
- Check file isn't open elsewhere

## Outlook Errors

**0x8004010F: Cannot Access Data File**
- Close Outlook
- Run SCANPST.EXE
- Repair data file
- Restart Outlook

## Network Errors

**DNS_PROBE_FINISHED_NXDOMAIN**
- Flush DNS cache: ipconfig /flushdns
- Use Google DNS: 8.8.8.8
- Restart router

**ERR_CONNECTION_TIMED_OUT**
- Check internet connection
- Disable VPN temporarily
- Clear browser cache
