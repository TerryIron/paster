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


from packet import Packet, PacketVerError, PacketItemUnexpected, PacketErrorMsg, PacketWarnMsg, push_status


class IPv4(Packet):
    """
    >>> i = IPv4()
    >>> i['version'] = 4
    >>> i['header_length'] = 8
    """
    """
    IP V4 Header

    See details in RPC760, RFC791.
    """
    FORMAT = [
        ('version', 4),
        ('header_length', 4),
        ('servcie_type', 8),
        ('total_length', 16),
        ('ident', 16),
        ('flag', 3),
        ('fragment_offset', 13),
        ('time_to_live', 8),
        ('protocol', 8),
        ('checksum', 16),
        ('src_addr', 32),
        ('dst_addr', 32),
    ]

    @push_status('version', '版本信息')
    def _check_version(self):
        val = self.__getitem__('version')
        if val != 4:
            raise PacketVerError('Expected version 4, but it is {0}.'.format(val))
        self.status['version'] = 4

    def _check_header_length(self):
        val = self.__getitem__('header_length')
        if not (val >= 5):
            raise PacketErrorMsg('Dont need this packet because of its length is {0}'.format(val))
        self.status['header_length'] = val

    def _check_service_type(self):
        val = self.__getitem__('service_type')
        precedence_dict = {
            0: 'Routine',
            1: 'Priority',
            2: 'Immediate',
            3: 'Flash',
            4: 'Flash Override',
            5: 'CRITIC/ECP',
            6: 'Internetwork Control',
            7: 'Network Control'
        }
        precedence = (val & 224) >> 5
        self.status['precedence'] = precedence_dict.get(precedence, None)
        if not self.status['precedence']:
            raise PacketItemUnexpected(self, 'service_type', val)
        self.status['delay'] = 'Low' if (val & 16) >> 4 else 'Normal'
        self.status['throughput'] = 'Low' if (val & 8) >> 3 else 'Normal'
        self.status['relibility'] = 'Low' if (val & 4) >> 2 else 'Normal'

    def _parse_total_length(self):
        val = self.__getitem__('service_type')
        if val > 382:
            raise PacketWarnMsg('IP4 Packet length is too longger, val:{0}'.format(val))
        self.status['total_length'] = val

    def _parse_flag(self):
        val = self.__getitem__('flag')
        if (val & 4) >> 2:
            raise PacketItemUnexpected(self, 'flag', val)
        self.status['can_flagged'] = True if not (val & 2) >> 1 else False
        self.status['is_last'] = True if not val & 1 else False

    def _parse_protocol(self):
        """
        Copy choice from RFC790.
        """
        from ip_protocol import parse_protocol
        val = self.__getitem__('protocol')
        self.status['protocol'] = parse_protocol(val)
        if self.status['protocol']:
            self.status['protocol'] = 'Unassigned'

    def _parse_src_address(self):
        val = self.__getitem__('src_addr')
        self.status['src_addr'] = '.' .join(str((val >> 24) & 15),
                                            str((val >> 16) & 15),
                                            str((val >> 8) & 15),
                                            str(val & 15))

    def _parse_dst_address(self):
        val = self.__getitem__('dst_addr')
        self.status['dst_addr'] = '.' .join(str((val >> 24) & 15),
                                            str((val >> 16) & 15),
                                            str((val >> 8) & 15),
                                            str(val & 15))


class IPv6(Packet):
    """
    IP V6 Header

    See details in RFC2460.
    """
    FORMAT = [
        ('version', 4),
        ('traffic_class', 8),
        ('flow_label', 20),
        ('payload_len', 16),
        ('next_header', 8),
        ('hop_limit', 8),
        ('src_addr0', 32),
        ('src_addr1', 32),
        ('src_addr2', 32),
        ('src_addr3', 32),
        ('dst_addr0', 32),
        ('dst_addr1', 32),
        ('dst_addr2', 32),
        ('dst_addr3', 32),
    ]


if __name__ == '__main__':
    import doctest
    doctest.testmod()
