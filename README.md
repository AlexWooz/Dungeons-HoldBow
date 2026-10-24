# Hold Bow for Minecraft Dungeons

A Blueprint mod for **Minecraft Dungeons** (Steam, v1.17.0.0, UE 4.22) that keeps the bow in hand after you shoot, as in Minecraft Dungeons II, until your next melee attack.

**Status:** working. After a shot the ranged weapon stays in hand while you walk, until a melee press (A or Left Mouse). Tested in camp with the Bow, Longbow and Exploding Crossbow. The Blueprint is still the probe (`BP_HoldBowProbe`), with its readout and probe keys switched off (`DEBUG = False` in `tools/blueprint/gen.py`). See [docs/TECHNICAL.md](docs/TECHNICAL.md).

## Install
1. Install Dungeons Blueprint Loader 1.0 (`Blueprint-Loader.pak`) in your `~mods` folder.
2. Download `HoldBow.pak` from [Releases](../../releases) and put it in `<Steam>\steamapps\common\MinecraftDungeons\Dungeons\Content\Paks\~mods\`.

## Building
Same setup as ThirdPersonCam: Dokucraft's Dungeons Mod Kit at `..\Dungeons-Mod-Kit`, UE 4.22. The Blueprint is generated headlessly with the Mod Kit's BPTool commandlet (`UE4Project\Source\DungeonsBPTools`, which needs `newbp`/`newlevel`), so the editor isn't needed. Keep it closed.
1. `.\tools\blueprint\build.ps1` recreates `BP_HoldBowProbe` from `tools\blueprint\gen.py`.
   On a fresh Mod Kit, first run `.\tools\sync.ps1 -ToModKit` for the debug widget and loader levels.
2. Run the Mod Kit's `cook_assets.bat` (exit code 16 just means the Precooked folder is missing), then `.\tools\package.ps1` (or `.\tools\package.ps1 -Out .\release\HoldBow.pak -Compress` for a release). That packs only this mod's assets; `package.bat` would also pack the other mods.
3. Run `.\tools\sync.ps1 -FromModKit` before committing.

### Layout
| Path | Contents |
|---|---|
| `ModKit/UE4Project/Content/Mods/HoldBow/` | `BP_HoldBowProbe` (all logic), `W_HoldBowDebug` (readout) |
| `ModKit/UE4Project/Content/BPLoader/{InGame,Lobby}/HB_*.umap` | Loader levels that spawn the actor |
| `ModKit/UE4Project/Source/Dungeons/PlayerCharacter.h` | Editor-only stub of the game's `PlayerCharacter`, `EquipmentDisplayComponent` (`ShowWeaponSlot`, `RestoreWeaponVisibility`) and `ESlotType`; rebuild `DungeonsEditor` after `sync.ps1 -ToModKit` |
| `tools/blueprint/` | `gen.py` (the graph as paste text + ops) and `build.ps1` (newbp → addvar → paste) |
| `tools/sync.ps1`, `tools/package.ps1` | Copy files to and from the Mod Kit; pack this mod alone |
