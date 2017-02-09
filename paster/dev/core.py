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
import uuid
import functools

__author__ = 'terry'


def generate_uuid():
    return str(uuid.uuid4())


def bool_str(val):
    try:
        if isinstance(val, str) and str(val).lower() == ('false' or 'none'):
            return False
    except:
        return bool(val)


def bool_int(val):
    return int(bool(val))


def decode_string(string):
    try:
        return str(string).decode('utf-8')
    except:
        return string


def to_list(obj):
    if not isinstance(obj, list):
        _obj = [obj] if obj else []
    else:
        _obj = obj
    return _obj


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class VerAdapter(object):

    class AdapterVerNotFound(Exception):
        pass

    def __init__(self, default_version=None):
        """
        版本适配器

        :param default_version: 默认版本
        """
        self.default_version = default_version or 'default'
        self.version = {}
        self._versions = []

    def set_default_version(self, version):
        self.default_version = version

    def set_version(self, version, obj):
        self.version[version] = obj

    def add_version(self, version):
        if version not in self._versions:
            self._versions.append(version)

    @classmethod
    def get_hook_to_filter_version(cls):
        pass

    def __getitem__(self, item):
        if item in self.version:
            return self.version[item]
        return self.__call__()

    def __setitem__(self, key, value):
        if key not in self.version:
            self.version[key] = value

    def __call__(self, version=None):
        _version = version or self.default_version
        if _version in self.version:
            return self.version.get(_version)
        if 'default' in self.version:
            return self.version.get('default')
        return None

    def __getattr__(self, item):
        _hook = getattr(self, 'get_hook_to_filter_version')
        _version = _hook() if _hook and callable(_hook) else None
        obj = self.__call__(version=_version)
        if obj and hasattr(obj, item):
            return getattr(obj, item)
        else:
            raise AttributeError('{0} has no attribute {1}'.format(obj, item))


def set_ver_adapter(callback, args, version='v1', adapter=None, hook=None):
    d = VerAdapter() if not adapter else adapter
    d.add_version(version)
    if isinstance(args, dict):
        _args = {}
        _args.update(args)
        _args.pop('__default__')
        d.set_version(version, callback(_args))
    else:
        d.set_version(version, callback(args))
    d.set_default_version(version)
    if callable(hook):
        d.get_hook_to_filter_version = hook
    return d


def set_adapter(operations, args, adapter=None, hook=None):
    _operations = {}
    _operations.update(operations)
    default_version = _operations.pop('select', 'v1')
    d = Adapter() if not adapter else adapter
    ver_adapters = {}
    for name, tags in _operations.items():
        for tag, _class in tags.items():
            if name not in ver_adapters:
                ver_adapters[name] = VerAdapter()
            d.set_operation(name, ver_adapters[name])
            # 定义操作对象并注册名称
            set_ver_adapter(functools.partial(_class, name=':'.join([name, tag])), args, tag,
                            adapter=ver_adapters[name],
                            hook=hook)
    for d in ver_adapters.values():
        d.set_default_version(default_version)
    return d


class Adapter(object):
    class AdapterObjectNotFound(Exception):
        pass

    def __init__(self, operations=None):
        """
        控制器适配器

        :param operations: 版本操作模版, 如{VER: {operation_name: OBJECT}}
        """
        self._operations = operations if operations else {}

    def get_operations(self):
        return self._operations.keys()

    def get_operation(self, name):
        return self._operations.get(name)

    def set_operation(self, name, obj):
        if name not in self._operations:
            self._operations[name] = obj

    def __getattr__(self, item):
        if item in self._operations:
            _item = self._operations.get(item)
            return _item
        else:
            return super(Adapter, self).__getattribute__(item)
