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
import inspect
import os.path
from io import BytesIO
from functools import partial, wraps

from deploy import loadapp
from rpcmap import FILE_PATH, URL_PATH
from utils import myException, as_config
from content import get_default_content_type, get_content_process
from log import get_logger

__author__ = 'terry'


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


def proto_load_config(name, obj, config_proto):
    obj = ''.join(obj.split('config:')[1:])
    relative_to = config_proto.relative_path()
    if obj.startswith('normal:'):
        _path = obj.split('normal:')[1]
        try:
            _path, sect = _path.split(':')
            _obj = as_config(os.path.join(relative_to, _path))
            if sect.lower() == 'default':
                config = _obj.defaults()
            else:
                config = {}
                for _k in _obj.options(sect):
                    config[_k] = _obj.get(sect, _k)
            config_proto.set_config(config)
            _ret = config.get(name, '')
            return _ret
        except:
            _ret = as_config(os.path.join(relative_to, _path))
            setattr(_ret, '__path__', os.path.join(relative_to, os.path.dirname(_path)))
            return _ret
    else:
        return loadapp(obj, relative_to=relative_to)


def proto_load_version(name, obj, config_proto):
    config = config_proto.get_config()
    _conf = {'__default__': None}
    for ver in obj.split():
        ver = ''.join(ver.split('version:')[1:])
        if ver.startswith('apply:'):
            _ver = ver.split('apply:')[1]
            _val = config.get('_'.join([name, _ver]))
            _conf[_ver] = _val
        elif ver.startswith('default:'):
            _ver = ver.split('default:')[1]
            _val = config.get('_'.join([name, _ver]))
            _conf[_ver] = _val
            if not _conf['__default__']:
                _conf['__default__'] = _ver
    return _conf


def parse_config_proto(name, obj, config, relative_to):
    _config_proto_dict = {
        'config:': proto_load_config,
        'version:': proto_load_version
    }
    if isinstance(obj, str) and len(obj.split(':')) >= 3:
        _config_proto_dict_items = _config_proto_dict.items()
        for k, f in _config_proto_dict_items:
            if k in obj:
                _config = {'config': {}}
                _config['config'].update(config)

                def get_config():
                    return _config['config']

                def set_config(conf):
                    _config['config'] = conf

                class ConfigProto:
                    def relative_path(self):
                        return relative_to

                    def get_config(self):
                        return get_config()

                    def set_config(self, conf):
                        set_config(conf)

                proto = ConfigProto()

                _val = f(name, obj, proto)
                return parse_config_proto(name, _val, proto.get_config(), proto.relative_path())
    return obj


def load_config(dict_obj, relative_to=''):
    _config = {}
    for k, v in dict_obj.items():
        if isinstance(v, str):
            _v = parse_config_proto(k, v, dict_obj, relative_to)
            _config[k] = _v
        else:
            _config[k] = v
    return _config


