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
import werkzeug.http
import urlparse
import copy
from paste.urlmap import URLMap as _URLMap, parse_path_expression
from zope.mimetype import typegetter

from utils import myException
from wsgi import NotFound
from http import is_response_wrapper
from rpcmap import URL_PATH
from log import get_logger

__author__ = 'terry'


logger = get_logger(__name__)


def urlmap_factory(loader, global_conf, **local_conf):
    if 'not_found_app' in local_conf:
        not_found_app = local_conf.pop('not_found_app')
    else:
        not_found_app = global_conf.get('not_found_app')
    if not_found_app:
        not_found_app = loader.get_app(not_found_app, global_conf=global_conf)
    _map = URLMap(not_found_app=not_found_app)
    for path, app_name in local_conf.items():
        path = parse_path_expression(path)
        _global_conf = copy.copy(global_conf)
        if URL_PATH not in _global_conf:
            _global_conf[URL_PATH] = '[{0}]'.format(app_name)
        _global_conf[URL_PATH] += path
        app, hooks = loader.get_app(app_name, global_conf=_global_conf)
        _map[path] = app
        for hook in hooks:
            _map.add_hook(hook)
    return _map


class UnsupportedContentTypes(myException):
    """Raised when not found content-type in local environ"""


SUPPORTED_CONTENT_TYPES = [
    'application/json',
    'application/xml',
]


