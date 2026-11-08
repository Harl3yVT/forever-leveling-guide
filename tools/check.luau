-- Syntax check: compiles every .lua file given (or every .lua under the given folders) with Luau.
--   lune run tools/check.luau <file-or-folder> ...
-- Prints one line per failure and "N files, M failed"; exits 1 when anything fails.
-- Luau accepts all Lua 5.1 syntax WoW uses, so a compile error here is a load error in game.
local fs = require("@lune/fs")
local luau = require("@lune/luau")
local process = require("@lune/process")

local files = {}
local function walk(path)
	if fs.isDir(path) then
		for _, name in fs.readDir(path) do
			walk(path .. "/" .. name)
		end
	elseif string.sub(path, -4) == ".lua" then
		table.insert(files, path)
	end
end
for _, arg in process.args do
	walk(arg)
end
table.sort(files)

local failed = 0
for _, f in files do
	local ok, err = pcall(luau.compile, fs.readFile(f))
	if not ok then
		failed += 1
		print("FAIL " .. f .. ": " .. tostring(err))
	end
end
print(`{#files} files, {failed} failed`)
if failed > 0 then
	process.exit(1)
end
