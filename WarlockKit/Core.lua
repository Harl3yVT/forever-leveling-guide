-- WarlockKit core. The generic parts (client compat, events, versioned settings, slash command with a combat guard,
-- self-test + /wk status window, movable frames) come from HarleyLib, the shared core MageKit and AltKit use too,
-- so a Forever client fix made there lands here as well. This file only holds the warlock data and settings.
local _, ns = ...
BINDING_HEADER_WARLOCKKIT = "WarlockKit"
_G["BINDING_NAME_CLICK WarlockKitButton_void:LeftButton"] = "Summon Voidwalker"
_G["BINDING_NAME_CLICK WarlockKitButton_hs:LeftButton"] = "Create / use Healthstone"
_G["BINDING_NAME_CLICK WarlockKitButton_ss:LeftButton"] = "Create / use Soulstone"

HarleyLib.Embed(ns, {
  name = "WarlockKit", color = "9482c9", slash = { "/wk", "/warlockkit" }, slashKey = "WARLOCKKIT", db = "WarlockKitDB",
  dbVersion = 2,
  defaults = {
    alerts = { enabled = true, shards = 3, stones = true, armor = true, pet = true, autocast = true },
    buttons = { enabled = true },
    talents = { enabled = true },
    bars = { chars = {} },
    ui = { locked = false },
    pos = {},
  },
  migrations = {
    -- v2 (HarleyLib port): the lock moved to db.ui.locked; self-test rows are now per character
    [2] = function(db)
      if db.locked ~= nil then db.ui = { locked = db.locked and true or false }; db.locked = nil end
      if type(db.selftest) == "table" and db.selftest.time then db.selftest = nil end
    end,
  },
  enabled = function()
    if ns.class == "WARLOCK" then return true end
    return false, "only active on warlocks"
  end,
  help = function()
    ns.Print("commands:")
    print("  /wk shards N        - warn when Soul Shards drop below N (now " .. tostring(ns.db.alerts.shards) .. ")")
    print("  /wk alerts on|off   - shard / pet / autocast / armor / stone reminders")
    print("  /wk buttons show|hide - pet summon + Healthstone/Soulstone buttons (right-drag to move)")
    print("  /wk lock|unlock     - lock frame positions")
    print("  /wk talents [test|on|off] - next talent from the Affliction leveling plan")
    print("  /wk bars            - preview the leveling hotbar layout; /wk bars apply asks before changing anything")
  end,
})

ns.isWarlock = ns.class == "WARLOCK"
function ns.Known(name) return ns.Book()[name] ~= nil end
function ns.Locked() return ns.db.ui.locked end

-- frames lock through db.ui unless a module passes its own lock table (false = never locked)
local libMovable = ns.Movable
function ns.Movable(frame, key, secure, lockTable)
  if lockTable == nil then lockTable = "ui" end
  return libMovable(frame, key, secure, lockTable)
end

ns.commands.lock = function() ns.db.ui.locked = true; ns.Print("frames locked.") end
ns.commands.unlock = function() ns.db.ui.locked = false; ns.Print("frames unlocked (buttons: right-drag).") end

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
