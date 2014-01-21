#!python3

import argparse
import mmap
import struct
import ctypes
import yaml
from urllib import request

try:
    from yaml.cyaml import CLoader as YamlLoader
except ImportError:
    from yaml import Loader as YamlLoader

VERSION = '1.0.1'

SIM_STATUS_URL = 'http://127.0.0.1:32034/get_sim_status?object=simStatus'

MEMMAPFILE = 'Local\\IRSDKMemMapFileName'
MEMMAPFILESIZE = 780 * 1024
BROADCASTMSGNAME = 'IRSDK_BROADCASTMSG'

VAR_TYPE_MAP = ['c', '?', 'i', 'I', 'f', 'd']

class StatusField:
    STATUS_CONNECTED = 1

class EngineWarnings:
    WATER_TEMP_WARNING    = 0x01
    FUEL_PRESSURE_WARNING = 0x02
    OIL_PRESSURE_WARNING  = 0x04
    ENGINE_STALLED        = 0x08
    PIT_SPEED_LIMITER     = 0x10
    REV_LIMITER_ACTIVE    = 0x20

class Flags:
    # global flags
    CHECKERED        = 0x00000001
    WHITE            = 0x00000002
    GREEN            = 0x00000004
    YELLOW           = 0x00000008
    RED              = 0x00000010
    BLUE             = 0x00000020
    DEBRIS           = 0x00000040
    CROSSED          = 0x00000080
    YELLOW_WAVING    = 0x00000100
    ONE_LAP_TO_GREEN = 0x00000200
    GREEN_HELD       = 0x00000400
    TEN_TO_GO        = 0x00000800
    FIVE_TO_GO       = 0x00001000
    RANDOM_WAVING    = 0x00002000
    CAUTION          = 0x00004000
    CAUTION_WAVING   = 0x00008000

    # drivers black flags
    BLACK      = 0x00010000
    DISQUALIFY = 0x00020000
    SERVICIBLE = 0x00040000 # car is allowed service (not a flag)
    FURLED     = 0x00080000
    REPAIR     = 0x00100000

    # start lights
    START_HIDDEN = 0x10000000
    START_READY  = 0x20000000
    START_SET    = 0x40000000
    START_GO     = 0x80000000

class TrkLoc:
    NOT_IN_WORLD    = -1
    OFF_TRACK       = 0
    IN_PIT_STALL    = 1
    APROACHING_PITS = 2
    ON_TRACK        = 3

class SessionState:
    INVALID     = 0
    GET_IN_CAR  = 1
    WARMUP      = 2
    PARADE_LAPS = 3
    RACING      = 4
    CHECKERED   = 5
    COOL_DOWN   = 6

class CameraState:
    IS_SESSION_SCREEN       = 0x0001 # the camera tool can only be activated if viewing the session screen (out of car)
    IS_SCENIC_ACTIVE        = 0x0002 # the scenic camera is active (no focus car)

    # these can be changed with a broadcast message
    CAM_TOOL_ACTIVE         = 0x0004
    UI_HIDDEN               = 0x0008
    USE_AUTO_SHOT_SELECTION = 0x0010
    USE_TEMPORARY_EDITS     = 0x0020
    USE_KEY_ACCELERATION    = 0x0040
    USE_KEY10X_ACCELERATION = 0x0080
    USE_MOUSE_AIM_MODE      = 0x0100

class BroadcastMsg:
    CAM_SWITCH_POS           = 0 # car position, group, camera
    CAM_SWITCH_NUM           = 1 # driver #, group, camera
    CAM_SET_STATE            = 2 # CameraState, unused, unused
    REPLAY_SET_PLAY_SPEED    = 3 # speed, slowMotion, unused
    REPLAY_SET_PLAY_POSITION = 4 # RpyPosMode, Frame Number (high, low)
    REPLAY_SEARCH            = 5 # RpySrchMode, unused, unused
    REPLAY_SET_STATE         = 6 # RpyStateMode, unused, unused
    RELOAD_TEXTURES          = 7 # ReloadTexturesMode, carIdx, unused
    CHAT_COMMAND             = 8 # ChatCommandMode, subCommand, unused
    PIT_COMMAND              = 9 # PitCommandMode, parameter

class ChatCommandMode:
    MACRO      = 0 # pass in a number from 1-15 representing the chat macro to launch
    BEGIN_CHAT = 1 # Open up a new chat window
    REPLY      = 2 # Reply to last private chat
    CANCEL     = 3 # Close chat window

