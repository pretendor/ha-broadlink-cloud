# Publish a prepared local repository to an existing *empty* PUBLIC GitHub repository.
# Usage: .\publish-github.ps1 -Owner YOUR_GITHUB_USERNAME -Repo ha-broadlink-cloud
param(
    [Parameter(Mandatory=$true)][string]$Owner,
    [string]$Repo = 'ha-broadlink-cloud'
)

$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw 'Git is not installed. Install Git for Windows or use GitHub Desktop.'
}
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw 'Python is not available in PATH.'
}

python .\setup_github.py --owner $Owner --repo $Repo
if ($LASTEXITCODE -ne 0) { throw 'GitHub metadata preparation failed.' }

if (-not (Test-Path '.git')) {
    git init
    if ($LASTEXITCODE -ne 0) { throw 'git init failed.' }
}

git branch -M main
if ($LASTEXITCODE -ne 0) { throw 'git branch failed.' }

$remotes = @(git remote)
$expected = "https://github.com/$Owner/$Repo.git"
if ($remotes -contains 'origin') {
    $origin = git remote get-url origin
    if ($origin.Trim() -ne $expected) {
        throw "Existing origin points to '$origin'. Refusing to overwrite it; check your remote."
    }
} else {
    git remote add origin $expected
    if ($LASTEXITCODE -ne 0) { throw 'git remote add failed.' }
}

git add .
if ($LASTEXITCODE -ne 0) { throw 'git add failed.' }

# Safety net: check staged paths before pushing.
$staged = git diff --cached --name-only
if ($staged -match '(?i)(^|/)(\.storage|\.venv|secrets\.yaml|secrets\.json|configuration\.yaml)(/|$)') {
    throw 'Sensitive Home Assistant files were staged; remove them before publishing.'
}

git diff --cached --quiet
if ($LASTEXITCODE -ne 0) {
    git commit -m "Initial BroadLink Cloud Home Assistant release"
    if ($LASTEXITCODE -ne 0) { throw 'git commit failed. Configure git user.name/user.email first.' }
}

git push -u origin main
if ($LASTEXITCODE -ne 0) { throw 'git push failed. Verify the empty public GitHub repository exists and GitHub authentication is configured.' }

Write-Host "Published: https://github.com/$Owner/$Repo"
Write-Host 'Next: check Actions, then publish the 0.1.2 GitHub Release.'
