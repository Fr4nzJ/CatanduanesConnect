# Untrack model/tokenizer.json and ensure .gitattributes is updated
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
    Write-Host "git add .gitattributes .gitignore";
    Write-Host "git commit -m 'Fix: remove broken tokenizer.json and use slow tokenizer fallback'";
}