class PitCommandMode:            # this only works when the driver is in the car
    CLEAR = 0 # Clear all pit checkboxes
    WS    = 1 # Clean the winshield, using one tear off
    FUEL  = 2 # Add fuel, optionally specify the amount to add in liters or pass '0' to use existing amount
    LF    = 3 # Change the left front tire, optionally specifying the pressure in KPa or pass '0' to use existing pressure
    RF    = 4 # right front
    LR    = 5 # left rear
    RR    = 6 # right rear

class RpyStateMode:
    ERASE_TAPE = 0 # clear any data in the replay tape

class ReloadTexturesMode:
    ALL     = 0 # reload all textuers
    CAR_IDX = 1 # reload only textures for the specific carIdx

class RpySrchMode:
    TO_START      = 0
    TO_END        = 1
    PREV_SESSION  = 2
    NEXT_SESSION  = 3
    PREV_LAP      = 4
    NEXT_LAP      = 5
    PREV_FRAME    = 6
    NEXT_FRAME    = 7
    PREV_INCIDENT = 8
    NEXT_INCIDENT = 9

class RpyPosMode:
    BEGIN   = 0
    CURRENT = 1
    END     = 2

class csMode:
    AT_INCIDENT = -3
    AT_LEADER   = -2
    AT_EXCITING = -1



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

class VarHeader(IRSDKStruct):
    type = IRSDKStruct.property_value(0, 'i')
    offset = IRSDKStruct.property_value(4, 'i')
    count = IRSDKStruct.property_value(8, 'i')

    name = IRSDKStruct.property_value_str(16, '32s')
    desc = IRSDKStruct.property_value_str(48, '64s')
    unit = IRSDKStruct.property_value_str(112, '32s')