class URLMap(_URLMap):
    def __init__(self, not_found_app=None):
        self.hooks = set()
        super(URLMap, self).__init__(not_found_app=not_found_app)

    def add_hook(self, callback):
        if callable(callback):
            self.hooks.add(callback)

    def init(self):
        for hook in self.hooks:
            if callable(hook):
                hook()

    def _match(self, host, port, path_info):
        """Find longest match for a given URL path."""
        for (domain, app_url), app in self.applications:
            if domain and domain != host and domain != host + ':' + port:
                continue
            if path_info == app_url or path_info.startswith(app_url + '/'):
                return app, app_url

        return None, None

    def _set_script_name(self, app, app_url):
        def wrap(environ, start_response):
            environ['SCRIPT_NAME'] += app_url
            return app(environ, start_response)

        return wrap

    def _munge_path(self, app, path_info, app_url):
        def wrap(environ, start_response):
            environ['SCRIPT_NAME'] += app_url
            environ['PATH_INFO'] = path_info[len(app_url):]
            return app(environ, start_response)
        return wrap

    def _path_strategy(self, host, port, path_info):
        """Check path suffix for MIME type and path prefix for API version."""
        mime_type = app = app_url = None

        parts = path_info.rsplit('.', 1)
        if len(parts) > 1:
            possible_type = 'application/' + parts[1]
            if possible_type in SUPPORTED_CONTENT_TYPES:
                mime_type = possible_type

        parts = path_info.split('/')
        if len(parts) > 1:
            possible_app, possible_app_url = self._match(host, port, path_info)
            # Don't use prefix if it ends up matching default
            if possible_app and possible_app_url:
                app_url = possible_app_url
                app = self._munge_path(possible_app, path_info, app_url)

        return mime_type, app, app_url

    def _content_type_strategy(self, host, port, environ):
        """Check Content-Type header for API version."""
        app = None
        params = werkzeug.http.parse_options_header(environ.get('CONTENT_TYPE', ''))[1]
        if 'version' in params:
            app, app_url = self._match(host, port, '/v' + params['version'])
            if app:
                app = self._set_script_name(app, app_url)

        return app

    def _accept_strategy(self, host, port, environ, supported_content_types):
        """Check Accept header for best matching MIME type and API version."""
        accept = werkzeug.http.parse_accept_header(environ.get('HTTP_ACCEPT', ''))

        app = None

        # Find the best match in the Accept header
        match = accept.best_match(supported_content_types)
        if match:
            mime_type, params = match[0], match[1]
        else:
            mime_type, params = None, dict()
        if 'version' in params:
            app, app_url = self._match(host, port, '/v' + params['version'])
            if app:
                app = self._set_script_name(app, app_url)

        return mime_type, app

    def not_found(self, environ, start_response):
        mime_type, err = self.get_support_mimetype(), NotFound()
        _header = (('CONTENT-TYPE', mime_type), )
        start_response(self.get_status_code(err.status_code), list(_header), )
        return json.dumps(dict(err_msg=str(err), err_code=err.error_code), ensure_ascii=False)

    @staticmethod
    def get_support_mimetype():
        return SUPPORTED_CONTENT_TYPES[0]

    @staticmethod
    def get_status_code(status_code):
        status_code = str(status_code)
        if status_code == '200':
            return status_code + ' OK'
        else:
            return status_code + ' Oops'

    def __call__(self, environ, start_response=None):
        host = environ.get('HTTP_HOST', environ.get('SERVER_NAME')).lower()
        if ':' in host:
            host, port = host.split(':', 1)
        else:
            if environ['wsgi.url_scheme'] == 'http':
                port = '80'
            else:
                port = '443'

        path_info = environ['PATH_INFO']
        path_info = self.normalize_url(path_info, False)[1]

        # The MIME type for the response is determined in one of two ways:
        # 1) URL path suffix (eg /servers/detail.json)
        # 2) Accept header (eg application/json;q=0.8, application/xml;q=0.2)

        # The API version is determined in one of three ways:
        # 1) URL path prefix (eg /v1.1/tenant/servers/detail)
        # 2) Content-Type header (eg application/json;version=1.1)
        # 3) Accept header (eg application/json;q=0.8;version=1.1)

        supported_content_types = list(SUPPORTED_CONTENT_TYPES)

        mime_type, app, app_url = self._path_strategy(host, port, path_info)

        # Accept application/atom+xml for the index query of each API
        # version mount point as well as the root index
        if (app_url and app_url + '/' == path_info) or path_info == '/':
            supported_content_types.append('application/atom+xml')

        if not app:
            app = self._content_type_strategy(host, port, environ)

        if not mime_type or not app:
            possible_mime_type, possible_app = self._accept_strategy(
                    host, port, environ, supported_content_types)
            if possible_mime_type and not mime_type:
                mime_type = possible_mime_type
            if possible_app and not app:
                app = possible_app

        if not app:
            # Didn't match a particular version, probably matches default
            app, app_url = self._match(host, port, path_info)
            if app:
                app = self._munge_path(app, path_info, app_url)

        if app:
            environ['best_content_type'] = mime_type
            if 'QUERY_STRING' in environ:
                environ['REQUEST_KWARGS'] = dict()
                for k, v in urlparse.parse_qs(environ['QUERY_STRING']).items():
                    environ['REQUEST_KWARGS'][k] = v[0]
            environ['paster.result'] = type('ResultIO', (), {'result': None})
            logger.debug(environ)
            val = app(environ, start_response)
            try:
                result, result_response = val
                environ['paster.result'].result = val
            except:
                try:
                    result, result_response = environ['paster.result'].result
                except:
                    return self.not_found(environ, start_response)
            mime_type = typegetter.mimeTypeGuesser(name=path_info)
            if not mime_type:
                mime_type = self.get_support_mimetype()

            def _verify_content(_result):
                _result.content = _result.content if _result.content else []

            def _get_status_code(_val):
                status_code = str(_val.status_code)
                return self.get_status_code(status_code)

            target = result.content
            if is_response_wrapper(target):
                _header = set([(k.upper(), v) for k, v in target.headers.items()])
                _header.add(('CONTENT-TYPE', mime_type))
                result_response(_get_status_code(target), list(_header), )

                _verify_content(target)
                return target.content
            else:
                _header = (('CONTENT-TYPE', mime_type), )
                result_response(_get_status_code(result), list(_header), )

                _verify_content(result)
                return json.dumps(result.content, ensure_ascii=False)

        return self.not_found(environ, start_response)
