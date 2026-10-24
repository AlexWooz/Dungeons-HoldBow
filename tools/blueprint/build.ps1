# Rebuilds BP_HoldBowProbe from scratch with the Mod Kit's BPTool: newbp, addvar, then paste + ops from gen.py.
#   .\tools\blueprint\build.ps1                                     # the real probe
#   .\tools\blueprint\build.ps1 -Bp /Game/Mods/HoldBow/BP_CmdTest    # a throwaway copy (delete its .uasset before cooking)
# Keep the editor closed. Intermediates (vars.log, probe.paste, probe.ops) go to build\blueprint.
param(
    [string]$Bp = '/Game/Mods/HoldBow/BP_HoldBowProbe',
    [string]$ModKit = (Join-Path $PSScriptRoot '..\..\..\Dungeons-Mod-Kit')
)
$ErrorActionPreference = 'Stop'
$env:PATH = [Environment]::GetEnvironmentVariable('Path','Machine') + ';' + [Environment]::GetEnvironmentVariable('Path','User')
$ModKit = (Resolve-Path $ModKit).Path
$t = Join-Path $ModKit 'UE4Project\Source\DungeonsBPTools\bptool.ps1'
$work = Join-Path $PSScriptRoot '..\..\build\blueprint'
New-Item -ItemType Directory -Force $work | Out-Null
$file = (Join-Path $ModKit 'UE4Project\Content') + ($Bp -replace '^/Game', '' -replace '/', '\') + '.uasset'
if (Test-Path $file) { Remove-Item $file }

& $t newbp "-bp=$Bp" | Select-String 'Error|created'
if ($LASTEXITCODE) { throw "newbp failed" }
@'
addvar PC object:/Script/Engine.PlayerController
addvar Dbg object:/Game/Mods/HoldBow/W_HoldBowDebug.W_HoldBowDebug_C
addvar Bow object:/Script/Engine.Actor
addvar Melee object:/Script/Engine.Actor
addvar Holding bool
addvar Off bool
addvar Str string
addvar BowMesh object:/Script/Engine.SceneComponent
addvar LastMont string
addvar Seen string
addvar Freeze bool
addvar BowSK object:/Script/Engine.SkeletalMeshComponent
addvar BowStr string
addvar Part int
addvar LastPos float
addvar Bow4 object:/Script/Engine.PrimitiveComponent
addvar ParamStr string
addvar MatSwapped bool
addvar MaxPos float
addvar AimAsset object:/Script/Engine.AnimationAsset
addvar Ending bool
addvar Reattached bool
addvar Found bool
addvar ScanIdx int
addvar RangedSlot int
addvar PressT float
addvar PendRestore bool
'@ | Set-Content "$work\vars.ops" -Encoding ascii
& $t edit "-bp=$Bp" "-ops=$work\vars.ops" | Out-File "$work\vars.log" -Encoding utf8
if ($LASTEXITCODE) { Get-Content "$work\vars.log"; throw "addvar failed" }
python -I (Join-Path $PSScriptRoot 'gen.py') $work "$work\vars.log"
if ($LASTEXITCODE) { throw "gen.py failed" }
& $t edit "-bp=$Bp" "-paste=$work\probe.paste" "-ops=$work\probe.ops" | Select-String 'Error|Warning|compiled|saved'
if ($LASTEXITCODE) { throw "edit failed" }