class IRSDK:
    def __init__(self):
        self.is_initialized = False
        self.last_tick_count = 0
        self.last_session_info_update = 0

        self._shared_mem = None
        self._header = None

        self.__var_headers = None
        self.__var_headers_dict = None
        self.__session_info_dict = None
        self.__broadcast_msg_id = None

    def __getitem__(self, key):
        if key in self._var_headers_dict:
            var_header = self._var_headers_dict[key]
            var_buf_latest = self._var_buffer_latest
            res = struct.unpack_from(
                VAR_TYPE_MAP[var_header.type] * var_header.count,
                self._shared_mem,
                var_buf_latest.buf_offset + var_header.offset)
            return res[0] if var_header.count == 1 else list(res)

        return self._get_session_info(key)

    @property
    def is_connected(self):
        return self._header and self._header.status == StatusField.STATUS_CONNECTED

    @property
    def session_info_update(self):
        return self._header.session_info_update

    def startup(self, test_file=None, dump_to=None):
        if test_file is None and not self._check_sim_status():
            return False

        if self._shared_mem is None:
            if test_file:
                f = open(test_file, 'rb')
                self._shared_mem = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
            else:
                self._shared_mem = mmap.mmap(0, MEMMAPFILESIZE, MEMMAPFILE, access=mmap.ACCESS_READ)

        if self._shared_mem:
            if dump_to:
                f = open(dump_to, 'wb')
                f.write(self._shared_mem)
                f.close()
            self._header = Header(self._shared_mem)
            self.is_initialized = self._header.version == 1 and len(self._header.var_buf) > 0

        return self.is_initialized

    def shutdown(self):
        self.is_initialized = False
        self.last_tick_count = 0
        self.last_session_info_update = 0
        if self._shared_mem:
            self._shared_mem.close()
            self._shared_mem = None
        self._header = None
        self.__var_headers = None
        self.__var_headers_dict = None
        self.__session_info_dict = None
        self.__broadcast_msg_id = None

    def parse_to(self, to_file):
        if not self.is_initialized:
            return
        f = open(to_file, 'w', encoding='utf-8')
        f.write(self._shared_mem[self._header.session_info_offset:self._header.session_info_len].rstrip(b'\x00').decode('latin-1'))
        f.write('\n'.join([
            '{:32}{}'.format(i, self[i])
            for i in sorted(self._var_headers_dict.keys(), key=str.lower)
        ]))
        f.close()

    def cam_switch_pos(self, position=1, group=0, camera=0):
        return self._broadcast_msg(BroadcastMsg.CAM_SWITCH_POS, position, group, camera)

    def cam_switch_num(self, driver_num="1", group=0, camera=0):
        leading_zeros = len(driver_num) - len(driver_num.lstrip("0"))
        driver_num = self._pad_car_num(int(driver_num), leading_zeros)
        return self._broadcast_msg(BroadcastMsg.CAM_SWITCH_NUM, driver_num, group, camera)

    def cam_set_state(self, camera_state=CameraState.CAM_TOOL_ACTIVE):
        return self._broadcast_msg(BroadcastMsg.CAM_SET_STATE, camera_state)

    def replay_set_play_speed(self, speed=0, slow_motion=False):
        return self._broadcast_msg(BroadcastMsg.REPLAY_SET_PLAY_SPEED, speed, 1 if slow_motion else 0)

    def replay_set_play_position(self, pos_mode=RpyPosMode.BEGIN, frame_num=0):
        return self._broadcast_msg(BroadcastMsg.REPLAY_SET_PLAY_POSITION, pos_mode, frame_num)

    def replay_search(self, search_mode=RpySrchMode.TO_START):
        return self._broadcast_msg(BroadcastMsg.REPLAY_SEARCH, search_mode)

    def replay_set_state(self, state_mode=RpyStateMode.ERASE_TAPE):
        return self._broadcast_msg(BroadcastMsg.REPLAY_SET_STATE, state_mode)

    def reload_all_textures(self):
        return self._broadcast_msg(BroadcastMsg.RELOAD_TEXTURES, ReloadTexturesMode.ALL)

    def reload_texture(self, car_idx=0):
        return self._broadcast_msg(BroadcastMsg.RELOAD_TEXTURES, ReloadTexturesMode.CAR_IDX, car_idx)

    def chat_command(self, chat_command_mode=ChatCommandMode.BEGIN_CHAT):
        return self._broadcast_msg(BroadcastMsg.CHAT_COMMAND, chat_command_mode)

    def chat_command_macro(self, macro_num=1):
        return self._broadcast_msg(BroadcastMsg.CHAT_COMMAND, ChatCommandMode.MACRO, macro_num)

    def pit_command(self, pit_command_mode=PitCommandMode.CLEAR, var=0):
        return self._broadcast_msg(BroadcastMsg.PIT_COMMAND, pit_command_mode, var)

    def _check_sim_status(self):
        return 'running:1' in request.urlopen(SIM_STATUS_URL).read().decode('utf-8')

    @property
    def _var_buffer_latest(self):
        if not self.is_initialized and not self.startup():
            self.last_tick_count = 0
            return None

        var_buf = self._header.var_buf
        var_buf_latest = var_buf[0]
        for i in range(1, self._header.num_buf):
            if var_buf_latest.tick_count < var_buf[i].tick_count:
                var_buf_latest = var_buf[i]

        return var_buf_latest

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

    def _get_session_info(self, key=None):
        if self.last_session_info_update < self._header.session_info_update:
            self.last_session_info_update = self._header.session_info_update
            self.__session_info_dict = {}

        if key is None:
            self.__session_info_dict = {}

        if key not in self.__session_info_dict:
            start = self._header.session_info_offset
            end = self._header.session_info_len

            if key is not None:
                self._shared_mem.seek(0)
                start = self._shared_mem.find(('\n%s:\n' % key).encode('latin-1'), start, end)
                end = self._shared_mem.find(b'\n\n', start, end)

            if start != -1 and end != -1:
                yaml_src = self._shared_mem[start:end].rstrip(b'\x00').decode('latin-1')
                result = yaml.load(yaml_src, Loader=YamlLoader)
                if result:
                    self.__session_info_dict.update(result)
            elif key is not None:
                self.__session_info_dict[key] = None

        if key is None:
            return self.__session_info_dict
        return self.__session_info_dict.get(key)

    @property
    def _broadcast_msg_id(self):
        if self.__broadcast_msg_id is None:
            self.__broadcast_msg_id = ctypes.windll.user32.RegisterWindowMessageW(BROADCASTMSGNAME)
        return self.__broadcast_msg_id

    def _broadcast_msg(self, broadcast_type=0, var1=0, var2=0, var3=0):
        return ctypes.windll.user32.SendNotifyMessageW(0xFFFF, self._broadcast_msg_id,
            broadcast_type | var1 << 16, var2 | var3 << 16)

    def _pad_car_num(self, num, zero):
        if zero:
            num_place = 3 if num > 99 else 2 if num > 9 else 1
            return num + 1000 * (num_place + zero)
        return num

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
