#!/usr/bin/env python
# coding=utf-8
import sys
import datetime
import os.path
import tornado.gen
from tornado.httpserver import HTTPServer
from tornado.wsgi import WSGIContainer
from tornado.ioloop import IOLoop
from functools import wraps

from paster.dev.vshell import VShell
from paster.deploy import loadapp
from paster.log import get_logger


__author__ = 'terry'


logger = get_logger(__name__)


here = os.path.dirname(os.path.abspath(__file__))


def call_later(delay=0):
    def wrap_loop(func):

        @wraps(func)
        def wrap_func(*args, **kwargs):
            return IOLoop.instance().call_later(delay, func, *args, **kwargs)
        return wrap_func
    return wrap_loop


def sync_loop_call(delta=60):
    _delta = delta * 1000
    _args = {'args': None}

    def wrap_loop(func):
        @wraps(func)
        @tornado.gen.coroutine
        def wrap_func(*args, **kwargs):
            ret = None
            if not _args['args']:
                _args['args'] = args
            try:
                ret = func(*_args['args'], **kwargs)
            except Exception as e:
                pass

            IOLoop.instance().add_timeout(datetime.timedelta(milliseconds=_delta), wrap_func)
            return ret
        return wrap_func
    return wrap_loop


class Shell(VShell):
    def prepare(self):
        pass
        command = self.command('start', help_text=u"启动服务")
        command.install_argument(['-i', '--ini'], 'config', default='setting.ini', help_text=u"配置文件")
        command.install_argument(['-d', '--daemon'], 'daemon', is_bool=True, help_text=u"启动守护进程")
        # command = self.command('restart', help_text=u"重新启动服务")
        # command.install_argument(['-i', '--ini'], 'config', default='setting.ini', help_text=u"配置文件")
        # command.install_argument(['-d', '--daemon'], 'daemon', is_bool=True, help_text=u"启动守护进程")

    def run(self):
        def _run(_conf, _is_daemon):
            app = loadapp('config:{0}'.format(_conf), sys.platform, relative_to=here)
            for _app, _conf in app.values():
                _app.init()
                container = WSGIContainer(_app)
                http_server = HTTPServer(container)
                # http_server = HTTPServer(container, ssl_options={'certfile': 'foobar.crt',
                #                                                  'keyfile': 'foobar.key'
                #                                                  })
                http_server.listen(port=_conf['port'], address=_conf['address'])
            IOLoop.instance().start()
        if self.has_command('start'):
            conf = self.get_argument('config')
            daemon = self.get_argument('daemon')
            _run(conf, daemon)
        # if self.has_command('restart'):
        #     conf = self.get_argument('config')
        #     daemon = self.get_argument('daemon')
        #     _run(conf, daemon)

if __name__ == '__main__':
    shell = Shell()
    shell.run()
