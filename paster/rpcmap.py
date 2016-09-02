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

import os
import cgi
import copy
try:
    import cpickle as pickle
except:
    import pickle

try:
    from UserDict import DictMixin
except ImportError:
    from collections import MutableMapping as DictMixin
from functools import partial

import rpcexceptions
from utils import as_config, import_class
from log import handler_init


def _load_factory(factory_line, global_conf, **local_conf):
    model, cls = factory_line.split(':')
    cls = cls.split('.')
    if len(cls) > 1: func = cls[1]
    else: func = 'factory'
    model = '.'.join([model, cls[0]])
    middleware = import_class(model)
    func = getattr(middleware, func)
    if callable(func):
        return func(global_conf, **local_conf)


def _get_shell_kwargs(local_conf):
    d = dict()
    for key in local_conf.keys():
        if key.startswith('shell_class_'):
            d[key.split('shell_class_')[1]] = eval(local_conf.pop(key))
    return d


def _get_model_kwargs(local_conf):
    d = dict()
    for key in local_conf.keys():
        if key.startswith('model_'):
            d[key.split('model_')[1]] = eval(local_conf.pop(key))
    return d


def shell_factory(loader, global_conf, **local_conf):
    assert 'paste.app_factory' in local_conf, 'please install model config as paste.app_factory=x'
    assert 'shell_class' in local_conf, 'please install model config as shell_class=x'
    assert 'shell' in local_conf, 'please install model config as shell=x'
    app_factory = local_conf.pop('paste.app_factory')
    shell_class = local_conf.pop('shell_class')
    shells = local_conf.pop('shell').split()
    root_path = os.path.dirname(global_conf['__file__'])
    shell_class_kw = _get_shell_kwargs(local_conf)
    sh = import_class(shell_class)(**shell_class_kw)
    sh.load_root(root_path)
    conf = as_config(global_conf['__file__'])
    for shell in shells:
        sh_conf = dict()
        for k, v in conf.items('shell:{0}'.format(shell)):
            sh_conf[k] = v
        models = sh_conf.pop('models', None)
        models = models.split() if models else []
        for model in models:
            mod_conf = dict()
            mod_conf.update(sh_conf)
            for k, v in conf.items('model:{0}'.format(model)):
                mod_conf[k] = v
            model_kwargs = _get_model_kwargs(mod_conf)
            model = loader.get_app(model, global_conf=global_conf)
            mod = import_class(model, root_path)
            mod = partial(mod, **model_kwargs)
            sh.load_model(mod, config=mod_conf)
    local_conf['shell'] = sh
    app = _load_factory(app_factory, global_conf, **local_conf)
    return app


def platform_factory(loader, global_conf, **local_conf):
    assert 'platform' in local_conf, 'please install platform config as platform=x'
    _log_format = global_conf.get('log_format', None)
    _log_level = global_conf.get('log_level', None)
    _log_path = global_conf.get('log_path', None)
    handler_init(_log_path, _log_level, _log_format)
    platform = {}
    platform_address = local_conf.get('platform_address', '127.0.0.1')
    for i, pf in enumerate(local_conf['platform'].split()):
        app = loader.get_app(pf, global_conf=global_conf)
        try:
            _key = local_conf['platform_listen'].split()[i]
            _key = _key.split(':')
            if len(_key) > 1:
                _key = (_key[0], int(_key[1]))
            else:
                _key = (platform_address, int(_key[0]))
        except:
            _key = (platform_address, 8000)
        platform[_key] = app
    return platform


def filter_factory(global_conf, **local_conf):
    _filter_factory = local_conf.pop('paste.filter_factory')
    _filter = _load_factory(_filter_factory, global_conf, **local_conf)
    return _filter


