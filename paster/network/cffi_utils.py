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

import cffi


def build_api_data(api_data, struct_data=''):
    return '''
        {struct_data}

        {api_data}
    '''.format(api_data=api_data, struct_data=struct_data)


def build_data(data, struct_data=''):
    return '''
        {struct_data}

        {data}
    '''.format(data=data, struct_data=struct_data)


class CFFIObject(object):
    ffi = cffi.FFI()
    STRUCTURE_CONTEXT = ''
    API_CONTEXT = ''
    CONTEXT = ''

    def __init__(self):
        api_data = build_api_data(struct_data=self.STRUCTURE_CONTEXT,
                                  api_data=self.API_CONTEXT)
        data = build_data(struct_data=self.STRUCTURE_CONTEXT,
                          data=self.CONTEXT)
        self.ffi.cdef(api_data)
        self.api = self.ffi.verify(data)
