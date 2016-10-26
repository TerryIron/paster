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


import sys
import ctypes
import ctypes.util
from datetime import date, datetime


if sys.platform.startswith('linux'):
    CLOCK_MONOTONIC_RAW = 0
    librt = ctypes.CDLL(ctypes.util.find_library("rt"), mode=ctypes.RTLD_GLOBAL)
    clock_gettime = librt.clock_gettime
else:
    CLOCK_MONOTONIC_RAW = 0
    librt = ctypes.CDLL(ctypes.util.find_library("bios"), mode=ctypes.RTLD_GLOBAL)
    print librt
    clock_gettime = librt.biostime
    print clock_gettime


class TimeSpec(ctypes.Structure):
    _fields_ = [
        ('tv_sec', ctypes.c_long),
        ('tv_nsec', ctypes.c_long)
    ]


def hwclock():
    if callable(clock_gettime):
        t = TimeSpec()
        clock_gettime(CLOCK_MONOTONIC_RAW, ctypes.pointer(t))
        return date.fromtimestamp(t.tv_sec)
    else:
        return datetime.now()


print hwclock()
