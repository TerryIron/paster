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
try:
    import cPickle as pickle
except:
    import pickle
import uuid
import base64
import redis
import OpenSSL
import urlparse
from Cookie import SimpleCookie
from functools import wraps, partial

from wsgi import get_virtual_config_inside, Middleware, WSGIMiddleware, \
    get_func_environ, push_environ_args, runner_return, get_self_object
from utils import myException
from log import get_logger

__author__ = 'terry'


logger = get_logger(__name__)


class SessionOperationError(myException):
    """ Session 操作失败"""


class SessionMiddleware(Middleware, WSGIMiddleware):
    SESSION_KEY = 'session_id'
    SESSION_LOCAL_NAME = '__session_id__'

    def process_request(self, context, start_response):
        _cookie = SimpleCookie()
        if 'HTTP_COOKIE' in context:
            _cookie.load(context['HTTP_COOKIE'])
        _protocol = str(context.get('SERVER_PROTOCOL', 'HTTP/1.1'))
        if _protocol.startswith('HTTPS'):
            _is_secure = True
        else:
            _is_secure = False
        session_id = None
        if self.SESSION_KEY in _cookie:
            session_id = _cookie[self.SESSION_KEY].value
        if not session_id:
            session_id = str(uuid.UUID(bytes=OpenSSL.rand.bytes(16)))
        push_environ_args(context, self.SESSION_LOCAL_NAME, session_id)

        def _start_response(status, response_headers, exc_info=None):
            cookie = SimpleCookie()
            cookie[self.SESSION_KEY] = session_id
            cookie[self.SESSION_KEY]['path'] = '/'
            if _is_secure:
                cookie[self.SESSION_KEY]['http'] = True
                cookie[self.SESSION_KEY]['secure'] = True
            cookie_string = cookie[self.SESSION_KEY].OutputString()
            response_headers.append(('Set-Cookie', cookie_string))
            return start_response(status, response_headers, exc_info)

        return super(SessionMiddleware, self).process_request(context, _start_response)


CONNECTIONS = {}

NAMESPACE_DNS = uuid.UUID('6ba7b810-9dad-11d1-80b4-00c04fd430c8')


class BaseSession(object):
    def __init__(self, n, session_pool, default_key='', expired_time=3600):
        self.name = n
        self.session = session_pool
        self._default_key = default_key
        self.expired_time = expired_time

    def clear(self, item=None):
        try:
            _name = self.name
            if item:
                _name += str(item)
            _name = base64.b64encode(_name)
            d = self.session.hgetall(_name)
            self.session.hdel(_name, *d.keys())
        except Exception as e:
            logger.debug(SessionOperationError(e))
            pass

    def get(self, item=None):
        try:
            _name = self.name
            if not item:
                item = self._default_key
            else:
                item = str(item)
                _name += item
            # logger.debug('get item {0} key:{1}'.format(_name, item))
            item = base64.b64encode(item)
            _name = base64.b64encode(_name)
            value = self.session.hget(_name, item)
            if value:
                value = pickle.loads(value)
            return value
        except Exception as e:
            logger.error(SessionOperationError(e))
            pass

    def set(self, value, item=None):
        try:
            _value = pickle.dumps(value)
            _name = self.name
            if not item:
                item = self._default_key
            else:
                item = str(item)
                _name += item
            # logger.debug('set item {0} key:{1}, value:{2}'.format(_name, item, value))
            item = base64.b64encode(item)
            _name = base64.b64encode(_name)
            self.session.hset(_name, item, _value)
            self.session.expire(_name, self.expired_time)
        except Exception as e:
            logger.debug(SessionOperationError(e))
            pass


def make_session(conn, db=0):
    url = urlparse.urlparse(conn)
    host, port = url.netloc.split(':')
    pool = redis.ConnectionPool(host=host, port=port)
    return redis.StrictRedis(connection_pool=pool, db=db)


def redis_session(connection=None, connection_option='connection', expired_time=86400,
                  key=None, key_option=None, name=None,
                  use_cache=False, write_cache=False,
                  class_member_name='__session__'):
    """
    Redis 会话装饰器, 将session对象绑定在__session__(类缓存对象名)属性

    :param connection: 连接地址
    :param connection_option: 连接地址配置项
    :param key: 存储的key
    :param key_option: key的配置项
    :param name: 存储域配置项
    :param expired_time: 存活时间
    :param use_cache: 是否快速使用缓存
    :param write_cache: 是否写缓存
    :param class_member_name: 类缓存对象名
    :return:
    """

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

    redis_target = dict(key=get_key('key', key if not callable(key) else key())
                        if not key_option else get_key('opt_key', key_option))

    if _connection_name in CONNECTIONS and CONNECTIONS[_connection_name]:
        redis_target['session'] = CONNECTIONS[_connection_name]

    def _wrap(func):
        @wraps(func)
        def _wrap_func(*args, **kwargs):
            _obj, _key = get_self_object(func, *args), None
            if 'real_key' not in redis_target:
                config = get_virtual_config_inside(func, _obj)
                if callable(redis_target['key']):
                    _key = redis_target['key'](config)
                if _key:
                    redis_target['real_key'] = _key
            else:
                _key = redis_target['real_key']
            if not name:
                _name = get_func_environ(args, SessionMiddleware.SESSION_LOCAL_NAME)
                if not _name:
                    _name = str(uuid.uuid5(NAMESPACE_DNS, str(_key)))
            else:
                _name = name

            # 初始化Session池
            if 'session' not in redis_target:
                config = get_virtual_config_inside(func, _obj)
                _connection = config[connection_option] if config.get(connection_option) else connection
                conn = make_session(_connection if not callable(_connection) else _connection())
                CONNECTIONS[_connection_name] = conn
                redis_target['session'] = conn

            # 配置Session会话
            if not _obj:
                # 如果不是对象, 通过设置将输出缓存
                session = BaseSession(_name, redis_target['session'],
                                      default_key=_key, expired_time=expired_time)
            else:
                if isinstance(expired_time, str):
                    _expired_time = getattr(_obj, str(expired_time))
                else:
                    _expired_time = expired_time
                setattr(_obj, class_member_name, BaseSession(_name, redis_target['session'],
                                                             default_key=_key, expired_time=_expired_time))
                session = getattr(_obj, class_member_name)

            ret = None
            if use_cache and _key:
                ret = session.get(_key)
            if not ret:
                ret = runner_return(func, *args, **kwargs)
            if write_cache and _key:
                session.set(_key, ret)
            return ret
        return _wrap_func
    return _wrap
