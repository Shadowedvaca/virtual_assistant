#Normal
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000got
# W/ Verbose Logs
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 --log-level debug
# W/O reloader and with access logs
uvicorn app.main:app --host 127.0.0.1 --port 8000 --log-level debug --access-log