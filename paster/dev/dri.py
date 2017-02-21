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

try:
    import cPickle as pickle
except:
    import pickle
try:
    from urlparse import urlparse
except:
    from urllib.parse import urlparse
import weakref
import functools
import datetime
from sqlalchemy import Table as _Table
from sqlalchemy import *
from sqlalchemy.exc import *
import sqlalchemy.util
from sqlalchemy import sql, event
from sqlalchemy.sql import util as sql_util
from sqlalchemy.sql.expression import ClauseElement
import sqlalchemy.orm.base as orm_base
import sqlalchemy.sql.schema
from sqlalchemy.ext.declarative import DeclarativeMeta, clsregistry
from sqlalchemy.ext.declarative.base import _MapperConfig
from sqlalchemy.orm.interfaces import MapperProperty
from sqlalchemy.ext.declarative import base
from sqlalchemy.orm.attributes import InstrumentedAttribute, QueryableAttribute
from sqlalchemy.orm import scoped_session, Session as _Session, sessionmaker, \
    relationship, query, mapper, synonym
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.pool import QueuePool
from sqlalchemy.util.langhelpers import symbol

__author__ = 'terry'


__all__ = ['declarative_base', 'sql', 'and_', 'or_', 'func', 'join', 'distinct',
           'Engine', 'SingleTonEngine', 'BaseOperation', 'Operation', 'BaseMixin',
           'Column', 'StrColumn', 'IntColumn', 'DateTimeColumn', 'Integer', 'String', 'DateTime', 'ForeignKey',
           'event', 'mapper', 'relationship', 'symbol']


def contain_version(ver, diff_ver):
    def _len(z):
        return len([_i for _i in z if _i == '.'])
    from distutils.version import LooseVersion

    if LooseVersion(ver) <= LooseVersion(diff_ver + '.0' * (_len(ver) / _len(diff_ver))) \
            and str(ver).split('.')[0] <= str(diff_ver).split('.')[0]:
        return True


