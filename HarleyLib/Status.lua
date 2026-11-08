-- HarleyLib status window: one frame listing every module of an addon with PASS/FAIL/SKIP, its self-test text,
-- its last error and any client API it needs that is missing. Reads ns.db.selftest[character] (fill it first
-- with ns.SelfTest). The same record is in SavedVariables after /reload.
local L = HarleyLib
local frames = {}

local COLORS = { PASS = "|cff00ff00", FAIL = "|cffff3333", SKIP = "|cff999999" }

local function Build(ns)
  local f = CreateFrame("Frame", ns.opts.name .. "StatusFrame", UIParent, "BackdropTemplate")
  f:SetSize(620, 200)
  f:SetPoint("CENTER")
  f:SetFrameStrata("DIALOG")
  if f.SetBackdrop then
    f:SetBackdrop({ bgFile = "Interface\\Tooltips\\UI-Tooltip-Background",
      edgeFile = "Interface\\Tooltips\\UI-Tooltip-Border", edgeSize = 14,
      insets = { left = 4, right = 4, top = 4, bottom = 4 } })
    f:SetBackdropColor(0, 0, 0, 0.9)
  end
  f:SetMovable(true); f:EnableMouse(true); f:RegisterForDrag("LeftButton")
  f:SetScript("OnDragStart", f.StartMoving)
  f:SetScript("OnDragStop", f.StopMovingOrSizing)
  f.title = f:CreateFontString(nil, "OVERLAY", "GameFontNormalLarge")
  f.title:SetPoint("TOPLEFT", 12, -10)
  local close = CreateFrame("Button", nil, f, "UIPanelCloseButton")
  close:SetPoint("TOPRIGHT", 0, 0)
  f.body = f:CreateFontString(nil, "OVERLAY", "GameFontHighlightSmall")
  f.body:SetPoint("TOPLEFT", 12, -36)
  f.body:SetWidth(596)
  f.body:SetJustifyH("LEFT"); f.body:SetJustifyV("TOP")
  if f.body.SetSpacing then f.body:SetSpacing(2) end
  tinsert(UISpecialFrames, f:GetName()) -- Escape closes it
  return f
end

function L.ShowStatus(ns)
  local r = ns.db and ns.db.selftest and ns.db.selftest[UnitName("player") or "?"]
  if not r then return ns.Print("no self-test yet") end
  local f = frames[ns] or Build(ns)
  frames[ns] = f
  f.title:SetText(("%s %s  -  %s %s %s  -  %s"):format(ns.opts.name, tostring(r.version), UnitName("player") or "?",
    tostring(r.class), tostring(r.level), r.summary or ""))
  local lines = {}
  for _, name in ipairs(r.order or {}) do
    local row = r.modules[name]
    lines[#lines + 1] = ("%s%-4s|r  |cffffd100%s|r  %s"):format(COLORS[row.status] or "", row.status, name, row.text or "")
    if row.missing then lines[#lines + 1] = "        |cffff8800missing API: " .. row.missing .. "|r" end
    if row.error then lines[#lines + 1] = "        |cffff8800last error: " .. row.error .. "|r" end
  end
  lines[#lines + 1] = " "
  lines[#lines + 1] = "Client APIs missing: " .. (#r.apiMissing > 0 and table.concat(r.apiMissing, ", ") or "none")
  if #r.events > 0 then lines[#lines + 1] = "Events this client refuses: " .. table.concat(r.events, ", ") end
  if r.lastError then
    lines[#lines + 1] = ("Last error (%s, %s): %s"):format(tostring(r.lastError.module or "core"), r.lastError.time, r.lastError.msg)
  end
  lines[#lines + 1] = ("Saved %s to %s.selftest - /reload writes it to disk."):format(r.time, ns.opts.db)
  f.body:SetText(table.concat(lines, "\n"))
  f:SetHeight(f.body:GetStringHeight() + 52)
  f:Show()
end
