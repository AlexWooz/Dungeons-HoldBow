# Generates probe.paste / probe.ops for BP_HoldBowProbe (v3: keep the bow out after shooting until a melee press).
#   python gen.py <outdir> <vars.log>   (vars.log = output of the addvar edit, for the variable guids)
import sys, os, re
out = sys.argv[1]
G = dict(re.findall(r"added variable (\w+) \([^)]*\) guid=(\w+)", open(sys.argv[2], encoding="utf-8", errors="ignore").read()))
ARRAY_MACROS = "/Engine/EditorBlueprintResources/StandardMacros.StandardMacros"
DEBUG = False  # True: on-screen readout plus the probe keys B (feature off), N (mode), M (bow material test)

nodes = []; pos = [0]
def node(name, cls, *props):
    pos[0] += 1
    body = "\n".join("   " + p for p in props)
    nodes.append('Begin Object Class=%s Name="%s"\n%s\n   NodePosX=%d\n   NodePosY=%d\nEnd Object'
                 % (cls, name, body, (pos[0] % 12) * 260, (pos[0] // 12) * 220))
CF = "/Script/BlueprintGraph.K2Node_CallFunction"
def fn(name, parent, member, pure=False, const=False):
    p = []
    if pure: p.append("bIsPureFunc=True")
    if const: p.append("bIsConstFunc=True")
    p.append("FunctionReference=(MemberParent=Class'\"%s\"',MemberName=\"%s\")" % (parent, member))
    node(name, CF, *p)
def selffn(name, member):
    node(name, CF, 'FunctionReference=(MemberName="%s",bSelfContext=True)' % member)
def vget(name, var):
    node(name, "/Script/BlueprintGraph.K2Node_VariableGet", 'VariableReference=(MemberName="%s",MemberGuid=%s,bSelfContext=True)' % (var, G[var]))
def vset(name, var):
    node(name, "/Script/BlueprintGraph.K2Node_VariableSet", 'VariableReference=(MemberName="%s",MemberGuid=%s,bSelfContext=True)' % (var, G[var]))
def xget(name, parent, var, cls="Class"):
    node(name, "/Script/BlueprintGraph.K2Node_VariableGet",
         "VariableReference=(MemberParent=%s'\"%s\"',MemberName=\"%s\")" % (cls, parent, var), "SelfContextInfo=NotSelfContext")
def isvalid(name):
    node(name, "/Script/BlueprintGraph.K2Node_MacroInstance",
         "MacroGraphReference=(MacroGraph=EdGraph'\"/Engine/EditorBlueprintResources/StandardMacros.StandardMacros:IsValid\"',GraphBlueprint=Blueprint'\"/Engine/EditorBlueprintResources/StandardMacros.StandardMacros\"',GraphGuid=64422BCD430703FF5CAEA8B79A32AA65)")
def branch(name):
    node(name, "/Script/BlueprintGraph.K2Node_IfThenElse")
def cast(name, cls):
    node(name, "/Script/BlueprintGraph.K2Node_DynamicCast", "TargetType=Class'\"%s\"'" % cls)

GS, KSL, KML, KTL = "/Script/Engine.GameplayStatics", "/Script/Engine.KismetSystemLibrary", "/Script/Engine.KismetMathLibrary", "/Script/Engine.KismetTextLibrary"
ACT, SC, CAC = "/Script/Engine.Actor", "/Script/Engine.SceneComponent", "/Script/Engine.ChildActorComponent"
ops = []
def L(a, b): ops.append("link %s -> %s" % (a, b))
def S(p, v): ops.append("set %s = %s" % (p, v))
def chain(*refs):
    for a, b in zip(refs, refs[1:]):
        L(a + ".then", b + ".execute")

# --- BeginPlay: tick after the game's animation (so forced values win), debug widget
fn("Dly", KSL, "Delay"); S("new:Dly.Duration", "0.5")
selffn("STG", "SetTickGroup"); S("new:STG.NewTickGroup", "TG_PostUpdateWork")
fn("GPC", GS, "GetPlayerController", pure=True)
vset("SetPC", "PC"); selffn("EI", "EnableInput"); vget("GetPC1", "PC")
node("CW", "/Script/UMGEditor.K2Node_CreateWidget")
vset("SetDbg", "Dbg"); fn("ATV", "/Script/UMG.UserWidget", "AddToViewport")
L("K2Node_Event_0.then", "new:Dly.execute")
if DEBUG:
    chain("new:Dly", "new:STG", "new:SetPC", "new:EI", "new:CW", "new:SetDbg", "new:ATV")
else:  # no widget: Dbg stays invalid, so Tick skips the readout
    chain("new:Dly", "new:STG", "new:SetPC", "new:EI", "new:SetPt0")
L("new:GPC.ReturnValue", "new:SetPC.PC"); L("new:GetPC1.PC", "new:EI.PlayerController")
S("new:CW.Class", "/Game/Mods/HoldBow/W_HoldBowDebug.W_HoldBowDebug_C"); L("new:GetPC1.PC", "new:CW.OwningPlayer")
L("new:CW.ReturnValue", "new:SetDbg.Dbg"); L("new:SetDbg.Output_Get", "new:ATV.self")


# Weapons are separate actors attached to the hero (BP_Bow_C, BP_Hammer_..._C), each under the hero's
# RangedWeapon / MeleeWeapon component; the game swaps them with SetActorHiddenInGame (probe v2).
def foreach(name):
    node(name, "/Script/BlueprintGraph.K2Node_MacroInstance",
         "MacroGraphReference=(MacroGraph=EdGraph'\"%s:ForEachLoop\"',GraphBlueprint=Blueprint'\"%s\"',GraphGuid=99DBFD5540A796041F72A5A9DA655026)" % (ARRAY_MACROS, ARRAY_MACROS))
def tagged(p, tag):
    """Pure: the hero's first component tagged `tag`; returns its output pin."""
    fn("Tag" + p, ACT, "GetComponentsByTag", pure=True, const=True); L("new:GPCh.ReturnValue", "new:Tag%s.self" % p)
    S("new:Tag%s.ComponentClass" % p, "/Script/Engine.SceneComponent"); S("new:Tag%s.Tag" % p, tag)
    node("Arr" + p, "/Script/BlueprintGraph.K2Node_GetArrayItem"); L("new:Tag%s.ReturnValue" % p, "new:Arr%s.Array" % p)
    S("new:Arr%s.Dimension 1" % p, "0")
    return "new:Arr%s.Output" % p
def set_hidden(name, actor_pin, hidden):
    fn(name, ACT, "SetActorHiddenInGame"); L(actor_pin, "new:%s.self" % name); S("new:%s.bNewHidden" % name, "true" if hidden else "false")

# --- B: toggle the feature off/on (Off = probe comparison)
node("KB", "/Script/BlueprintGraph.K2Node_InputKey", "InputKey=B", "bConsumeInput=False")
vget("GetOff", "Off"); fn("NotOff", KML, "Not_PreBool", pure=True); vset("SetOff", "Off")
L("new:KB.Pressed", "new:SetOff.execute"); L("new:GetOff.Off", "new:NotOff.A"); L("new:NotOff.ReturnValue", "new:SetOff.Off")

# --- Melee press (A, Left Mouse): stop holding and give the game back its normal weapon state
vget("GetHoldR", "Holding"); branch("BrRel"); vset("SetHold0", "Holding")
# A / Left Mouse only arm the release (PressT); Tick releases if a non-bow montage starts within 0.5 s, so a
# Left Mouse click that just walks keeps the bow (melee = AnimMontage_N, walking = no montage; rolls play none,
# potions and artifacts aren't on these keys).
fn("NowP", GS, "GetTimeSeconds", pure=True); vset("SetPressT", "PressT"); L("new:NowP.ReturnValue", "new:SetPressT.PressT")
for name, key in (("KA", "Gamepad_FaceButton_Bottom"), ("KLMB", "LeftMouseButton")):
    node(name, "/Script/BlueprintGraph.K2Node_InputKey", "InputKey=" + key, "bConsumeInput=False")
    L("new:%s.Pressed" % name, "new:SetPressT.execute")
L("new:GetHoldR.Holding", "new:BrRel.Condition")
L("new:BrRel.then", "new:SetHold0.execute"); S("new:SetHold0.Holding", "false")
# Release changes nothing itself: the montage that triggered it sets the weapons (melee: ShowWeaponSlot(melee);
# petting the dog: HideWeapons). Forcing the melee weapon visible here made the hero pet the dog with the hammer.
# Once that montage is over, call RestoreWeaponVisibility() once as a safety net (PendRestore, at the start of Tick).
vset("SetPR1", "PendRestore"); S("new:SetPR1.PendRestore", "true")
# ...but only when that montage hid the weapons (the hold keeps the bow shown, so a hidden bow means the game just
# ran HideWeapons). A melee swing sets nothing (the melee weapon is the default), so then swap back right away.
vget("GetBowR", "Bow"); xget("BowHidR", ACT, "bHidden"); L("new:GetBowR.Bow", "new:BowHidR.self")
branch("BrHidR"); L("new:SetHold0.then", "new:BrHidR.execute"); L("new:BowHidR.bHidden", "new:BrHidR.Condition")
L("new:BrHidR.then", "new:SetPR1.execute")
vget("GetMelR", "Melee"); set_hidden("RelBow", "new:GetBowR.Bow", True); set_hidden("RelMel", "new:GetMelR.Melee", False)
L("new:BrHidR.else", "new:RelBow.execute"); chain("new:RelBow", "new:RelMel"); L("new:RelMel.then", "new:CastPCh2.execute")
cast("CastPCh2", "/Script/Dungeons.PlayerCharacter"); L("new:GPChR.ReturnValue", "new:CastPCh2.Object")
fn("GPChR", GS, "GetPlayerCharacter", pure=True)
xget("EDC2", "/Script/Dungeons.PlayerCharacter", "EquipmentDisplayComponent"); L("new:CastPCh2.AsPlayer Character", "new:EDC2.self")
fn("RWV", "/Script/Dungeons.EquipmentDisplayComponent", "RestoreWeaponVisibility"); L("new:EDC2.EquipmentDisplayComponent", "new:RWV.self")
L("new:CastPCh2.then", "new:RWV.execute")
vset("SetPR0", "PendRestore"); S("new:SetPR0.PendRestore", "false"); L("new:RWV.then", "new:SetPR0.execute")

# --- Tick: find the two weapon actors, start holding when the game shows the bow, keep it shown
fn("GPCh", GS, "GetPlayerCharacter", pure=True)
rtag = tagged("R", "RangedWeapon"); mtag = tagged("M", "MeleeWeapon")
vset("ClrBow", "Bow"); vset("ClrMel", "Melee"); vset("ClrStr", "Str"); vset("ClrBM", "BowMesh")
L("K2Node_Event_2.then", "new:ClrBow.execute"); chain("new:ClrBow", "new:ClrMel", "new:ClrStr", "new:ClrBM")
# Weapon actors count as attached to the hero but their root isn't attached (v3.1: parent None) and nothing hangs
# under the weapon slots (v3.2), so look at every scene component of every attached actor: one on J_L_Weapon_Socket
# marks the bow, one on J_R_Weapon_Socket the melee weapon. Lines for socketed components go to Str.
KSTR = "/Script/Engine.KismetStringLibrary"
fn("Att", ACT, "GetAttachedActors", pure=True, const=True); L("new:GPCh.ReturnValue", "new:Att.self")
foreach("FA"); L("new:Att.OutActors", "new:FA.Array"); L("new:ClrBM.then", "new:FA.Exec")
fn("AComps", ACT, "GetComponentsByClass", pure=True, const=True); L("new:FA.Array Element", "new:AComps.self")
S("new:AComps.ComponentClass", SC)
foreach("FC"); L("new:AComps.ReturnValue", "new:FC.Array"); L("new:FA.LoopBody", "new:FC.Exec")
fn("CPar", SC, "GetAttachParent", pure=True, const=True); L("new:FC.Array Element", "new:CPar.self")
fn("CSock", SC, "GetAttachSocketName", pure=True, const=True); L("new:FC.Array Element", "new:CSock.self")
fn("HasSock", KML, "NotEqual_NameName", pure=True); L("new:CSock.ReturnValue", "new:HasSock.A"); S("new:HasSock.B", "None")
branch("BrLine"); vget("GetStrC", "Str"); vset("SetStrC", "Str")
L("new:FC.LoopBody", "new:BrLine.execute"); L("new:HasSock.ReturnValue", "new:BrLine.Condition")
fn("AN", KSL, "GetObjectName", pure=True); L("new:FA.Array Element", "new:AN.Object")
fn("CN", KSL, "GetObjectName", pure=True); L("new:FC.Array Element", "new:CN.Object")
fn("PN", KSL, "GetObjectName", pure=True); L("new:CPar.ReturnValue", "new:PN.Object")
fn("SN", KSTR, "Conv_NameToString", pure=True); L("new:CSock.ReturnValue", "new:SN.InName")
parts = ["new:GetStrC.Str", "new:AN.ReturnValue", ("lit", "|"), "new:CN.ReturnValue", ("lit", "|parent="),
         "new:PN.ReturnValue", ("lit", "@"), "new:SN.ReturnValue", ("lit", r"\n")]
acc = parts[0]
for i, part in enumerate(parts[1:]):
    n = "CatC%d" % i; fn(n, KSTR, "Concat_StrStr", pure=True)
    L(acc, "new:%s.A" % n)
    if isinstance(part, tuple): S("new:%s.B" % n, part[1])
    else: L(part, "new:%s.B" % n)
    acc = "new:%s.ReturnValue" % n
L(acc, "new:SetStrC.Str"); L("new:BrLine.then", "new:SetStrC.execute")
fn("IsL", KML, "EqualEqual_NameName", pure=True); L("new:CSock.ReturnValue", "new:IsL.A"); S("new:IsL.B", "J_L_Weapon_Socket")
fn("IsR", KML, "EqualEqual_NameName", pure=True); L("new:CSock.ReturnValue", "new:IsR.A"); S("new:IsR.B", "J_R_Weapon_Socket")
branch("BrR"); branch("BrM"); vset("SetBow", "Bow"); vset("SetMel", "Melee")
L("new:SetStrC.then", "new:BrR.execute"); L("new:IsL.ReturnValue", "new:BrR.Condition")
L("new:BrR.then", "new:SetBow.execute"); L("new:FA.Array Element", "new:SetBow.Bow")
# the bow mesh on the hand socket: the game also hides it with component visibility (v3.3: actor shown, bow invisible)
vset("SetBM", "BowMesh"); L("new:SetBow.then", "new:SetBM.execute"); L("new:FC.Array Element", "new:SetBM.BowMesh")
cast("CastSK", "/Script/Engine.SkeletalMeshComponent"); vset("SetBSK", "BowSK")
L("new:SetBM.then", "new:CastSK.execute"); L("new:FC.Array Element", "new:CastSK.Object")
L("new:CastSK.then", "new:SetBSK.execute"); L("new:CastSK.AsSkeletal Mesh Component", "new:SetBSK.BowSK")
L("new:BrR.else", "new:BrM.execute"); L("new:IsR.ReturnValue", "new:BrM.Condition")
L("new:BrM.then", "new:SetMel.execute"); L("new:FA.Array Element", "new:SetMel.Melee")
done_m = "new:FA.Completed"

# after the loop: if not Off and both found
vget("GetBow1", "Bow"); vget("GetMel1", "Melee"); vget("GetOff1", "Off")
fn("VBow", KSL, "IsValid", pure=True); fn("VMel", KSL, "IsValid", pure=True); fn("NOff", KML, "Not_PreBool", pure=True)
fn("And1", KML, "BooleanAND", pure=True); fn("And2", KML, "BooleanAND", pure=True)
L("new:GetBow1.Bow", "new:VBow.Object"); L("new:GetMel1.Melee", "new:VMel.Object"); L("new:GetOff1.Off", "new:NOff.A")
L("new:VBow.ReturnValue", "new:And1.A"); L("new:VMel.ReturnValue", "new:And1.B")
L("new:And1.ReturnValue", "new:And2.A"); L("new:NOff.ReturnValue", "new:And2.B")
vget("GetEnd1", "Ending"); fn("NotEnd", KML, "Not_PreBool", pure=True); fn("And3", KML, "BooleanAND", pure=True)
L("new:GetEnd1.Ending", "new:NotEnd.A"); L("new:And2.ReturnValue", "new:And3.A"); L("new:NotEnd.ReturnValue", "new:And3.B")
branch("BrOk"); L(done_m, "new:BrOk.execute"); L("new:And3.ReturnValue", "new:BrOk.Condition")
node("EvEnd", "/Script/BlueprintGraph.K2Node_Event", "EventReference=(MemberParent=Class'\"/Script/Engine.Actor\"',MemberName=\"ReceiveEndPlay\")", "bOverrideFunction=True")
vset("SetEnd", "Ending"); S("new:SetEnd.Ending", "true"); L("new:EvEnd.then", "new:SetEnd.execute")
# the game showed the bow (a shot started) -> hold
xget("BowHid", ACT, "bHidden"); L("new:GetBow1.Bow", "new:BowHid.self")
fn("BowShown", KML, "Not_PreBool", pure=True); L("new:BowHid.bHidden", "new:BowShown.A")
branch("BrShown"); vset("SetHold1", "Holding")
L("new:BrOk.then", "new:BrShown.execute"); L("new:BowShown.ReturnValue", "new:BrShown.Condition")
L("new:BrShown.then", "new:SetHold1.execute"); S("new:SetHold1.Holding", "true")
vget("GetHold2", "Holding"); branch("BrHold")
L("new:SetHold1.then", "new:BrHold.execute"); L("new:BrShown.else", "new:BrHold.execute"); L("new:GetHold2.Holding", "new:BrHold.Condition")
set_hidden("HoldBow", "new:GetBow1.Bow", False); set_hidden("HoldMel", "new:GetMel1.Melee", True)
vget("GetBM1", "BowMesh"); fn("HoldBM", SC, "SetVisibility"); L("new:GetBM1.BowMesh", "new:HoldBM.self")
S("new:HoldBM.bNewVisibility", "true"); S("new:HoldBM.bPropagateToChildren", "true")
fn("HoldBH", SC, "SetHiddenInGame"); L("new:GetBM1.BowMesh", "new:HoldBH.self")
S("new:HoldBH.NewHidden", "false"); S("new:HoldBH.bPropagateToChildren", "true")
L("new:BrHold.then", "new:HoldBow.execute"); chain("new:HoldBow", "new:HoldMel", "new:HoldBM", "new:HoldBH")

# readout
vget("GetDbg", "Dbg"); isvalid("IV"); L("new:GetDbg.Dbg", "new:IV.InputObject")
L("new:BrOk.else", "new:IV.exec")
L("new:BrHold.else", "new:FrzSet.execute")
# --- v12: the weapon notify calls the native PlayerCharacter.EquipmentDisplayComponent.ShowWeaponSlot(SlotType) /
# RestoreWeaponVisibility() (FModel bytecode). While holding outside the bow montage, call ShowWeaponSlot(ranged).
# ESlotType is a placeholder stub (Source/Dungeons/PlayerCharacter.h); the ranged value is found by its real name.
EN = "/Script/Dungeons.ESlotType"; PCH = "/Script/Dungeons.PlayerCharacter"; EDC = "/Script/Dungeons.EquipmentDisplayComponent"
# v12 found only item/ammo names at 0..7 (HealthPotion|Arrow|...|VoidArrow), so scan one value per tick at the start
# of Tick until the real name is "RangedWeapon" (Found), then keep it in RangedSlot.
vget("GetFound", "Found"); fn("NotFound", KML, "Not_PreBool", pure=True); L("new:GetFound.Found", "new:NotFound.A")
vget("GetScan", "ScanIdx"); fn("ScanLt", KML, "Less_IntInt", pure=True); L("new:GetScan.ScanIdx", "new:ScanLt.A"); S("new:ScanLt.B", "256")
fn("ScanGo", KML, "BooleanAND", pure=True); L("new:NotFound.ReturnValue", "new:ScanGo.A"); L("new:ScanLt.ReturnValue", "new:ScanGo.B")
branch("BrScan"); L("K2Node_Event_2.then", "new:BrScan.execute"); L("new:ScanGo.ReturnValue", "new:BrScan.Condition")
fn("ScanB", KML, "Conv_IntToByte", pure=True); L("new:GetScan.ScanIdx", "new:ScanB.InInt")
node("ToES", "/Script/BlueprintGraph.K2Node_CastByteToEnum", "Enum=Enum'\"%s\"'" % EN); L("new:ScanB.ReturnValue", "new:ToES.Byte")
node("ENS", "/Script/BlueprintGraph.K2Node_GetEnumeratorNameAsString", "Enum=Enum'\"%s\"'" % EN); L("new:ToES.ReturnValue", "new:ENS.Enumerator")
fn("IsRW", "/Script/Engine.KismetStringLibrary", "EqualEqual_StrStr", pure=True); L("new:ENS.ReturnValue", "new:IsRW.A"); S("new:IsRW.B", "RangedWeapon")
branch("BrIsRW"); L("new:BrScan.then", "new:BrIsRW.execute"); L("new:IsRW.ReturnValue", "new:BrIsRW.Condition")
vset("SetRS", "RangedSlot"); vset("SetFound", "Found"); S("new:SetFound.Found", "true")
L("new:BrIsRW.then", "new:SetRS.execute"); L("new:GetScan.ScanIdx", "new:SetRS.RangedSlot"); L("new:SetRS.then", "new:SetFound.execute")
fn("ScanInc", KML, "Add_IntInt", pure=True); L("new:GetScan.ScanIdx", "new:ScanInc.A"); S("new:ScanInc.B", "1")
vset("SetScan", "ScanIdx"); L("new:BrIsRW.else", "new:SetScan.execute"); L("new:ScanInc.ReturnValue", "new:SetScan.ScanIdx")
for src in ("new:BrScan.else", "new:SetFound.then", "new:SetScan.then"):
    L(src, "new:BrPend.execute")
fn("NowT", GS, "GetTimeSeconds", pure=True); vget("GetPressT", "PressT")
fn("SinceP", KML, "Subtract_FloatFloat", pure=True); L("new:NowT.ReturnValue", "new:SinceP.A"); L("new:GetPressT.PressT", "new:SinceP.B")
fn("Recent", KML, "LessEqual_FloatFloat", pure=True); L("new:SinceP.ReturnValue", "new:Recent.A"); S("new:Recent.B", "0.5")
fn("HasMont", "/Script/Engine.KismetStringLibrary", "NotEqual_StrStr", pure=True); L("new:MName.ReturnValue", "new:HasMont.A"); S("new:HasMont.B", "None")
vget("GetHoldP", "Holding")
fn("PdA", KML, "BooleanAND", pure=True); fn("PdB", KML, "BooleanAND", pure=True); fn("PdC", KML, "BooleanAND", pure=True)
L("new:GetHoldP.Holding", "new:PdA.A"); L("new:Recent.ReturnValue", "new:PdA.B")
L("new:PdA.ReturnValue", "new:PdB.A"); L("new:HasMont.ReturnValue", "new:PdB.B")
L("new:PdB.ReturnValue", "new:PdC.A"); L("new:NotBowMont.ReturnValue", "new:PdC.B")
branch("BrPend"); L("new:PdC.ReturnValue", "new:BrPend.Condition")
vset("ClrPressT", "PressT"); S("new:ClrPressT.PressT", "-100.0")
L("new:BrPend.then", "new:ClrPressT.execute"); L("new:ClrPressT.then", "new:BrRel.execute"); vget("GetPR", "PendRestore"); fn("NoMont", "/Script/Engine.KismetStringLibrary", "EqualEqual_StrStr", pure=True)
L("new:MName.ReturnValue", "new:NoMont.A"); S("new:NoMont.B", "None")
fn("PRgo", KML, "BooleanAND", pure=True); L("new:GetPR.PendRestore", "new:PRgo.A"); L("new:NoMont.ReturnValue", "new:PRgo.B")
branch("BrPR"); L("new:BrPend.else", "new:BrPR.execute"); L("new:PRgo.ReturnValue", "new:BrPR.Condition")
L("new:BrPR.then", "new:CastPCh2.execute"); L("new:BrPR.else", "new:ClrBow.execute")
L("new:SetPR0.then", "new:ClrBow.execute"); L("new:CastPCh2.CastFailed", "new:SetPR0.execute")
vget("GetRS", "RangedSlot"); fn("RSbyte", KML, "Conv_IntToByte", pure=True); L("new:GetRS.RangedSlot", "new:RSbyte.InInt")
node("ToER", "/Script/BlueprintGraph.K2Node_CastByteToEnum", "Enum=Enum'\"%s\"'" % EN); L("new:RSbyte.ReturnValue", "new:ToER.Byte")
vget("GetPt12", "Part"); fn("Pt12On", KML, "Greater_IntInt", pure=True); L("new:GetPt12.Part", "new:Pt12On.A"); S("new:Pt12On.B", "0")
fn("SWa", KML, "BooleanAND", pure=True); fn("SWb", KML, "BooleanAND", pure=True)
L("new:Pt12On.ReturnValue", "new:SWa.A"); L("new:NotBowMont.ReturnValue", "new:SWa.B"); L("new:SWa.ReturnValue", "new:SWb.A"); L("new:GetFound.Found", "new:SWb.B")
branch("BrSWS"); L("new:HoldBH.then", "new:BrSWS.execute"); L("new:SWb.ReturnValue", "new:BrSWS.Condition")
cast("CastPCh", PCH); L("new:BrSWS.then", "new:CastPCh.execute"); L("new:GPCh.ReturnValue", "new:CastPCh.Object")
xget("EDC1", PCH, "EquipmentDisplayComponent"); L("new:CastPCh.AsPlayer Character", "new:EDC1.self")
fn("SWS", EDC, "ShowWeaponSlot"); L("new:EDC1.EquipmentDisplayComponent", "new:SWS.self"); L("new:ToER.ReturnValue", "new:SWS.SlotType")
L("new:CastPCh.then", "new:SWS.execute"); L("new:SWS.then", "new:FrzSet.execute")
L("new:BrSWS.else", "new:FrzSet.execute"); L("new:CastPCh.CastFailed", "new:FrzSet.execute")
xget("DT", "/Game/Mods/HoldBow/W_HoldBowDebug.W_HoldBowDebug_C", "DebugText", "WidgetBlueprintGeneratedClass")
fn("ST", "/Script/UMG.TextBlock", "SetText"); node("Fmt", "/Script/BlueprintGraph.K2Node_FormatText")
L("new:IV.Is Valid", "new:ST.execute"); L("new:GetDbg.Dbg", "new:DT.self"); L("new:DT.DebugText", "new:ST.self")
S("new:Fmt.Format", r"HOLD BOW PROBE v3   B = feature off {OF}   holding {HO}\nBow {BN}  hidden {BH}  mesh visible {BV}  hiddenInGame {BG}  scale {BS}\nMelee {MN}  hidden {MH}\nMontage {AM}   seen: {SM}\nA / Left Mouse = melee, stops holding   N = mode {FZ} (0 off, 1 ShowWeaponSlot, 2 + pose pin, 3 + J_L_Hand)   reattached {RA}\nBow anim {BA}   bow montage {BO}   pos {PO}   aimPos {LP}   aimAsset {AA}   ending {EN}\nweapon socket to hand {DW}   SM_Bow4 to hand {DB}\nRangedWeapon slot found {SN}   value {RS}   scan {SC}\nSM_Bow4 material {MT}   bow skeleton material {MK}\nparams {PS}\nM = put the hero's material on the bow (until restart): {MS}\n{BC}")
L("new:Fmt.Result", "new:ST.InText")
def btxt(n, src, arg):
    fn(n, KTL, "Conv_BoolToText", pure=True); L(src, "new:%s.InBool" % n); L("new:%s.ReturnValue" % n, "new:Fmt." + arg)
def ntxt(n, src, arg):
    fn(n + "o", KSL, "GetObjectName", pure=True); fn(n, KTL, "Conv_StringToText", pure=True)
    L(src, "new:%so.Object" % n); L("new:%so.ReturnValue" % n, "new:%s.InString" % n); L("new:%s.ReturnValue" % n, "new:Fmt." + arg)
vget("GetOff3", "Off"); btxt("TOf", "new:GetOff3.Off", "OF")
vget("GetHold3", "Holding"); btxt("THo", "new:GetHold3.Holding", "HO")
vget("GetBow3", "Bow"); ntxt("TBn", "new:GetBow3.Bow", "BN")
xget("BowHid3", ACT, "bHidden"); L("new:GetBow3.Bow", "new:BowHid3.self"); btxt("TBh", "new:BowHid3.bHidden", "BH")
vget("GetMel3", "Melee"); ntxt("TMn", "new:GetMel3.Melee", "MN")
xget("MelHid3", ACT, "bHidden"); L("new:GetMel3.Melee", "new:MelHid3.self"); btxt("TMh", "new:MelHid3.bHidden", "MH")

vget("GetBM3", "BowMesh"); fn("BMV3", SC, "IsVisible", pure=True, const=True); L("new:GetBM3.BowMesh", "new:BMV3.self")
btxt("TBv", "new:BMV3.ReturnValue", "BV")
xget("HMesh", "/Script/Engine.Character", "Mesh"); L("new:GPCh.ReturnValue", "new:HMesh.self")
fn("HAnim", "/Script/Engine.SkeletalMeshComponent", "GetAnimInstance", pure=True, const=True); L("new:HMesh.Mesh", "new:HAnim.self")
fn("HMont", "/Script/Engine.AnimInstance", "GetCurrentActiveMontage", pure=True, const=True); L("new:HAnim.ReturnValue", "new:HMont.self")
ntxt("TAm", "new:HMont.ReturnValue", "AM")

xget("BMHid3", SC, "bHiddenInGame"); L("new:GetBM3.BowMesh", "new:BMHid3.self"); btxt("TBg", "new:BMHid3.bHiddenInGame", "BG")
fn("BMSc3", SC, "K2_GetComponentScale", pure=True, const=True); L("new:GetBM3.BowMesh", "new:BMSc3.self")
fn("BMScB", KML, "BreakVector", pure=True); L("new:BMSc3.ReturnValue", "new:BMScB.InVec"); L("new:BMScB.X", "new:Fmt.BS")
vget("GetSeen", "Seen"); fn("SeenT", KTL, "Conv_StringToText", pure=True)
L("new:GetSeen.Seen", "new:SeenT.InString"); L("new:SeenT.ReturnValue", "new:Fmt.SM")

# montage log: append each new montage name (not None) to Seen, before the readout
KSTR = "/Script/Engine.KismetStringLibrary"
fn("MName", KSL, "GetObjectName", pure=True); L("new:HMont.ReturnValue", "new:MName.Object")
vget("GetLastM", "LastMont"); fn("MNew", KSTR, "NotEqual_StrStr", pure=True)
L("new:MName.ReturnValue", "new:MNew.A"); L("new:GetLastM.LastMont", "new:MNew.B")
fn("MNotNone", KSTR, "NotEqual_StrStr", pure=True); L("new:MName.ReturnValue", "new:MNotNone.A"); S("new:MNotNone.B", "None")
fn("MAnd", KML, "BooleanAND", pure=True); L("new:MNew.ReturnValue", "new:MAnd.A"); L("new:MNotNone.ReturnValue", "new:MAnd.B")
branch("BrMont"); vset("SetLastM", "LastMont"); vset("SetSeen", "Seen")
L("new:IV.Is Valid", "new:BrMont.execute"); L("new:MAnd.ReturnValue", "new:BrMont.Condition")
L("new:BrMont.then", "new:SetLastM.execute"); L("new:MName.ReturnValue", "new:SetLastM.LastMont")
fn("SeenCat1", KSTR, "Concat_StrStr", pure=True); fn("SeenCat2", KSTR, "Concat_StrStr", pure=True)
L("new:GetSeen.Seen", "new:SeenCat1.A"); L("new:MName.ReturnValue", "new:SeenCat1.B")
L("new:SeenCat1.ReturnValue", "new:SeenCat2.A"); S("new:SeenCat2.B", "/")
L("new:SetLastM.then", "new:SetSeen.execute"); L("new:SeenCat2.ReturnValue", "new:SetSeen.Seen")
L("new:SetSeen.then", "new:ST.execute"); L("new:BrMont.else", "new:ST.execute")


# --- v5: is the bow's own skeleton collapsing it? (all visibility flags were on, yet nothing drawn)
# v5 showed the bow is alternative meshes picked by bone scale: StaticMesh at rest, SM_Bow4 drawn while aiming, the
# others at 0.01. While holding (outside the bow montage) SM_Bow<Part+1> is scaled back to 1 after the game's animation.
# N cycles Part: 0 off, 1 SM_Bow2, 2 SM_Bow3, 3 SM_Bow4 (BeginPlay starts at 1). Freeze (tick off) stays unused.
node("KN", "/Script/BlueprintGraph.K2Node_InputKey", "InputKey=N", "bConsumeInput=False")
vget("GetPt", "Part"); fn("AddPt", KML, "Add_IntInt", pure=True); fn("ModPt", KML, "Percent_IntInt", pure=True); vset("SetPt", "Part")
L("new:KN.Pressed", "new:SetPt.execute"); L("new:GetPt.Part", "new:AddPt.A"); S("new:AddPt.B", "1")
L("new:AddPt.ReturnValue", "new:ModPt.A"); S("new:ModPt.B", "4"); L("new:ModPt.ReturnValue", "new:SetPt.Part")
vset("SetPt0", "Part"); S("new:SetPt0.Part", "1")
if DEBUG: L("new:ATV.then", "new:SetPt0.execute")
vget("GetPt2", "Part"); fn("AddPt2", KML, "Add_IntInt", pure=True); fn("PtStr", KSTR, "Conv_IntToString", pure=True)
fn("PtName", KSTR, "Concat_StrStr", pure=True)
L("new:GetPt2.Part", "new:AddPt2.A"); S("new:AddPt2.B", "1"); L("new:AddPt2.ReturnValue", "new:PtStr.InInt")
S("new:PtName.A", "SM_Bow"); L("new:PtStr.ReturnValue", "new:PtName.B")
fn("IsBowMont", KSTR, "EqualEqual_StrStr", pure=True); L("new:MName.ReturnValue", "new:IsBowMont.A"); S("new:IsBowMont.B", "Player_Bow_Charge_Montage")
fn("NotBowMont", KML, "Not_PreBool", pure=True); L("new:IsBowMont.ReturnValue", "new:NotBowMont.A")
vget("GetFz2", "Freeze"); vget("GetHold5", "Holding")
fn("FzA", KML, "BooleanAND", pure=True); fn("FzB", KML, "BooleanAND", pure=True); fn("FzTick", KML, "Not_PreBool", pure=True)
L("new:GetFz2.Freeze", "new:FzA.A"); L("new:GetHold5.Holding", "new:FzA.B")
L("new:FzA.ReturnValue", "new:FzB.A"); L("new:NotBowMont.ReturnValue", "new:FzB.B"); L("new:FzB.ReturnValue", "new:FzTick.A")
vget("GetBM5", "BowMesh"); fn("FrzSet", "/Script/Engine.ActorComponent", "SetComponentTickEnabled")
L("new:GetBM5.BowMesh", "new:FrzSet.self"); L("new:FzTick.ReturnValue", "new:FrzSet.bEnabled")
vget("GetPt3", "Part"); L("new:GetPt3.Part", "new:Fmt.FZ")

# bow skeleton's anim instance + montage (BowSK = SK_BowRigTpose, cast in the find loop)
vget("GetBSK", "BowSK")
fn("BAnim", "/Script/Engine.SkeletalMeshComponent", "GetAnimInstance", pure=True, const=True); L("new:GetBSK.BowSK", "new:BAnim.self")
fn("BACls", GS, "GetObjectClass", pure=True); L("new:BAnim.ReturnValue", "new:BACls.Object")
fn("BACn", KSL, "GetClassDisplayName", pure=True); fn("BACt", KTL, "Conv_StringToText", pure=True)
L("new:BACls.ReturnValue", "new:BACn.Class"); L("new:BACn.ReturnValue", "new:BACt.InString"); L("new:BACt.ReturnValue", "new:Fmt.BA")
fn("BMont", "/Script/Engine.AnimInstance", "GetCurrentActiveMontage", pure=True, const=True); L("new:BAnim.ReturnValue", "new:BMont.self")
ntxt("TBo", "new:BMont.ReturnValue", "BO")

# one line per bow component: name, world scale X, visible -> BowStr, built before the readout
vset("ClrBS", "BowStr"); L("new:IV.Is Valid", "new:ClrBS.execute")
vget("GetBow7", "Bow"); fn("BComps", ACT, "GetComponentsByClass", pure=True, const=True); L("new:GetBow7.Bow", "new:BComps.self")
S("new:BComps.ComponentClass", SC)
foreach("FB"); L("new:BComps.ReturnValue", "new:FB.Array"); L("new:ClrBS.then", "new:FB.Exec")
fn("BCN", KSL, "GetObjectName", pure=True); L("new:FB.Array Element", "new:BCN.Object")
fn("BCSc", SC, "K2_GetComponentScale", pure=True, const=True); L("new:FB.Array Element", "new:BCSc.self")
fn("BCScB", KML, "BreakVector", pure=True); L("new:BCSc.ReturnValue", "new:BCScB.InVec")
fn("BCScS", KSTR, "Conv_FloatToString", pure=True); L("new:BCScB.X", "new:BCScS.InFloat")
fn("BCV", SC, "IsVisible", pure=True, const=True); L("new:FB.Array Element", "new:BCV.self")
fn("BCVS", KSTR, "Conv_BoolToString", pure=True); L("new:BCV.ReturnValue", "new:BCVS.InBool")
vget("GetBS", "BowStr"); vset("SetBS", "BowStr")
parts = ["new:GetBS.BowStr", "new:BCN.ReturnValue", ("lit", "[scale="), "new:BCScS.ReturnValue", ("lit", "] [vis="),
         "new:BCVS.ReturnValue", ("lit", r"]\n")]
acc = parts[0]
for i, part in enumerate(parts[1:]):
    n = "CatB%d" % i; fn(n, KSTR, "Concat_StrStr", pure=True)
    L(acc, "new:%s.A" % n)
    if isinstance(part, tuple): S("new:%s.B" % n, part[1])
    else: L(part, "new:%s.B" % n)
    acc = "new:%s.ReturnValue" % n
L(acc, "new:SetBS.BowStr"); L("new:FB.LoopBody", "new:SetBS.execute")

# --- v8: with N=2 the parts matched the aiming state exactly (SM_Bow4 1.0, all visible) yet nothing was drawn, so test
# the material. Bow4 = the SM_Bow4 component (seen in hand while aiming).
fn("Is4", KSTR, "EqualEqual_StrStr", pure=True); L("new:BCN.ReturnValue", "new:Is4.A"); S("new:Is4.B", "SM_Bow4")
branch("BrIs4"); cast("CastP4", "/Script/Engine.PrimitiveComponent"); vset("SetB4", "Bow4")
L("new:SetBS.then", "new:BrIs4.execute"); L("new:Is4.ReturnValue", "new:BrIs4.Condition")
L("new:BrIs4.then", "new:CastP4.execute"); L("new:FB.Array Element", "new:CastP4.Object")
L("new:CastP4.then", "new:SetB4.execute"); L("new:CastP4.AsPrimitive Component", "new:SetB4.Bow4")
# after the loop: Bow4's material 0 as a dynamic instance -> read candidate fade parameters into ParamStr
vget("GetB4", "Bow4"); fn("B4Mat", "/Script/Engine.PrimitiveComponent", "GetMaterial", pure=True, const=True)
L("new:GetB4.Bow4", "new:B4Mat.self"); S("new:B4Mat.ElementIndex", "0")
cast("CastMID", "/Script/Engine.MaterialInstanceDynamic"); L("new:FB.Completed", "new:CastMID.execute"); L("new:B4Mat.ReturnValue", "new:CastMID.Object")
PARAMS = ["Opacity", "Dissolve", "DissolveAmount", "Fade", "Alpha", "Visibility", "Appear", "Erode", "Glow", "Transition"]
prev = "new:CastMID.then"; acc = None
for i, pname in enumerate(PARAMS):
    n = "GSP%d" % i; fn(n, "/Script/Engine.MaterialInstanceDynamic", "K2_GetScalarParameterValue")
    L("new:CastMID.AsMaterial Instance Dynamic", "new:%s.self" % n); S("new:%s.ParameterName" % n, pname)
    L(prev, "new:%s.execute" % n); prev = "new:%s.then" % n
    fs = "GSPs%d" % i; fn(fs, KSTR, "Conv_FloatToString", pure=True); L("new:%s.ReturnValue" % n, "new:%s.InFloat" % fs)
    c1 = "GSPc%da" % i; c2 = "GSPc%db" % i
    fn(c1, KSTR, "Concat_StrStr", pure=True); fn(c2, KSTR, "Concat_StrStr", pure=True)
    S("new:%s.A" % c1, pname + "="); L("new:%s.ReturnValue" % fs, "new:%s.B" % c1)
    if acc: L(acc, "new:%s.A" % c2)
    else: S("new:%s.A" % c2, "[")
    L("new:%s.ReturnValue" % c1, "new:%s.B" % c2)
    acc = "new:%s.ReturnValue" % c2
vset("SetPS", "ParamStr"); L(prev, "new:SetPS.execute"); L(acc, "new:SetPS.ParamStr")
vset("SetPS0", "ParamStr"); S("new:SetPS0.ParamStr", "material 0 is not a MaterialInstanceDynamic")
L("new:CastMID.CastFailed", "new:SetPS0.execute")
L("new:SetPS.then", "new:BrMont.execute"); L("new:SetPS0.then", "new:BrMont.execute")
vget("GetPS", "ParamStr"); fn("PST", KTL, "Conv_StringToText", pure=True); L("new:GetPS.ParamStr", "new:PST.InString"); L("new:PST.ReturnValue", "new:Fmt.PS")
fn("B4MatN", KSL, "GetObjectName", pure=True); L("new:B4Mat.ReturnValue", "new:B4MatN.Object")
fn("B4MatT", KTL, "Conv_StringToText", pure=True); L("new:B4MatN.ReturnValue", "new:B4MatT.InString"); L("new:B4MatT.ReturnValue", "new:Fmt.MT")
vget("GetBSK8", "BowSK"); fn("SKMat", "/Script/Engine.PrimitiveComponent", "GetMaterial", pure=True, const=True)
L("new:GetBSK8.BowSK", "new:SKMat.self"); S("new:SKMat.ElementIndex", "0")
fn("SKMatN", KSL, "GetObjectName", pure=True); L("new:SKMat.ReturnValue", "new:SKMatN.Object")
fn("SKMatT", KTL, "Conv_StringToText", pure=True); L("new:SKMatN.ReturnValue", "new:SKMatT.InString"); L("new:SKMatT.ReturnValue", "new:Fmt.MK")

# M (one-way until restart): put the hero mesh's material 0 on SM_Bow4 and on the bow skeleton
node("KM", "/Script/BlueprintGraph.K2Node_InputKey", "InputKey=M", "bConsumeInput=False")
xget("HMesh2", "/Script/Engine.Character", "Mesh"); L("new:GPCh.ReturnValue", "new:HMesh2.self")
fn("HMat", "/Script/Engine.PrimitiveComponent", "GetMaterial", pure=True, const=True); L("new:HMesh2.Mesh", "new:HMat.self"); S("new:HMat.ElementIndex", "0")
vget("GetB4m", "Bow4"); vget("GetBSKm", "BowSK"); vset("SetMS", "MatSwapped")
fn("SwapB4", "/Script/Engine.PrimitiveComponent", "SetMaterial"); fn("SwapSK", "/Script/Engine.PrimitiveComponent", "SetMaterial")
L("new:GetB4m.Bow4", "new:SwapB4.self"); S("new:SwapB4.ElementIndex", "0"); L("new:HMat.ReturnValue", "new:SwapB4.Material")
L("new:GetBSKm.BowSK", "new:SwapSK.self"); S("new:SwapSK.ElementIndex", "0"); L("new:HMat.ReturnValue", "new:SwapSK.Material")
L("new:KM.Pressed", "new:SwapB4.execute"); chain("new:SwapB4", "new:SwapSK", "new:SetMS"); S("new:SetMS.MatSwapped", "true")
vget("GetMS", "MatSwapped"); btxt("TMs", "new:GetMS.MatSwapped", "MS")

# --- v7: v6 scaling SM_Bow2 to 1 drew nothing, so the visible bow is SK_BowRigTpose's own skinned geometry, collapsed
# by its single-node animation. While the hero is in the bow montage, record the bow animation's position (LastPos);
# while holding outside it, pin the animation: Part 1 = LastPos, Part 2 = 0 (N cycles 0 off / 1 / 2).
vget("GetBSK7", "BowSK"); fn("BPos", "/Script/Engine.SkeletalMeshComponent", "GetPosition", pure=True, const=True)
L("new:GetBSK7.BowSK", "new:BPos.self")
branch("BrRec"); vset("SetLP", "LastPos"); L("new:FrzSet.then", "new:BrRec.execute")
vget("GetB4r", "Bow4"); fn("B4Sc", SC, "K2_GetComponentScale", pure=True, const=True); L("new:GetB4r.Bow4", "new:B4Sc.self")
fn("B4ScB", KML, "BreakVector", pure=True); L("new:B4Sc.ReturnValue", "new:B4ScB.InVec")
fn("B4Full", KML, "GreaterEqual_FloatFloat", pure=True); L("new:B4ScB.X", "new:B4Full.A"); S("new:B4Full.B", "0.99")
fn("RecC", KML, "BooleanAND", pure=True); L("new:IsBowMont.ReturnValue", "new:RecC.A"); L("new:B4Full.ReturnValue", "new:RecC.B")
L("new:RecC.ReturnValue", "new:BrRec.Condition")
cast("CastSN", "/Script/Engine.AnimSingleNodeInstance"); L("new:BrRec.then", "new:CastSN.execute"); L("new:BAnim.ReturnValue", "new:CastSN.Object")
fn("GetAA", "/Script/Engine.AnimSingleNodeInstance", "GetAnimationAsset", pure=True, const=True); L("new:CastSN.AsAnim Single Node Instance", "new:GetAA.self")
vset("SetAA", "AimAsset"); L("new:CastSN.then", "new:SetAA.execute"); L("new:GetAA.ReturnValue", "new:SetAA.AimAsset")
L("new:SetAA.then", "new:SetLP.execute"); L("new:CastSN.CastFailed", "new:SetLP.execute"); L("new:BPos.ReturnValue", "new:SetLP.LastPos")
vget("GetMP", "MaxPos"); fn("MaxP", KML, "FMax", pure=True); vset("SetMP", "MaxPos")
L("new:GetMP.MaxPos", "new:MaxP.A"); L("new:BPos.ReturnValue", "new:MaxP.B"); L("new:MaxP.ReturnValue", "new:SetMP.MaxPos")
L("new:SetLP.then", "new:SetMP.execute")
vget("GetHold7", "Holding"); vget("GetPt7", "Part")
fn("Pt7Pos", KML, "Greater_IntInt", pure=True); L("new:GetPt7.Part", "new:Pt7Pos.A"); S("new:Pt7Pos.B", "1")
fn("Pin1", KML, "BooleanAND", pure=True); fn("Pin2", KML, "BooleanAND", pure=True)
L("new:GetHold7.Holding", "new:Pin1.A"); L("new:NotBowMont.ReturnValue", "new:Pin1.B")
L("new:Pin1.ReturnValue", "new:Pin2.A"); L("new:Pt7Pos.ReturnValue", "new:Pin2.B")
branch("BrPin"); L("new:SetMP.then", "new:BrPin.execute"); L("new:BrRec.else", "new:BrPin.execute"); L("new:Pin2.ReturnValue", "new:BrPin.Condition")
vget("GetLP7", "LastPos"); fn("Pt7One", KML, "EqualEqual_IntInt", pure=True); L("new:GetPt7.Part", "new:Pt7One.A"); S("new:Pt7One.B", "1")
fn("Pt7Two", KML, "EqualEqual_IntInt", pure=True); L("new:GetPt7.Part", "new:Pt7Two.A"); S("new:Pt7Two.B", "2")
vget("GetMP7", "MaxPos"); fn("PinPos2", KML, "SelectFloat", pure=True)
S("new:PinPos2.A", "0.0"); L("new:GetMP7.MaxPos", "new:PinPos2.B"); L("new:Pt7Two.ReturnValue", "new:PinPos2.bPickA")
fn("PinPos", KML, "SelectFloat", pure=True); L("new:GetLP7.LastPos", "new:PinPos.A"); L("new:PinPos2.ReturnValue", "new:PinPos.B"); L("new:Pt7One.ReturnValue", "new:PinPos.bPickA")
fn("SetPos", "/Script/Engine.SkeletalMeshComponent", "SetPosition"); L("new:GetBSK7.BowSK", "new:SetPos.self")
L("new:GetLP7.LastPos", "new:SetPos.InPos"); S("new:SetPos.bFireNotifies", "false")
cast("CastSN2", "/Script/Engine.AnimSingleNodeInstance"); L("new:BrPin.then", "new:CastSN2.execute"); L("new:BAnim.ReturnValue", "new:CastSN2.Object")
fn("CurAA", "/Script/Engine.AnimSingleNodeInstance", "GetAnimationAsset", pure=True, const=True); L("new:CastSN2.AsAnim Single Node Instance", "new:CurAA.self")
vget("GetAA2", "AimAsset"); fn("AADiff", KML, "NotEqual_ObjectObject", pure=True); fn("AAValid", KSL, "IsValid", pure=True)
L("new:CurAA.ReturnValue", "new:AADiff.A"); L("new:GetAA2.AimAsset", "new:AADiff.B"); L("new:GetAA2.AimAsset", "new:AAValid.Object")
fn("AASw", KML, "BooleanAND", pure=True); L("new:AADiff.ReturnValue", "new:AASw.A"); L("new:AAValid.ReturnValue", "new:AASw.B")
branch("BrAA"); L("new:CastSN2.then", "new:BrAA.execute"); L("new:AASw.ReturnValue", "new:BrAA.Condition")
fn("SetAsset", "/Script/Engine.AnimSingleNodeInstance", "SetAnimationAsset"); L("new:CastSN2.AsAnim Single Node Instance", "new:SetAsset.self")
L("new:GetAA2.AimAsset", "new:SetAsset.NewAsset"); S("new:SetAsset.bIsLooping", "false"); S("new:SetAsset.InPlayRate", "1.0")
L("new:BrAA.then", "new:SetAsset.execute"); L("new:SetAsset.then", "new:SetPos.execute"); L("new:BrAA.else", "new:SetPos.execute")
L("new:CastSN2.CastFailed", "new:IV.exec")
# --- v11: v10 restored the aiming asset + position and still nothing showed, so maybe J_L_Weapon_Socket itself is out
# of view outside the bow animations. Part 2 also re-attaches the bow skeleton to the hero's J_L_Hand while pinned.
xget("HMesh3", "/Script/Engine.Character", "Mesh"); L("new:GPCh.ReturnValue", "new:HMesh3.self")
vget("GetPt11", "Part"); fn("Pt11Two", KML, "EqualEqual_IntInt", pure=True); L("new:GetPt11.Part", "new:Pt11Two.A"); S("new:Pt11Two.B", "3")
vget("GetRA", "Reattached"); fn("NotRA", KML, "Not_PreBool", pure=True); L("new:GetRA.Reattached", "new:NotRA.A")
fn("DoRA", KML, "BooleanAND", pure=True); L("new:Pt11Two.ReturnValue", "new:DoRA.A"); L("new:NotRA.ReturnValue", "new:DoRA.B")
branch("BrRA"); L("new:SetPos.then", "new:BrRA.execute"); L("new:DoRA.ReturnValue", "new:BrRA.Condition")
vget("GetBSK11", "BowSK"); fn("AttHand", SC, "K2_AttachToComponent"); L("new:GetBSK11.BowSK", "new:AttHand.self")
L("new:HMesh3.Mesh", "new:AttHand.Parent"); S("new:AttHand.SocketName", "J_L_Hand")
S("new:AttHand.LocationRule", "SnapToTarget"); S("new:AttHand.RotationRule", "SnapToTarget"); S("new:AttHand.ScaleRule", "KeepWorld")
vset("SetRA1", "Reattached"); S("new:SetRA1.Reattached", "true")
L("new:BrRA.then", "new:AttHand.execute"); L("new:AttHand.then", "new:SetRA1.execute"); L("new:SetRA1.then", "new:IV.exec"); L("new:BrRA.else", "new:IV.exec")
# not pinning (shot started, hold ended, or off): put it back on the weapon socket
branch("BrBack"); L("new:BrPin.else", "new:BrBack.execute"); L("new:GetRA.Reattached", "new:BrBack.Condition")
fn("AttBack", SC, "K2_AttachToComponent"); L("new:GetBSK11.BowSK", "new:AttBack.self")
L("new:HMesh3.Mesh", "new:AttBack.Parent"); S("new:AttBack.SocketName", "J_L_Weapon_Socket")
S("new:AttBack.LocationRule", "SnapToTarget"); S("new:AttBack.RotationRule", "SnapToTarget"); S("new:AttBack.ScaleRule", "KeepWorld")
vset("SetRA0", "Reattached"); S("new:SetRA0.Reattached", "false")
L("new:BrBack.then", "new:AttBack.execute"); L("new:AttBack.then", "new:SetRA0.execute"); L("new:SetRA0.then", "new:IV.exec"); L("new:BrBack.else", "new:IV.exec")
vget("GetRA2", "Reattached"); btxt("TRa", "new:GetRA2.Reattached", "RA")
# distances: weapon socket -> left hand, SM_Bow4 -> left hand
fn("SockWS", SC, "GetSocketLocation", pure=True, const=True); L("new:HMesh3.Mesh", "new:SockWS.self"); S("new:SockWS.InSocketName", "J_L_Weapon_Socket")
fn("SockLH", SC, "GetSocketLocation", pure=True, const=True); L("new:HMesh3.Mesh", "new:SockLH.self"); S("new:SockLH.InSocketName", "J_L_Hand")
fn("DWv", KML, "Subtract_VectorVector", pure=True); L("new:SockWS.ReturnValue", "new:DWv.A"); L("new:SockLH.ReturnValue", "new:DWv.B")
fn("DWl", KML, "VSize", pure=True); L("new:DWv.ReturnValue", "new:DWl.A"); L("new:DWl.ReturnValue", "new:Fmt.DW")
vget("GetB4d", "Bow4"); fn("B4Loc", SC, "K2_GetComponentLocation", pure=True, const=True); L("new:GetB4d.Bow4", "new:B4Loc.self")
fn("DBv", KML, "Subtract_VectorVector", pure=True); L("new:B4Loc.ReturnValue", "new:DBv.A"); L("new:SockLH.ReturnValue", "new:DBv.B")
fn("DBl", KML, "VSize", pure=True); L("new:DBv.ReturnValue", "new:DBl.A"); L("new:DBl.ReturnValue", "new:Fmt.DB")
L("new:BPos.ReturnValue", "new:Fmt.PO"); vget("GetAA3", "AimAsset"); ntxt("TAa", "new:GetAA3.AimAsset", "AA"); vget("GetEn", "Ending"); btxt("TEn", "new:GetEn.Ending", "EN"); vget("GetLP8", "LastPos"); L("new:GetLP8.LastPos", "new:Fmt.LP")
vget("GetBS2", "BowStr"); fn("BST", KTL, "Conv_StringToText", pure=True)
L("new:GetBS2.BowStr", "new:BST.InString"); L("new:BST.ReturnValue", "new:Fmt.BC")
# v12 readout links (need the Format pins, created by the Format set above)
vget("GetRS2", "RangedSlot"); L("new:GetRS2.RangedSlot", "new:Fmt.RS"); vget("GetScan2", "ScanIdx"); L("new:GetScan2.ScanIdx", "new:Fmt.SC")
vget("GetFound2", "Found"); btxt("TFd", "new:GetFound2.Found", "SN")
# release: the probe keys stay unconnected
if not DEBUG:
    ops = [o for o in ops if not any(o.startswith("link new:%s.Pressed" % k) for k in ("KB", "KN", "KM"))]
open(os.path.join(out, "probe.paste"), "w", encoding="utf-8").write("\n".join(nodes) + "\n")
open(os.path.join(out, "probe.ops"), "w", encoding="utf-8").write("\n".join(ops) + "\n")
print(len(nodes), "nodes", len(ops), "ops")