class WSGIMiddleware(object):
    middleware = {}
    hooks = {}
    app_name_re = re.compile('^(\[[^]]*\]).*')

    @classmethod
    def factory(cls, global_config, **local_config):
        sh = local_config.pop('shell') if 'shell' in local_config else None
        here = os.path.dirname(global_config[FILE_PATH])
        global_config = as_config(global_config[FILE_PATH])
        _global_config = load_config(getattr(global_config, '_defaults', {}), here)
        _local_name = local_config[URL_PATH]
        _local_app_name = cls.app_name_re.match(_local_name).groups()[0]
        if _local_name not in cls.middleware:
            cls.middleware[_local_name] = []
        _local_config = load_config(local_config, here)
        cls.middleware[_local_name].append((cls, _global_config, _local_config, sh))
        if _local_app_name not in cls.hooks:
            cls.hooks[_local_app_name] = set()
        if sh:
            for hook in getattr(sh, 'hooks', []):
                if callable(hook):
                    cls.hooks[_local_app_name].add(hook)

        def call_factory(context=None, start_response=None, app_name=None):
            return cls._factory(context, start_response, app_name=app_name)

        call_factory_wrap = partial(call_factory, app_name=_local_app_name)
        return call_factory_wrap, cls.hooks[_local_app_name]

    @classmethod
    def _factory(cls, context, start_response=None, app_name=None):
        _start_response = start_response
        _context = type('Response', (), {'content': None, 'status_code': 200})
        _composite_url = app_name + context['SCRIPT_NAME']
        for c, _conf, _local_conf, sh in cls.middleware[_composite_url][::-1]:
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
            logger.error(traceback.format_exc())
            return self.resposne_error(e, start_response)

    def _get_request_info(self, context):
        target_name = context.get('PATH_INFO', None)
        method_name = context.get('REQUEST_METHOD', 'GET')
        if target_name and method_name:
            kwargs = context.get('REQUEST_KWARGS', {})
            return target_name, method_name, kwargs
        else:
            raise BadRequest('Bad request for {0}:{1}'.format(target_name, method_name))

    def filter_request(self, target_name, method, arg_list, context):
        method = [method] if not isinstance(method, list) else method
        _target_name, _method_name, _kwargs = self._get_request_info(context)
        if not (_target_name == target_name and _method_name in method):
            return False, None

        content_type = context.get('CONTENT_TYPE', get_default_content_type())
        content_type = str(content_type).split()[0].strip(';')
        request_body_size = int(context.get('CONTENT_LENGTH', 0))
        request_body = context['wsgi.input'].read(request_body_size)
        _content_process = get_content_process()
        if content_type in _content_process:
            out_kwargs = _content_process[content_type](request_body)
            context['paster.kwargs'] = request_body
            if isinstance(out_kwargs, dict):
                _kwargs.update(out_kwargs)
        _new = {}
        try:
            for arg in arg_list:
                _new[arg] = _kwargs[arg]
        finally:
            return True, _new

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


class FunctionEnviron(object):
    def __init__(self, env):
        self.env = env if isinstance(env, dict) else {}

    def get(self, item, default=None):
        if item in self.env:
            return self.env[item]
        else:
            return {} if not default else default


class URLMiddleware(Middleware, WSGIMiddleware):
    METHOD_LOCAL_NAME = '__method_name__'
    
    def process_request(self, context, start_response):
        if self.handler:
            if not hasattr(self.handler, 'run'):
                raise NotFound('Resource Handler not found')
            target_name, method_name, kwargs = self._get_request_info(context)

            content_type = context.get('CONTENT_TYPE', get_default_content_type())
            content_type = str(content_type).split()[0].strip(';')
            _file = None

            def process_request_body():
                def text_plain_process(rbody):
                    global _file
                    _file = BytesIO(rbody)

                request_body_size = int(context.get('CONTENT_LENGTH', 0))
                if 'paster.kwargs' not in context:
                    request_body = context['wsgi.input'].read(request_body_size)
                else:
                    request_body = context['paster.kwargs']
                text_plain_process(request_body)

                def _process_request_body(url_kwargs):
                    _content_process = get_content_process()
                    # logger.debug(_content_process)
                    logger.debug(content_type)
                    if content_type in _content_process and request_body:
                        out_kwargs = _content_process[content_type](request_body)
                        if isinstance(out_kwargs, dict):
                            url_kwargs.update(out_kwargs)
                        return url_kwargs
                return _process_request_body

            pro_method = process_request_body()

            class HeaderDict(dict):
                def __getitem__(self, item):
                    super(HeaderDict, self).__getitem__(str(item).lower())

                def __setitem__(self, item, value):
                    super(HeaderDict, self).__setitem__(str(item).lower(), value)

            headers_env = HeaderDict()
            for k in [key.split('HTTP_')[1] for key in context.keys() if key.startswith('HTTP_') and len(key) > 5]:
                headers_env[k] = context['HTTP_' + k]
            push_environ_args(context,
                              URLMiddleware.METHOD_LOCAL_NAME,
                              dict(method=method_name,
                                   file=_file,
                                   headers=headers_env,
                                   url=target_name))
            func_env = context.get('paster.args', {})
            cb = partial(self.handler.run,
                         target_name,
                         method_name + content_type,
                         FunctionEnviron(func_env),
                         partial(pro_method, kwargs))
            context = cb()
        return super(URLMiddleware, self).process_request(context, start_response)


