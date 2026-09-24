param([Parameter(ValueFromRemainingArguments=$true)][string[]]$MvpArgs)
& "$PSScriptRoot/.venv/Scripts/python.exe" "$PSScriptRoot/mvp/launch.py" @MvpArgs
exit $LASTEXITCODE
