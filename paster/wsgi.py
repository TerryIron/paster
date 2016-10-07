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

import re
import json
import inspect
from io import BytesIO
from functools import partial, wraps

from utils import myException, as_config
from log import get_logger

logger = get_logger(__name__)


class BadRequest(myException):
    """Raised when request comming with invalid data """

    status_code = 400
    error_code = 100


class NotFound(myException):
    """Raised when no handler to process request"""

    status_code = 404
    error_code = 104


class BaseException(myException):
    pass


class WSGIMiddleware(object):

    middleware = {}

    @classmethod
    def factory(cls, global_config, **local_config):
        sh = local_config.pop('shell') if 'shell' in local_config else None
        global_config = as_config(global_config['__file__'])
        _global_config = {}
        for k, v in getattr(global_config, '_defaults', {}).items():
            _global_config[k] = v
        global_config = _global_config
        if local_config['__path__'] not in cls.middleware:
            cls.middleware[local_config['__path__']] = []
        cls.middleware[local_config['__path__']].append((cls, global_config, local_config, sh))

        def call_factory(context=None, start_response=None):
            return cls._factory(context, start_response)
        return call_factory

    @classmethod
    def _factory(cls, context, start_response=None):
        _start_response = start_response
        _context = type('Response', (), {'content': None, 'status_code': 200})
        for c, _conf, _local_conf, sh in cls.middleware[context['SCRIPT_NAME']][::-1]:
            c = c(sh, _conf, **_local_conf)
            context, _start_response = c.__call__(context, _start_response)
        if isinstance(context, Exception):
            # Readable errors
            status_code = getattr(context, 'status_code', 200)
            error_code = getattr(context, 'error_code', None)
            if error_code:
                context = dict(err_msg=str(context), err_code=error_code)
            else:
                context = dict(err_msg='')
            _context.status_code = status_code
        _context.content = context if context else None
        return _context, _start_response


class Middleware(object):
    def __init__(self, handler, global_config, **local_config):
        self.global_config = global_config
        self.local_config = local_config
        self.handler = handler

    def __call__(self, context, start_response):
        if isinstance(context, Exception):
            if not isinstance(context, myException):
                context = myException(str(context))
                setattr(context, 'status_code', 500)
            return self.resposne_error(context, start_response)

        try:
            _context, _start_response = self.process_request(context, start_response)
            return self.resposne_normal(_context, _start_response)
        except Exception as e:
            import traceback
            logger.debug(traceback.format_exc())
            return self.resposne_error(e, start_response)

    def process_request(self, context, start_response):
        return context, start_response

    def resposne_normal(self, context, start_response):
        return context, start_response

    def resposne_error(self, err, start_response):
        return err, start_response


def push_environ_args(environ, item, val):
    if 'paster.args' not in environ:
        environ['paster.args'] = {}
    if item not in environ['paster.args']:
        environ['paster.args'][item] = val


def pop_environ_args(environ, item):
    if 'paster.args' not in environ:
        return ''
    return environ['paster.args'].pop(item, None)


class URLMiddleware(Middleware, WSGIMiddleware):
    METHOD_LOCAL_NAME = '__method_name__'
    
    def process_request(self, context, start_response):
        if self.handler:
            if not hasattr(self.handler, 'run'):
                raise NotFound('Resource Handler not found')
            target_name = context.get('PATH_INFO', None)
            method_name = context.get('REQUEST_METHOD', 'GET')
            if target_name and method_name:

                kwargs = context.get('REQUEST_KWARGS', {})
                try:
                    request_body_size = int(context.get('CONTENT_LENGTH', 0))
                except (ValueError, ):
                    request_body_size = 0

                content_type = context.get('CONTENT_TYPE', 'application/x-www-form-urlencoded')
                content_type = str(content_type).split()[0].strip(';')
                _file = None

                def process_request_body():
                    def text_plain_process(rbody):
                        global _file
                        _file = BytesIO(rbody)

                    def key_value_process(rbody):
                        text_plain_process(rbody)
                        try:
                            _kwargs = json.loads(rbody)
                            kwargs.update(_kwargs)
                        except:
                            pass

                    def form_data_process(rbody):
                        text_plain_process(rbody)

                    _process = {
                        'application/x-www-form-urlencoded': key_value_process,
                        'multipart/form-data': form_data_process,
                        'text/plain': text_plain_process,
                    }

                    if content_type in _process:
                        request_body = context['wsgi.input'].read(request_body_size)
                        if request_body:
                            _process[content_type](request_body)
                process_request_body()
                push_environ_args(context,
                                  URLMiddleware.METHOD_LOCAL_NAME,
                                  dict(method=method_name,
                                       file=_file,
                                       url=target_name))
                func_env = context.get('paster.args', {})
                cb = partial(self.handler.run,
                             target_name,
                             method_name,
                             func_env,
                             **kwargs)
                context = cb()
            else:
                raise BadRequest('Bad request for {0}:{1}'.format(target_name, method_name))
        return super(URLMiddleware, self).process_request(context, start_response)


