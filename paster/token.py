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
import base64
import time
import uuid
from functools import wraps
from oauthlib import oauth2

from session import BaseSession, make_session
from wsgi import get_virtual_config_inside, Middleware, WSGIMiddleware, \
    get_func_environ, push_environ_args, runner_return, get_self_object
from utils import myException
from log import get_logger


__author__ = 'terry'


logger = get_logger(__name__)


TYPE_BEARER = 0
TYPE_SAML = 1
TYPE_MAC = 2


TOKEN_TYPES = {
    TYPE_BEARER: oauth2.BearerToken(),
    TYPE_SAML: None,
    TYPE_MAC: None,
}


class TokenScopeV1(object):
    """
        input_scope:
        [被要求的检查的权限ID]

    """

    @classmethod
    def get_input(cls, scope_obj):
        try:
            return scope_obj.get('application', {})
        except:
            return {}

    @classmethod
    def put_input(cls, item, scope_obj=None):
        if not scope_obj:
            scope_obj = {}
        scope_obj['application'] = item
        return scope_obj


def random_values():
    return base64.b64encode(str(uuid.uuid4()))


class AuthTokenV1(object):
    @staticmethod
    def generate_token(token_type=TYPE_BEARER, expires_in=3600, scopes=None):
        t = None
        if token_type in TOKEN_TYPES:
            t = TOKEN_TYPES[token_type]
        if not t:
            t = TOKEN_TYPES[TYPE_BEARER]
        token = t.create_token(type('request', (),
                               {'expires_in': expires_in,
                                'scopes': [],
                                'state': 1,
                                'extra_credentials': {'timestamp': time.time()}}), save_token=False)
        scope_input_api = base64.b64encode(json.dumps(TokenScopeV1.get_input(scopes)))
        scope_domain_val = random_values()
        # Token随机值 +  Token域值 + 被允许的API表
        token['access_token'] = ':'.join([token['access_token'], scope_domain_val, scope_input_api])
        token['refresh_token'] = ':'.join([random_values(), random_values()])
        if 'scope' in token:
            token.pop('scope')
        return token

    @staticmethod
    def parse_token(token):
        new_token = str(token).split(':')
        if len(new_token) != 3:
            return {}
        else:
            _n = new_token[-1]
            _n = json.loads(base64.b64decode(_n))
            return _n

    @staticmethod
    def update_token(token, token_type=TYPE_BEARER, expires_in=3600, scopes=None):
        token_scopes = AuthTokenV1.parse_token(token=token)
        if token_scopes:
            new_scopes = {}
            TokenScopeV1.put_input(new_scopes, token_scopes)
            new_scopes.update(scopes)
            new_token = AuthTokenV1.generate_token(token_type=token_type, expires_in=expires_in, scopes=new_scopes)
            return new_token

    @staticmethod
    def diff_token(token, token_info, expired_time):
        if not token_info:
            raise InValidToken()
        try:
            if token != token_info['token']:
                raise InValidToken()
            _token_time = token_info['timestamp']
            if time.time() - int(_token_time) > expired_time:
                raise ExpiredToken()
        except:
            logger.debug('token: {0}, token_info:{1}'.format(token, token_info))
            raise InValidToken()


class TokenMiddleware(Middleware, WSGIMiddleware):
    TOKEN_LOCAL_NAME = '__token__'

    def get_token_env(self, context):
        _token_env = {'in_headers': {}, 'in_urls': {}}
        if 'REQUEST_KWARGS' in context:
            _token_env['in_urls'] = context['REQUEST_KWARGS']
        for k, v in [(_k, _v) for _k, _v in context.items() if _k.startswith('HTTP_')]:
            _token_env['in_headers'][k[5:]] = v
        return _token_env

    def process_request(self, context, start_response, token_env=None):
        _token_env = token_env
        if not _token_env:
            _token_env = self.get_token_env(context)
        push_environ_args(context, self.TOKEN_LOCAL_NAME, _token_env)

        return super(TokenMiddleware, self).process_request(context, start_response)


class AuthenticationFailed(myException):
    status_code = 401
    error_code = 4001


class ExpiredToken(myException):
    status_code = 401
    error_code = 4002


class InValidToken(myException):
    status_code = 401
    error_code = 4003


class TokenSession(BaseSession):

    @staticmethod
    def encode(token_info):
        _token_val = token_info.get('access_token')
        _timestamp = token_info.get('timestamp')
        return {'token': _token_val, 'timestamp': _timestamp}

    @staticmethod
    def decode(token_info):
        _token_val = token_info.get('token')
        _timestamp = token_info.get('timestamp')
        if _token_val and _timestamp:
            return token_info

    def set(self, token_info, item=None):
        super(TokenSession, self).set(token_info, item=item)

    def get(self, item=None):
        _value = super(TokenSession, self).get(item=item)
        return self.decode(_value)


def get_token_info(token_env, check_headers=None, check_kwargs=None):
    try:
        check_headers = check_headers if isinstance(check_headers, list) else [check_headers]
        check_kwargs = check_kwargs if isinstance(check_kwargs, list) else [check_kwargs]
        _token_info = ''
        if check_headers:
            for _h in check_headers:
                _h = str(_h).upper()
                if _h in token_env['in_headers']:
                    _token_info += token_env['in_headers'][_h]
        elif check_kwargs:
            for _h in check_headers:
                _h = str(_h).upper()
                if _h in token_env['in_urls']:
                    _token_info += token_env['in_urls'][_h]
        return _token_info
    except:
        pass


def token_key(key_list):
    return base64.b64encode(''.join([str(s) for s in key_list]))


def token_session(keys, name, connection=None, connection_option='connection', expired_time=3600,
                  check_headers=None, check_kwargs=None, need_check=True,
                  class_member_name='__token__'):
    """
    令牌会话装饰器

    :param keys: Token输入键值表
    :param name: Session对象名
    :param connection: 连接地址
    :param connection_option: 连接地址配置项
    :param expired_time: 存活时间
    :param check_headers: Token客户端消息检查头定义
    :param check_kwargs: Token客户端消息检查定义
    :param need_check: 是否检查
    :param class_member_name: 类缓存对象名
    :return:
    """
    key_list = keys if isinstance(keys, list) else [keys]

    def _wrap(func):
        @wraps(func)
        def _wrap_func(*args, **kwargs):
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
            _token_info = get_token_info(_env, check_headers=check_headers, check_kwargs=check_kwargs)

            if not _token_info:
                raise AuthenticationFailed()

            # 检查Token准备条件
            _token_kwargs = AuthTokenV1.parse_token(_token_info)
            _token_args = []

            for k in key_list:
                if k not in _token_kwargs:
                    raise AuthenticationFailed()
                else:
                    _token_args.append(_token_kwargs[k])

            # 初始化Session
            _conn = make_session(_connection)
            _name = token_key(_token_args)
            if not _obj:
                session = TokenSession(name, _conn, expired_time=expired_time)
            else:
                setattr(_obj, class_member_name, TokenSession(name, _conn, expired_time=expired_time))
                session = getattr(_obj, class_member_name)

            # 检查Token过期和验证通过
            if need_check:
                _save_token = session.get(_name)
                AuthTokenV1.diff_token(_token_info, _save_token, expired_time)

            ret = runner_return(func, *args, **kwargs)
            return ret
        return _wrap_func
    return _wrap
