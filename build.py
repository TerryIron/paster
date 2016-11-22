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

import commands
import os
import os.path

from utils.vshell import VShell


class Shell(VShell):
    def prepare(self):
        command = self.command('all', help_text=u'生成环境')
        command.install_argument(['-i', '--ignore'], 'ignore_dir', default=['env'], help_text=u'可以忽略的目录')
        command.install_argument(['-t', '--topdir-packname'], 'top_dir', default='__top__',
                                 help_text=u'设置根目录')
        command = self.command('clean', help_text=u'释放环境')
        command.install_argument(['-t', '--topdir-packname'], 'top_dir', default='__top__',
                                 help_text=u'设置根目录')

    def run(self):
        git_dir = ['.git']
        front_dir = ['static', 'templates']
        default_dir = ['paster']
        if self.has_command('all'):
            _ignore = self.get_argument('ignore_dir')
            _topname = self.get_argument('top_dir')
            if isinstance(_ignore, str):
                _ignore = _ignore.split(',')
            ignore_dir = git_dir + front_dir + default_dir + _ignore
            ignore_str = '\|'.join(ignore_dir)
            cur_dir = os.getcwd()

            if commands.getoutput('find . -type f | grep ".*{0}.py"'.format(_topname)):
                raise Exception("Please change name of top package name by '-t'")

            def check(_dir):
                _dir = os.path.join(cur_dir, _dir)
                for l in default_dir:
                    if _dir.endswith(l):
                        return None
                return _dir

            def tempfile(filename, topdir):
                if not os.path.exists(filename):
                    with open(filename, 'w') as f:
                        temp = """
import sys
import os.path

top_dir = os.path.join(os.path.dirname(__file__), '{0}')
abs_dir = os.path.abspath(top_dir)
if abs_dir not in sys.path:
    sys.path.insert(0, top_dir)
""".format(topdir)
                        f.write(temp)

            for d in [i for i in commands.getoutput('find . -type d  | grep -v "{0}"'.format(ignore_str)).split()
                      if check(i)]:
                _dir_path = '/'.join(['..' for i in d.split('/') if i != '.'])
                if _dir_path and os.path.exists(os.path.join(d, '__init__.py')):
                    file_name = os.path.join(d, _topname + '.py')
                    tempfile(file_name, _dir_path)
        if self.has_command('clean'):
            ignore_dir = git_dir + front_dir + default_dir
            _topname = self.get_argument('top_dir')
            grep_dir = ['paster']
            grep_str = '\|'.join(grep_dir)
            for d in commands.getoutput('find . -type f | grep -v "{0}" | grep "{1}.py"'.format(grep_str, _topname)).split():
                commands.getoutput('rm -f {0}'.format(d))


if __name__ == '__main__':
    shell = Shell()
    shell.run()
