#!python3

import re
import argparse
import mmap
import struct
import ctypes
import yaml
from threading import Thread
from urllib import request, error
from yaml.reader import Reader as YamlReader

try:
    from yaml.cyaml import CLoader as YamlLoader
except ImportError:
    from yaml import Loader as YamlLoader

VERSION = '1.2.4'

SIM_STATUS_URL = 'http://127.0.0.1:32034/get_sim_status?object=simStatus'

MEMMAPFILE = 'Local\\IRSDKMemMapFileName'
MEMMAPFILESIZE = 1164 * 1024
BROADCASTMSGNAME = 'IRSDK_BROADCASTMSG'

VAR_TYPE_MAP = ['c', '?', 'i', 'I', 'f', 'd']

YAML_TRANSLATER = bytes.maketrans(b'\x81\x8D\x8F\x90\x9D', b'     ')
YAML_CODE_PAGE = 'cp1252'

class StatusField:
    status_connected = 1

class EngineWarnings:
    water_temp_warning    = 0x01
    fuel_pressure_warning = 0x02
    oil_pressure_warning  = 0x04
    engine_stalled        = 0x08
    pit_speed_limiter     = 0x10
    rev_limiter_active    = 0x20

class Flags:
    # global flags
    checkered        = 0x0001
    white            = 0x0002
    green            = 0x0004
    yellow           = 0x0008
    red              = 0x0010
    blue             = 0x0020
    debris           = 0x0040
    crossed          = 0x0080
    yellow_waving    = 0x0100
    one_lap_to_green = 0x0200
    green_held       = 0x0400
    ten_to_go        = 0x0800
    five_to_go       = 0x1000
    random_waving    = 0x2000
    caution          = 0x4000
    caution_waving   = 0x8000

    # drivers black flags
    black      = 0x010000
    disqualify = 0x020000
    servicible = 0x040000 # car is allowed service (not a flag)
    furled     = 0x080000
    repair     = 0x100000

    # start lights
    start_hidden = 0x10000000
    start_ready  = 0x20000000
    start_set    = 0x40000000
    start_go     = 0x80000000

class TrkLoc:
    not_in_world    = -1
    off_track       = 0
    in_pit_stall    = 1
    aproaching_pits = 2
    on_track        = 3

class TrkSurf:
    not_in_world  = -1
    undefined     =  0
    asphalt_1     =  1
    asphalt_2     =  2
    asphalt_3     =  3
    asphalt_4     =  4
    concrete_1    =  5
    concrete_2    =  6
    racing_dirt_1 =  7
    racing_dirt_2 =  8
    paint_1       =  9
    paint_2       = 10
    rumble_1      = 11
    rumble_2      = 12
    rumble_3      = 13
    rumble_4      = 14
    grass_1       = 15
    grass_2       = 16
    grass_3       = 17
    grass_4       = 18
    dirt_1        = 19
    dirt_2        = 20
    dirt_3        = 21
    dirt_4        = 22
    sand          = 23
    gravel_1      = 24
    gravel_2      = 25
    grasscrete    = 26
    astroturf     = 27

class SessionState:
    invalid     = 0
    get_in_car  = 1
    warmup      = 2
    parade_laps = 3
    racing      = 4
    checkered   = 5
    cool_down   = 6

class CameraState:
    is_session_screen       = 0x0001 # the camera tool can only be activated if viewing the session screen (out of car)
    is_scenic_active        = 0x0002 # the scenic camera is active (no focus car)

    # these can be changed with a broadcast message
    cam_tool_active         = 0x0004
    ui_hidden               = 0x0008
    use_auto_shot_selection = 0x0010
    use_temporary_edits     = 0x0020
    use_key_acceleration    = 0x0040
    use_key10x_acceleration = 0x0080
    use_mouse_aim_mode      = 0x0100

