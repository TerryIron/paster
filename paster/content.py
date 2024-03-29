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
import json

__author__ = 'terry'


CONTENT_TYPE_X_WWW_FORM_URLENCODED = 'application/x-www-form-urlencoded'
CONTENT_TYPE_MULTI_FORM_DATA = 'multipart/form-data'
CONTENT_TYPE_JSON = 'application/json'
CONTENT_TYPE_PLAIN = 'text/plain'

CONTENT_PROCESS = {}


def get_default_content_type():
    return CONTENT_TYPE_X_WWW_FORM_URLENCODED


def get_content_process():
    return CONTENT_PROCESS


def content_process_form_urlencoded(body):
    try:
        return json.loads(body)
    except:
        return {}

CONTENT_PROCESS[CONTENT_TYPE_X_WWW_FORM_URLENCODED] = content_process_form_urlencoded
CONTENT_PROCESS[CONTENT_TYPE_JSON] = content_process_form_urlencoded


def content_process_multi_form_data(body):
    pass


CONTENT_PROCESS[CONTENT_TYPE_MULTI_FORM_DATA] = content_process_multi_form_data
