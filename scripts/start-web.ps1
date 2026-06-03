Push-Location "$PSScriptRoot\..\web"
try {
    npm.cmd run dev
}
finally {
    Pop-Location
}
