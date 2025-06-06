# test_all.ps1
$baseUrl = "http://127.0.0.1:5000"

Write-Host "`n--- 1. Create Session ---"
$sessionResp = Invoke-RestMethod -Uri "$baseUrl/api/session" -Method POST -Body (@{ name = "Test Session"; gm_user_id = "gm-user" } | ConvertTo-Json) -ContentType "application/json"
$sessionId = $sessionResp.session_id
Write-Host "Session ID: $sessionId"

Write-Host "`n--- 2. Join as Player ---"
$userJoinResp = Invoke-RestMethod -Uri "$baseUrl/api/session/$sessionId/join" -Method POST -Body (@{ user_id = "test-player"; role = "player" } | ConvertTo-Json) -ContentType "application/json"
Write-Host "Player joined: $($userJoinResp.user_id) as $($userJoinResp.role)"

Write-Host "`n--- 3. Join as GM ---"
$gmJoinResp = Invoke-RestMethod -Uri "$baseUrl/api/session/$sessionId/join" -Method POST -Body (@{ user_id = "gm-user"; role = "gm" } | ConvertTo-Json) -ContentType "application/json"
Write-Host "GM joined: $($gmJoinResp.user_id) as $($gmJoinResp.role)"

Write-Host "`n--- 4. Set Scene (as GM) ---"
$sceneSetResp = Invoke-RestMethod -Uri "$baseUrl/api/session/$sessionId/scene" -Method POST -Body (@{ summary = "Neon-lit alleyway, rain falling, danger everywhere."; user_id = "gm-user" } | ConvertTo-Json) -ContentType "application/json"
Write-Host "Scene set: $($sceneSetResp.summary)"

Write-Host "`n--- 5. Get Scene ---"
$sceneGetResp = Invoke-RestMethod -Uri "$baseUrl/api/session/$sessionId/scene" -Method GET
Write-Host "Scene fetched: $($sceneGetResp.summary)"

Write-Host "`n--- 6. Add Entity (as GM) ---"
$entityAddResp = Invoke-RestMethod -Uri "$baseUrl/api/session/$sessionId/entities" -Method POST -Body (@{ name = "Shadowrunner"; type = "player"; status = "active"; extra_data = '{"edge":3,"notes":"Armed and ready"}'; user_id = "gm-user" } | ConvertTo-Json) -ContentType "application/json"
$entityId = $entityAddResp.id
Write-Host "Entity added: $($entityAddResp.name) (ID: $entityId)"

Write-Host "`n--- 7. List Entities ---"
$entities = Invoke-RestMethod -Uri "$baseUrl/api/session/$sessionId/entities" -Method GET
Write-Host "Entities: " ($entities | ConvertTo-Json -Depth 5)

Write-Host "`n--- 8. Update Entity (as GM) ---"
$entityUpdateResp = Invoke-RestMethod -Uri "$baseUrl/api/session/$sessionId/entities" -Method POST -Body (@{ id = $entityId; name = "Shadowrunner"; type = "player"; status = "marked"; extra_data = '{"edge":2,"notes":"Wounded"}'; user_id = "gm-user" } | ConvertTo-Json) -ContentType "application/json"
Write-Host "Entity updated: $($entityUpdateResp.name) status $($entityUpdateResp.status)"

Write-Host "`n--- 9. Delete Entity (as GM) ---"
$entityDeleteResp = Invoke-RestMethod -Uri "$baseUrl/api/session/$sessionId/entities/$entityId" -Method DELETE -Body (@{ user_id = "gm-user" } | ConvertTo-Json) -ContentType "application/json"
Write-Host "Entity deleted: $($entityDeleteResp.status)"

Write-Host "`n--- 10. Test LLM Streaming Endpoint ---"
$llmPayload = @{
    session_id = $sessionId
    user_id = "test-player"
    input = "Say hello in character."
    model = "openai"
    model_name = "gpt-4o"
}
$llmJson = $llmPayload | ConvertTo-Json
$tmp = New-TemporaryFile
Set-Content -Path $tmp -Value $llmJson -Encoding UTF8
Write-Host "Streaming AI response (Ctrl+C to stop):"
curl.exe -X POST "$baseUrl/api/llm" -H "Content-Type: application/json" --data-binary "@$tmp"
Remove-Item $tmp