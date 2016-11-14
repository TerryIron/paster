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
import logging

__author__ = 'terry'

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

# Color escape string
COLOR_RED = '\033[1;31m'
COLOR_GREEN = '\033[1;32m'
COLOR_YELLOW = '\033[1;33m'
COLOR_BLUE = '\033[1;34m'
COLOR_PURPLE = '\033[1;35m'
COLOR_CYAN = '\033[1;36m'
COLOR_GRAY = '\033[1;37m'
COLOR_WHITE = '\033[1;38m'
COLOR_RESET = '\033[1;0m'

# Define log color
LOG_COLORS = {
    'DEBUG': '%s',
    'INFO': COLOR_GREEN + '%s' + COLOR_RESET,
    'WARNING': COLOR_YELLOW + '%s' + COLOR_RESET,
    'ERROR': COLOR_RED + '%s' + COLOR_RESET,
    'CRITICAL': COLOR_RED + '%s' + COLOR_RESET,
    'EXCEPTION': COLOR_RED + '%s' + COLOR_RESET,
}


class ColorFormatter(logging.Formatter):
    def __init__(self, fmt=None, datefmt=None):
        logging.Formatter.__init__(self, fmt, datefmt)

    def format(self, record):
        level_name = record.levelname
        msg = logging.Formatter.format(self, record)
        return LOG_COLORS.get(level_name, '%s') % msg


class Logger(logging.Logger):
    def __init__(self, name, level=logging.NOTSET):
        self.logger = None
        logging.Logger.__init__(self, name, level=level)

    def _log(self, level, msg, args, exc_info=None, extra=None):
        if not self.logger:
            self._init()
        super(Logger, self)._log(level, msg, args, exc_info=exc_info, extra=extra)

    def _init(self, colorful=True):
        if not self.logger:
            if not __LOGGER__:
                _handler = logging.StreamHandler()
                _level = LOGGER_LEVEL
            else:
                _handler, _level = __LOGGER__
            if colorful:
                _handler.setFormatter(ColorFormatter(LOGGER_FORMAT))
            else:
                _handler.setFormatter(logging.Formatter(LOGGER_FORMAT))
            self.addHandler(_handler)
            self.setLevel(_level)
            self.logger = True
