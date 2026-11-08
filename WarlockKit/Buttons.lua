-- Buttons: one-click secure buttons for each pet summon, Create Healthstone and Create Soulstone.
-- Casting by spell name (no rank) uses the highest rank you know. Buttons for spells you have not
-- learned stay hidden; the row re-lays out out of combat when you learn something new.
-- Left-click casts. With a Healthstone/Soulstone already in your bags, the stone button uses it instead
-- (Soulstone on yourself when you have no target, or on your friendly target).
-- /wk buttons show|hide   right-drag the row to move it
local _, ns = ...
local M = { name = "buttons" }
table.insert(ns.modules, M)

local ENTRIES = {
  { key = "imp", spell = "Summon Imp" },
  { key = "void", spell = "Summon Voidwalker" },
  { key = "succ", spell = "Summon Succubus" },
  { key = "incu", spell = "Summon Incubus" },
  { key = "felh", spell = "Summon Felhunter" },
  { key = "hs", spell = "Create Healthstone", stones = ns.HEALTHSTONES },
  { key = "ss", spell = "Create Soulstone", stones = ns.SOULSTONES },
}
local row, buttons = nil, {}
local pending = false

local function Configure(btn, e)
  local info = ns.Book()[e.spell]
  btn.known = info ~= nil
  if not btn.known then return end
  btn.icon:SetTexture(ns.SpellIcon(info.id) or 136243)
  local held = e.stones and ns.FirstHeld(e.stones)
  if held then
    btn:SetAttribute("type", "item")
    btn:SetAttribute("item", "item:" .. held)
    btn.icon:SetTexture(ns.ItemIcon(held) or btn.icon:GetTexture())
  else
    btn:SetAttribute("type", "spell")
    btn:SetAttribute("spell", e.spell)
  end
  btn.count:SetText(e.stones and (ns.CountAny(e.stones) > 0 and ns.CountAny(e.stones) or "") or "")
end

local function Layout()
  if InCombatLockdown() then pending = true; return end
  pending = false
  if not ns.db.buttons.enabled then row:Hide(); return end
  local x = 0
  for i, e in ipairs(ENTRIES) do
    local btn = buttons[i]
    Configure(btn, e)
    btn:ClearAllPoints()
    if btn.known then
      btn:SetPoint("LEFT", row, "LEFT", x, 0); btn:Show(); x = x + 38
    else btn:Hide() end
  end
  row:SetWidth(math.max(x, 36))
  row:Show()
end

function M.Init()
  row = CreateFrame("Frame", "WarlockKitButtons", UIParent)
  row:SetSize(36, 36)
  row:SetPoint("CENTER", UIParent, "CENTER", -120, -230)
  ns.Movable(row, "buttons", true)
  for i, e in ipairs(ENTRIES) do
    local btn = CreateFrame("Button", "WarlockKitButton_" .. e.key, row, "SecureActionButtonTemplate")
    btn:SetSize(36, 36)
    btn:RegisterForClicks(ns.KeyDown() and "AnyDown" or "AnyUp")
    btn:RegisterForDrag("RightButton")
    btn:SetScript("OnDragStart", function() if not InCombatLockdown() and not ns.db.locked then row:StartMoving() end end)
    btn:SetScript("OnDragStop", function()
      row:StopMovingOrSizing()
      local p, _, rp, x, y = row:GetPoint(); ns.db.pos.buttons = { p, rp, x, y }
    end)
    btn.icon = btn:CreateTexture(nil, "ARTWORK"); btn.icon:SetAllPoints()
    btn.count = btn:CreateFontString(nil, "OVERLAY", "NumberFontNormal"); btn.count:SetPoint("BOTTOMRIGHT", -2, 2)
    btn:SetHighlightTexture("Interface\\Buttons\\ButtonHilight-Square", "ADD")
    btn:SetScript("OnEnter", function(s)
      GameTooltip:SetOwner(s, "ANCHOR_TOP")
      GameTooltip:SetText(e.spell)
      if e.stones then GameTooltip:AddLine("Uses the stone in your bags if you have one.", 1, 1, 1, true) end
      GameTooltip:AddLine("Right-drag to move.", 0.7, 0.7, 0.7)
      GameTooltip:Show()
    end)
    btn:SetScript("OnLeave", function() GameTooltip:Hide() end)
    btn:Hide()
    buttons[i] = btn
  end
  local soon = ns.Throttle(0.5, function() xpcall(Layout, geterrorhandler()) end)
  ns.On("SPELLS_CHANGED", soon)
  ns.On("BAG_UPDATE", soon)
  ns.On("PLAYER_REGEN_ENABLED", function() if pending then soon() end end)
  C_Timer.After(2, soon)
end

ns.commands.buttons = function(arg)
  arg = (arg or ""):lower()
  if arg == "show" then ns.db.buttons.enabled = true elseif arg == "hide" then ns.db.buttons.enabled = false end
  if InCombatLockdown() then return ns.Print("not in combat.") end
  Layout()
  ns.Print("buttons: " .. (ns.db.buttons.enabled and "shown" or "hidden"))
end

function M.Test()
  local known = {}
  for i, e in ipairs(ENTRIES) do if ns.Known(e.spell) then known[#known + 1] = e.key end end
  return "known=" .. (#known > 0 and table.concat(known, ",") or "none")
end
