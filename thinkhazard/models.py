from sqlalchemy import (
    Column,
    Integer,
    Unicode,
    )

from sqlalchemy.ext.declarative import declarative_base, AbstractConcreteBase

from sqlalchemy.orm import (
    scoped_session,
    sessionmaker,
    )

from zope.sqlalchemy import ZopeTransactionExtension

DBSession = scoped_session(sessionmaker(extension=ZopeTransactionExtension()))
Base = declarative_base()


class Admin(AbstractConcreteBase, Base):
    __table_args__ = {'schema': 'adminunits'}

    id = Column(Integer, primary_key=True)
    name = Column(Unicode)


class Admin0(Admin):
    __tablename__ = 'admin0'
    order = 0

    def __json__(self, request):
        return {'admin0': self.name}


class Admin1(Admin):
    __tablename__ = 'admin1'
    order = 1

    admin0_name = Column(Unicode)

    def __json__(self, request):
        return {'admin0': self.admin0_name, 'admin1': self.name}


class Admin2(Admin):
    __tablename__ = 'admin2'
    order = 2

    admin0_name = Column(Unicode)
    admin1_name = Column(Unicode)

    def __json__(self, request):
        return {'admin0': self.admin0_name, 'admin1': self.admin1_name,
                'admin2': self.name}
