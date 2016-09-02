#!/usr/bin/env python
# coding=utf-8

#
# Copyright (c) 2015-2018  Terry Xi
# All Rights Reserved.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED
# TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
# PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
# LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#

__author__ = 'terry'


import struct
import logging


LOG = logging.getLogger(__name__)


def lazy_packs(datas):
    return struct.pack(''.join([str(chr(len(i))) + 's' for i in datas]), *datas)


def packs(datas, lengths):
    return struct.pack(''.join([str(chr(i)) + 's' for i in lengths]), *datas)


def pack(data, length):
    return struct.pack('{0}s'.format(length), str(data))


def unpack(data, length):
    return struct.unpack('{0}s'.format(length), data)[0]


def append(old_packdata, packdata):
    return struct.pack('{0}s{1}s'.format(len(old_packdata), len(packdata)),
                       old_packdata,
                       packdata)


def pop(length, packdata):
    return struct.unpack('{0}s{1}s'.format(length, len(packdata) - length),
                         packdata)[0]


from offset import *


class PacketError(Exception):
    pass


class PacketErrorMsg(PacketError):
    pass


class PacketVerError(PacketError):
    pass


class PacketItemUnexpected(PacketError):
    def __init__(self, target, name, unexpected_val):
        self.target = target
        self.name = name
        self.unexpected_val = unexpected_val

    def __str__(self):
        return "Packet {0} item {1} is unexcepted".format(self.target.__class__, self.name, self.unexpected_val)


class PacketWarn(Exception):
    pass


class PacketWarnMsg(PacketWarn):
    pass


class Packet(object):
    FORMAT = None

    def __init__(self):
        self.struct = [[k, l, None] for k, l in self.FORMAT]
        self.status = {}
        self.len = None

    def __getitem__(self, key):
        k_b = []
        for k, l, v in self.struct:
            if k.startswith(key):
                k_b.append(v)
            elif len(k_b) > 0:
                break
        return ''.join(k_b) or None

    def __setitem__(self, key, value):
        i = 0
        for k, l, v in self.struct:
            if k == key:
                self.struct[i][2] = value
                return True
            i += 1
        return False

    def iterate_packet_itemkey(self):
        return [k for k, l, v in self.struct]

    def iterate_packet_itemval(self):
        return [v for k, l, v in self.struct]

    def is_expected(self, name):
        try:
            with self.__getitem__(name) as it:
                _func = getattr(self, '_parse_{0}')
                if callable(_func):
                    return _func()
                else:
                    self.status[name] = it
        except PacketError as e:
            LOG.error(e)
            raise e
        except PacketWarn as e:
            LOG.warn(e)

    def pack(self, header, data):
        raise NotImplementedError()

    @classmethod
    def force_unpack(cls, data):
        raise NotImplementedError()

    @classmethod
    def safe_unpack(cls, data):
        raise NotImplementedError()