class BroadcastMsg:
    cam_switch_pos             =  0 # car position, group, camera
    cam_switch_num             =  1 # driver #, group, camera
    cam_set_state              =  2 # CameraState, unused, unused
    replay_set_play_speed      =  3 # speed, slowMotion, unused
    replay_set_play_position   =  4 # RpyPosMode, Frame Number (high, low)
    replay_search              =  5 # RpySrchMode, unused, unused
    replay_set_state           =  6 # RpyStateMode, unused, unused
    reload_textures            =  7 # ReloadTexturesMode, carIdx, unused
    chat_command               =  8 # ChatCommandMode, subCommand, unused
    pit_command                =  9 # PitCommandMode, parameter
    telem_command              = 10 # irsdk_TelemCommandMode, unused, unused
    ffb_command                = 11 # irsdk_FFBCommandMode, value (float, high, low)
    replay_search_session_time = 12 # sessionNum, sessionTimeMS (high, low)

class ChatCommandMode:
    macro      = 0 # pass in a number from 1-15 representing the chat macro to launch
    begin_chat = 1 # Open up a new chat window
    reply      = 2 # Reply to last private chat
    cancel     = 3 # Close chat window

class PitCommandMode: # this only works when the driver is in the car
    clear       =  0 # Clear all pit checkboxes
    ws          =  1 # Clean the winshield, using one tear off
    fuel        =  2 # Add fuel, optionally specify the amount to add in liters or pass '0' to use existing amount
    lf          =  3 # Change the left front tire, optionally specifying the pressure in KPa or pass '0' to use existing pressure
    rf          =  4 # right front
    lr          =  5 # left rear
    rr          =  6 # right rear
    clear_tires =  7 # Clear tire pit checkboxes
    fr          =  8 # Request a fast repair
    clear_ws    =  9 # Uncheck Clean the winshield checkbox
    clear_fr    = 10 # Uncheck request a fast repair
    clear_fuel  = 11 # Uncheck add fuel

class TelemCommandMode: # You can call this any time, but telemtry only records when driver is in there car
    stop    = 0 # Turn telemetry recording off
    start   = 1 # Turn telemetry recording on
    restart = 2 # Write current file to disk and start a new one

class RpyStateMode:
    erase_tape = 0 # clear any data in the replay tape

class ReloadTexturesMode:
    all     = 0 # reload all textuers
    car_idx = 1 # reload only textures for the specific carIdx

class RpySrchMode:
    to_start      = 0
    to_end        = 1
    prev_session  = 2
    next_session  = 3
    prev_lap      = 4
    next_lap      = 5
    prev_frame    = 6
    next_frame    = 7
    prev_incident = 8
    next_incident = 9

class RpyPosMode:
    begin   = 0
    current = 1
    end     = 2

class csMode:
    at_incident = -3
    at_leader   = -2
    at_exciting = -1

class PitSvFlags:
    lf_tire_change     = 0x01
    rf_tire_change     = 0x02
    lr_tire_change     = 0x04
    rr_tire_change     = 0x08
    fuel_fill          = 0x10
    windshield_tearoff = 0x20
    fast_repair        = 0x40

class CarLeftRight:
    clear          = 1 # no cars around us.
    car_left       = 2 # there is a car to our left.
    car_right      = 3 # there is a car to our right.
    car_left_right = 4 # there are cars on each side.
    two_cars_left  = 5 # there are two cars to our left.
    two_cars_right = 6 # there are two cars to our right.

class FFBCommandMode: # You can call this any time
    ffb_command_max_force = 0 # Set the maximum force when mapping steering torque force to direct input units (float in Nm)



class IRSDKStruct:
    @classmethod
    def property_value(cls, offset, var_type):
        struct_type = struct.Struct(var_type)
        return property(lambda self: self.get(offset, struct_type))

    @classmethod
    def property_value_str(cls, offset, var_type):
        struct_type = struct.Struct(var_type)
        return property(lambda self: self.get(offset, struct_type).strip(b'\x00').decode('latin-1'))

    def __init__(self, shared_mem, offset=0):
        self._shared_mem = shared_mem
        self._offset = offset

    def get(self, offset, struct_type):
        return struct_type.unpack_from(self._shared_mem, self._offset + offset)[0]

