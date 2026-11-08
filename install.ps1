param(
    # Your WoW Forever folder (the one that holds Interface\AddOns). Pass your own if it is elsewhere.
    [string]$GameDir = 'C:\Program Files (x86)\World of Warcraft\_forever_'
)
$addons = Join-Path $GameDir 'Interface\AddOns'
if (-not (Test-Path $addons)) { throw "AddOns folder not found: $addons  (run: .\install.ps1 -GameDir 'D:\path\to\_forever_')" }
foreach ($f in @('Guidelime_HarleyMage', 'Guidelime_Bethink', 'WarlockKit')) {
    $src = Join-Path $PSScriptRoot $f
    $dst = Join-Path $addons $f
    if (Test-Path $dst) { Remove-Item -Recurse -Force $dst }
    Copy-Item -Recurse $src $dst
    Write-Host "Installed $f -> $dst"
}
Write-Host 'Done. Restart the game if it was running, then type /lime and open the Harley Mage group. Warlocks: /wk'