class Table(_Table):

    __meta_data__ = {}

    def __init__(self, *args, **kwargs):
        if args:
            name = args[0]
            _name = str(name).split(':')
            if len(_name) > 1:
                self._tag = ''.join(_name[1:])
                list(args)[0] = _name
                args = tuple(args)
        super(Table, self).__init__(*args, **kwargs)

    def __repr__(self):
        _tag = self.tag
        if not _tag:
            return self.__str__()
        else:
            return self.__str__() + ':' + _tag

    @property
    def tag(self):
        if hasattr(self, '_tag'):
            return str(self._tag)

    @classmethod
    def _get_meta_table(cls, name):
        _name = str(name).split(':')
        if len(_name) > 1:
            if _name[0] in cls.__meta_data__:
                _tag = ''.join(_name[1:])
                for k, inst in sorted(cls.__meta_data__[_name[0]].items()):
                    try:
                        if contain_version(k, _tag):
                            return inst
                    except:
                        if str(k) == str(_tag):
                            return inst
            return ''
        else:
            return cls.__meta_data__.get(name)

    @classmethod
    def _set_meta_table(cls, name, tb_instance):
        _name = str(name).split(':')
        if len(_name) > 1:
            if _name[0] not in cls.__meta_data__:
                cls.__meta_data__[_name[0]] = {}
            _tag = ''.join(_name[1:])
            setattr(tb_instance, '_tag', _tag)
            if _tag and _tag not in cls.__meta_data__[_name[0]]:
                cls.__meta_data__[_name[0]][_tag] = tb_instance
        else:
            if name not in cls.__meta_data__:
                cls.__meta_data__[name] = tb_instance

    @classmethod
    def _table_name(cls, base_name, tag_name):
        return base_name + ':' + tag_name

    @classmethod
    def _base_table_name(cls, name):
        _name = str(name).split(':')
        return _name[0] if len(_name) > 0 else name

    def __new__(cls, *args, **kwargs):
        if not args:
            # python3k pickle seems to call this
            return object.__new__(cls)

        try:
            name, metadata, args = args[0], args[1], args[2:]
        except IndexError:
            raise TypeError("Table() takes at least two arguments")

        _schema = kwargs.get('schema', None)

        if _schema is None:
            _schema = metadata.schema
        elif _schema is BLANK_SCHEMA:
            _schema = None
        keep_existing = kwargs.pop('keep_existing', False)
        extend_existing = kwargs.pop('extend_existing', False)
        if 'useexisting' in kwargs:
            msg = "useexisting is deprecated.  Use extend_existing."
            sqlalchemy.util.warn_deprecated(msg)
            if extend_existing:
                msg = "useexisting is synonymous with extend_existing."
                raise ArgumentError(msg)
            extend_existing = kwargs.pop('useexisting', False)

        if keep_existing and extend_existing:
            msg = "keep_existing and extend_existing are mutually exclusive."
            raise ArgumentError(msg)

        mustexist = kwargs.pop('mustexist', False)
        key = getattr(sqlalchemy.sql.schema, '_get_table_key')(name, _schema)
        if key in metadata.tables:
            if not keep_existing and not extend_existing and bool(args):
                raise InvalidRequestError(
                    "Table '%s' is already defined for this MetaData "
                    "instance.  Specify 'extend_existing=True' "
                    "to redefine "
                    "options and columns on an "
                    "existing Table object." % key)
            _table = metadata.tables[key]
            if extend_existing:
                getattr(_table, '_init_existing')(*args, **kwargs)
            return _table
        else:
            if mustexist:
                raise InvalidRequestError("Table '%s' not defined" % key)

            _table = cls._get_meta_table(name)
            if isinstance(_table, Table):
                return _table
            elif _table == '':
                return None

            name = Table._base_table_name(name)
            _table = object.__new__(cls)
            _table.dispatch.before_parent_attach(_table, metadata)
            getattr(metadata, '_add_table')(name, _schema, _table)
            try:
                _table._init(name, metadata, *args, **kwargs)
                _table.dispatch.after_parent_attach(_table, metadata)
                return _table
            except:
                with sqlalchemy.util.safe_reraise():
                    getattr(metadata, '_remove_table')(name, _schema)


