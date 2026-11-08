-- Talents: one-click "spend next point" following the Affliction/Voidwalker leveling plan (see notes/warlock-research.md).
-- Never spends on its own: shows the next talent and a Spend button when you have a free point, out of combat.
-- Works with the classic talent API (GetTalentInfo/LearnTalent) or the newer C_Traits API, whichever the client has
-- (same code paths as PriestKit). Talents not found by name are skipped.
-- /wk talents        show/hide the helper
-- /wk talents test   print which API was found and the next planned talent
-- /wk talents on|off
local _, ns = ...
local M = { name = "talents" }
table.insert(ns.modules, M)

-- Plan in order: each step raises a talent to an absolute rank ("max" = the talent's max rank).
local PLAN = {
  { "Improved Corruption", 5 },    -- 10-14
  { "Suppression", 5 },            -- 15-19
  { "Unholy Power", 5 },           -- 20-24
  { "Demonic Energies", 2 },       -- 25-26
  { "Improved Drains", 3 },        -- 27-29
  { "Amplify Curse", 1 },          -- 30
  { "Improved Bane of Agony", 2 }, -- 31-32
  { "Improved Life Tap", 2 },      -- 33-34
  { "Pandemic", 3 },               -- 35-37
  { "Soul Siphon", 3 },            -- 38-40
  { "Siphon Life", 1 },            -- 41
  { "Malevolence", 5 },            -- 42-46
  { "Shadow Mastery", 5 },
  { "Fel Concentration", 3 },
  { "Nightfall", 2 },
}

local frame

------------------------------------------------------------------ API layer (copied from PriestKit)
-- Each backend returns: talents = { [name] = { rank=, max=, spend=function() } }, unspent
local function Classic()
  if not (GetNumTalentTabs and GetTalentInfo and LearnTalent) then return end
  local t = {}
  for tab = 1, GetNumTalentTabs() do
    for i = 1, (GetNumTalents and GetNumTalents(tab) or 0) do
      local name, _, _, _, rank, max = GetTalentInfo(tab, i)
      if name then t[name] = { rank = rank or 0, max = max or 0, spend = function() LearnTalent(tab, i) end } end
    end
  end
  local unspent = UnitCharacterPoints and UnitCharacterPoints("player") or 0
  return t, unspent, "classic"
end

local function Traits()
  if not (C_ClassTalents and C_ClassTalents.GetActiveConfigID and C_Traits and C_Traits.GetConfigInfo) then return end
  local configID = C_ClassTalents.GetActiveConfigID()
  if not configID then return end
  local cfg = C_Traits.GetConfigInfo(configID)
  local treeID = cfg and cfg.treeIDs and cfg.treeIDs[1]
  if not treeID then return end
  local t = {}
  for _, nodeID in ipairs(C_Traits.GetTreeNodes(treeID) or {}) do
    local node = C_Traits.GetNodeInfo(configID, nodeID)
    if node and node.entryIDs and #node.entryIDs == 1 then
      local entry = C_Traits.GetEntryInfo(configID, node.entryIDs[1])
      local def = entry and entry.definitionID and C_Traits.GetDefinitionInfo(entry.definitionID)
      local name = def and (def.overrideName or (def.spellID and ns.SpellName(def.spellID)))
      if name then
        t[name] = { rank = node.currentRank or node.activeRank or 0, max = node.maxRanks or 0,
          spend = function()
            if C_Traits.PurchaseRank(configID, nodeID) then C_ClassTalents.CommitConfig(configID) end
          end }
      end
    end
  end
  local unspent = 0
  if C_Traits.GetTreeCurrencyInfo then
    for _, c in ipairs(C_Traits.GetTreeCurrencyInfo(configID, treeID, false) or {}) do
      unspent = unspent + (c.quantity or 0)
    end
  end
  return t, unspent, "traits"
end

local function Read()
  local ok, t, unspent, kind = pcall(Classic)
  if ok and t and next(t) then return t, unspent, kind end
  ok, t, unspent, kind = pcall(Traits)
  if ok and t and next(t) then return t, unspent, kind end
  return nil, 0, "none"
end

-- Next planned talent: the first plan step whose talent is below its target rank.
-- Returns name, talent, rank after this point, step target, list of plan names not found.
local function Next(t)
  local skipped = {}
  for _, step in ipairs(PLAN) do
    local name, want = step[1], step[2]
    local cur = t[name]
    if not cur then
      skipped[#skipped + 1] = name
    else
      local target = want == "max" and cur.max or want
      if cur.max and cur.max > 0 and target > cur.max then target = cur.max end
      if cur.rank < target then return name, cur, cur.rank + 1, target, skipped end
    end
  end
  return nil, nil, nil, nil, skipped
end

local function Describe(t)
  local name, cur, nextRank, target, skipped = Next(t or {})
  local s = name and ("%s %d/%d (plan step to %d)"):format(name, nextRank, cur.max, target) or "plan complete"
  if #skipped > 0 then s = s .. " | not found: " .. table.concat(skipped, ", ") end
  return s
end

------------------------------------------------------------------ UI
local function Update()
  if not frame then return end
  if not ns.db.talents.enabled or InCombatLockdown() then frame:Hide(); return end
  local t, unspent = Read()
  if not t or (unspent or 0) < 1 then frame:Hide(); return end
  local name, cur, nextRank = Next(t)
  if not name then frame:Hide(); return end
  frame.next = cur
  frame.text:SetFormattedText("Next talent: |cffffd100%s|r %d/%d  (%d free)", name, nextRank, cur.max, unspent)
  frame.btn:Enable()
  frame:Show()
end

function M.Init()
  ns.db.talents = ns.db.talents or {}
  if ns.db.talents.enabled == nil then ns.db.talents.enabled = true end

  frame = CreateFrame("Frame", "WarlockKitTalents", UIParent, "BackdropTemplate")
  frame:SetSize(330, 54)
  frame:SetPoint("TOP", UIParent, "TOP", 0, -120)
  if frame.SetBackdrop then
    frame:SetBackdrop({ bgFile = "Interface\\Tooltips\\UI-Tooltip-Background",
      edgeFile = "Interface\\Tooltips\\UI-Tooltip-Border", edgeSize = 12,
      insets = { left = 3, right = 3, top = 3, bottom = 3 } })
    frame:SetBackdropColor(0, 0, 0, 0.8)
  end
  ns.Movable(frame, "talents", false, false)
  frame.text = frame:CreateFontString(nil, "OVERLAY", "GameFontHighlight")
  frame.text:SetPoint("TOPLEFT", 10, -8); frame.text:SetPoint("TOPRIGHT", -10, -8); frame.text:SetJustifyH("LEFT")
  frame.btn = CreateFrame("Button", nil, frame, "UIPanelButtonTemplate")
  frame.btn:SetSize(80, 20); frame.btn:SetPoint("BOTTOMLEFT", 8, 6); frame.btn:SetText("Spend")
  frame.btn:SetScript("OnClick", function()
    if InCombatLockdown() or not frame.next then return end
    local ok, err = pcall(frame.next.spend)
    if not ok then ns.Print("talent spend failed: " .. tostring(err)) end
    C_Timer.After(0.5, function()
      Update()
      ns.Print("next talent: " .. Describe((Read())))
    end)
  end)
  local close = CreateFrame("Button", nil, frame, "UIPanelButtonTemplate")
  close:SetSize(60, 20); close:SetPoint("BOTTOMRIGHT", -8, 6); close:SetText("Later")
  close:SetScript("OnClick", function() frame:Hide() end)
  frame:Hide()

  local ev = CreateFrame("Frame")
  for _, e in ipairs({ "PLAYER_LEVEL_UP", "CHARACTER_POINTS_CHANGED", "PLAYER_REGEN_ENABLED",
                       "PLAYER_ENTERING_WORLD", "TRAIT_CONFIG_UPDATED" }) do
    pcall(ev.RegisterEvent, ev, e)
  end
  ev:SetScript("OnEvent", function() C_Timer.After(1, function() xpcall(Update, geterrorhandler) end) end)
end

ns.commands.talents = function(arg)
  arg = (arg or ""):lower()
  if arg == "test" then ns.Print(M.Test())
  elseif arg == "off" then ns.db.talents.enabled = false; Update()
  elseif arg == "on" then ns.db.talents.enabled = true; Update()
  else
    if frame:IsShown() then frame:Hide() else
      Update()
      if not frame:IsShown() then ns.Print("no free talent point. Next: " .. Describe((Read()))) end
    end
  end
end

function M.Test()
  local t, unspent, kind = Read()
  local n = 0; for _ in pairs(t or {}) do n = n + 1 end
  -- every plan talent the tree does not have by that name (checks the plan names on Forever)
  local missing, seen = {}, {}
  for _, step in ipairs(PLAN) do
    if t and not t[step[1]] and not seen[step[1]] then seen[step[1]] = true; missing[#missing + 1] = step[1] end
  end
  return ("api=%s talents=%d free=%s next=%s planNotInTree=%s"):format(kind, n, tostring(unspent), Describe(t),
    #missing > 0 and table.concat(missing, ", ") or "none")
end
