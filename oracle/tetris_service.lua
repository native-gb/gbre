-- Persistent live-control service for pinned headless mGBA.
-- Protocol: request-id<TAB>command<TAB>argument... followed by a newline.

local port = assert(tonumber(os.getenv("GBRE_SERVICE_PORT")),
    "missing GBRE_SERVICE_PORT")
local ready_path = assert(os.getenv("GBRE_SERVICE_READY"),
    "missing GBRE_SERVICE_READY")
local adapter_path = assert(os.getenv("GBRE_SERVICE_ADAPTER"),
    "missing GBRE_SERVICE_ADAPTER")
local rom_sha1 = assert(os.getenv("GBRE_SERVICE_ROM_SHA1"),
    "missing GBRE_SERVICE_ROM_SHA1")
local mgba_build = assert(os.getenv("GBRE_SERVICE_MGBA_BUILD"),
    "missing GBRE_SERVICE_MGBA_BUILD")

dofile(adapter_path)
assert(GBRE_TETRIS_OBSERVATION, "observation adapter did not load")
assert(emu.writeRGBAFramebuffer, "pinned mGBA lacks the raw framebuffer hook")

local server = nil
local client = nil
local receive_buffer = ""
local send_buffer = ""
local held_keys = 0
local mode = "pausing"
local frozen_state = nil
local deferred = nil
local step_remaining = 0
local step_last_frame = -1

local function json_escape(value)
    return (tostring(value):gsub('[%z\1-\31\\"]', function(character)
        local escapes = {
            ['"'] = '\\"', ['\\'] = '\\\\', ['\b'] = '\\b',
            ['\f'] = '\\f', ['\n'] = '\\n', ['\r'] = '\\r', ['\t'] = '\\t',
        }
        return escapes[character] or string.format('\\u%04x', string.byte(character))
    end))
end

local function quoted(value)
    return '"' .. json_escape(value) .. '"'
end

