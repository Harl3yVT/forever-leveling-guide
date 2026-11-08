-- HarleyLib seller: at a merchant, a button that sells white-quality (quality 1) armor/weapons the rules mark as
-- useless for this character. Never sells without a click; skips soulbound, locked, quest and kept items; checks
-- the slot still holds the same item before each sale; prints a summary.
-- L.Seller(ns, { buttonName=, title=, sells=function(classID, subID, equipLoc) -> bool, keepCmd="/mk keep" }) -> module
local L = HarleyLib

local function Money(c) return GetCoinTextureString and GetCoinTextureString(c) or tostring(c) end

function L.Seller(ns, o)
  local M = ns.Module("vendor", { needs = { "C_Container.UseContainerItem" } })
  local btn, list = nil, {}

  local function Scan()
    wipe(list)
    local total = 0
    ns.EachBagItem(function(bag, slot, link, quality, id, locked, _, count, bound)
      if link and quality == 1 and not locked and not bound and not ns.db.vendor.keep[id] then
        local _, _, _, _, _, _, _, _, equipLoc, _, price, classID, subID, bindType = ns.GetItemInfo(link)
        if price and price > 0 and equipLoc and equipLoc ~= "" and bindType ~= 4 and o.sells(classID, subID, equipLoc) then
          list[#list + 1] = { bag = bag, slot = slot, id = id, link = link, value = price * (count or 1) }
          total = total + price * (count or 1)
        end
      end
    end)
    return total
  end
  M.Scan, M.list = Scan, list

  local function Refresh()
    if not btn then return end
    if not (MerchantFrame and MerchantFrame:IsShown()) then btn:Hide(); return end
    local total = Scan()
    if #list == 0 then btn:Hide(); return end
    btn:SetText(("Sell %d unusable (%s)"):format(#list, Money(total)))
    btn:SetWidth(btn:GetTextWidth() + 24)
    btn:Show()
  end

  local function SellAll()
    if InCombatLockdown() then return ns.Print("not in combat.") end
    local queue = {}
    for i, it in ipairs(list) do queue[i] = it end
    local i, sold, value = 0, 0, 0
    local function step()
      i = i + 1
      local it = queue[i]
      if not it or not (MerchantFrame and MerchantFrame:IsShown()) then
        if sold > 0 then ns.Print(("sold %d unusable item%s for %s"):format(sold, sold == 1 and "" or "s", Money(value))) end
        return Refresh()
      end
      local _, _, id = ns.SlotInfo(it.bag, it.slot)
      if id == it.id then
        ns.UseItem(it.bag, it.slot)
        sold, value = sold + 1, value + it.value
        ns.Print("sold " .. it.link)
      end
      ns.After(0.15, step)
    end
    step()
  end

  function M.Init()
    if not ns.db.vendor.enabled or not MerchantFrame then return end
    btn = CreateFrame("Button", o.buttonName, MerchantFrame, "UIPanelButtonTemplate")
    btn:SetHeight(22)
    btn:SetPoint("BOTTOMRIGHT", MerchantFrame, "TOPRIGHT", 0, o.yOffset or 2)
    btn:Hide()
    btn:SetScript("OnClick", SellAll)
    btn:SetScript("OnEnter", function(s)
      GameTooltip:SetOwner(s, "ANCHOR_RIGHT")
      GameTooltip:SetText(o.title)
      for _, it in ipairs(list) do GameTooltip:AddLine(it.link) end
      GameTooltip:AddLine(o.keepCmd .. " [item] to never sell one", 0.6, 0.8, 1)
      GameTooltip:Show()
    end)
    btn:SetScript("OnLeave", function() GameTooltip:Hide() end)
    local soon = ns.Throttle(0.3, Refresh)
    ns.On("MERCHANT_SHOW", soon)
    ns.On("MERCHANT_CLOSED", function() btn:Hide() end)
    ns.On("BAG_UPDATE_DELAYED", function() if MerchantFrame and MerchantFrame:IsShown() then soon() end end)
    ns.On("GET_ITEM_INFO_RECEIVED", function() if MerchantFrame and MerchantFrame:IsShown() then soon() end end)
  end

  ns.commands.keep = function(arg)
    local id = tonumber((arg or ""):match("item:(%d+)"))
    if not id then return ns.Print("usage: " .. o.keepCmd .. " [shift-click item]") end
    ns.db.vendor.keep[id] = not ns.db.vendor.keep[id] or nil
    ns.Print((ns.db.vendor.keep[id] and "keeping " or "no longer keeping ") .. arg)
    Refresh()
  end

  function M.Test()
    local total = Scan()
    local names = {}
    for _, it in ipairs(list) do names[#names + 1] = it.link end
    return ("sellable=%d value=%d %s"):format(#list, total, table.concat(names, " "))
  end
  return M
end
