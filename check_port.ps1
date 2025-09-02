Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
# should print nothing
