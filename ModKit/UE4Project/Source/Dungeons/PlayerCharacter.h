#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "GameFramework/Character.h"
#include "PlayerCharacter.generated.h"

// Stubs of the game's native /Script/Dungeons.PlayerCharacter, EquipmentDisplayComponent and ESlotType.
// They only exist so Blueprints can call these by name; at runtime they resolve against the real classes in the
// game executable. The module DLL is never packaged, so none of this ships.
// The weapon anim notify AnimNS_Player_ShowWeaponSlot calls ShowWeaponSlot(SlotType) on begin and
// RestoreWeaponVisibility() on end (FModel bytecode export).

// The real enum has at least Armor, MeleeWeapon and RangedWeapon, in an unknown order. Blueprints store enum
// literals as numbers, so these placeholders stand for the values 0..7; read the real names at runtime with
// "Enum to Name/String", which uses the game's enum.
UENUM(BlueprintType)
enum class ESlotType : uint8
{
	Slot0, Slot1, Slot2, Slot3, Slot4, Slot5, Slot6, Slot7
};

UCLASS(BlueprintType)
class DUNGEONS_API UEquipmentDisplayComponent : public UActorComponent
{
	GENERATED_BODY()

public:
	UFUNCTION(BlueprintCallable)
	void ShowWeaponSlot(ESlotType SlotType) {}

	UFUNCTION(BlueprintCallable)
	void RestoreWeaponVisibility() {}
};

UCLASS()
class DUNGEONS_API APlayerCharacter : public ACharacter
{
	GENERATED_BODY()

public:
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly)
	UEquipmentDisplayComponent* EquipmentDisplayComponent = nullptr;
};