def rpcmap_factory(loader, global_conf, **local_conf):
    if 'not_found_app' in local_conf:
        not_found_app = local_conf.pop('not_found_app')
    else:
        not_found_app = global_conf.get('not_found_app')
    if not_found_app:
        not_found_app = loader.get_app(not_found_app, global_conf=global_conf)

    rpcmap = RPCMap(not_found_app=not_found_app)
    for rpc_line, app_name in local_conf.items():
        rpc_line = parse_rpcline_expression(rpc_line)
        app = loader.get_app(app_name, global_conf=global_conf)
        rpcmap[rpc_line] = app
    return rpcmap


def parse_rpcline_expression(rpcline):
    try:
        return pickle.dumps(dict([item.split('|', 1) for item in rpcline.split(',')]))
    except:
        return rpcline
    

class RPCMap(DictMixin):
    def __init__(self, not_found_app=None):
        self.applications = []
        if not not_found_app:
            not_found_app = self.not_found_app
        self.not_found_application = not_found_app

    def not_found_app(self, environ, start_response=None):
        environ_is_dict = isinstance(environ, dict)
        mapper = environ.get('paste.rpcmap_object') if environ_is_dict else None
        if mapper:
            matches = [p for p, a in mapper.applications]
            extra = 'defined apps: %s' % (
                ',\n  '.join(map(repr, matches)))
        else:
            extra = ''
        excute = environ.get('execute') if environ_is_dict else None
        extra += '\nEXECUTE: %r' % excute
        app = rpcexceptions.RPCNotFound(
            excute, comment=cgi.escape(extra))
        return app.wsgi_application(app.message, start_response)

    def sort_apps(self):
        self.applications.sort()

    def __setitem__(self, rpc, app):
        if app is None:
            try:
                del self[rpc]
            except KeyError:
                pass
        dom_rpc = self.normalize_rpc(rpc)
        if dom_rpc in self:
            del self[dom_rpc]
        self.applications.append((dom_rpc, app))
        self.sort_apps()

    def __getitem__(self, rpc):
        dom_rpc = self.normalize_rpc(rpc)
        for app_rpc, app in self.applications:
            if app_rpc == dom_rpc:
                return app
        raise KeyError(
            "No application with the rpcline %r (existing: %s)"
            % (rpc, self.applications))

    def __delitem__(self, rpc):
        rpc = self.normalize_rpc(rpc)
        for app_rpc, app in self.applications:
            if app_rpc == rpc:
                self.applications.remove((app_rpc, app))
                break
            else:
                raise KeyError(
                    "No application with the rpcline %r" % (rpc,))

    def normalize_rpc(self, rpc):
        try:
            _rpc = pickle.loads(rpc)
            assert isinstance(_rpc, dict), 'RPC request format error.'
            return rpc
        except:
            return rpc

    def keys(self):
        return [app_rpc for app_rpc, app in self.applications if app_rpc != 'transport']

    def items(self):
        return [(pickle.loads(app_rpc), app) for app_rpc, app in self.applications if app_rpc != 'transport']

    def transports(self):
        return [app for app_rpc, app in self.applications if app_rpc == 'transport']

    @staticmethod
    def _check_rpc_exist(rpc, environ):
        app_is_found = True
        for k, v in rpc.items():
            if (k not in environ) or environ[k] != v:
                app_is_found = False
                break
        return app_is_found

    @staticmethod
    def _is_environ_dict(environ):
        return isinstance(environ, dict)

    def __call__(self, environ, start_response=None):
        is_environ_dict = self._is_environ_dict(environ)
        _environ = None
        while not is_environ_dict:
            copy_environ = copy.copy(environ)
            for _app in self.transports():
                _environ = _app(copy_environ, start_response)
                is_environ_dict = self._is_environ_dict(_environ)
            break
        if not _environ:
            _environ = environ
        for app_rpc_dict, app in self.items():
            if is_environ_dict and self._check_rpc_exist(app_rpc_dict, _environ):
                for _app in app:
                    _environ = _app(_environ, start_response)
                return _environ
        if is_environ_dict:
            _environ['paste.rpcmap_object'] = self
        return self.not_found_application(_environ, start_response)
