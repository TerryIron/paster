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

import logging


__LOGGER__ = None

LOGGER_FORMAT = '[%(asctime)s][%(levelname)s][%(filename)s:%(lineno)d %(funcName)s] %(message)s'
LOGGER_LEVEL = 'DEBUG'


def handler_init(filename=None, level=LOGGER_LEVEL, fmt=LOGGER_FORMAT):
    if filename:
        handler = logging.FileHandler(filename)
    else:
        handler = logging.StreamHandler()

    if not level:
        level = LOGGER_LEVEL

    if not fmt:
        fmt = LOGGER_FORMAT
    handler.setFormatter(logging.Formatter(fmt))

    global __LOGGER__
    __LOGGER__ = (handler, level)
    return __LOGGER__


def get_logger(name):
    logger = Logger(name)
    return logger


class Logger(logging.Logger):
    def __init__(self, name, level=logging.NOTSET):
        self.logger = None
        logging.Logger.__init__(self, name, level=level)

    def _log(self, level, msg, args, exc_info=None, extra=None):
        if not self.logger:
            self._init()
        super(Logger, self)._log(level, msg, args, exc_info=exc_info, extra=extra)

    def _init(self):
        if not self.logger:
            if not __LOGGER__:
                _handler = logging.StreamHandler()
                _handler.setFormatter(logging.Formatter(LOGGER_FORMAT))
                _level = LOGGER_LEVEL
            else:
                _handler, _level = __LOGGER__
            self.addHandler(_handler)
            self.setLevel(_level)
            self.logger = True
