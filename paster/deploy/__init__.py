#########################################################################
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
#########################################################################

__author__ = 'terry'

import pkg_resources
import os.path
from paste.deploy.compat import unquote

############################################################                                                                                                                                              
## Object types
############################################################
import paste.deploy.loadwsgi
from paste.deploy.loadwsgi import _ObjectType, _PipeLine, _FilterApp, _App
from paste.deploy.loadwsgi import ConfigLoader, LoaderContext
from paste.deploy.loadwsgi import loadcontext, fix_call
from paste.deploy.loadwsgi import FILTER, FILTER_WITH

############################################################                                                                                                                                              
## Loaders
############################################################
from paste.deploy.loadwsgi import _loaders

from paste.deploy.loadwsgi import *

__all__ = ['loadapp', 'loadserver', 'loadfilter', 'appconfig']


class _PIPELINE(_PipeLine):
    name = 'pipeline'

    def invoke(self, context):
        app = context.app_context.create()
        filters = [c.create() for c in context.filter_contexts]
        return filters[-1]

PIPELINE = _PIPELINE()
paste.deploy.loadwsgi.PIPELINE = PIPELINE


class _Shell(_ObjectType):
    name = 'shell'
    config_prefixes = [['shell', 'sh']]
    egg_protocols = ['paste.shell_factory', 'paste.sh_factory']

    def invoke(self, context):
        sh = context.app_context.create()
        filters = [c.create() for c in context.filter_contexts]
        filters.reverse()
        for filter in filters:
            if filter: sh = filter(sh)
        return sh

SHELL = _Shell()


class _Model(_ObjectType):
    name = 'model'
    config_prefixes = [['model', 'mod']]
    egg_protocols = ['paste.model_factory', 'paste.mod_factory']

    def invoke(self, context):
        app = context.app_context.create()
        return app

MODEL = _Model()


#class _CommandPack(_PipeLine):
#    name = 'command_package'
#    config_prefixes = [['cmds', 'commands', 'cmd-pack', 'command-pack']]
#
#COMMANDPACK = _CommandPack()


#class _Command(_FilterApp):
#    name = 'command'
#    config_prefixes = [['command', 'cmd']]
#    egg_protocols = ['paste.command_factory', 'paste.cmd_factory']
#
#COMMAND = _Command()


class _APP(_App):
    egg_protocols = ['paste.app_factory',
                     'paste.platform_factory',
                     'paste.model_factory',
                     'paste.shell_factory',
                     'paste.filter_factory',
                     'paste.composit_factory',
                     'paste.composite_factory',
                     ]
    config_prefixes = [
                        ['app', 'application'],
                        ['platform', 'pf', 'plat'],
                        ['shell', 'sh'],
                        ['composite', 'composit'],
                        'pipeline', 'filter-app',
                        'model', 'filter',
                      ]

    def invoke(self, context):
        supports = [
            'paste.app_factory',
            'paste.platform_factory',
            'paste.shell_factory',
            'paste.model_factory',
            'paste.filter_factory',
        ]
        if context.protocol in supports:
            return fix_call(context.object,
                            context.loader, context.global_conf,
                            **context.local_conf)
        return super(_APP, self).invoke(context)

APP = _APP()
paste.deploy.loadwsgi.APP = APP


class _Platform(_ObjectType):
    name = 'platform'
    config_prefixes = [['platform', 'pf']]
    egg_protocols = ['paste.platform_factory']

    def invoke(self, context):
        app = context.app_context.create()
        filters = [c.create() for c in context.filter_contexts]
        filters.reverse()
        for filter in filters:
            if filter: app = filter(app)
        return app

PLATFORM = _Platform()


def app_context(self, name=None, global_conf=None):
    return self.get_context(APP, name=name, global_conf=global_conf)


