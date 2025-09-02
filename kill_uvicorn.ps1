# Run in an elevated PowerShell
Stop-Process -Name python  -Force -ErrorAction SilentlyContinue
Stop-Process -Name pythonw -Force -ErrorAction SilentlyContinue
Stop-Process -Name uvicorn -Force -ErrorAction SilentlyContinue
Stop-Process -Name watchfiles -Force -ErrorAction SilentlyContinue