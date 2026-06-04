Push-Location "$PSScriptRoot\..\api"
try {
    ..\.venv\Scripts\python.exe -m app.migrate_kalshi_fills
}
finally {
    Pop-Location
}
