-- Deterministic semantic trace adapter for Tetris (JUE) v1.1.
-- Configuration is passed through GBRE_ORACLE_* environment variables.

local input_path = assert(os.getenv("GBRE_ORACLE_INPUT"), "missing GBRE_ORACLE_INPUT")
local output_path = assert(os.getenv("GBRE_ORACLE_OUTPUT"), "missing GBRE_ORACLE_OUTPUT")
local frame_limit = assert(tonumber(os.getenv("GBRE_ORACLE_FRAMES")), "missing GBRE_ORACLE_FRAMES")
local rom_sha1 = assert(os.getenv("GBRE_ORACLE_ROM_SHA1"), "missing GBRE_ORACLE_ROM_SHA1")
local patch_path = os.getenv("GBRE_ORACLE_PATCHES")
local forced_music_id = tonumber(os.getenv("GBRE_ORACLE_MUSIC_ID") or "")
local forced_music_frame = tonumber(os.getenv("GBRE_ORACLE_MUSIC_FRAME") or "700")

local key_bits = {
    A = 1 << 0,
    B = 1 << 1,
    SELECT = 1 << 2,
    START = 1 << 3,
    RIGHT = 1 << 4,
    LEFT = 1 << 5,
    UP = 1 << 6,
    DOWN = 1 << 7,
    NONE = 0,
}

local function trim(value)
    return value:match("^%s*(.-)%s*$")
end

local function parse_keys(text, line_number)
    local result = 0
    text = trim(text):upper()
    if text == "" or text == "NONE" then
        return result
    end
    for name in text:gmatch("[^+|%s]+") do
        local bit = key_bits[name]
        assert(bit, string.format("unknown key '%s' on input line %d", name, line_number))
        result = result | bit
    end
    return result
end

local function load_input_events(path)
    local events = {}
    local previous_frame = -1
    local line_number = 0
    for line in io.lines(path) do
        line_number = line_number + 1
        local content = trim(line:gsub("#.*$", ""))
        if content ~= "" then
            local frame_text, keys_text = content:match("^([^,]+),?(.*)$")
            local frame = tonumber(trim(frame_text))
            assert(frame and frame >= 0 and frame == math.floor(frame),
                string.format("invalid frame on input line %d", line_number))
            assert(frame > previous_frame,
                string.format("input frames must increase on line %d", line_number))
            events[#events + 1] = {
                frame = frame,
                keys = parse_keys(keys_text, line_number),
            }
            previous_frame = frame
        end
    end
    return events
end

