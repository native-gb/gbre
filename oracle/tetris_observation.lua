-- Stable original-side observation adapter for Tetris (JUE) v1.1.
-- Loaded by the live service. Keep addresses here, outside the coordinator/UI.

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
            result[#result + 1] = string.format(
                "%02x", byte(0xC802 + row * 0x20 + column))
        end
    end
    return table.concat(result)
end

local function object(fields)
    return "{" .. table.concat(fields, ",") .. "}"
end

function GBRE_TETRIS_OBSERVATION(input_mask)
    local pc = emu:readRegister("pc") or 0
    local sp = emu:readRegister("sp") or 0
    return object({
        '"schema":"gbre.observation.v1"',
        '"side":"original"',
        '"clock":' .. object({
            string.format('"emulator_frame":%d', emu:currentFrame()),
        }),
        '"input":' .. object({
            string.format('"mask":%d', input_mask or 0),
            string.format('"held":%d', byte(0xFF80)),
            string.format('"pressed":%d', byte(0xFF81)),
        }),
        '"selection":' .. object({
            string.format('"game_type":%d', byte(0xFFC0)),
            string.format('"music_type":%d', byte(0xFFC1)),
            string.format('"type_a_level":%d', byte(0xFFC2)),
            string.format('"type_b_level":%d', byte(0xFFC3)),
            string.format('"type_b_height":%d', byte(0xFFC4)),
            string.format('"is_multiplayer":%d', byte(0xFFC5)),
        }),
        '"game":' .. object({
            string.format('"state":%d', byte(0xFFE1)),
            string.format('"frame":%d', byte(0xFFE2)),
            string.format('"demo_number":%d', byte(0xFFE4)),
            string.format('"paused":%d', byte(0xFFAB)),
            string.format('"level":%d', byte(0xFFA9)),
            string.format('"lines":%s', bytes_json(0xFF9E, 2)),
            string.format('"score":%s', bytes_json(0xC0A0, 3)),
            string.format('"pieces_played":%d', byte(0xFFB0)),
            string.format('"lock_state":%d', byte(0xFF98)),
            string.format('"board_hex":"%s"', board_hex()),
        }),
        '"piece":' .. object({
            string.format('"active":%s', bytes_json(0xC200, 4)),
            string.format('"preview":%s', bytes_json(0xC210, 4)),
            string.format('"next_preview_piece":%d', byte(0xFFAE)),
        }),
        '"timing":' .. object({
            string.format('"drop_timer":%d', byte(0xFF99)),
            string.format('"frames_per_drop":%d', byte(0xFF9A)),
            string.format('"key_repeat_timer":%d', byte(0xFFAA)),
            string.format('"timer1":%d', byte(0xFFA6)),
            string.format('"timer2":%d', byte(0xFFA7)),
            string.format('"soft_drop_counter":%d', byte(0xFFE5)),
        }),
        '"ending":' .. object({
            string.format('"text_position":%s', bytes_json(0xFFC9, 2)),
            string.format('"wipe_counter":%d', byte(0xFFE3)),
            string.format('"oam":%s', bytes_json(0xC200, 160)),
        }),
        '"audio":' .. object({
            string.format('"square_sfx":%s', bytes_json(0xDFE0, 6)),
            string.format('"wave_sfx":%s', bytes_json(0xDFF0, 6)),
            string.format('"noise_sfx":%s', bytes_json(0xDFF8, 6)),
            string.format('"pause":%s', bytes_json(0xDF7E, 2)),
            string.format('"new_music":%d', byte(0xDFE8)),
            string.format('"current_music":%d', byte(0xDFE9)),
            string.format('"pan_state":%s', bytes_json(0xDF75, 6)),
            string.format('"music_state":%s', bytes_json(0xDF90, 64)),
            string.format('"registers":%s', bytes_json(0xFF10, 23)),
        }),
        '"hardware":' .. object({
            string.format('"pc":%d', pc),
            string.format('"sp":%d', sp),
        }),
    })
end
