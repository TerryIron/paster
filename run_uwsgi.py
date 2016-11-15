#!/usr/bin/env python
# coding=utf-8
import sys
import os.path

from paster.dev.vshell import VShell
from paster.deploy import loadapp
from paster.log import get_logger


__author__ = 'terry'


logger = get_logger(__name__)


here = os.path.dirname(os.path.abspath(__file__))

default_conf_path = os.path.join(here, './uwsgi.ini')
default_uwsgi_path = os.path.join(here, './.uwsgi_conf')


def get_app(app_name):

    app = loadapp('config:setting.ini', sys.platform, relative_to=here)
    for name, (_app, _conf) in app.items():
        if name == app_name:
            return _app

application = get_app('main_ctl')


def process_conf(app_path, init_path, name, data):
    with open(init_path, 'w') as f:
        f.write(data)
    context = """
import sys
import os.path

here = os.path.dirname(os.path.abspath(__file__))
root = os.path.join(here, '..')

sys.path.insert(0, root)

from paster.deploy import loadapp
from paster.log import get_logger

logger = get_logger(__name__)


def get_app(app_name):

    app = loadapp('config:setting.ini', sys.platform, relative_to=root)
    for name, (_app, _conf) in app.items():
        if name == app_name:
            return _app

application = get_app('{service_name}')
    """
    with open(app_path, 'w') as f:
        f.write(context.format(service_name=name))


class Shell(VShell):
    def prepare(self):
        pass
        command = self.command('start', help_text=u"启动服务")
        command.install_argument(['-i', '--ini'], 'config', default='uwsgi.ini', help_text=u"配置文件")
        command.install_argument(['-d', '--daemon'], 'daemon', is_bool=True, help_text=u"启动守护进程")
        # command = self.command('restart', help_text=u"重新启动服务")
        # command.install_argument(['-i', '--ini'], 'config', default='setting.ini', help_text=u"配置文件")
        # command.install_argument(['-d', '--daemon'], 'daemon', is_bool=True, help_text=u"启动守护进程")

    def run(self):
        if self.has_command('start'):
            conf = self.get_argument('config')
            daemon = self.get_argument('daemon')

            f = open(conf, 'r')
            data = f.read()

            def run_uwsgi(is_daemon=True):
                if not os.path.exists(default_uwsgi_path):
                    os.mkdir(default_uwsgi_path)

                app = loadapp('config:setting.ini', sys.platform, relative_to=here)
                for name, (_app, _conf) in app.items():
                    new_data = data.format(address=_conf['address'],
                                           port=_conf['port'],
                                           name=name)
                    process_conf(os.path.join(default_uwsgi_path, name + '.py'),
                                 os.path.join(default_uwsgi_path, name + '.ini'),
                                 name, new_data)

                cmd = "uwsgi --emperor {0}".format(default_uwsgi_path)
                os.system(cmd)
            return run_uwsgi(is_daemon=daemon)

if __name__ == '__main__':
    shell = Shell()
    shell.run()