class Header(IRSDKStruct):
    version = IRSDKStruct.property_value(0, 'i')
    status = IRSDKStruct.property_value(4, 'i')
    tick_rate = IRSDKStruct.property_value(8, 'i')

    session_info_update = IRSDKStruct.property_value(12, 'i')
    session_info_len = IRSDKStruct.property_value(16, 'i')
    session_info_offset = IRSDKStruct.property_value(20, 'i')

    num_vars = IRSDKStruct.property_value(24, 'i')
    var_header_offset = IRSDKStruct.property_value(28, 'i')

    num_buf = IRSDKStruct.property_value(32, 'i')
    buf_len = IRSDKStruct.property_value(36, 'i')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.var_buf = [
            VarBuffer(self._shared_mem, 48 + i * 16)
            for i in range(self.num_buf)
        ]

class VarBuffer(IRSDKStruct):
    tick_count = IRSDKStruct.property_value(0, 'i')
    buf_offset = IRSDKStruct.property_value(4, 'i')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._freezed_memory = None

    def freeze(self):
        self._freezed_memory = self._shared_mem[:]

    def unfreeze(self):
        self._freezed_memory = None

    def get_memory(self):
        return self._freezed_memory or self._shared_mem

class VarHeader(IRSDKStruct):
    type = IRSDKStruct.property_value(0, 'i')
    offset = IRSDKStruct.property_value(4, 'i')
    count = IRSDKStruct.property_value(8, 'i')
    count_as_time = IRSDKStruct.property_value(12, '?')
    name = IRSDKStruct.property_value_str(16, '32s')
    desc = IRSDKStruct.property_value_str(48, '64s')
    unit = IRSDKStruct.property_value_str(112, '32s')

