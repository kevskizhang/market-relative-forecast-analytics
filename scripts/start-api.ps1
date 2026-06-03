Push-Location "$PSScriptRoot\..\api"
try {
    ..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
}
finally {
    Pop-Location
}
