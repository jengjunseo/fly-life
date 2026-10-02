param([Parameter(ValueFromRemainingArguments=$true)][string[]]$MvpArgs)
if (-not (Test-Path -LiteralPath "$PSScriptRoot/.venv/Scripts/python.exe")) {
    Write-Error '실행용 Python 환경이 없습니다. README의 새 PC 설치 절차를 먼저 실행하세요.'
    exit 1
}
$env:PYTHONUTF8='1'
& "$PSScriptRoot/.venv/Scripts/python.exe" "$PSScriptRoot/mvp/launch.py" @MvpArgs
exit $LASTEXITCODE
