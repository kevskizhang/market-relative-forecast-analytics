Push-Location "$PSScriptRoot\..\api"
try {
    ..\.venv\Scripts\python.exe -m app.init_db
}
finally {
    Pop-Location
}
