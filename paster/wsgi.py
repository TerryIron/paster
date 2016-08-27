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
import traceback
import json
import inspect
from functools import partial, wraps


from utils import myException, as_config


class BadRequest(myException):
    """Raised when request comming with invalid data """
    status_code = 400


class NotFound(myException):
    """Raised when no handler to process request"""
    status_code = 404


class WSGIMiddleware(object):

    middleware = []

    @classmethod
    def factory(cls, global_config, **local_config):
        sh = local_config.pop('shell') if 'shell' in local_config else None
        global_config = as_config(global_config['__file__'])
        _global_config = {}
        for k, v in getattr(global_config, '_defaults', {}).items():
            _global_config[k] = v
        global_config = _global_config
        cls.middleware.append((cls, global_config, local_config, sh))

        def call_factory(context=None, start_response=None):
            return cls._factory(context, start_response)
        return call_factory

    @classmethod
    def _factory(cls, context, start_response=None):
        for c, g, l, sh in cls.middleware[::-1]:
            c = c(sh, g, **l)
            context = c.__call__(context, start_response)
        if isinstance(context, Exception):
            return dict(err_msg=str(context))
        return context


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
            return self.resposne_error(context)

        try:
            result = self.process_request(context, start_response)
            return self.resposne_normal(result)
        except Exception as e:
            return self.resposne_error(e)

    def process_request(self, context, start_response):
        return context

    def resposne_normal(self, context):
        return context

    def resposne_error(self, err):
        return err


class URLMiddleware(Middleware, WSGIMiddleware):
    def process_request(self, context, start_response):
        if not self.handler:
            return super(URLMiddleware, self).process_request(context, start_response)
        else:
            try:
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

                    request_body = context['wsgi.input'].read(request_body_size)
                    if request_body:
                        _kwargs = json.loads(request_body)
                        kwargs.update(_kwargs)
                    cb = partial(self.handler.run,
                                 target_name,
                                 method_name,
                                 **kwargs)
                    return cb()
                else:
                    raise BadRequest()
            except (TypeError, KeyError):
                raise BadRequest()
            except Exception as e:
                print traceback.print_exc()
                raise e


DEFAULT_ROUTES = {}


def _update_route(key, val):
    if key not in DEFAULT_ROUTES:
        DEFAULT_ROUTES[key] = val


def _get_route(key):
    if key in DEFAULT_ROUTES:
        return DEFAULT_ROUTES[key]


def route(url, method='GET'):
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

    def decorator(func):
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
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapper
    return decorator


def _get_virtual_config(func, class_object=None):
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


class VirtualShell(object):
    config = {}
    root_path = None

    def __init__(self):
        self.objects = {}
        self.mapping_api = {}

    def run(self, name, method, **kwargs):
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
            return meth(**kwargs)
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
