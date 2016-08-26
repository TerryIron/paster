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


NAMESPACE_DNS = uuid.UUID('6ba7b810-9dad-11d1-80b4-00c04fd430c8')

CONNECTIONS = {}


def redis_session(option_name, name=None, name_option=None, key=None, key_option=None, timeout=86400, is_force=False):
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

    redis_target = dict(key=get_key('key', key) if not key_option else get_key('opt_key', key_option),
                        name=get_key('key', name) if not name_option else get_key('opt_key', name_option))

    if _connection_name in CONNECTIONS and CONNECTIONS[_connection_name]:
        redis_target['session'] = CONNECTIONS[_connection_name]

    def _wrap(func):

        @wraps(func)
        def _wrap_func(*args, **kwargs):
            _obj = None
            if args and hasattr(args[0], func.__name__):
                _obj = args[0]
            if 'real_name' not in redis_target:
                if not redis_target['name']:
                    _name = _connection_name
                else:
                    config = _get_virtual_config(func, _obj)
                    _name = redis_target['name'](config)
            else:
                _name = redis_target['real_name']
            if 'real_key' not in redis_target:
                if not redis_target['key']:
                    _key = uuid.uuid5(NAMESPACE_DNS, func.__module__ + func.__name__)
                else:
                    config = _get_virtual_config(func, _obj)
                    _key = redis_target['key'](config)
                    _key = uuid.uuid5(NAMESPACE_DNS, _key)
                redis_target['real_key'] = _key
            else:
                _key = redis_target['real_key']
            if 'session' not in redis_target:
                config = _get_virtual_config(func, _obj)
                try:
                    url = urlparse.urlparse(config[option_name])
                    host, port = url.netloc.split(':')
                    pool = redis.ConnectionPool(host=host, port=port)
                    connection = redis.StrictRedis(connection_pool=pool)
                    if connection:
                        CONNECTIONS[_connection_name] = connection
                        redis_target['session'] = connection
                except Exception as e:
                    print e
                    pass

            def save_session(_val):
                if _val:
                    redis_target['session'].hset(_name, _key, val)
                    redis_target['session'].expire(_name, timeout)
            if is_force:
                val = func(*args, **kwargs)
                save_session(val)
            else:
                val = redis_target['session'].hget(_name, _key)
                if not val:
                    val = func(*args, **kwargs)
                    save_session(val)
            return val
        return _wrap_func
    return _wrap
