-- HarleyLib embed: the shared addon skeleton (events, saved variables with versioned migrations, slash command
-- with a combat guard, dry-run confirmation, modules, self-test). MageKit, AltKit and WarlockKit call HarleyLib.Embed(ns, opts)
-- in their Core.lua, so a fix here lands in all three.
local L = HarleyLib
local C = L.compat

-- client APIs every self-test reports on (missing ones are listed in the status window)
L.API = { "C_Item.GetItemInfo", "C_Container.UseContainerItem", "C_Container.GetItemCooldown",
  "C_Container.GetContainerItemInfo", "C_Item.GetItemCount", "C_Item.GetItemSpell", "C_Spell.GetSpellName",
  "C_Spell.GetSpellInfo", "C_Spell.GetSpellPowerCost", "C_Spell.IsSpellInRange", "C_UnitAuras.GetAuraDataBySpellName",
  "C_SpellBook.IsSpellKnown", "IsPlayerSpell", "issecretvalue", "CombatLogGetCurrentEventInfo", "C_CVar.GetCVarBool",
  "UnitInRange", "C_SpellBook.GetNumSpellBookSkillLines", "GetNumSpellTabs", "GetTalentInfo", "LearnTalent",
  "C_ClassTalents.GetActiveConfigID", "C_Traits.PurchaseRank", "C_Spell.PickupSpell", "PickupSpell", "PickupMacro",
  "C_Item.PickupItem", "PickupAction", "PlaceAction", "GetActionInfo", "GetActionText", "HasAction", "GetCursorInfo",
  "ClearCursor", "CreateMacro", "EditMacro", "GetNumMacros", "GetMacroIndexByName", "GetMacroInfo",
  "GetBonusBarOffset", "GetShapeshiftFormInfo", "GetNumShapeshiftForms", "GetWeaponEnchantInfo",
  "GetPetActionInfo", "TogglePetAutocast", "C_MountJournal.Pickup" }

-- copy defaults into db without overwriting existing values
function L.Merge(dst, src)
  for k, v in pairs(src) do
    if type(v) == "table" then
      if type(dst[k]) ~= "table" then dst[k] = {} end
      L.Merge(dst[k], v)
    elseif dst[k] == nil then dst[k] = v end
  end
end