class MapperConfig(_MapperConfig):

    __base_attr_name__ = (
        '__table__', '__tablename__', '__mapper_args__',
    )

    __attr_name__ = {
        '__tag_name__': '__get_tag__',
        '__version__': '__get_version__',
    }

    __table_cls__ = Table

    def __init__(self, cls_, classname, dict_):
        # todo by terry
        # 设置为只读字典
        dict_ = dict(dict_.items())

        for k in self.__attr_name__:
            _k = self.__attr_name__.get(k) if hasattr(self.__attr_name__, 'get') else k
            if hasattr(cls_, _k):
                _k = getattr(cls_, _k)
                dict_[k] = _k() if callable(_k) else _k

        super(MapperConfig, self).__init__(cls_=cls_, classname=classname, dict_=dict_)

    def _setup_table(self):
        # todo by terry
        # 优化流程
        cls = self.cls
        _tablename = self.tablename
        table_args = self.table_args
        dict_ = self.dict_
        declared_columns = self.declared_columns

        declared_columns = self.declared_columns = sorted(
            declared_columns, key=lambda _c: getattr(_c, '_creation_order'))

        _table = None

        if hasattr(cls, '__table_cls__'):
            table_cls = sqlalchemy.util.unbound_method_to_callable(cls.__table_cls__)
        else:
            table_cls = self.__table_cls__

        if '__table__' not in dict_:
            if _tablename is not None:

                args, table_kw = (), {}
                if table_args:
                    if isinstance(table_args, dict):
                        table_kw = table_args
                    elif isinstance(table_args, tuple):
                        if isinstance(table_args[-1], dict):
                            args, table_kw = table_args[0:-1], table_args[-1]
                        else:
                            args = table_args

                autoload = dict_.get('__autoload__')
                if autoload:
                    table_kw['autoload'] = True

                cls.__table__ = _table = table_cls(
                    _tablename, cls.metadata,
                    *(tuple(declared_columns) + tuple(args)),
                    **table_kw)
                for k in self.__attr_name__:
                    _tag = dict_.get(k)
                    if _tag:
                        _name = getattr(Table, '_table_name')(str(_table), _tag)
                        getattr(Table, '_set_meta_table')(_name, _table)
        else:
            _table = cls.__table__

            if declared_columns:
                for c in declared_columns:
                    if not table.c.contains_column(c):
                        raise ArgumentError(
                            "Can't add additional column %r when "
                            "specifying __table__" % c.key
                        )
        self.local_table = _table

    def _extract_mappable_attributes(self):
        # todo by terry
        # 优化流程
        cls, dict_, our_stuff = self.cls, self.dict_, self.properties

        _attr_name_list = self.__base_attr_name__ + tuple(self.__attr_name__)

        for k in list(dict_):
            if k in _attr_name_list:
                continue

            value = dict_[k]
            if isinstance(value, (declared_attr, sqlalchemy.util.classproperty)):
                value = getattr(cls, k)

            elif isinstance(value, QueryableAttribute) \
                    and value.class_ is not cls \
                    and value.key != k:
                # detect a QueryableAttribute that's already mapped being
                # assigned elsewhere in userland, turn into a synonym()
                value = synonym(value.key)
                setattr(cls, k, value)

            if (isinstance(value, tuple) and len(value) == 1 and
                    isinstance(value[0], (Column, MapperProperty))):
                sqlalchemy.util.warn("Ignoring declarative-like tuple value of attribute "
                                     "%s: possibly a copy-and-paste error with a comma "
                                     "left at the end of the line?" % k)
                continue
            elif not isinstance(value, (Column, MapperProperty)):
                # using @declared_attr for some object that
                # isn't Column/MapperProperty; remove from the dict_
                # and place the evaluated value onto the class.
                if not k.startswith('__'):
                    dict_.pop(k)
                    setattr(cls, k, value)
                continue
            # we expect to see the name 'metadata' in some valid cases;
            # however at this point we see it's assigned to something trying
            # to be mapped, so raise for that.
            elif k == 'metadata':
                raise InvalidRequestError(
                    "Attribute name 'metadata' is reserved "
                    "for the MetaData instance when using a "
                    "declarative base class."
                )
            our_stuff[k] = getattr(clsregistry, '_deferred_relationship')(cls, value)


base._MapperConfig = MapperConfig


class IntColumn(Column):
    def __init__(self, primary_key=False, default=None, **kwargs):
        if primary_key:
            super(IntColumn, self).__init__(Integer, primary_key=primary_key)
        else:
            super(IntColumn, self).__init__(Integer, primary_key=primary_key, default=default)


class StrColumn(Column):
    def __init__(self, length, default='', **kwargs):
        super(StrColumn, self).__init__(String(length), default=default)


class DateTimeColumn(Column):
    def __init__(self, auto_now=False, **kwargs):
        if not auto_now:
            super(DateTimeColumn, self).__init__(DateTime)
        else:
            super(DateTimeColumn, self).__init__(DateTime, default=datetime.datetime.utcnow)


