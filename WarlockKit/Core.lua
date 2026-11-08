-- WarlockKit core: client compat helpers, events, saved settings, slash commands, self-test.
-- Patterns copied from MageKit (Forever 1.60.1 client: many old globals moved to C_* tables,
-- some unit/aura values can come back as "secret" values, so every read is guarded).
local ADDON, ns = ...
BINDING_HEADER_WARLOCKKIT = "WarlockKit"
_G["BINDING_NAME_CLICK WarlockKitButton_void:LeftButton"] = "Summon Voidwalker"
_G["BINDING_NAME_CLICK WarlockKitButton_hs:LeftButton"] = "Create / use Healthstone"
_G["BINDING_NAME_CLICK WarlockKitButton_ss:LeftButton"] = "Create / use Soulstone"

ns.isWarlock = select(2, UnitClass("player")) == "WARLOCK"
ns.badEvents = {}

---------------------------------------------------------------- compat
ns.issecret = issecretvalue or function() return false end

function ns.ItemCount(id)
  local f = (C_Item and C_Item.GetItemCount) or GetItemCount
  if not f then return 0 end
  local ok, n = pcall(f, id)
  if ok and type(n) == "number" and not ns.issecret(n) then return n end
  return 0
end
function ns.ItemIcon(id)
  if C_Item and C_Item.GetItemIconByID then return C_Item.GetItemIconByID(id) end
  if GetItemIcon then return GetItemIcon(id) end
end
function ns.SpellName(id)
  if C_Spell and C_Spell.GetSpellName then return C_Spell.GetSpellName(id) end
  return GetSpellInfo and (GetSpellInfo(id))
end
function ns.SpellIcon(id)
  if C_Spell and C_Spell.GetSpellTexture then return C_Spell.GetSpellTexture(id) end
  return GetSpellTexture and GetSpellTexture(id)
end

-- true / false, or nil when the client hides the answer (secret value) or errors
function ns.HasAura(unit, name, filter)
  local ok, res = pcall(function()
    if C_UnitAuras and C_UnitAuras.GetAuraDataBySpellName then
      return C_UnitAuras.GetAuraDataBySpellName(unit, name, filter or "HELPFUL")
    end
    return AuraUtil and AuraUtil.FindAuraByName(name, unit, filter or "HELPFUL")
  end)
  if not ok or ns.issecret(res) then return nil end
  return res ~= nil
end
function ns.KeyDown()
  if C_CVar and C_CVar.GetCVarBool then return C_CVar.GetCVarBool("ActionButtonUseKeyDown") end
  return GetCVarBool and GetCVarBool("ActionButtonUseKeyDown")
end

-- Spellbook scan by name: Forever spell IDs differ from classic, so everything here works by name.
-- name -> { id = spellID, index = spellbook slot }; later (higher) ranks overwrite earlier ones.
function ns.BookSpells()
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
          local name = GetSpellBookItemName and GetSpellBookItemName(i, book) or (GetSpellName and GetSpellName(i, book))
          local kind, id = nil, nil
          if GetSpellBookItemInfo then kind, id = GetSpellBookItemInfo(i, book) end
          if name and kind ~= "FUTURESPELL" and kind ~= "PETACTION" then map[name] = { id = id, index = i } end
        end
      end
    end
  end)
  return map
end
local book, bookStamp = {}, -1
function ns.Book()
  local now = GetTime and GetTime() or 0
  if now - bookStamp > 2 then book = ns.BookSpells(); bookStamp = now end
  return book
end
function ns.Known(name) return ns.Book()[name] ~= nil end
function ns.FlushBook() bookStamp = -1 end

-- cursor helpers for action-bar placement
function ns.CursorHas() return GetCursorInfo and GetCursorInfo() ~= nil end
function ns.PickupSpell(id, bookIndex)
  if id and C_Spell and C_Spell.PickupSpell then pcall(C_Spell.PickupSpell, id) end
  if id and not ns.CursorHas() and PickupSpell then pcall(PickupSpell, id) end
  if bookIndex and not ns.CursorHas() then
    if C_SpellBook and C_SpellBook.PickupSpellBookItem and Enum and Enum.SpellBookSpellBank then
      pcall(C_SpellBook.PickupSpellBookItem, bookIndex, Enum.SpellBookSpellBank.Player)
    elseif PickupSpellBookItem then
      pcall(PickupSpellBookItem, bookIndex, BOOKTYPE_SPELL or "spell")
    end
  end
  return ns.CursorHas()
end
function ns.PickupItem(id)
  local f = (C_Item and C_Item.PickupItem) or PickupItem
  if f then pcall(f, id) end
  return ns.CursorHas()
end

function ns.Print(...) print("|cff9482c9WarlockKit|r", ...) end

---------------------------------------------------------------- warlock data
ns.SHARD = 6265
-- every rank of conjured stones, including the Improved Healthstone variants
ns.HEALTHSTONES = { 5512, 19004, 19005, 5511, 19006, 19007, 5509, 19008, 19009, 5510, 19010, 19011, 9421, 19012, 19013 }
ns.SOULSTONES = { 5232, 16892, 16893, 16895, 16896 }
function ns.CountAny(list)
  local n = 0
  for _, id in ipairs(list) do n = n + ns.ItemCount(id) end
  return n
end
function ns.FirstHeld(list)
  for i = #list, 1, -1 do if ns.ItemCount(list[i]) > 0 then return list[i] end end
end

