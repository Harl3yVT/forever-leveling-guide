-- HarleyLib compat: one copy of the client-compat helpers MageKit and AltKit used to duplicate.
-- WoW Forever (Interface 16001) removed many classic globals and hides some values (issecretvalue), so every
-- helper tries the C_ namespace first, falls back to the old global, and returns nil/0 instead of a secret.
HarleyLib = HarleyLib or {}
local L = HarleyLib
L.version = 1
local C = {}
L.compat = C

C.GetItemInfo = (C_Item and C_Item.GetItemInfo) or GetItemInfo
C.ItemInfoInstant = (C_Item and C_Item.GetItemInfoInstant) or GetItemInfoInstant
C.NumSlots = (C_Container and C_Container.GetContainerNumSlots) or GetContainerNumSlots
C.UseItem = (C_Container and C_Container.UseContainerItem) or UseContainerItem
C.ItemCooldown = (C_Container and C_Container.GetItemCooldown) or GetItemCooldown
C.issecret = issecretvalue or function() return false end

-- link, quality, itemID, locked, icon, count, bound
function C.SlotInfo(bag, slot)
  if C_Container and C_Container.GetContainerItemInfo then
    local i = C_Container.GetContainerItemInfo(bag, slot)
    if i then return i.hyperlink, i.quality, i.itemID, i.isLocked, i.iconFileID, i.stackCount, i.isBound end
    return
  end
  if not GetContainerItemInfo then return end
  local tex, count, locked, quality, _, _, link, _, _, id, bound = GetContainerItemInfo(bag, slot)
  return link, quality, id, locked, tex, count, bound
end

-- calls fn(bag, slot, link, quality, itemID, locked, icon, count, bound) for every filled bag slot
function C.EachBagItem(fn)
  for bag = 0, NUM_BAG_SLOTS or 4 do
    for slot = 1, C.NumSlots(bag) or 0 do
      local link, q, id, locked, icon, count, bound = C.SlotInfo(bag, slot)
      if id then
        if fn(bag, slot, link, q, id, locked, icon, count, bound) == false then return end
      end
    end
  end
end

function C.ItemCount(id)
  local f = (C_Item and C_Item.GetItemCount) or GetItemCount
  if not f then return 0 end
  local ok, n = pcall(f, id)
  if ok and type(n) == "number" and not C.issecret(n) then return n end
  return 0
end
-- total count of bag items whose name contains `pattern` (plain find); also returns the first such itemID
function C.CountByName(pattern)
  local total, first = 0, nil
  C.EachBagItem(function(_, _, _, _, id, _, _, count)
    local name = C.GetItemInfo(id)
    if type(name) == "string" and name:find(pattern, 1, true) then
      total = total + (count or 1); first = first or id
    end
  end)
  return total, first
end
function C.ItemSpell(id) -- "Drink", "Food", "Refreshment"...
  local f = (C_Item and C_Item.GetItemSpell) or GetItemSpell
  if not f then return nil end
  local ok, name = pcall(f, id)
  if ok and type(name) == "string" then return name end
end
function C.ItemIcon(id)
  if C_Item and C_Item.GetItemIconByID then return C_Item.GetItemIconByID(id) end
  if GetItemIcon then return GetItemIcon(id) end
  if C.ItemInfoInstant then return select(5, C.ItemInfoInstant(id)) end
end

function C.SpellName(id)
  if not id then return nil end
  if C_Spell and C_Spell.GetSpellName then return C_Spell.GetSpellName(id) end
  return GetSpellInfo and (GetSpellInfo(id))
end
function C.SpellIcon(id)
  if not id then return nil end
  if C_Spell and C_Spell.GetSpellTexture then return C_Spell.GetSpellTexture(id) end
  return GetSpellTexture and GetSpellTexture(id)
end
function C.CastTime(id) -- milliseconds
  if C_Spell and C_Spell.GetSpellInfo then local i = C_Spell.GetSpellInfo(id); return i and i.castTime end
  return GetSpellInfo and select(4, GetSpellInfo(id))
end
function C.ManaCost(id)
  local f = (C_Spell and C_Spell.GetSpellPowerCost) or GetSpellPowerCost
  local costs = f and f(id)
  if type(costs) ~= "table" then return nil end
  for _, c in ipairs(costs) do if c.type == 0 or c.name == "MANA" then return c.cost end end
end
function C.Description(id)
  if C_Spell and C_Spell.GetSpellDescription then return C_Spell.GetSpellDescription(id) end
  return GetSpellDescription and GetSpellDescription(id)
end
function C.Knows(id)
  if IsPlayerSpell and IsPlayerSpell(id) then return true end
  if C_SpellBook and C_SpellBook.IsSpellKnown and C_SpellBook.IsSpellKnown(id) then return true end
  return (IsSpellKnown and IsSpellKnown(id)) or false
end
function C.HighestKnown(ranks)
  for i = #ranks, 1, -1 do if C.Knows(ranks[i]) then return ranks[i], i end end
end

-- true / false, or nil when the client hides the answer (secret value) or errors
function C.HasAura(unit, name, filter)
  if not name then return false end
  local ok, res = pcall(function()
    if C_UnitAuras and C_UnitAuras.GetAuraDataBySpellName then
      return C_UnitAuras.GetAuraDataBySpellName(unit, name, filter or "HELPFUL")
    end
    return AuraUtil and AuraUtil.FindAuraByName(name, unit, filter or "HELPFUL")
  end)
  if not ok or C.issecret(res) then return nil end
  return res ~= nil