class BaseMixin(object):

    @classmethod
    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()


    __table_args__ = {
        'mysql_engine': 'InnoDB',
        'mysql_charset': 'utf8',
    }

    __version__ = (1, 0, 0)
    __tag_name__ = None

    @classmethod
    def __get_version__(cls):
        if hasattr(cls, '__version__'):
            _version = getattr(cls, '__version__')
            if isinstance(_version, (tuple or list)):
                return '.'.join([str(i) for i in _version])
            else:
                return _version
        else:
            return 1, 0, 0

    @classmethod
    def __get_tag__(cls):
        if hasattr(cls, '__tag_name__'):
            return getattr(cls, '__tag_name__')
        else:
            return cls.__get_version__()

    def _update_from_dict(self, dic_data):
        return None if [setattr(self, k, v) for k, v in dic_data.items() if
                        hasattr(self, k) and getattr(self, k, None) != v] else None

    def update(self, table_obj, list_name=None):
        return self._update_from_dict(table_obj.to_dict(list_name=list_name))

    def to_dict(self, list_name=None):
        __dict = self.__dict__
        d = {}
        if '_sa_instance_state' in __dict and len(__dict) == 1:
            __dict = [_n for _n in dir(self) if not str(_n).startswith('_')
                      and _n not in ('to_dict',
                                     'metadata',
                                     'update')
                      ]
            if list_name and isinstance(list_name, list):
                for n in list_name:
                    if n in __dict:
                        d[n] = getattr(self, n)
            elif not list_name:
                for n in __dict:
                    d[n] = getattr(self, n)

        else:
            if list_name and isinstance(list_name, list):
                for n in list_name:
                    if n in __dict and not isinstance(__dict[n], InstrumentedAttribute):
                        d[n] = getattr(self, n)
            elif not list_name:
                for n in __dict:
                    if not isinstance(__dict[n], InstrumentedAttribute):
                        d[n] = getattr(self, n)
        if '_sa_instance_state' in d:
            d.pop('_sa_instance_state')
        return d


class _BaseMixin(BaseMixin):
    id = IntColumn(primary_key=True)


def declarative_base(bind=None, metadata=None, mapper=None, cls=_BaseMixin,
                     name='Base', constructor=base._declarative_constructor,
                     class_registry=None,
                     metaclass=DeclarativeMeta):
    # todo by terry
    # 优化流程
    lcl_metadata = metadata or MetaData()
    if bind:
        lcl_metadata.bind = bind

    if class_registry is None:
        class_registry = weakref.WeakValueDictionary()

    bases = not isinstance(cls, tuple) and (cls,) or cls
    class_dict = dict(_decl_class_registry=class_registry,
                      metadata=lcl_metadata)

    if isinstance(cls, type):
        class_dict['__doc__'] = cls.__doc__
        for k in MapperConfig.__attr_name__:
            if hasattr(MapperConfig.__attr_name__, 'get'):
                _v = getattr(cls, MapperConfig.__attr_name__.get(k))
            else:
                _v = getattr(cls, k)
            _v = _v if not callable(_v) else _v()
            class_dict[k] = _v

    if constructor:
        class_dict['__init__'] = constructor
    if mapper:
        class_dict['__mapper_cls__'] = mapper
    ret = metaclass(name, bases, class_dict)
    return ret


class Engine(object):
    def __init__(self, name=None):
        self.name = name
        self.engine = None

    def make_connection(self, db_url, pool_recycle=3600, pool_size=50, pool_timeout=30):
        if not self.engine:
            o_items = urlparse(db_url)
            if o_items.path:
                d = create_engine(db_url,
                                  poolclass=QueuePool,
                                  pool_size=pool_size,
                                  pool_recycle=pool_recycle,
                                  pool_timeout=pool_timeout,
                                  max_overflow=0,
                                  encoding='utf-8')
                self.engine = d
                return d
        else:
            return self.engine


class SingleTonEngine(Engine):
    _instances = {}

    def __new__(cls, *args, **kwargs):
        if 'name' in kwargs:
            name = kwargs['name']
            if name in cls._instances:
                _obj = cls._instances[name]
            else:
                _obj = super(SingleTonEngine, cls).__new__(cls, *args)
                cls._instances[name] = _obj
        else:
            _obj = super(SingleTonEngine, cls).__new__(cls, *args)
        return _obj


