# Untrack model/tokenizer.json from git while keeping the file locally
# Run this in the repository root (PowerShell)

if (!(Test-Path -Path .git)) {
    Write-Error "This doesn't look like a git repository. Run from the repo root."
    exit 1
}

Write-Host "Removing model/tokenizer.json from git index (keeps file locally)..."

git rm --cached model/tokenizer.json
if ($LASTEXITCODE -ne 0) {
    Write-Error "git rm --cached failed. You may need to run this command manually:";
    Write-Host "git rm --cached model/tokenizer.json"
} else {
    Write-Host "Success. Commit the change:";
    Write-Host "git commit -m 'Stop tracking model/tokenizer.json'";
}
