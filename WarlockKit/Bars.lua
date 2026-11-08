-- Bars: a leveling action-bar layout for warlocks (main bar 1-12, bottom-left bar 61-72).
-- Nothing changes until you confirm: /wk bars shows a preview, /wk bars apply opens a confirm
-- dialog, and only then are spells placed. By default only EMPTY slots are filled;
-- /wk bars apply force also replaces occupied slots (still asks first).
-- Spells you have not learned are skipped; run it again after training.
local _, ns = ...
local M = { name = "bars" }
table.insert(ns.modules, M)

-- slot -> list of spell names, first known wins (Forever renamed Curse of Agony to Bane of Agony)
local LAYOUT = {
  [1] = { "Shadow Bolt" },
  [2] = { "Immolate" },
  [3] = { "Corruption" },
  [4] = { "Bane of Agony", "Curse of Agony" },
  [5] = { "Siphon Life", "Curse of Weakness" },
  [6] = { "Drain Life" },
  [7] = { "Drain Soul" },
  [8] = { "Life Tap" },
  [9] = { "Shoot" },
  [10] = { "Fear" },
  [11] = { "Howl of Terror", "Death Coil" },
  [12] = { "Health Funnel" },
  [61] = { "Demon Armor", "Demon Skin" },
  [62] = { "Summon Voidwalker", "Summon Imp" },
  [63] = { "Summon Succubus", "Summon Incubus" },
  [64] = { "Summon Felhunter" },
  [65] = { "Create Healthstone" },
  [66] = { "Create Soulstone" },
  [67] = { "Shadowburn", "Searing Pain" },
  [68] = { "Rain of Fire", "Hellfire" },
  [69] = { "Curse of the Elements", "Curse of Recklessness" },
  [70] = { "Unending Breath" },
  [71] = { "Banish", "Enslave Demon", "Subjugate Demon" },
  [72] = { "Summon Felsteed" },
}
local ORDER = {}
for slot in pairs(LAYOUT) do ORDER[#ORDER + 1] = slot end
table.sort(ORDER)

local function Pick(names)
  local book = ns.Book()
  for _, n in ipairs(names) do if book[n] then return n, book[n] end end
end

local function Status(slot, force)
  local name, info = Pick(LAYOUT[slot])
  if not name then return "learn later", LAYOUT[slot][1] end
  if HasAction(slot) then
    local kind, id = GetActionInfo(slot)
    if kind == "spell" and ns.SpellName(id) == name then return "already there", name end
    if not force then return "occupied (keep)", name end
    return "replace", name, info
  end
  return "place", name, info
end

local function Preview(force)
  ns.Print("leveling layout (" .. (force and "force: replaces occupied slots" or "fills empty slots only") .. "):")
  for _, slot in ipairs(ORDER) do
    local st, name = Status(slot, force)
    print(("  %2d  %-22s %s"):format(slot, name, st))
  end
end

local function Apply(force)
  if InCombatLockdown() then return ns.Print("not in combat.") end
  local done = 0
  for _, slot in ipairs(ORDER) do
    local st, name, info = Status(slot, force)
    if (st == "place" or st == "replace") and info then
      ClearCursor()
      if ns.PickupSpell(info.id, info.index) then
        PlaceAction(slot)
        done = done + 1
      end
      ClearCursor()
    end
  end
  ns.db.bars.chars[(UnitName("player") or "?")] = { applied = time and time() or 0, force = force or false }
  ns.Print(("bars: placed %d spells."):format(done))
end

StaticPopupDialogs = StaticPopupDialogs or {}
StaticPopupDialogs.WARLOCKKIT_BARS = {
  text = "WarlockKit: put the leveling spells on your action bars?\n%s",
  button1 = YES or "Yes", button2 = NO or "No",
  OnAccept = function(self, data) Apply(data and data.force) end,
  timeout = 0, whileDead = true, hideOnEscape = true, preferredIndex = 3,
}

function M.Init() end

ns.commands.bars = function(arg)
  local cmd, rest = (arg or ""):lower():match("^(%S*)%s*(.-)$")
  if cmd == "apply" then
    local force = rest == "force"
    Preview(force)
    local text = force and "Occupied slots will be REPLACED." or "Only empty slots are filled."
    if StaticPopup_Show then
      local dialog = StaticPopup_Show("WARLOCKKIT_BARS", text)
      if dialog then dialog.data = { force = force } end
    else
      ns.Print("no confirm dialog on this client; type /wk bars yes" .. (force and " force" or "") .. " to apply.")
    end
  elseif cmd == "yes" then Apply(rest == "force")
  else Preview(false); ns.Print("type /wk bars apply to fill empty slots (asks first).") end
end

function M.Test()
  local ready, later = 0, 0
  for _, slot in ipairs(ORDER) do
    if Pick(LAYOUT[slot]) then ready = ready + 1 else later = later + 1 end
  end
  return ("layout slots=%d known=%d later=%d"):format(#ORDER, ready, later)
end