class Session(_Session):
    __metadata__ = {}
    __tags__ = []

    def __init__(self, bind=None, autoflush=True, expire_on_commit=True, _enable_transaction_accounting=True,
                 autocommit=False, twophase=False, weak_identity_map=True, binds=None, extension=None,
                 info=None, query_cls=query.Query):
        _Session.__init__(self, bind=bind, autoflush=autoflush, expire_on_commit=expire_on_commit,
                          _enable_transaction_accounting=_enable_transaction_accounting, autocommit=autocommit,
                          twophase=twophase, weak_identity_map=weak_identity_map, binds=binds, extension=extension,
                          info=info, query_cls=query_cls)
        _binds = {}
        _binds.update(self.__binds)

        self.__tags = self.__tags__
        for i, b in self.__binds.items():
            # _tag = i.tag
            # if _tag and _tag not in self.__tags:
            #     self.__tags.append(_tag)
            if isinstance(i, Table):
                _binds[repr(i)] = b
            else:
                _binds[i] = b
        self.__tags = sorted(self.__tags)
        self.__binds = _binds

    def __del__(self):
        self.close()

    def get_bind(self, mapper=None, clause=None):
        # todo by terry
        # 优化流程
        if mapper is clause is None:
            if self.bind:
                return self.bind
            else:
                raise UnboundExecutionError(
                    "This session is not bound to a single Engine or "
                    "Connection, and no context was provided to locate "
                    "a binding.")

        c_mapper = mapper is not None and getattr(orm_base, '_class_to_mapper')(mapper) or None

        # manually bound?
        if self.__binds:
            if c_mapper:
                _name = repr(c_mapper.mapped_table)
                _name_list = _name.split(':')
                if len(_name_list) > 1:
                    _tag = c_mapper.class_.__get_version__()
                    for t in self.__tags:
                        if contain_version(_tag, t):
                            _name = ':'.join([_name_list[0], t])
                            break
                if _name in self.__metadata__:
                    return self.__metadata__[_name]
                if repr(c_mapper.mapped_table) in self.__binds:
                    return self.__binds[repr(c_mapper.mapped_table)]

            # 非ORM不支持版本控制
            if clause is not None:
                for t in sql_util.find_tables(clause, include_crud=True):
                    if repr(t) in self.__binds:
                        return self.__binds[repr(t)]
                    elif str(t) in self.__binds:
                        return self.__binds[str(t)]

        if self.bind:
            return self.bind

        if isinstance(clause, ClauseElement) and clause.bind:
            return clause.bind

        if c_mapper and c_mapper.mapped_table.bind:
            return c_mapper.mapped_table.bind
        context = []
        if mapper is not None:
            context.append('mapper %s' % c_mapper)
        if clause is not None:
            context.append('SQL expression')
        raise UnboundExecutionError(
            "Could not locate a bind configured on %s or this Session" % (
                ', '.join(context)))


def _build_kw(**kw):
    metadata = kw.pop('metadata')
    binds = kw.pop('binds', {})
    _d = dict(kw.items())
    _binds = {}

    # todo by terry
    # 防止表名引起的异常
    _tables = []
    [_tables.extend(binds[tag].table_names()) for tag, meta in metadata.items() if tag in binds]
    for tag, meta in sorted(metadata.items()):
        if tag not in Session.__tags__:
            Session.__tags__.append(tag)
        _bind = binds[tag]
        for table_name in _tables:
            _name = getattr(Table, '_table_name')(table_name, tag)
            _table = Table(_name, meta, autoload=True)
            if isinstance(_table, Table):
                _binds[_table] = _bind
                if repr(_table) not in Session.__metadata__:
                    Session.__metadata__[repr(_table)] = _bind
    if _binds:
        _d['binds'] = _binds
    kw.update(_d)

    return kw


class MyScopedSession(scoped_session):

    __func_factory__ = None

    def __call__(self, **kw):
        if 'metadata' in kw:
            kw = _build_kw(**kw)
        if 'binds' in kw:
            if not self.__func_factory__:
                self.__func_factory__ = self.registry.createfunc
            self.registry.createfunc = functools.partial(self.__func_factory__, binds=kw.pop('binds'))
        ret = scoped_session.__call__(self, **kw)
        return ret