DEFAULT_ROUTES = {}


def _update_route(key, val):
    if key not in DEFAULT_ROUTES:
        DEFAULT_ROUTES[key] = val


def _get_route(key):
    if key in DEFAULT_ROUTES:
        return DEFAULT_ROUTES[key]


def route(url, method='GET', class_member_name='__method__'):
    """
    路由装饰器, 将method对象绑定在__method__(类对象缓存名)属性

    :param url: url路径
    :param method: 请求方式
    :param class_member_name: 类对象缓存名
    :return:
    """
    url = str(url)

    if isinstance(method, list):
        _packs = method
    else:
        _packs = [method]

    if not url.startswith('^'):
        url = '^' + url

    if not url.endswith('$'):
        url += '$'

    url_re = re.compile(url)

    def _wrap(func):
        cls_name = inspect.stack()[1][3]
        if not cls_name == '<module>':
            mod_name = '.'.join([func.__module__, cls_name])
            func_name = func.__name__
        else:
            mod_name = None
            func_name = '.'.join([func.__module__, func.__name__])
        _update_route(mod_name, {})

        mod_dict = _get_route(mod_name)
        for _pack in _packs:
            if _pack not in mod_dict:
                mod_dict[_pack] = {}

            mod_dict[_pack][url_re] = (mod_name, func_name)

        @wraps(func)
        def _wrap_func(*args, **kwargs):
            _obj = get_self_object(func, *args)
            if _obj:
                val = get_func_environ(args, URLMiddleware.METHOD_LOCAL_NAME)
                setattr(_obj, class_member_name, val)

            return runner_return(func, *args, **kwargs)
        return _wrap_func
    return _wrap


def get_self_object(func, *args):
    _obj = None
    if args and hasattr(args[0], func.__name__):
        _obj = args[0]
    return _obj


def get_virtual_config_inside(func, class_object=None):
    # Support decorator
    if class_object:
        _name = str(class_object.__class__).split()[1].strip('>').strip("'")
    else:
        _name = '.'.join([func.__module__, func.__name__])

    return VirtualShell.config.get(_name, {})


def get_virtual_config(class_object=None):
    _name = inspect.stack()[1][3]
    if class_object:
        _name = str(class_object.__class__).split()[1].strip('>').strip("'")
    else:
        _pack = inspect.stack()[1][1]
        _pack = str(_pack).split(VirtualShell.root_path)
        if len(_pack) > 1:
            _pack = _pack[1].strip('/').strip('.py').strip('\\').replace('/', '.').replace('\\', '.')
        _name = '.'.join([_pack, _name])

    return VirtualShell.config.get(_name, {})


def get_func_environ(d, item):
    if d:
        env = d[-1]
        return env.get(item, {}) if isinstance(env, dict) else {}
    else:
        return {}


def ignore_function_environ(d):
    if len(d) > 1:
        val = tuple(d[:-1]) if isinstance(d[-1], dict) else tuple(d[:])
    else:
        val = () if not d or isinstance(d[0], dict) else (d[0], )
    return val


def runner_return(func, *args, **kwargs):
    if str(func.__code__).split()[2] != func.__name__:
        return func(*args, **kwargs)
    else:
        return func(*ignore_function_environ(args), **kwargs)


class VirtualShell(object):
    config = {}
    root_path = None

    def __init__(self):
        self.objects = {}
        self.mapping_api = {}

    def run(self, name, method, env, **kwargs):
        if method not in self.mapping_api:
            raise NotFound()
        apis = self.mapping_api[method]
        selected_name = None
        for k in apis.keys():
            if k.match(name):
                selected_name = k
                break
        if selected_name:
            mod_name, func_name = apis[selected_name]
            if not mod_name:
                meth = self.objects[func_name]
            else:
                obj = self.objects[mod_name]
                meth = getattr(obj, func_name)

            environ = {}
            environ.update(env)

            return meth(environ, **kwargs)
        else:
            raise NotFound()

    def _update_mapping(self, name):
        _conf = _get_route(name)
        if _conf:
            for _method, _dict in _conf.items():
                if _method not in self.mapping_api:
                    self.mapping_api[_method] = _dict
                _map_dict = self.mapping_api[_method]
                for _match, _api_args in _dict.items():
                    _map_dict[_match] = _api_args

    def load_model(self, mod, config=None):
        mod_name = mod.func
        mod_name = '.'.join([mod_name.__module__, mod_name.__name__])
        VirtualShell.config[mod_name] = config

        if mod_name not in self.objects:
            if inspect.isclass(mod.func):
                self.objects[mod_name] = mod()
            else:
                self.objects[mod_name] = mod

        # Update object-function mapping
        self._update_mapping(mod_name)
        # Update function mapping
        self._update_mapping(None)

    @staticmethod
    def load_root(root_path):
        VirtualShell.root_path = root_path