local function response(request_id, command, fields)
    local values = {
        '"id":' .. tostring(request_id),
        '"ok":true',
        '"command":' .. quoted(command),
    }
    for _, field in ipairs(fields or {}) do
        values[#values + 1] = field
    end
    return "{" .. table.concat(values, ",") .. "}\n"
end

local function error_response(request_id, command, message)
    return string.format(
        '{"id":%d,"ok":false,"command":%s,"error":%s}\n',
        request_id or 0, quoted(command or "invalid"), quoted(message))
end

local function flush_send()
    if not client then return end
    if #send_buffer == 0 then return end
    local sent, err = client:send(send_buffer)
    if sent then
        send_buffer = send_buffer:sub(sent + 1)
    elseif err ~= socket.ERRORS.AGAIN then
        console:error("GBRE service send failed: " .. tostring(err))
        client:close()
        client = nil
        send_buffer = ""
    end
end

local function send(text)
    send_buffer = send_buffer .. text
    flush_send()
end

local function split_line(line)
    local values = {}
    for value in (line .. "\t"):gmatch("([^\t]*)\t") do
        values[#values + 1] = value
    end
    return values
end

local function integer(value, name, minimum, maximum)
    local result = tonumber(value or "")
    if not result or result ~= math.floor(result) or result < minimum or result > maximum then
        error(string.format("%s must be an integer in %d..%d", name, minimum, maximum))
    end
    return result
end

local function synchronize_paused_state()
    if mode == "paused" and frozen_state then
        assert(emu:loadStateBuffer(frozen_state), "could not restore paused state")
    end
end

local function finish_deferred(extra_fields)
    if not deferred then return end
    send(response(deferred.id, deferred.command, extra_fields or {
        string.format('"frame":%d', emu:currentFrame()),
        '"mode":' .. quoted(mode),
    }))
    deferred = nil
end

local function defer(request_id, command)
    if deferred then error("another boundary command is still pending") end
    deferred = {id = request_id, command = command}
end

local function handle(request_id, command, arguments)
    if command == "hello" then
        send(response(request_id, command, {
            '"protocol":"gbre.mgba.v1"',
            '"rom_sha1":' .. quoted(rom_sha1),
            '"mgba_build":' .. quoted(mgba_build),
            '"title":' .. quoted(emu:getGameTitle() or ""),
            string.format('"frame":%d', emu:currentFrame()),
            '"mode":' .. quoted(mode),
        }))
    elseif command == "pause" then
        if mode == "paused" then
            send(response(request_id, command, {
                string.format('"frame":%d', emu:currentFrame()),
                '"mode":"paused"',
            }))
        else
            frozen_state = emu:saveStateBuffer()
            mode = "paused"
            send(response(request_id, command, {
                string.format('"frame":%d', emu:currentFrame()),
                '"mode":"paused"',
            }))
        end
    elseif command == "run" then
        mode = "running"
        frozen_state = nil
        send(response(request_id, command, {'"mode":"running"'}))
    elseif command == "step" then
        synchronize_paused_state()
        step_remaining = integer(arguments[1], "frame count", 1, 1000000)
        step_last_frame = emu:currentFrame()
        frozen_state = nil
        mode = "stepping"
        defer(request_id, command)
    elseif command == "reset" then
        emu:reset()
        held_keys = 0
        emu:setKeys(0)
        frozen_state = emu:saveStateBuffer()
        mode = "paused"
        send(response(request_id, command, {
            string.format('"frame":%d', emu:currentFrame()),
            '"mode":"paused"',
        }))
    elseif command == "keys" then
        held_keys = integer(arguments[1], "key mask", 0, 255)
        emu:setKeys(held_keys)
        send(response(request_id, command, {
            string.format('"mask":%d', held_keys),
        }))
    elseif command == "read" then
        synchronize_paused_state()
        local address = integer(arguments[1], "address", 0, 0xFFFF)
        local count = integer(arguments[2], "count", 1, 4096)
        if address + count > 0x10000 then error("read extends beyond address space") end
        local values = {}
        for offset = 0, count - 1 do
            values[#values + 1] = tostring(emu:read8(address + offset))
        end
        send(response(request_id, command, {
            string.format('"address":%d', address),
            '"values":[' .. table.concat(values, ",") .. ']',
        }))
    elseif command == "write" then
        synchronize_paused_state()
        local address = integer(arguments[1], "address", 0, 0xFFFF)
        local value = integer(arguments[2], "value", 0, 255)
        emu:write8(address, value)
        if mode == "paused" then frozen_state = emu:saveStateBuffer() end
        send(response(request_id, command, {
            string.format('"address":%d', address),
            string.format('"value":%d', value),
        }))
    elseif command == "observe" then
        synchronize_paused_state()
        send(response(request_id, command, {
            '"observation":' .. GBRE_TETRIS_OBSERVATION(held_keys),
        }))
    elseif command == "save" then
        synchronize_paused_state()
        local path = assert(arguments[1], "save requires path")
        assert(emu:saveStateFile(path), "mGBA could not save state")
        send(response(request_id, command, {'"path":' .. quoted(path)}))
    elseif command == "load" then
        local path = assert(arguments[1], "load requires path")
        assert(emu:loadStateFile(path), "mGBA could not load state")
        frozen_state = emu:saveStateBuffer()
        mode = "paused"
        send(response(request_id, command, {
            string.format('"frame":%d', emu:currentFrame()),
            '"mode":"paused"',
        }))
    elseif command == "capture" then
        synchronize_paused_state()
        local path = assert(arguments[1], "capture requires path")
        emu:screenshot(path)
        send(response(request_id, command, {
            '"path":' .. quoted(path),
            '"width":160',
            '"height":144',
        }))
    elseif command == "capture-raw" then
        synchronize_paused_state()
        local path = assert(arguments[1], "capture-raw requires path")
        assert(emu:writeRGBAFramebuffer(path), "could not write raw framebuffer")
        send(response(request_id, command, {
            '"path":' .. quoted(path),
            '"width":160',
            '"height":144',
            '"format":"rgba32"',
        }))
    elseif command == "shutdown" then
        send(response(request_id, command))
        if client then client:close() end
        if server then server:close() end
        os.exit(0, true)
    else
        error("unknown command " .. quoted(command))
    end
end

local function handle_line(line)
    local values = split_line(line:gsub("\r$", ""))
    local request_id = tonumber(values[1] or "")
    local command = values[2] or "invalid"
    if not request_id or request_id < 1 or request_id ~= math.floor(request_id) then
        send(error_response(0, command, "invalid request id"))
        return
    end
    local arguments = {}
    for index = 3, #values do arguments[#arguments + 1] = values[index] end
    local ok, message = pcall(handle, request_id, command, arguments)
    if not ok then send(error_response(request_id, command, message)) end
end

local function receive()
    if not client then return end
    while true do
        local chunk, err = client:receive(4096)
        if chunk then
            receive_buffer = receive_buffer .. chunk
            while true do
                local newline = receive_buffer:find("\n", 1, true)
                if not newline then break end
                handle_line(receive_buffer:sub(1, newline - 1))
                receive_buffer = receive_buffer:sub(newline + 1)
            end
        else
            if err ~= socket.ERRORS.AGAIN then
                client:close()
                client = nil
                receive_buffer = ""
            end
            return
        end
    end
end

local function accept()
    local accepted, err = server:accept()
    if not accepted then
        if err ~= socket.ERRORS.AGAIN then
            console:error("GBRE service accept failed: " .. tostring(err))
        end
        return
    end
    if client then client:close() end
    client = accepted
    receive_buffer = ""
    send_buffer = ""
    client:add("received", receive)
end

local function apply_keys()
    emu:setKeys(held_keys)
end

local function frame_boundary()
    flush_send()
    local frame = emu:currentFrame()
    if mode == "running" then return end
    if mode == "stepping" then
        if frame ~= step_last_frame then
            step_remaining = step_remaining - 1
            step_last_frame = frame
        end
        if step_remaining > 0 then return end
        frozen_state = emu:saveStateBuffer()
        mode = "paused"
        finish_deferred()
        return
    end
    if mode == "pausing" then
        frozen_state = emu:saveStateBuffer()
        mode = "paused"
        finish_deferred()
        return
    end
    if mode == "paused" and frozen_state then
        assert(emu:loadStateBuffer(frozen_state), "could not hold paused state")
    end
end

server = assert(socket.bind("127.0.0.1", port))
assert(server:listen(1))
server:add("received", accept)

local ready = assert(io.open(ready_path, "w"))
ready:write(string.format("%d\n", port))
ready:close()

callbacks:add("keysRead", apply_keys)
callbacks:add("frame", frame_boundary)