class MySessionMaker(sessionmaker):

    def __init__(self, bind=None, class_=Session, autoflush=True, autocommit=False, expire_on_commit=True,
                 info=None, **kw):
        if 'metadata' in kw:
            kw = _build_kw(**kw)

        sessionmaker.__init__(self, bind=bind, class_=class_, autoflush=autoflush,
                              autocommit=autocommit, expire_on_commit=expire_on_commit, info=info, **kw)


class BaseOperation(object):
    __tableclass__ = None
    __version__ = (1, 0, 0)

    class VersionNotSupport(Exception):
        pass

    class DBEngineNotSupport(Exception):
        pass

    instance_table = {}

    def __new__(cls, *args, **kwargs):
        if 'name' in kwargs:
            name = kwargs['name']
            _obj = cls.get_instance(name)
            if not _obj:
                _obj = super(BaseOperation, cls).__new__(cls, *args)
                cls.instance_table[name] = _obj
            return _obj

        _obj = super(BaseOperation, cls).__new__(cls, *args)
        return _obj

    @classmethod
    def get_instance(cls, name):
        if name in cls.instance_table:
            return cls.instance_table[name]

    def __init__(self, db_engine, name=None, engine_class_=SingleTonEngine):
        self.name = name
        if isinstance(db_engine, str):
            _engine = engine_class_()
            self._db_engine = _engine.make_connection(db_engine)
            self._metadata = MetaData(self._db_engine)
            self._session = scoped_session(
                sessionmaker(autocommit=False,
                             autoflush=False,
                             class_=Session,
                             bind=self._db_engine)
            )
        elif isinstance(db_engine, dict):
            self._metadata = {}
            self._db_engine = {}
            for tag, url in db_engine.items():
                if tag not in self._db_engine:
                    _engine = engine_class_(name=tag)
                    self._db_engine[tag] = _engine.make_connection(url)
                if tag not in self._metadata:
                    self._metadata[tag] = MetaData(self._db_engine[tag])
            self._session = MyScopedSession(
                MySessionMaker(autocommit=False,
                               autoflush=False,
                               metadata=self._metadata,
                               binds=self._db_engine)
            )
        else:
            raise self.DBEngineNotSupport(db_engine)

    @staticmethod
    def ver(version):
        return '.'.join([str(i) for i in version])

    @staticmethod
    def get_version(version):
        return BaseOperation.ver(version)

    @property
    def version(self):
        return self.get_version(self.__version__)

    @staticmethod
    def install_module(db_engine, database):
        conn = db_engine.connect()
        conn.execute("COMMIT")
        # Do not substitute user-supplied database names here.
        try:
            conn.execute("CREATE DATABASE %s" % database)
        except:
            pass
        conn.close()

    @property
    def db_engine(self):
        _obj = self._db_engine
        if not isinstance(_obj, dict):
            return _obj
        else:
            version = self.version
            for v, obj in sorted(_obj.items()):
                if contain_version(version, v):
                    return obj

    @property
    def metadata(self):
        _obj = self._metadata
        if not isinstance(_obj, dict):
            return _obj
        else:
            version = self.version
            for v, obj in sorted(_obj.items()):
                if contain_version(version, v):
                    return obj

    @staticmethod
    def _get_session(sess):
        _session = sess() if callable(sess) else sess
        return _session

    def use_session(self, version=None):
        _obj = self._session
        if not isinstance(self._metadata, dict):
            return self._get_session(_obj)
        else:
            if hasattr(version, 'version'):
                version = getattr(version, 'version') or self.version
            else:
                version = version or self.version
            for v, obj in sorted(self._metadata.items()):
                if contain_version(version, v):
                    _obj = _obj(**{'metadata': self._metadata, 'binds': self._db_engine})
                    return self._get_session(_obj)

    @property
    def session(self):
        return self.use_session(self.version)

    def get_table(self, name):
        try:
            metadata = self.metadata
            if metadata:
                return Table(name, self.metadata, autoload=True)
        except NoSuchTableError:
            pass

    def has_table(self, table_cls):
        _table = self.get_table(table_cls.__tablename__)
        if not isinstance(_table, Table):
            return False
        return True

    def define_table(self, table_cls):
        if not self.has_table(table_cls):
            table_cls.metadata.create_all(self.db_engine)

    def undefine_table(self, table_cls):
        if self.has_table(table_cls):
            table_cls.__table__.drop(self.db_engine)

    def clear_table(self, table_cls):
        if self.has_table(table_cls):
            table_cls.__table__.drop(self.db_engine)
        table_cls.metadata.create_all(self.db_engine)