---------------------------------------------------------------- events
local handlers, ev = {}, CreateFrame("Frame")
function ns.On(event, fn)
  if not handlers[event] then
    local ok = pcall(ev.RegisterEvent, ev, event)
    if not ok then ns.badEvents[event] = true; return false end
    handlers[event] = {}
  end
  table.insert(handlers[event], fn)
  return true
end
ev:SetScript("OnEvent", function(_, event, ...)
  for _, fn in ipairs(handlers[event]) do xpcall(fn, geterrorhandler(), event, ...) end
end)

function ns.Throttle(delay, fn)
  local queued = false
  return function()
    if queued then return end
    queued = true
    C_Timer.After(delay, function() queued = false; fn() end)
  end
end

---------------------------------------------------------------- saved settings
local defaults = {
  alerts = { enabled = true, shards = 3, stones = true, armor = true, pet = true, autocast = true },
  buttons = { enabled = true },
  talents = { enabled = true },
  bars = { chars = {} },
  pos = {},
}
local function merge(dst, src)
  for k, v in pairs(src) do
    if type(v) == "table" then
      if type(dst[k]) ~= "table" then dst[k] = {} end
      merge(dst[k], v)
    elseif dst[k] == nil then dst[k] = v end
  end
end
ns.modules = {}
ns.On("PLAYER_LOGIN", function()
  WarlockKitDB = WarlockKitDB or {}
  merge(WarlockKitDB, defaults)
  ns.db = WarlockKitDB
  if not ns.isWarlock then return end -- silent on every other class
  for _, m in ipairs(ns.modules) do xpcall(m.Init, geterrorhandler()) end
end)
ns.On("SPELLS_CHANGED", function() ns.FlushBook() end)

-- movable frame helper; secure frames only move out of combat
function ns.Movable(frame, key, secure)
  frame:SetMovable(true); frame:SetClampedToScreen(true); frame:EnableMouse(true)
  frame:RegisterForDrag(secure and "RightButton" or "LeftButton")
  frame:SetScript("OnDragStart", function(s)
    if secure and InCombatLockdown() then return end
    if ns.db.locked then return end
    s:StartMoving()
  end)
  frame:SetScript("OnDragStop", function(s)
    s:StopMovingOrSizing()
    local p, _, rp, x, y = s:GetPoint(); ns.db.pos[key] = { p, rp, x, y }
  end)
  local p = ns.db.pos[key]
  if p then frame:ClearAllPoints(); frame:SetPoint(p[1], UIParent, p[2], p[3], p[4]) end
end

---------------------------------------------------------------- slash + self-test
ns.commands = {}
SLASH_WARLOCKKIT1 = "/wk"
SLASH_WARLOCKKIT2 = "/warlockkit"
SlashCmdList.WARLOCKKIT = function(msg)
  local cmd, rest = (msg or ""):match("^%s*(%S*)%s*(.-)%s*$")
  cmd = cmd:lower()
  if not ns.isWarlock then return ns.Print("only active on warlocks.") end
  if ns.commands[cmd] then return ns.commands[cmd](rest) end
  ns.Print("commands:")
  print("  /wk shards N        - warn when Soul Shards drop below N (now " .. tostring(ns.db.alerts.shards) .. ")")
  print("  /wk alerts on|off   - shard / pet / autocast / armor / stone reminders")
  print("  /wk buttons show|hide - pet summon + Healthstone/Soulstone buttons (right-drag to move)")
  print("  /wk lock|unlock     - lock frame positions")
  print("  /wk talents [test|on|off] - next talent from the Affliction leveling plan")
  print("  /wk bars            - preview the leveling hotbar layout; /wk bars apply asks before changing anything")
  print("  /wk test            - self-test (saved to WarlockKitDB.selftest)")
end
ns.commands.lock = function() ns.db.locked = true; ns.Print("frames locked.") end
ns.commands.unlock = function() ns.db.locked = false; ns.Print("frames unlocked (buttons: right-drag).") end

ns.commands.test = function()
  local r = { time = date("%Y-%m-%d %H:%M"), api = {}, events = {}, notes = {} }
  local apis = { "C_Item.GetItemCount", "GetItemCount", "C_Spell.GetSpellName", "C_Spell.PickupSpell",
    "C_UnitAuras.GetAuraDataBySpellName", "AuraUtil.FindAuraByName", "issecretvalue",
    "C_SpellBook.GetNumSpellBookSkillLines", "GetNumSpellTabs", "GetPetActionInfo", "TogglePetAutocast",
    "GetTalentInfo", "LearnTalent", "C_ClassTalents.GetActiveConfigID", "PlaceAction", "GetActionInfo",
    "HasAction", "GetCursorInfo", "ClearCursor", "StaticPopup_Show" }
  for _, a in ipairs(apis) do
    local t = _G
    for part in a:gmatch("[^%.]+") do t = type(t) == "table" and t[part] or nil end
    r.api[a] = t ~= nil
  end
  for e in pairs(ns.badEvents) do table.insert(r.events, e) end
  for _, m in ipairs(ns.modules) do
    if m.Test then
      local ok, res = pcall(m.Test)
      r.notes[m.name] = ok and res or ("ERROR: " .. tostring(res))
    end
  end
  ns.db.selftest = r
  local missing = {}
  for a, present in pairs(r.api) do if not present then table.insert(missing, a) end end
  table.sort(missing)
  ns.Print("self-test saved. Missing APIs: " .. (#missing > 0 and table.concat(missing, ", ") or "none")
    .. (#r.events > 0 and (" | blocked events: " .. table.concat(r.events, ", ")) or ""))
  for k, v in pairs(r.notes) do print("  " .. k .. ": " .. tostring(v)) end
end
