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
import re
import ConfigParser

__author__ = 'terry'


class myException(Exception):
    status_code = 500  # 返回client的状态码
    error_code = 0  # 错误号

    def __init__(self, string=''):
        self.string = str(string)

    def __str__(self):
        #  存在错误号, 表示表示对外公开
        if self.error_code:
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
        else:
            return '{0}: {1}'.format(self.__class__, self.string)


def as_config(config_file):
    if isinstance(config_file, ConfigParser.ConfigParser):
        return config_file
    config = ConfigParser.ConfigParser()
    config.read(config_file)
    return config


def import_class(class_name, root_path=None):
    class_name = str(class_name).split('.')
    module_name = '.'.join(class_name[0:-1])
    cls = __import__(module_name, fromlist=[class_name[-1]])
    try:
        return getattr(cls, class_name[-1])
    except:
        import imp
        # 为加载模块提供根目录
        if root_path:
            import os.path
            _class_name = str(module_name).replace('.', '/')
            file_path = os.path.join(root_path, _class_name + '.py')
            s = imp.load_source(class_name[-1], file_path)
            return getattr(s, class_name[-1])
