$ErrorActionPreference = 'Stop'
$base = 'http://127.0.0.1:8000'
$task = Invoke-RestMethod "$base/tasks" -Method Post -ContentType 'application/json' -Body '{"prompt":"Plan a community garden with a measurable pilot"}'
Invoke-RestMethod "$base/tasks/$($task.id)/start" -Method Post
$deadline = (Get-Date).AddSeconds(30)
do {
    Start-Sleep -Milliseconds 300
    $result = Invoke-RestMethod "$base/tasks/$($task.id)"
    Write-Host $result.status
} while ($result.status -in @('CREATED', 'RUNNING') -and (Get-Date) -lt $deadline)
$result | ConvertTo-Json -Depth 10
if ($result.status -ne 'COMPLETED') { throw 'Pipeline did not complete' }
Invoke-RestMethod "$base/tasks/$($task.id)/events" | Format-Table