class IRSDK:
    def __init__(self, parse_yaml_async=False):
        self.parse_yaml_async = parse_yaml_async
        self.is_initialized = False
        self.last_session_info_update = 0

        self._shared_mem = None
        self._header = None

        self.__var_headers = None
        self.__var_headers_dict = None
        self.__var_headers_names = None
        self.__var_buffer_latest = None
        self.__session_info_dict = {}
        self.__broadcast_msg_id = None
        self.__is_using_test_file = False
        self.__workaround_connected_state = 0

    def __getitem__(self, key):
        if key in self._var_headers_dict:
            var_header = self._var_headers_dict[key]
            var_buf_latest = self._var_buffer_latest
            res = struct.unpack_from(
                VAR_TYPE_MAP[var_header.type] * var_header.count,
                var_buf_latest.get_memory(),
                var_buf_latest.buf_offset + var_header.offset)
            return res[0] if var_header.count == 1 else list(res)

        return self._get_session_info(key)

    @property
    def is_connected(self):
        if self._header:
            if self._header.status == StatusField.status_connected:
                self.__workaround_connected_state = 0
            if self.__workaround_connected_state == 0 and self._header.status != StatusField.status_connected:
                self.__workaround_connected_state = 1
            if self.__workaround_connected_state == 1 and (self['SessionNum'] is None or self.__is_using_test_file):
                self.__workaround_connected_state = 2
            if self.__workaround_connected_state == 2 and self['SessionNum'] is not None:
                self.__workaround_connected_state = 3
        return self._header is not None and \
            (self._header.status == StatusField.status_connected or self.__workaround_connected_state == 3)

    @property
    def session_info_update(self):
        return self._header.session_info_update

    @property
    def var_headers_names(self):
        if self.__var_headers_names is None:
            self.__var_headers_names = [var_header.name for var_header in self._var_headers]
        return self.__var_headers_names

    def startup(self, test_file=None, dump_to=None):
        if test_file is None and not self._check_sim_status():
            return False

        if self._shared_mem is None:
            if test_file:
                f = open(test_file, 'rb')
                self._shared_mem = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
                self.__is_using_test_file = True
            else:
                self._shared_mem = mmap.mmap(0, MEMMAPFILESIZE, MEMMAPFILE, access=mmap.ACCESS_READ)

        if self._shared_mem:
            if dump_to:
                with open(dump_to, 'wb') as f:
                    f.write(self._shared_mem)
            self._header = Header(self._shared_mem)
            self.is_initialized = self._header.version >= 1 and len(self._header.var_buf) > 0

        return self.is_initialized

    def shutdown(self):
        self.is_initialized = False
        self.last_session_info_update = 0
        if self._shared_mem:
            self._shared_mem.close()
            self._shared_mem = None
        self._header = None
        self.__var_headers = None
        self.__var_headers_dict = None
        self.__var_headers_names = None
        self.__var_buffer_latest = None
        self.__session_info_dict = {}
        self.__broadcast_msg_id = None

    def parse_to(self, to_file):
        if not self.is_initialized:
            return
        f = open(to_file, 'w', encoding='utf-8')
        f.write(self._shared_mem[self._header.session_info_offset:self._header.session_info_len].rstrip(b'\x00').decode(YAML_CODE_PAGE))
        f.write('\n'.join([
            '{:32}{}'.format(i, self[i])
            for i in sorted(self._var_headers_dict.keys(), key=str.lower)
        ]))
        f.close()

    def cam_switch_pos(self, position=0, group=1, camera=0):
        return self._broadcast_msg(BroadcastMsg.cam_switch_pos, position, group, camera)

    def cam_switch_num(self, car_number='1', group=1, camera=0):
        return self._broadcast_msg(BroadcastMsg.cam_switch_num, self._pad_car_num(car_number), group, camera)

    def cam_set_state(self, camera_state=CameraState.cam_tool_active):
        return self._broadcast_msg(BroadcastMsg.cam_set_state, camera_state)

    def replay_set_play_speed(self, speed=0, slow_motion=False):
        return self._broadcast_msg(BroadcastMsg.replay_set_play_speed, speed, 1 if slow_motion else 0)

    def replay_set_play_position(self, pos_mode=RpyPosMode.begin, frame_num=0):
        return self._broadcast_msg(BroadcastMsg.replay_set_play_position, pos_mode, frame_num)

    def replay_search(self, search_mode=RpySrchMode.to_start):
        return self._broadcast_msg(BroadcastMsg.replay_search, search_mode)

    def replay_set_state(self, state_mode=RpyStateMode.erase_tape):
        return self._broadcast_msg(BroadcastMsg.replay_set_state, state_mode)

    def reload_all_textures(self):
        return self._broadcast_msg(BroadcastMsg.reload_textures, ReloadTexturesMode.all)

    def reload_texture(self, car_idx=0):
        return self._broadcast_msg(BroadcastMsg.reload_textures, ReloadTexturesMode.car_idx, car_idx)

    def chat_command(self, chat_command_mode=ChatCommandMode.begin_chat):
        return self._broadcast_msg(BroadcastMsg.chat_command, chat_command_mode)

    def chat_command_macro(self, macro_num=0):
        return self._broadcast_msg(BroadcastMsg.chat_command, ChatCommandMode.macro, macro_num)

    def pit_command(self, pit_command_mode=PitCommandMode.clear, var=0):
        return self._broadcast_msg(BroadcastMsg.pit_command, pit_command_mode, var)

    def telem_command(self, telem_command_mode=TelemCommandMode.stop):
        return self._broadcast_msg(BroadcastMsg.telem_command, telem_command_mode)

    def ffb_command(self, ffb_command_mode=FFBCommandMode.ffb_command_max_force, value=0.0):
        return self._broadcast_msg(BroadcastMsg.ffb_command, ffb_command_mode, float(value))

    def replay_search_session_time(self, session_num=0, session_time_ms=0):
        return self._broadcast_msg(BroadcastMsg.replay_search_session_time, session_num, session_time_ms)

    def _check_sim_status(self):
        try:
            return 'running:1' in request.urlopen(SIM_STATUS_URL).read().decode('utf-8')
        except error.URLError as e:
            print("Failed to connect to sim: {}".format(e.reason))
            return False

    @property
    def _var_buffer_latest(self):
        if not self.is_initialized and not self.startup():
            return None
        if self.__var_buffer_latest:
            return self.__var_buffer_latest
        return sorted(self._header.var_buf, key=lambda v: v.tick_count)[-1]

    @property
    def _var_headers(self):
        if self.__var_headers is None:
            self.__var_headers = []
            for i in range(self._header.num_vars):
                var_header = VarHeader(self._shared_mem, self._header.var_header_offset + i * 144)
                self._var_headers.append(var_header)
        return self.__var_headers

    @property
    def _var_headers_dict(self):
        if self.__var_headers_dict is None:
            self.__var_headers_dict = {}
            for var_header in self._var_headers:
                self.__var_headers_dict[var_header.name] = var_header
        return self.__var_headers_dict

    def freeze_var_buffer_latest(self):
        self.unfreeze_var_buffer_latest()
        self.__var_buffer_latest = self._var_buffer_latest
        self.__var_buffer_latest.freeze()

    def unfreeze_var_buffer_latest(self):
        if self.__var_buffer_latest:
            self.__var_buffer_latest.unfreeze()
            self.__var_buffer_latest = None

    def get_session_info_update_by_key(self, key):
        if key in self.__session_info_dict:
            return self.__session_info_dict[key]['update']
        return None

    def _get_session_info(self, key):
        if self.last_session_info_update < self._header.session_info_update:
            self.last_session_info_update = self._header.session_info_update
            for session_data in self.__session_info_dict.values():
                # keep previous parsed data, in case binary data not changed
                if session_data['data']:
                    session_data['data_last'] = session_data['data']
                session_data['data'] = None

        if key not in self.__session_info_dict:
            self.__session_info_dict[key] = dict(data=None)

        session_data = self.__session_info_dict[key]

        # already have and parsed
        if session_data['data']:
            return session_data['data']

        if self.parse_yaml_async:
            if 'async_session_info_update' not in session_data or session_data['async_session_info_update'] < self.last_session_info_update:
                session_data['async_session_info_update'] = self.last_session_info_update
                Thread(target=self._parse_yaml, args=(key, session_data)).start()
        else:
            self._parse_yaml(key, session_data)
        return session_data['data']

    def _parse_yaml(self, key, session_data):
        session_info_update = self.last_session_info_update

        start = self._header.session_info_offset
        end = self._header.session_info_len

        # search section by key
        self._shared_mem.seek(0)
        start = self._shared_mem.find(('\n%s:\n' % key).encode(YAML_CODE_PAGE), start, end)
        match_end = re.compile(rb'\n\w').search(self._shared_mem, start + 1, end)
        if match_end:
            end = match_end.start()
        data_binary = self._shared_mem[start:end]

        # section not found
        if not data_binary:
            if 'data_last' in session_data:
                return session_data['data_last']
            else:
                return None

        # is binary data the same as last time?
        if 'data_binary' in session_data and data_binary == session_data['data_binary'] and 'data_last' in session_data:
            session_data['data'] = session_data['data_last']
            return session_data['data']
        session_data['data_binary'] = data_binary

        # parsing
        yaml_src = re.sub(YamlReader.NON_PRINTABLE, '', data_binary.translate(YAML_TRANSLATER).rstrip(b'\x00').decode(YAML_CODE_PAGE))
        if key == 'DriverInfo':
            def name_replace(m):
                return m.group(1) + '"%s"' % re.sub(r'(["\\])', r'\\\1', m.group(2))
            yaml_src = re.sub(r'((?:UserName|TeamName|AbbrevName|Initials): )(.*)', name_replace, yaml_src)
        if key == 'WeekendInfo':
            yaml_src = re.sub(r'(Date: )(.*)', r'\1"\2"', yaml_src)
        result = yaml.load(yaml_src, Loader=YamlLoader)
        # check if result is available, and yaml data is not updated while we were parsing it in async mode
        if result and (not self.parse_yaml_async or self.last_session_info_update == session_info_update):
            session_data['data'] = result[key]
            if session_data['data']:
                session_data['update'] = session_info_update
            elif 'data_last' in session_data:
                session_data['data'] = session_data['data_last']

    @property
    def _broadcast_msg_id(self):
        if self.__broadcast_msg_id is None:
            self.__broadcast_msg_id = ctypes.windll.user32.RegisterWindowMessageW(BROADCASTMSGNAME)
        return self.__broadcast_msg_id

    def _broadcast_msg(self, broadcast_type=0, var1=0, var2=0, var3=0):
        if isinstance(var2, float):
            var2 = int(var2 * 65536.0)
        return ctypes.windll.user32.SendNotifyMessageW(0xFFFF, self._broadcast_msg_id,
            broadcast_type | var1 << 16, var2 | var3 << 16)

    def _pad_car_num(self, num):
        num = str(num)
        num_len = len(num)
        zero = num_len - len(num.lstrip("0"))
        if zero > 0 and num_len == zero:
            zero -= 1
        num = int(num)
        if zero:
            num_place = 3 if num > 99 else 2 if num > 9 else 1
            return num + 1000 * (num_place + zero)
        return num