DEFAULT_ROUTES = {}


def _update_route(key, val):
    if key not in DEFAULT_ROUTES:
        DEFAULT_ROUTES[key] = val


def _get_route(key):
    if key in DEFAULT_ROUTES:
        return DEFAULT_ROUTES[key]


def route(url, method='GET', content_type=get_default_content_type(), class_member_name='__method__'):
    """
    路由装饰器, 将method对象绑定在__method__(类对象缓存名)属性

    :param url: url路径
    :param method: 请求方式
    :param content_type: 类型
    :param class_member_name: 类对象缓存名
    :return:
    """
    url = str(url)

    if isinstance(method, list):
        _packs = [m + content_type for m in method]
    else:
        _packs = [method + content_type]

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

    if _name in VirtualShell.config:
        return VirtualShell.config.get(_name, {})
    else:
        return VirtualShell.config.get('__default__', {})


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

    if _name in VirtualShell.config:
        return VirtualShell.config.get(_name, {})
    else:
        return VirtualShell.config.get('__default__', {})


def get_func_environ(d, item):
    if d:
        env = d[-1]
        return env.get(item, {}) if isinstance(env, FunctionEnviron) else {}
    else:
        return {}


def ignore_function_environ(d):
    if len(d) > 1:
        val = tuple(d[:-1]) if isinstance(d[-1], FunctionEnviron) else tuple(d[:])
    else:
        val = () if not d or isinstance(d[0], FunctionEnviron) else (d[0], )
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
        self.hook_objects = {}
        self.mapping_api = {}

    def run(self, name, method, env, kwargs_callback):
        if method not in self.mapping_api:
            raise NotFound()
        _apis, _meth = self.mapping_api[method], None
        for k, m in _apis:
            mod, func = m
            if k.match(name):
                _meth = self._get_method(mod, func)
                break
        if _meth:
            kwargs = kwargs_callback()
            kwargs = kwargs if kwargs else {}

            return _meth(env, **kwargs)
        else:
            raise NotFound()

    def _get_method(self, mod_name, func_name):
        if not mod_name:
            _meth = self.hook_objects[func_name]
        else:
            obj = self.hook_objects[mod_name]
            _meth = getattr(obj, func_name)
        return _meth

    def _update_mapping(self, name):
        _conf = _get_route(name)
        if _conf:
            for _method, _dict in _conf.items():
                if _method not in self.mapping_api:
                    self.mapping_api[_method] = []
                _map_dict = self.mapping_api[_method]
                for _match, _api_args in _dict.items():
                    _map_dict.append((_match, _api_args))

    def load_model(self, mod, global_conf=None, local_conf=None, relative_to=''):
        mod_name = mod.func
        mod_name = '.'.join([mod_name.__module__, mod_name.__name__])
        relative_dir = os.path.dirname(relative_to)
        if '__default__' not in VirtualShell.config:
            VirtualShell.config['__default__'] = load_config(global_conf, relative_to=relative_dir)
        VirtualShell.config[mod_name] = load_config(local_conf, relative_to=relative_dir)

        if mod_name not in self.hook_objects:
            if inspect.isclass(mod.func):
                self.hook_objects[mod_name] = mod()
            else:
                self.hook_objects[mod_name] = mod

        # Update object-function mapping
        self._update_mapping(mod_name)
        # Update function mapping
        self._update_mapping(None)

    @property
    def hooks(self):
        return self.hook_objects.values()

    @staticmethod
    def load_root(root_path):
        VirtualShell.root_path = root_path