end
-- true if any of `names` is up, false if none, nil if the client hides at least one answer and none is up
function C.HasAnyAura(unit, names, filter)
  local unknown = false
  for _, n in ipairs(names) do
    local has = C.HasAura(unit, n, filter)
    if has then return true end
    if has == nil then unknown = true end
  end
  if unknown then return nil end
  return false
end

-- friendly, alive, connected and visible: a unit a buff can go on
function C.UsableFriend(unit)
  return UnitExists(unit) and UnitIsConnected(unit) and not UnitIsDeadOrGhost(unit)
    and UnitIsVisible(unit) and UnitIsFriend("player", unit)
end
-- spell range check that tolerates hidden (secret) answers; false when unknown
function C.InRange(spellID, unit)
  if UnitIsUnit(unit, "player") then return true end
  if C_Spell and C_Spell.IsSpellInRange then
    local ok, r = pcall(C_Spell.IsSpellInRange, spellID, unit)
    if ok and not C.issecret(r) and r ~= nil then return r end
  end
  local ok, r = pcall(UnitInRange, unit)
  if ok and not C.issecret(r) then return r and true or false end
  return false
end

function C.KeyDown()
  if C_CVar and C_CVar.GetCVarBool then return C_CVar.GetCVarBool("ActionButtonUseKeyDown") end
  return GetCVarBool and GetCVarBool("ActionButtonUseKeyDown")
end
-- percent and current of mana (0) / any power type, or "health"; nil when hidden by the client
function C.Pct(kind, unit)
  unit = unit or "player"
  local ok, cur, max = pcall(function()
    if kind == "health" then return UnitHealth(unit), UnitHealthMax(unit) end
    return UnitPower(unit, kind == "mana" and 0 or kind), UnitPowerMax(unit, kind == "mana" and 0 or kind)
  end)
  if ok and not C.issecret(cur) and not C.issecret(max) and type(max) == "number" and max > 0 then
    return cur / max * 100, cur
  end
end
function C.UsesMana(unit)
  local ok, p = pcall(UnitPowerType, unit or "player")
  if not ok or C.issecret(p) then return true end
  return p == 0
end

-- Spellbook scan by name: name -> { id = spellID, index = book slot }. Later (higher) ranks overwrite earlier ones.
-- Works with names only, so it never depends on classic spell IDs matching this client.
function C.BookSpells()
  local map = {}
  pcall(function()
    if C_SpellBook and C_SpellBook.GetNumSpellBookSkillLines and Enum and Enum.SpellBookSpellBank then
      local bank = Enum.SpellBookSpellBank.Player
      local SPELL = Enum.SpellBookItemType and Enum.SpellBookItemType.Spell
      for line = 1, C_SpellBook.GetNumSpellBookSkillLines() do
        local info = C_SpellBook.GetSpellBookSkillLineInfo(line)
        if info then
          for i = info.itemIndexOffset + 1, info.itemIndexOffset + info.numSpellBookItems do
            local it = C_SpellBook.GetSpellBookItemInfo(i, bank)
            if it and it.name and it.spellID and (SPELL == nil or it.itemType == SPELL) and not it.isPassive then
              map[it.name] = { id = it.spellID, index = i }
            end
          end
        end
      end
    elseif GetNumSpellTabs and GetSpellTabInfo then
      local book = BOOKTYPE_SPELL or "spell"
      for tab = 1, GetNumSpellTabs() do
        local _, _, offset, num = GetSpellTabInfo(tab)
        for i = (offset or 0) + 1, (offset or 0) + (num or 0) do
          local name = (GetSpellBookItemName and GetSpellBookItemName(i, book)) or (GetSpellName and GetSpellName(i, book))
          local kind, id
          if GetSpellBookItemInfo then kind, id = GetSpellBookItemInfo(i, book) end
          if name and kind ~= "FUTURESPELL" and kind ~= "PETACTION" then map[name] = { id = id, index = i } end
        end
      end
    end
  end)
  return map
end

-- cursor helpers for action-bar placement
function C.CursorHas() return GetCursorInfo and GetCursorInfo() ~= nil end
function C.PickupSpell(id, bookIndex)
  if id and C_Spell and C_Spell.PickupSpell then pcall(C_Spell.PickupSpell, id) end
  if id and not C.CursorHas() and PickupSpell then pcall(PickupSpell, id) end
  if bookIndex and not C.CursorHas() then
    if C_SpellBook and C_SpellBook.PickupSpellBookItem and Enum and Enum.SpellBookSpellBank then
      pcall(C_SpellBook.PickupSpellBookItem, bookIndex, Enum.SpellBookSpellBank.Player)
    elseif PickupSpellBookItem then
      pcall(PickupSpellBookItem, bookIndex, BOOKTYPE_SPELL or "spell")
    end
  end
  return C.CursorHas()
end
function C.PickupItem(id)
  local f = (C_Item and C_Item.PickupItem) or PickupItem
  if f then pcall(f, id) end
  return C.CursorHas()
end
function C.PickupMacroByName(name)
  local idx = GetMacroIndexByName and GetMacroIndexByName(name)
  if idx and idx > 0 and PickupMacro then pcall(PickupMacro, idx) end
  return C.CursorHas()
end

function C.CharKey()
  return (UnitName("player") or "?") .. "-" .. (GetRealmName and GetRealmName() or "?")
end

-- "a.b.c" -> exists in _G?
function C.HasAPI(path)
  local t = _G
  for part in path:gmatch("[^%.]+") do
    if type(t) ~= "table" then return false end
    t = t[part]
  end
  return t ~= nil
end
