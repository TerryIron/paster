#########################################################################
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
#########################################################################


__author__ = 'terry'

import re
from ConfigParser import ConfigParser


class myException(Exception):
    status_code = 500

    def __init__(self, string='', errcode=''):
        self.string = string
        self.errcode = errcode

    def __str__(self):
        if not self.string:
            _str = '{0}.([a-zA-Z0-9_].*)'.format(self.__module__)
            _class = '{0}'.format(self.__class__)
            _class = _class.strip('>').strip('<')
            ret = re.compile(_str).findall(_class)
            if ret:
                _cls = ret[0]
                return _cls.strip('"').strip("'")
            else:
                return self.__class__
        else:
            return self.string


def as_config(config_file):
    if isinstance(config_file, ConfigParser):
        return config_file
    config = ConfigParser()
    config.read(config_file)
    return config


def import_class(class_name):
    class_name = str(class_name).split('.')
    cls = __import__('.'.join(class_name[0:-1]), fromlist=[class_name[-1]])
    return getattr(cls, class_name[-1])