--[[ opts:
  name, color ("ffa500"), slash = { "/ak", "/altkit" }, slashKey = "ALTKIT", db = "AltKitDB",
  dbVersion = n, defaults = {}, migrations = { [n] = function(db) end }  -- migration n turns version n-1 into n
  enabled = function(ns) return ok, reason end   -- false: only modules/commands marked allClasses run
  help = function(ns) end                         -- prints the command list
]]
function L.Embed(ns, o)
  for k, v in pairs(C) do ns[k] = v end
  ns.lib, ns.opts = L, o
  ns.class = select(2, UnitClass("player"))
  ns.badEvents, ns.modules, ns.commands, ns.anyClass = {}, {}, {}, {}
  ns.version = C_AddOns and C_AddOns.GetAddOnMetadata and C_AddOns.GetAddOnMetadata(o.name, "Version")
    or (GetAddOnMetadata and GetAddOnMetadata(o.name, "Version")) or "?"

  function ns.Print(...) print("|cff" .. o.color .. o.name .. "|r", ...) end

  ------------------------------------------------------------------ errors
  local function Record(owner, err)
    local e = { time = date("%H:%M:%S"), msg = tostring(err):sub(1, 300), module = owner and owner.name }
    ns.lastError = e
    if owner then owner.lastError = e end
  end
  ns.RecordError = Record
  -- runs fn(...) and records an error against owner (a module) before handing it to BugGrabber
  function ns.Safe(owner, fn, ...)
    if not fn then return true end
    return xpcall(fn, function(err)
      Record(owner, err)
      local h = geterrorhandler and geterrorhandler()
      if h then pcall(h, err) end
      return err
    end, ...)
  end

  ------------------------------------------------------------------ events
  local handlers, ev = {}, CreateFrame("Frame")
  function ns.On(event, fn)
    if not handlers[event] then
      local ok = pcall(ev.RegisterEvent, ev, event)
      if not ok then ns.badEvents[event] = true; return false end
      handlers[event] = {}
    end
    table.insert(handlers[event], { fn = fn, owner = ns.current })
    return true
  end
  ev:SetScript("OnEvent", function(_, event, ...)
    for _, h in ipairs(handlers[event]) do ns.Safe(h.owner, h.fn, event, ...) end
  end)
  -- run fn at most once per `delay` seconds (coalesces bursts like UNIT_AURA)
  function ns.Throttle(delay, fn)
    local queued, owner = false, ns.current
    return function()
      if queued then return end
      queued = true
      C_Timer.After(delay, function() queued = false; ns.Safe(owner, fn) end)
    end
  end
  function ns.After(delay, fn)
    local owner = ns.current
    C_Timer.After(delay, function() ns.Safe(owner, fn) end)
  end

  local book
  function ns.Book()
    if not book then book = C.BookSpells() end
    return book
  end
  function ns.ResetBook() book = nil end
  ns.On("SPELLS_CHANGED", ns.ResetBook)

  function ns.Module(name, fields)
    local m = fields or {}
    m.name = name
    table.insert(ns.modules, m)
    return m
  end

  ------------------------------------------------------------------ saved variables
  ns.On("PLAYER_LOGIN", function()
    local db = _G[o.db]
    if type(db) ~= "table" then db = {} end
    local fresh = next(db) == nil
    local from = tonumber(db.version) or (fresh and o.dbVersion or 1)
    if from < o.dbVersion then
      for v = from + 1, o.dbVersion do
        local fn = o.migrations and o.migrations[v]
        if fn then
          local ok, err = pcall(fn, db)
          if not ok then ns.Print(("settings migration to v%d failed: %s"):format(v, tostring(err))) end
        end
      end
      if not fresh then ns.Print(("settings upgraded v%d -> v%d"):format(from, o.dbVersion)) end
    elseif from > o.dbVersion then
      ns.Print(("settings are from a newer version (v%d > v%d); left as they are"):format(from, o.dbVersion))
    end
    db.version = math.max(from, o.dbVersion)
    L.Merge(db, o.defaults or {})
    _G[o.db] = db
    ns.db = db
    local ok, why = true, nil
    if o.enabled then ok, why = o.enabled(ns) end
    ns.active, ns.inactiveReason = ok, why
    ns.skippedCmd = {}
    for _, m in ipairs(ns.modules) do
      if ok or m.allClasses then
        -- skipIf: another addon owns this job here (e.g. WarlockKit on a warlock); reported as SKIP
        local why = m.skipIf and m.skipIf()
        if why then
          m.skipped = why
          for _, c in ipairs(m.cmds or {}) do ns.skippedCmd[c] = why end
        else
          ns.current = m
          m.initialized = ns.Safe(m, m.Init)
          ns.current = nil
        end
      end
    end
  end)

  ------------------------------------------------------------------ dry-run guard
  -- A placement command first shows its preview and remembers it; the same command with the same plan
  -- within 2 minutes then applies it. Returns true when the change may go ahead.
  local pending = {}
  function ns.Confirmed(key, signature)
    local p = pending[key]
    local now = GetTime()
    if p and p.sig == signature and now - p.t < 120 then pending[key] = nil; return true end
    pending[key] = { sig = signature, t = now }
    return false
  end

  ------------------------------------------------------------------ slash command
  for i, s in ipairs(o.slash) do _G["SLASH_" .. o.slashKey .. i] = s end
  SlashCmdList[o.slashKey] = function(msg)
    local cmd, rest = (msg or ""):match("^%s*(%S*)%s*(.-)%s*$")
    cmd = cmd:lower()
    if InCombatLockdown() then return ns.Print("not in combat: try again when the fight ends.") end
    if not ns.db then return ns.Print("not loaded yet.") end
    if cmd == "test" then return ns.SelfTest(true) end
    if cmd == "status" then ns.SelfTest(false); return L.ShowStatus(ns) end
    if ns.skippedCmd and ns.skippedCmd[cmd] then return ns.Print(cmd .. " is off here: " .. ns.skippedCmd[cmd]) end
    local f = ns.commands[cmd]
    if f and (ns.active or ns.anyClass[cmd]) then return ns.Safe(nil, f, rest) end
    if not ns.active then ns.Print("inactive here: " .. tostring(ns.inactiveReason)) end
    if o.help then o.help(ns) end
    print("  " .. o.slash[1] .. " status   self-test window      " .. o.slash[1] .. " test   self-test to chat + SavedVariables")
  end

  ------------------------------------------------------------------ self-test
  -- Saves db.selftest[character] = { time, class, level, summary, modules = { [name] = { status, text, error, missing } },
  -- notes = { [name] = "PASS text" }, apiMissing = {...}, events = {...} }. /reload writes it to disk.
  function ns.SelfTest(verbose)
    local r = { time = date("%Y-%m-%d %H:%M"), addon = o.name, version = ns.version, class = ns.class,
      level = UnitLevel("player"), active = ns.active, reason = ns.inactiveReason,
      modules = {}, notes = {}, events = {}, apiMissing = {} }
    for e in pairs(ns.badEvents) do r.events[#r.events + 1] = e end
    table.sort(r.events)
    for _, a in ipairs(L.API) do if not C.HasAPI(a) then r.apiMissing[#r.apiMissing + 1] = a end end
    local n = { PASS = 0, FAIL = 0, SKIP = 0 }
    for _, m in ipairs(ns.modules) do
      local row, missing = {}, {}
      for _, a in ipairs(m.needs or {}) do if not C.HasAPI(a) then missing[#missing + 1] = a end end
      if not (ns.active or m.allClasses) then
        row.status, row.text = "SKIP", "not for " .. tostring(ns.class)
      elseif m.skipped then
        row.status, row.text = "SKIP", m.skipped
      elseif m.initialized == false then
        row.status, row.text = "FAIL", "Init failed"
      elseif m.Test then
        local ok, text, good = pcall(m.Test)
        if not ok then
          Record(m, text)
          row.status, row.text = "FAIL", "ERROR: " .. tostring(text)
        else
          row.text = tostring(text)
          row.status = (good == false or #missing > 0) and "FAIL" or "PASS"
        end
      else
        row.status, row.text = "PASS", "no test"
      end
      if #missing > 0 then row.missing = table.concat(missing, ", ") end
      if m.lastError then row.error = m.lastError.time .. " " .. m.lastError.msg end
      r.modules[m.name], r.notes[m.name] = row, row.status .. " " .. row.text
      n[row.status] = n[row.status] + 1
      r.order = r.order or {}
      r.order[#r.order + 1] = m.name
    end
    r.summary = ("%d pass, %d fail, %d skip"):format(n.PASS, n.FAIL, n.SKIP)
    r.lastError = ns.lastError
    ns.db.selftest = type(ns.db.selftest) == "table" and ns.db.selftest or {}
    ns.db.selftest[UnitName("player") or "?"] = r
    if verbose then
      ns.Print(("self-test %s: %s. Missing APIs: %s%s. /reload to write it to disk."):format(r.time, r.summary,
        #r.apiMissing > 0 and table.concat(r.apiMissing, ", ") or "none",
        #r.events > 0 and (" | blocked events: " .. table.concat(r.events, ", ")) or ""))
      for _, name in ipairs(r.order or {}) do
        local row = r.modules[name]
        print(("  %s %s: %s%s"):format(row.status == "PASS" and "|cff00ff00PASS|r" or row.status == "FAIL" and "|cffff3333FAIL|r"
          or "|cff999999SKIP|r", name, row.text, row.error and ("  |cffff8800last error: " .. row.error .. "|r") or ""))
      end
    end
    return r
  end

  ------------------------------------------------------------------ shared frames
  -- movable frame helper; secure frames only move out of combat
  function ns.Movable(frame, key, secure, lockTable)
    frame:SetMovable(true); frame:SetClampedToScreen(true); frame:EnableMouse(true)
    frame:RegisterForDrag(secure and "RightButton" or "LeftButton")
    frame:SetScript("OnDragStart", function(s)
      if secure and InCombatLockdown() then return end
      if lockTable and ns.db[lockTable] and ns.db[lockTable].locked then return end
      s:StartMoving()
    end)
    frame:SetScript("OnDragStop", function(s)
      s:StopMovingOrSizing()
      local p, _, rp, x, y = s:GetPoint()
      ns.db.pos = ns.db.pos or {}
      ns.db.pos[key] = { p, rp, x, y }
    end)
    local p = ns.db.pos and ns.db.pos[key]
    if p then frame:ClearAllPoints(); frame:SetPoint(p[1], UIParent, p[2], p[3], p[4]) end
  end

  -- small square secure icon button (rebuff, conjure, disenchant)
  function ns.IconButton(name, key, x, y)
    local btn = CreateFrame("Button", name, UIParent, "SecureActionButtonTemplate")
    btn:SetSize(36, 36)
    btn:SetPoint("CENTER", x, y)
    btn:RegisterForClicks(C.KeyDown() and "AnyDown" or "AnyUp")
    ns.Movable(btn, key, true)
    btn.icon = btn:CreateTexture(nil, "ARTWORK"); btn.icon:SetAllPoints()
    btn.count = btn:CreateFontString(nil, "OVERLAY", "NumberFontNormal"); btn.count:SetPoint("BOTTOMRIGHT", -2, 2)
    btn.who = btn:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall"); btn.who:SetPoint("TOP", btn, "BOTTOM", 0, -1)
    btn:SetHighlightTexture("Interface\\Buttons\\ButtonHilight-Square", "ADD")
    btn:SetScript("OnLeave", function() GameTooltip:Hide() end)
    return btn
  end

  return ns
end