class _ConfigLoader(ConfigLoader):
    SECTION_PASTER = [
        ('filter-app:', '_filter_app_context'),
        ('pipeline:', '_pipeline_app_context'),
        ('shell:', '_shell_app_context'),
        ('model:', '_model_app_context'),
    ]

    def get_context(self, object_type, name=None, global_conf=None):
        if self.absolute_name(name):
            return loadcontext(object_type, name,
                               relative_to=os.path.dirname(self.filename),
                               global_conf=global_conf)
        section = self.find_config_section(
            object_type, name=name)
        if global_conf is None:
            global_conf = {}
        else:
            global_conf = global_conf.copy()
        defaults = self.parser.defaults()
        global_conf.update(defaults)
        local_conf = {}
        global_additions = {}
        get_from_globals = {}
        for option in self.parser.options(section):
            if option.startswith('set '):
                name = option[4:].strip()
                global_additions[name] = global_conf[name] = (
                    self.parser.get(section, option))
            elif option.startswith('get '):
                name = option[4:].strip()
                get_from_globals[name] = self.parser.get(section, option)
            else:
                if option in defaults:
                    # @@: It's a global option (?), so skip it
                    continue
                local_conf[option] = self.parser.get(section, option)
        for local_var, glob_var in get_from_globals.items():
            local_conf[local_var] = global_conf[glob_var]
        if object_type in (APP, FILTER) and 'filter-with' in local_conf:
            filter_with = local_conf.pop('filter-with')
        else:
            filter_with = None
        if 'require' in local_conf:
            for spec in local_conf['require'].split():
                pkg_resources.require(spec)
            del local_conf['require']
        # Additional sections
        is_section_func = False
        for sect, parser in self.SECTION_PASTER:
            parser_func = getattr(self, parser)
            if callable(parser_func):
                if section.startswith(sect):
                    context = parser_func(
                        object_type, section, name=name,
                        global_conf=global_conf, local_conf=local_conf,
                        global_additions=global_additions)
                    is_section_func = True
                    break
        if not is_section_func:
            if 'use' in local_conf:
                context = self._context_from_use(
                    object_type, local_conf, global_conf, global_additions,
                    section)
            else:
                context = self._context_from_explicit(
                    object_type, local_conf, global_conf, global_additions,
                    section)
        if filter_with is not None:
            filter_with_context = LoaderContext(
                obj=None,
                object_type=FILTER_WITH,
                protocol=None,
                global_conf=global_conf, local_conf=local_conf,
                loader=self)
            filter_with_context.filter_context = self.filter_context(
                name=filter_with, global_conf=global_conf)
            filter_with_context.next_context = context
            return filter_with_context
        return context

    def _pipeline_app_context(self, object_type, section, name,
                              global_conf, local_conf, global_additions):
        if 'pipeline' not in local_conf:
            raise LookupError(
                "The [%s] section in %s is missing a 'pipeline' setting"
                % (section, self.filename))
        pipeline = local_conf.pop('pipeline').split()
        if local_conf:
            raise LookupError(
                "The [%s] pipeline section in %s has extra "
                "(disallowed) settings: %s"
                % (', '.join(local_conf.keys())))
        context = LoaderContext(None, PIPELINE, None, global_conf,
                                local_conf, self)
        context.filter_contexts = [
            self.get_context(FILTER, name, global_conf)
            for name in pipeline[:-1][::-1]]
        context.app_context = self.get_context(
             APP, pipeline[-1], global_conf)
        return context

    def _shell_app_context(self, object_type, section, name,
                           global_conf, local_conf, global_additions):
        if 'models' not in local_conf:
            raise LookupError(
                "The [%s] section in %s is missing a 'models' setting"
                % (section, self.filename))
        models = local_conf.pop('models').split()
        if local_conf:
            raise LookupError(
                "The [%s] platform section in %s has extra "
                "(disallowed) settings: %s"
                % (', '.join(local_conf.keys())))
        context = LoaderContext(None, MODEL, None, global_conf,
                                local_conf, self)
        context.app_context = self.get_context(APP, models[-1], global_conf)
        context.filter_contexts = [
            self.get_context(APP, name, global_conf)
            for name in models[:-1]]
        return context

    def _model_app_context(self, object_type, section, name,
                           global_conf, local_conf, global_additions):
        if 'model' not in local_conf:
            raise LookupError(
                "The [%s] section in %s is missing a 'model' setting"
                % (section, self.filename))

        model = local_conf.pop('model').split()

        class _MinModel(object):
            def __init__(self, model):
                self.model = model

            def create(self):
                return self.model

        context = _MinModel(model[-1])
        return context


def _loadconfig(object_type, uri, path, name, relative_to,
                global_conf):                                                                                                                              
    isabs = os.path.isabs(path)
    # De-Windowsify the paths:
    path = path.replace('\\', '/')
    if not isabs:
        if not relative_to:
            raise ValueError(
                "Cannot resolve relative uri %r; no relative_to keyword "
                "argument given" % uri)
        relative_to = relative_to.replace('\\', '/')
        if relative_to.endswith('/'):
            path = relative_to + path
        else:
            path = relative_to + '/' + path
    if path.startswith('///'):
        path = path[2:]
    path = unquote(path)
    loader = _ConfigLoader(path)
    if global_conf:
        loader.update_defaults(global_conf, overwrite=False)
    return loader.get_context(object_type, name, global_conf)

_loaders['config'] = _loadconfig
