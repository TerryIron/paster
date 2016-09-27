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


import os.path
from zope.mimetype import typegetter


def is_response_wrapper(obj):
    if hasattr(obj, 'headers') and hasattr(obj, 'content'):
        return True
    else:
        return False


def check_mime_type(filename):
    _filename = os.path.basename(filename)
    content_type = typegetter.mimeTypeGuesser(name=_filename)
    return content_type

class BaseResponse(object):
    def __init__(self, content=None, headers=None, status_code=200):
        self.content = content
        self.status_code = status_code
        _headers = dict()
        headers = headers if headers else {}
        _headers.update(headers)
        self.headers = _headers
        self.init()

    def init(self):
        pass


class HttpResponse(BaseResponse):
    pass


class HttpUpload(BaseResponse):
    def __init__(self, filename=None):
        f = open(filename)
        content = f.read()
        content_type = check_mime_type(filename)
        content_type = content_type if content_type else 'application/octet-stream'
        headers = {'Content-Disposition': 'attachment;'
                                          'filename={0};'
                                          'filename*=utf-8 {0}'.format(filename),
                   'Content-Length': str(len(content)),
                   'Content-Type': content_type}
        super(HttpUpload, self).__init__(content, headers, status_code=200)


class HttpDownload(BaseResponse):
    def __init__(self, filename=None):
        f = open(filename)
        content = f.read()
        content_type = check_mime_type(filename)
        content_type = content_type if content_type else 'application/octet-stream'
        headers = {'Content-Disposition': 'attachment;'
                                          'filename={0};'
                                          'filename*=utf-8 {0}'.format(filename),
                   'Content-Length': str(len(content)),
                   'Content-Type': content_type}
        super(HttpDownload, self).__init__(content, headers, status_code=200)


class HttpRender(BaseResponse):
    pass

