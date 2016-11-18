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
from datetime import datetime

__author__ = 'terry'

try:
    import cPickle as pickle
except:
    import pickle

import sqlalchemy.sql as sql
from urlparse import urlparse
from sqlalchemy import *
from sqlalchemy.exc import *
from sqlalchemy.orm import scoped_session, Session
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.ext.declarative import declarative_base as local_declarative_base


__all__ = ['declarative_base', 'sql', 'and_', 'or_', 'join', 'BaseModelDriver', 'make_connection', 'BaseBackend',
           'StrColumn', 'IntColumn', 'MapColumn', 'DateTimeColumn']


class IntColumn(Column):
    def __init__(self, primary_key=False, default=None, **kwargs):
        super(IntColumn, self).__init__(Integer, primary_key=primary_key, default=default)


class StrColumn(Column):
    def __init__(self, length, default=None, **kwargs):
        super(StrColumn, self).__init__(String(length), default=default)


class DateTimeColumn(Column):
    def __init__(self, default=None, **kwargs):
        super(DateTimeColumn, self).__init__(DateTime, default=default)


# Don't use it in BaseMixin
class MapColumn(Column):
    def __init__(self, table_name, item_name, **kwargs):
        super(MapColumn, self).__init__(ForeignKey('.'.join([table_name, item_name])))


class BaseMixin(object):
    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()

    __table_args__ = {'mysql_engine': 'InnoDB',
                      'mysql_charset': 'utf8',
                      }

    id = IntColumn(primary_key=True)

    def _update_from_dict(cls, dic_data):
        return None if [setattr(cls, k, v) for k, v in dic_data.items() if
                        hasattr(cls, k) and getattr(cls, k, None) != v] else None

    def update(cls, table_obj, list_name=None):
        return cls._update_from_dict(table_obj.to_dict(list_name=list_name))

    def to_dict(cls, list_name=None):
        d = pickle.loads(pickle.dumps(cls.__dict__))
        d.pop('_sa_instance_state')
        if list_name:
            _d = {}
            for n in list_name:
                _d[n] = d[n]
            return _d
        else:
            return d


def declarative_base(cls=BaseMixin):
    return local_declarative_base(cls=cls)


def make_connection(db_url):
    o_items = urlparse(db_url)
    if o_items.path:
        return create_engine(db_url)


class BaseModelDriver(object):
    def __init__(self, db_engine):
        self.metadata = None
        self._session = None
        if isinstance(db_engine, str):
            db_engine = make_connection(db_engine)
        self.make_session(db_engine)
        self.db_engine = db_engine

    def make_session(self, db_engine):
        self.metadata = MetaData(db_engine)
        self._session = scoped_session(
            sessionmaker(autocommit=False,
                         autoflush=False,
                         bind=db_engine)
        )

    @staticmethod
    def installModule(db_engine, database):
        conn = db_engine.connect()
        conn.execute("COMMIT")
        # Do not substitute user-supplied database names here.
        try:
            conn.execute("CREATE DATABASE %s" % database)
        except:
            pass
        conn.close()

    @property
    def session(self):
        _session = self._session()
        if isinstance(_session, Session):
            _session.commit()
            return _session

    def getTable(self, name):
        try:
            table = Table(name,
                          self.metadata,
                          autoload=True)
            return table
        except NoSuchTableError:
            pass

    def hasTable(self, table_class):
        table = self.getTable(table_class.__tablename__)
        if not isinstance(table, Table):
            return False
        return True

    def defineTable(self, table_class):
        if not self.hasTable(table_class):
            table_class.metadata.create_all(self.db_engine)

    def undefineTable(self, table_class):
        if self.hasTable(table_class):
            table_class.__table__.drop(self.db_engine)

    def clearTable(self, table_class):
        if self.hasTable(table_class):
            table_class.__table__.drop(self.db_engine)
        table_class.metadata.create_all(self.db_engine)


class BaseBackend(BaseModelDriver):
    __tableclass__ = None

    def create(self, table=None):
        table = table if table else self.__tableclass__
        self.defineTable(table)

    def drop(self, table=None):
        table = table if table else self.__tableclass__
        self.undefineTable(table)

    def clear(self, table=None):
        table = table if table else self.__tableclass__
        self.clearTable(table)

    def get_one(self, dict_data=None, table=None):
        table = table if table else self.__tableclass__
        if dict_data:
            return self.session.query(table).filter_by(**dict_data).first()
        else:
            return self.session.query(table).first()

    def get(self, dict_data=None, table=None):
        table = table if table else self.__tableclass__
        if dict_data:
            return self.session.query(table).filter_by(**dict_data).all()
        else:
            return self.session.query(table).all()

    def update(self, data_set, new_data, table=None, limit=1000):
        table = table if table else self.__tableclass__
        data_set = data_set if isinstance(data_set, list) else [data_set]
        session = self.session
        for i, data in enumerate(data_set[::limit]):
            data = data_set[i*limit:i*limit + limit]
            for d in data:
                session.query(table).filter_by(**d).update(new_data)
        session.commit()

    def add(self, data_set, table=None, limit=1000):
        table = table if table else self.__tableclass__
        data_set = data_set if isinstance(data_set, list) else [data_set]
        session = self.session
        for i, data in enumerate(data_set[::limit]):
            data = data_set[i*limit:i*limit + limit]
            for d in data:
                record = table(**d)
                session.add(record)
            session.commit()

    def delete(self, data_set, table=None, limit=1000):
        table = table if table else self.__tableclass__
        data_set = data_set if isinstance(data_set, list) else [data_set]
        session = self.session
        for i, data in enumerate(data_set[::limit]):
            data = data_set[i*limit:i*limit + limit]
            for d in data:
                session.query(table).filter_by(**d).delete()
        session.commit()
