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
import os.path
import urllib
import pickle
import xml.etree.ElementTree as ET


__all__ = ['parse_protocol']


__target_file__ = os.path.join(os.path.dirname(__file__), 'ip_protocols.pc')


def update():
    f = urllib.urlopen('https://en.wikipedia.org/wiki/List_of_IP_protocol_numbers')
    root = ET.fromstring(f.read())
    try:
        for i, j, k, p, r in root.findall('./body/div/div/div/table/'):
            IP_PROTOCOLS[i.text] = p.text if not k.text else k.text
    except ValueError:
        pass
    with open(__target_file__, 'w') as f:
        pickle.dump(IP_PROTOCOLS, f)


try:
    IP_PROTOCOLS = pickle.load(open(__target_file__, 'r'))
except:
    IP_PROTOCOLS = dict()
    update()


def parse_protocol(val):
    return IP_PROTOCOLS.get(val, None)


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'update':
        update()