class Operation(BaseOperation):
    def create(self, table_cls=None):
        _table = table_cls if table_cls else self.__tableclass__
        if _table:
            self.define_table(_table)

    def drop(self, table_cls=None):
        _table = table_cls if table_cls else self.__tableclass__
        if _table:
            self.undefine_table(_table)

    def clear(self, table_cls=None):
        _table = table_cls if table_cls else self.__tableclass__
        if _table:
            self.clear_table(_table)

    @staticmethod
    def get_one_by_session(session, table_cls, dict_data=None):
        if table_cls:
            if dict_data:
                return session.query(table_cls).filter_by(**dict_data).first()
            else:
                return session.query(table_cls).first()

    def get_one(self, dict_data=None, table_cls=None):
        _table = table_cls if table_cls else self.__tableclass__
        return self.get_one_by_session(self.session, _table, dict_data=dict_data)

    @staticmethod
    def get_by_session(session, table_cls, dict_data=None):
        if table_cls:
            if dict_data:
                return session.query(table_cls).filter_by(**dict_data).all()
            else:
                return session.query(table_cls).all()

    def get(self, dict_data=None, table_cls=None):
        _table = table_cls if table_cls else self.__tableclass__
        return self.get_by_session(self.session, _table, dict_data=dict_data)

    @staticmethod
    def update_by_session(session, table_cls, data_set, new_data, limit=1000, commit=True):
        if not new_data:
            return
        if table_cls:
            data_set = data_set if isinstance(data_set, list) else [data_set]
            for i, data in enumerate(data_set[::limit]):
                data = data_set[i*limit:i*limit + limit]
                for d in data:
                    session.query(table_cls).filter_by(**d).update(new_data)
                if commit:
                    session.commit()

    def update(self, data_set, new_data, table_cls=None, limit=1000, session=None, commit=True):
        _table = table_cls if table_cls else self.__tableclass__
        _session = self.session if not session else session
        self.update_by_session(_session, _table, data_set=data_set, new_data=new_data, limit=limit, commit=commit)

    @staticmethod
    def add_by_session(session, table_cls, data_set, limit=1000, commit=True):
        if table_cls:
            data_set = data_set if isinstance(data_set, list) else [data_set]
            for i, data in enumerate(data_set[::limit]):
                data = data_set[i*limit:i*limit + limit]
                for d in data:
                    record = table_cls(**d) if isinstance(d, dict) else d
                    session.add(record)
                if commit:
                    session.commit()

    def add(self, data_set, table_cls=None, limit=1000, session=None, commit=True):
        _table = table_cls if table_cls else self.__tableclass__
        _session = self.session if not session else session
        self.add_by_session(_session, _table, data_set=data_set, limit=limit, commit=commit)

    @staticmethod
    def delete_by_session(session, table_cls, data_set, limit=1000, commit=True):
        if table_cls:
            data_set = data_set if isinstance(data_set, list) else [data_set]
            for i, data in enumerate(data_set[::limit]):
                data = data_set[i*limit:i*limit + limit]
                for d in data:
                    session.query(table_cls).filter_by(**d).delete()
                if commit:
                    session.commit()

    def delete(self, data_set, table_cls=None, limit=1000, session=None, commit=True):
        _table = table_cls if table_cls else self.__tableclass__
        _session = self.session if not session else session
        self.delete_by_session(_session, _table, data_set=data_set, limit=limit, commit=commit)
