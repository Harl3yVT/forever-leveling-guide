-- Alerts: a Soul Shard counter plus reminders (WeakAuras does not run on Forever).
--   Shard counter, red below the threshold (/wk shards N)
--   Pet missing or dismissed (out of combat, once you know Summon Imp)
--   Pet autocast off: Firebolt (Imp) or Torment (Voidwalker, solo only, because it taunts off a tank)
--   Demon Armor / Demon Skin missing (nil from a hidden aura = no alert)
--   No Healthstone / no Soulstone in bags once you know the Create spell
-- /wk alerts on|off   /wk shards N
local _, ns = ...
local M = { name = "alerts" }
table.insert(ns.modules, M)

local holder, shardText, lines
local warnedLow = false

local function PetAutocast()
  -- returns the name of a key pet spell whose autocast is off, or nil
  if not GetPetActionInfo or not UnitExists("pet") then return end
  local want = { ["Firebolt"] = true }
  if not IsInGroup or not IsInGroup() then want["Torment"] = true end
  for i = 1, (NUM_PET_ACTION_SLOTS or 10) do
    local r = { pcall(GetPetActionInfo, i) }
    if r[1] then
      local name = r[2]
      -- newer API: name, texture, isToken, isActive, autoCastAllowed, autoCastEnabled, spellID
      -- 1.12 API:  name, subtext, texture, isToken, isActive, autoCastAllowed, autoCastEnabled
      local allowed, enabled
      if type(r[8]) == "number" then allowed, enabled = r[6], r[7] else allowed, enabled = r[7], r[8] end
      if type(name) == "string" and want[name] and allowed and not enabled then return name end
    end
  end
end

local function ArmorMissing()
  local armor = (ns.Known("Demon Armor") and "Demon Armor") or (ns.Known("Demon Skin") and "Demon Skin")
  if not armor then return end
  local up = ns.HasAura("player", armor)
  if up == false then return armor end
end

local function Update()
  if not holder then return end
  local a = ns.db.alerts
  if not a.enabled or UnitIsDeadOrGhost("player") then holder:Hide(); return end
  holder:Show()
  local shards = ns.ItemCount(ns.SHARD)
  local low = shards < (a.shards or 0)
  shardText:SetFormattedText("%s%d|r Soul Shard%s", low and "|cffff4040" or "|cffd8b4ff", shards, shards == 1 and "" or "s")
  if low and not warnedLow and not InCombatLockdown() then
    warnedLow = true
    ns.Print(("only %d Soul Shards (target %d): finish a few kills with Drain Soul."):format(shards, a.shards))
  elseif not low then warnedLow = false end

  local msgs = {}
  local combat = InCombatLockdown()
  if a.pet and not combat and ns.Known("Summon Imp") and not UnitExists("pet") and not IsMounted() then
    msgs[#msgs + 1] = "|cffff8040No pet|r: summon your Voidwalker (or Imp)"
  end
  if a.autocast and UnitExists("pet") then
    local off = PetAutocast()
    if off then msgs[#msgs + 1] = ("|cffffd100%s autocast is off|r (ctrl-click it on the pet bar)"):format(off) end
  end
  if a.armor and not combat then
    local miss = ArmorMissing()
    if miss then msgs[#msgs + 1] = "|cffffd100" .. miss .. " is down|r" end
  end
  if a.stones and not combat then
    if ns.Known("Create Healthstone") and ns.CountAny(ns.HEALTHSTONES) == 0 then
      msgs[#msgs + 1] = "No Healthstone" .. (shards > 0 and " (Create Healthstone)" or " (need a shard)")
    end
    if ns.Known("Create Soulstone") and ns.CountAny(ns.SOULSTONES) == 0 then
      msgs[#msgs + 1] = "No Soulstone" .. (shards > 0 and " (Create Soulstone, then use it on yourself)" or " (need a shard)")
    end
  end
  for i, fs in ipairs(lines) do
    fs:SetText(msgs[i] or "")
  end
end

function M.Init()
  holder = CreateFrame("Frame", "WarlockKitAlerts", UIParent)
  holder:SetSize(260, 90)
  holder:SetPoint("CENTER", UIParent, "CENTER", 0, -170)
  ns.Movable(holder, "alerts", false)
  shardText = holder:CreateFontString(nil, "OVERLAY", "GameFontNormalLarge")
  shardText:SetPoint("TOP", 0, 0)
  lines = {}
  for i = 1, 4 do
    local fs = holder:CreateFontString(nil, "OVERLAY", "GameFontHighlight")
    fs:SetPoint("TOP", shardText, "BOTTOM", 0, -2 - (i - 1) * 15)
    lines[i] = fs
  end
  local soon = ns.Throttle(0.3, function() xpcall(Update, geterrorhandler()) end)
  for _, e in ipairs({ "BAG_UPDATE", "UNIT_PET", "PET_BAR_UPDATE", "UNIT_AURA", "PLAYER_REGEN_ENABLED",
                       "PLAYER_REGEN_DISABLED", "PLAYER_ENTERING_WORLD", "SPELLS_CHANGED", "GROUP_ROSTER_UPDATE",
                       "PLAYER_ALIVE", "PLAYER_UNGHOST" }) do
    ns.On(e, soon)
  end
  C_Timer.After(2, soon)
end

ns.commands.alerts = function(arg)
  arg = (arg or ""):lower()
  if arg == "on" or arg == "off" then ns.db.alerts.enabled = (arg == "on") end
  ns.Print("alerts: " .. (ns.db.alerts.enabled and "on" or "off"))
  Update()
end
ns.commands.shards = function(arg)
  local n = tonumber(arg)
  if n and n >= 0 and n <= 40 then ns.db.alerts.shards = math.floor(n) end
  ns.Print("low-shard warning below " .. ns.db.alerts.shards .. " (have " .. ns.ItemCount(ns.SHARD) .. ")")
  Update()
end

function M.Test()
  return ("shards=%d hs=%d ss=%d pet=%s autocastOff=%s armorMissing=%s"):format(ns.ItemCount(ns.SHARD),
    ns.CountAny(ns.HEALTHSTONES), ns.CountAny(ns.SOULSTONES), tostring(UnitExists("pet")),
    tostring(PetAutocast()), tostring(ArmorMissing()))
end
