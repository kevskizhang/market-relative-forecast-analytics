Push-Location "$PSScriptRoot\..\api"
try {
    ..\.venv\Scripts\python.exe -m app.migrate_decimal_quantities
}
finally {
    Pop-Location
}