class IBT:
    def __init__(self):
        self.buffers_length = 0

        self._ibt_file = None
        self._shared_mem = None
        self._header = None

        self.__var_headers = None
        self.__var_headers_dict = None
        self.__var_headers_names = None
        self.__session_info_dict = None

    def __getitem__(self, key):
        return self.get(self.buffers_length - 1, key)

    @property
    def file_name(self):
        return self._ibt_file and self._ibt_file.name

    @property
    def var_header_buffer_tick(self):
        return self._header and self._header.var_buf[0].tick_count

    @property
    def var_headers_names(self):
        if not self._header:
            return None
        if self.__var_headers_names is None:
            self.__var_headers_names = [var_header.name for var_header in self._var_headers]
        return self.__var_headers_names

    def open(self, ibt_file):
        self._ibt_file = open(ibt_file, 'rb')
        self._shared_mem = mmap.mmap(self._ibt_file.fileno(), 0, access=mmap.ACCESS_READ)
        self._header = Header(self._shared_mem)
        self.buffers_length = int((self._shared_mem.size() - self._header.var_buf[0].buf_offset) / self._header.buf_len)

    def close(self):
        if self._shared_mem:
            self._shared_mem.close()

        if self._ibt_file:
            self._ibt_file.close()

        self.buffers_length = 0

        self._ibt_file = None
        self._shared_mem = None
        self._header = None

        self.__var_headers = None
        self.__var_headers_dict = None
        self.__var_headers_names = None
        self.__session_info_dict = None

    def get(self, index, key):
        if not self._header:
            return None
        if 0 > index >= self.buffers_length:
            return None
        if key in self._var_headers_dict:
            var_header = self._var_headers_dict[key]
            fmt = VAR_TYPE_MAP[var_header.type] * var_header.count
            var_offset = var_header.offset + self._header.var_buf[0].buf_offset + index * self._header.buf_len
            res = struct.unpack_from(fmt, self._shared_mem, var_offset)
            return res[0] if var_header.count == 1 else list(res)
        return None

    def get_all(self, key):
        if not self._header:
            return None
        if key in self._var_headers_dict:
            var_header = self._var_headers_dict[key]
            fmt = VAR_TYPE_MAP[var_header.type] * var_header.count
            var_offset = var_header.offset + self._header.var_buf[0].buf_offset
            buf_len = self._header.buf_len
            sigle_or_array = var_header.count == 1
            results = []
            for i in range(self.buffers_length):
                res = struct.unpack_from(fmt, self._shared_mem, var_offset + i * buf_len)
                results.append(res[0] if sigle_or_array else list(res))
            return results
        return None

    @property
    def _var_headers(self):
        if not self._header:
            return None
        if self.__var_headers is None:
            self.__var_headers = []
            for i in range(self._header.num_vars):
                var_header = VarHeader(self._shared_mem, self._header.var_header_offset + i * 144)
                self._var_headers.append(var_header)
        return self.__var_headers

    @property
    def _var_headers_dict(self):
        if not self._header:
            return None
        if self.__var_headers_dict is None:
            self.__var_headers_dict = {}
            for var_header in self._var_headers:
                self.__var_headers_dict[var_header.name] = var_header
        return self.__var_headers_dict

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--version', action='version', version='Python iRacing SDK %s' % VERSION, help='show version and exit')
    parser.add_argument('--test', help='use test file as irsdk mmap')
    parser.add_argument('--dump', help='dump irsdk mmap to file')
    parser.add_argument('--parse', help='parse current irsdk mmap to file')
    args = parser.parse_args()

    ir = IRSDK()
    ir.startup(test_file=args.test, dump_to=args.dump)

    if args.parse:
        ir.parse_to(args.parse)

if __name__ == '__main__':
    main()
