$tok = (Get-Content 'E:\pat.txt' -Raw).Trim()
if (-not $tok) { Write-Error 'Token vacio en E:\pat.txt'; exit 1 }
$h = @{ Authorization = "Bearer $tok"; Accept = 'application/vnd.github+json' }

$me = Invoke-RestMethod -Uri 'https://api.github.com/user' -Headers $h
$owner = $me.login
$repo = 'dino-runner-20'
"OWNER: $owner"
"REPO: $repo"

$repoUrl = "https://api.github.com/repos/$owner/$repo"
try {
    Invoke-RestMethod -Uri $repoUrl -Headers $h | Out-Null
    "REPO YA EXISTE - se actualizara"
} catch {
    $body = @{ name = $repo; description = 'Dino Runner 2.0 Ultimate Edition - APK build (pygame)'; private = $false; auto_init = $true } | ConvertTo-Json
    Invoke-RestMethod -Method Post -Uri 'https://api.github.com/user/repos' -Headers $h -Body $body | Out-Null
    "REPO CREADO (publico)"
    Start-Sleep -Seconds 5
}

$base = 'E:\dino run'
# Excluir carpetas que no deben subirse
$exclude = @('__pycache__', '.git', 'crash.log', 'progreso_dino.json', 'top_scores.txt')
$files = Get-ChildItem $base -Recurse -File | Where-Object {
    $full = $_.FullName
    -not ($exclude | Where-Object { $full -like "*$_*" })
}
"Archivos a subir: $($files.Count)"
$count = 0
foreach ($f in $files) {
    $rel = $f.FullName.Substring($base.Length + 1) -replace '\\', '/'
    # para GitHub API necesita base64 y mensaje
    $b64 = [Convert]::ToBase64String([IO.File]::ReadAllBytes($f.FullName))
    # verificar si ya existe para obtener sha (update)
    $uri = "https://api.github.com/repos/$owner/$repo/contents/$($rel -replace ' ', '%20')"
    $sha = $null
    try {
        $existing = Invoke-RestMethod -Uri $uri -Headers $h -Method Get
        $sha = $existing.sha
    } catch {}
    $bodyObj = @{ message = "update $rel"; content = $b64 }
    if ($sha) { $bodyObj.sha = $sha }
    $body = $bodyObj | ConvertTo-Json -Depth 3
    try {
        Invoke-RestMethod -Method Put -Uri $uri -Headers $h -Body $body | Out-Null
        $count++
        Write-Host "OK $rel"
    } catch {
        Write-Error "FALLO $rel : $($_.Exception.Message) $($_.ErrorDetails.Message)"
    }
    Start-Sleep -Milliseconds 300
}
"SUBIDOS: $count de $($files.Count)"
Start-Sleep -Seconds 5
$actions = "https://api.github.com/repos/$owner/$repo/actions/runs"
try { $runs = Invoke-RestMethod -Uri $actions -Headers $h; "RUNS: " + $runs.workflow_runs.Count + " ultimo estado: " + $runs.workflow_runs[0].status } catch { "sin runs aun - revisa https://github.com/$owner/$repo/actions" }
"URL: https://github.com/$owner/$repo"
