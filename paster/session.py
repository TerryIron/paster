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

import uuid
import urlparse
from functools import wraps, partial

from wsgi import _get_virtual_config
from utils import myException


class SessionOperationError(myException):
    """ Session 操作失败"""

CONNECTIONS = {}

NAMESPACE_DNS = uuid.UUID('6ba7b810-9dad-11d1-80b4-00c04fd430c8')


def redis_session(option_name, key=None, key_option=None, timeout=86400, use_cache=False):
    import redis

    _connection_name = 'redis_session'

    def get_key(type_name, own_key):
        if own_key:
            def _gen_own_key():
                return '{0}:{1}'.format(type_name, own_key)
            if type_name == 'key':
                return partial(lambda x, y: str(x).split('key:')[1], _gen_own_key())
            elif type_name == 'opt_key':
                return partial(lambda x, y: y[str(x).split('opt_key:')[1]] if
                               str(x).split('opt_key:')[1] in y else None,
                               _gen_own_key())

    redis_target = dict(key=get_key('key', key) if not key_option else get_key('opt_key', key_option))

    if _connection_name in CONNECTIONS and CONNECTIONS[_connection_name]:
        redis_target['session'] = CONNECTIONS[_connection_name]

    def _wrap(func):

        @wraps(func)
        def _wrap_func(*args, **kwargs):
            _obj = None
            if args and hasattr(args[0], func.__name__):
                _obj = args[0]
            if 'real_key' not in redis_target:
                if not redis_target['key']:
                    _key = uuid.uuid5(NAMESPACE_DNS, func.__module__ + func.__name__)
                else:
                    config = _get_virtual_config(func, _obj)
                    _key = redis_target['key'](config)
                    _key = uuid.uuid3(NAMESPACE_DNS, _key)
                redis_target['real_key'] = _key
            else:
                _key = redis_target['real_key']
            _name = uuid.uuid5(NAMESPACE_DNS, _key)
            if 'session' not in redis_target:
                config = _get_virtual_config(func, _obj)
                url = urlparse.urlparse(config[option_name])
                host, port = url.netloc.split(':')
                pool = redis.ConnectionPool(host=host, port=port)
                connection = redis.StrictRedis(connection_pool=pool)
                CONNECTIONS[_connection_name] = connection
                redis_target['session'] = connection

            class LocalSession(object):

                @staticmethod
                def get(item=None):
                    if not item:
                        item = _key
                    try:
                        return redis_target['session'].hget(_name, item)
                    except Exception as e:
                        print SessionOperationError(e)

                @staticmethod
                def set(item=None, value=None):
                    if not item:
                        item = _key
                    if value:
                        try:
                            redis_target['session'].hset(_name, item, value)
                            redis_target['session'].expire(_name, timeout)
                        except Exception as e:
                            print SessionOperationError(e)

            if not _obj:
                session = LocalSession()
            else:
                setattr(_obj, '__session__', LocalSession())
                session = getattr(_obj, '__session__')
            if use_cache:
                ret = session.get(_key)
            else:
                ret = func(*args, **kwargs)
                session.set(_key, ret)
            return ret
        return _wrap_func
    return _wrap
