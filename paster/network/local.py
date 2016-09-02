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

from packet import Packet


class TCP(Packet):
    FORMAT = [
        ('src_port', 16),
        ('dst_port', 16),
        ('seq_num', 32),
        ('ack_num', 32),
        ('offset', 4),
        ('reserved', 4),
        ('flags', 8),
        ('window', 8),
        ('checksum', 16),
        ('urgent_pointer', 16),
    ]


class UDP(Packet):
    FORMAT = [
        ('src_port', 16),
        ('dst_port', 16),
        ('length', 16),
        ('checksum', 16),
    ]


class packetICMP(Packet):
    FORMAT = [
        ('type', 8),
        ('code', 8),
        ('checksum', 16),
        ('spec_info', 32),
    ]

