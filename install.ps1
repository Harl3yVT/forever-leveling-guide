param(
    # Your WoW Forever folder (the one that holds Interface\AddOns). Pass your own if it is elsewhere.
    [string]$GameDir = 'C:\Program Files (x86)\World of Warcraft\_forever_'
)
$addons = Join-Path $GameDir 'Interface\AddOns'
if (-not (Test-Path $addons)) { throw "AddOns folder not found: $addons  (run: .\install.ps1 -GameDir 'D:\path\to\_forever_')" }
# old copies are moved to _forever_\AddOn-backups\<date-time>\ first, so an update can be undone by copying them back
$backup = Join-Path $GameDir ("AddOn-backups\" + (Get-Date -Format 'yyyy-MM-dd_HHmm'))
foreach ($f in @('Guidelime_HarleyMage', 'Guidelime_Bethink', 'HarleyLib', 'WarlockKit')) {
    $src = Join-Path $PSScriptRoot $f
    $dst = Join-Path $addons $f
    if (Test-Path $dst) {
        New-Item -ItemType Directory -Force $backup | Out-Null
        Move-Item $dst (Join-Path $backup $f)
    }
    Copy-Item -Recurse $src $dst
    Write-Host "Installed $f -> $dst"
}
if (Test-Path $backup) { Write-Host "Old versions backed up to $backup" }
Write-Host 'Done. Restart the game if it was running, then type /lime and open the Harley Mage group. Warlocks: /wk'
