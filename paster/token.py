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

import json
import base64
import time
from functools import wraps

from session import LocalSession, make_session
from wsgi import get_virtual_config_inside, Middleware, WSGIMiddleware, \
    get_func_environ, push_environ_args, runner_return, get_self_object
from utils import myException
from log import get_logger


logger = get_logger(__name__)


class TokenMiddleware(Middleware, WSGIMiddleware):
    TOKEN_LOCAL_NAME = '__token__'

    def process_request(self, context, start_response):
        _token_env = {'in_headers': {}, 'in_urls': {}}
        if 'REQUEST_KWARGS' in context:
            _token_env['in_urls'] = context['REQUEST_KWARGS']
        for k, v in [(_k, _v) for _k, _v in context.items() if _k.startswith('HTTP_')]:
            _token_env['in_headers'][k[5:]] = v
        push_environ_args(context, self.TOKEN_LOCAL_NAME, _token_env)

        return super(TokenMiddleware, self).process_request(context, start_response)


class AuthenticationFailed(myException):
    error_code = 401


class ExpiredToken(myException):
    error_code = 402


class InValidToken(myException):
    error_code = 403


def token_session(keys, key_prefix=None, connection=None, connection_option='connection', expired_time=3600,
                  check_headers=None, check_kwargs=None, class_member_name='__token__'):
    """
    令牌会话装饰器

    :param keys: Token输入键值表
    :param key_prefix: Token输入键值头
    :param connection: 连接地址
    :param connection_option: 连接地址配置项
    :param expired_time: 存活时间
    :param check_headers: Token客户端消息检查头定义
    :param check_kwargs: Token客户端消息检查定义
    :param class_member_name: 类缓存对象名
    :return:
    """
    key_list = keys if isinstance(keys, list) else [keys]

    def _wrap(func):
        @wraps(func)
        def _wrap_func(*args, **kwargs):
            # 检查Token准备条件
            for k in key_list:
                if k not in kwargs:
                    raise AuthenticationFailed()

            # 获取Token会话入口
            _obj = get_self_object(func, *args)
            _connection = None
            if connection:
                _connection = connection
            elif connection_option:
                config = get_virtual_config_inside(func, _obj)
                _connection = config[connection_option]

            # 获取Token信息
            _env = get_func_environ(args, TokenMiddleware.TOKEN_LOCAL_NAME)
            _token_info = ''
            if check_headers:
                for _h in check_headers:
                    _h = str(_h).upper()
                    if _h in _env['in_headers']:
                        _token_info += _env['in_headers'][_h]
            elif check_kwargs:
                for _h in check_headers:
                    _h = str(_h).upper()
                    if _h in _env['in_urls']:
                        _token_info += _env['in_urls'][_h]
            if not _token_info:
                raise AuthenticationFailed()

            # 初始化Session
            _conn = make_session(_connection)
            _name = ''.join([key_prefix] + key_list)
            if _obj:
                session = LocalSession(_name, _conn, expired_time=expired_time)
            else:
                setattr(_obj, class_member_name, LocalSession(_name, _conn, expired_time=expired_time))
                session = getattr(_obj, class_member_name)

            # 检查Token过期和验证通过
            _save_token = session.get()
            if _save_token != _token_info:
                raise InValidToken()
            else:
                try:
                    _token_scope = json.loads(base64.b64decode(_token_info.split(':')[2]))
                    _token_time = _token_scope['timestamp']
                    if time.time() - int(_token_time) < expired_time:
                        raise ExpiredToken()
                except:
                    raise InValidToken()
                ret = runner_return(func, *args, **kwargs)
                return ret
        return _wrap_func
    return _wrap