local function load_patches(path)
    local patches = {}
    if not path or path == "" then
        return patches
    end
    local previous_frame = -1
    local line_number = 0
    for line in io.lines(path) do
        line_number = line_number + 1
        local content = trim(line:gsub("#.*$", ""))
        if content ~= "" then
            local frame_text, address_text, value_text =
                content:match("^([^,]+),([^,]+),([^,]+)$")
            local frame = tonumber(trim(frame_text or ""))
            local address = tonumber(trim(address_text or ""))
            local value = tonumber(trim(value_text or ""))
            assert(frame and frame >= 0 and frame == math.floor(frame),
                string.format("invalid patch frame on line %d", line_number))
            assert(frame >= previous_frame,
                string.format("patch frames must not decrease on line %d", line_number))
            assert(address and address >= 0 and address <= 0xFFFF,
                string.format("invalid patch address on line %d", line_number))
            assert(value and value >= 0 and value <= 0xFF,
                string.format("invalid patch value on line %d", line_number))
            patches[#patches + 1] = {frame = frame, address = address, value = value}
            previous_frame = frame
        end
    end
    return patches
end

local function byte(address)
    return emu:read8(address)
end

local function bytes_json(address, count)
    local values = {}
    for index = 0, count - 1 do
        values[#values + 1] = tostring(byte(address + index))
    end
    return "[" .. table.concat(values, ",") .. "]"
end

local function board_hex()
    local result = {}
    for row = 0, 17 do
        for column = 0, 9 do
            result[#result + 1] = string.format("%02x", byte(0xC802 + row * 0x20 + column))
        end
    end
    return table.concat(result)
end

local input_events = load_input_events(input_path)
local patches = load_patches(patch_path)
local next_event = 1
local next_patch = 1
local held_keys = 0
local output = assert(io.open(output_path, "w"))
local frames_written = 0
local forced_music_applied = false

output:write(string.format(
    '{"kind":"metadata","schema":"gbre.tetris.oracle.v2","rom_sha1":"%s","frame_limit":%d}\n',
    rom_sha1, frame_limit))

local function apply_input()
    local frame = emu:currentFrame()
    while next_event <= #input_events and input_events[next_event].frame <= frame do
        held_keys = input_events[next_event].keys
        next_event = next_event + 1
    end
    while next_patch <= #patches and patches[next_patch].frame <= frame do
        emu:write8(patches[next_patch].address, patches[next_patch].value)
        next_patch = next_patch + 1
    end
    if forced_music_id and not forced_music_applied and frame >= forced_music_frame then
        assert(forced_music_id >= 1 and forced_music_id <= 17,
            "forced music ID must be in 1..17")
        emu:write8(0xDFE8, forced_music_id)
        forced_music_applied = true
    end
    emu:setKeys(held_keys)
end

local function write_snapshot()
    local frame = emu:currentFrame()
    local pc = emu:readRegister("pc") or 0
    local sp = emu:readRegister("sp") or 0
    local fields = {
        string.format('"kind":"frame"'),
        string.format('"frame":%d', frame),
        string.format('"pc":%d', pc),
        string.format('"sp":%d', sp),
        string.format('"input_mask":%d', held_keys),
        string.format('"joy_held":%d', byte(0xFF80)),
        string.format('"joy_pressed":%d', byte(0xFF81)),
        string.format('"game_state":%d', byte(0xFFE1)),
        string.format('"game_frame":%d', byte(0xFFE2)),
        string.format('"demo_number":%d', byte(0xFFE4)),
        string.format('"game_type":%d', byte(0xFFC0)),
        string.format('"music_type":%d', byte(0xFFC1)),
        string.format('"type_a_level":%d', byte(0xFFC2)),
        string.format('"type_b_level":%d', byte(0xFFC3)),
        string.format('"type_b_height":%d', byte(0xFFC4)),
        string.format('"is_multiplayer":%d', byte(0xFFC5)),
        string.format('"paused":%d', byte(0xFFAB)),
        string.format('"drop_timer":%d', byte(0xFF99)),
        string.format('"frames_per_drop":%d', byte(0xFF9A)),
        string.format('"lines":%s', bytes_json(0xFF9E, 2)),
        string.format('"level":%d', byte(0xFFA9)),
        string.format('"key_repeat_timer":%d', byte(0xFFAA)),
        string.format('"timer1":%d', byte(0xFFA6)),
        string.format('"timer2":%d', byte(0xFFA7)),
        string.format('"ending_text_position":%s', bytes_json(0xFFC9, 2)),
        string.format('"wipe_counter":%d', byte(0xFFE3)),
        string.format('"soft_drop_counter":%d', byte(0xFFE5)),
        string.format('"next_preview_piece":%d', byte(0xFFAE)),
        string.format('"pieces_played":%d', byte(0xFFB0)),
        string.format('"lock_state":%d', byte(0xFF98)),
        string.format('"score":%s', bytes_json(0xC0A0, 3)),
        string.format('"line_statistics":%s', bytes_json(0xC0AC, 16)),
        string.format('"soft_drop_points":%s', bytes_json(0xC0C0, 5)),
        string.format('"scoreboard_state":%d', byte(0xC0C5)),
        string.format('"active":%s', bytes_json(0xC200, 4)),
        string.format('"preview":%s', bytes_json(0xC210, 4)),
        string.format('"ending_oam":%s', bytes_json(0xC200, 160)),
        string.format('"square_sfx":%s', bytes_json(0xDFE0, 6)),
        string.format('"wave_sfx":%s', bytes_json(0xDFF0, 6)),
        string.format('"noise_sfx":%s', bytes_json(0xDFF8, 6)),
        string.format('"pause_audio":%s', bytes_json(0xDF7E, 2)),
        string.format('"new_music":%d', byte(0xDFE8)),
        string.format('"current_music":%d', byte(0xDFE9)),
        string.format('"pan_state":%s', bytes_json(0xDF75, 6)),
        string.format('"music_state":%s', bytes_json(0xDF90, 64)),
        string.format('"audio_registers":%s', bytes_json(0xFF10, 23)),
        string.format('"board":"%s"', board_hex()),
    }
    output:write("{" .. table.concat(fields, ",") .. "}\n")
    frames_written = frames_written + 1
    if frames_written >= frame_limit then
        output:flush()
        output:close()
        os.exit(0, true)
    end
end

callbacks:add("keysRead", apply_input)
callbacks:add("frame", write_snapshot)
