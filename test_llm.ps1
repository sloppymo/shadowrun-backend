# PowerShell script to automate session, user join, and LLM test for Shadowrun backend

# 1. Create a session and extract session_id
$sessionResp = Invoke-RestMethod -Uri "http://127.0.0.1:5000/api/session" -Method POST -ContentType "application/json" -Body '{ "name": "Test Session", "gm_user_id": "test-gm" }'
$session_id = $sessionResp.session_id
Write-Host "Session ID: $session_id"

# 2. Join a user to the session
$userResp = Invoke-RestMethod -Uri "http://127.0.0.1:5000/api/session/$session_id/join" -Method POST -ContentType "application/json" -Body '{ "user_id": "test-user", "role": "player" }'
Write-Host "User joined: $($userResp.user_id) as $($userResp.role)"

# 3. Prepare JSON for LLM endpoint
$llmPayload = @{
    session_id = $session_id
    user_id    = "test-user"
    input      = "Say hello as a Shadowrun AI."
    model      = "openai"
    model_name = "gpt-4o"
} | ConvertTo-Json -Compress

# 4. Write payload to a temp file and test the LLM endpoint with curl (for streaming)
$tempFile = "payload.json"
Set-Content -Path $tempFile -Value $llmPayload -Encoding UTF8
Write-Host "`nTesting LLM endpoint (press Ctrl+C to stop streaming):"
curl.exe -N -X POST http://127.0.0.1:5000/api/llm -H "Content-Type: application/json" -d @$tempFile
Remove-Item $tempFile
