from sqlalchemy import (
    Column,
    Float,
    ForeignKey,
    Integer,
    Unicode,
    DateTime,
    String,
    )

from sqlalchemy.schema import MetaData, Table

from sqlalchemy.ext.declarative import declarative_base

from sqlalchemy.orm import (
    scoped_session,
    sessionmaker,
    relationship,
    )

from geoalchemy2 import Geometry

from zope.sqlalchemy import ZopeTransactionExtension

import datetime

DBSession = scoped_session(sessionmaker(extension=ZopeTransactionExtension()))
Base = declarative_base(metadata=MetaData(schema='datamart'))


class AdminLevelType(Base):
    __tablename__ = 'enum_adminleveltype'

    id = Column(Integer, primary_key=True)
    mnemonic = Column(Unicode)
    title = Column(Unicode, nullable=False)
    description = Column(Unicode)


class HazardLevel(Base):
    __tablename__ = 'enum_hazardlevel'

    id = Column(Integer, primary_key=True)
    mnemonic = Column(Unicode)
    title = Column(Unicode, nullable=False)
    order = Column(Integer)


class HazardType(Base):
    __tablename__ = 'enum_hazardtype'

    id = Column(Integer, primary_key=True)
    mnemonic = Column(Unicode)
    title = Column(Unicode, nullable=False)
    order = Column(Integer)


#class AdditionalInformationGroup(Base):
    #__tablename__ = 'enum_additionalinformationgroup'

    #id = Column(Integer, primary_key=True)
    #mnemonic = Column(Unicode)
    #title = Column(Unicode, nullable=False)
    #description = Column(Unicode)


#class AdditionalInformationType(Base):
    #__tablename__ = 'enum_additionalinformationtype'

    #id = Column(Integer, primary_key=True)
    #mnemonic = Column(Unicode)
    #title = Column(Unicode, nullable=False)
    #description = Column(Unicode)


#class FeedbackStatus(Base):
    #__tablename__ = 'enum_feedbackstatus'

    #id = Column(Integer, primary_key=True)
    #mnemonic = Column(Unicode)
    #title = Column(Unicode, nullable=False)
    #description = Column(Unicode)


#administrativedivision_additionalinformation_table = Table(
    #'rel_administrativedivision_additionalinformation', Base.metadata,
    #Column('id', Integer, primary_key=True),
    #Column('administrativedivision_id', Integer,
           #ForeignKey('administrativedivision.id'), nullable=False,
           #index=True),
    #Column('additionalinformation_id', Integer,
           #ForeignKey('additionalinformation.id'), nullable=False, index=True))


#additionalinformation_userfeedback_table = Table(
    #'rel_additionalinformation_userfeedback', Base.metadata,
    #Column('id', Integer, primary_key=True),
    #Column('additionalinformation_id', Integer,
           #ForeignKey('additionalinformation.id'), nullable=False,
           #index=True),
    #Column('userfeedback_id', Integer,
           #ForeignKey('userfeedback.id'), nullable=False, index=True))


hazardcategory_administrativedivision_table = Table(
    'rel_hazardcategory_administrativedivision', Base.metadata,
    Column('id', Integer, primary_key=True),
    Column('administrativedivision_id', Integer,
           ForeignKey('administrativedivision.id'), nullable=False,
           index=True),
    Column('hazardcategory_id', Integer,
           ForeignKey('hazardcategory.id'), nullable=False, index=True))


#class HazardCategoryAdditionalInformationAssociation(Base):
    #__tablename__ = 'rel_hazardcategory_additionalinformation'
    #id = Column(Integer, primary_key=True)
    #hazardcategory_id = Column(Integer, ForeignKey('hazardcategory.id'),
                               #nullable=False, index=True)
    #additionalinformation_id = Column(Integer,
                                      #ForeignKey('additionalinformation.id'),
                                      #nullable=False, index=True)
    #order = Column(Integer, nullable=False)

    #hazardcategory = relationship('HazardCategory')
    #additionalinformation = relationship('AdditionalInformation',
                                         #lazy='joined', innerjoin=True)


class AdministrativeDivision(Base):
    __tablename__ = 'administrativedivision'

    id = Column(Integer, primary_key=True)
    code = Column(Integer, index=True, unique=True, nullable=False)
    leveltype_id = Column(Integer, ForeignKey(AdminLevelType.id),
                          nullable=False, index=True)
    name = Column(Unicode, nullable=False)
    parent_code = Column(Integer, ForeignKey(
        'administrativedivision.code', use_alter=True,
        name='administrativedivision_parent_code_fkey'))
    geom = Column(Geometry('MULTIPOLYGON', 3857))

    leveltype = relationship(AdminLevelType)
    parent = relationship('AdministrativeDivision', uselist=False,
                          remote_side=code)

    hazardcategories = relationship(
        'HazardCategory',
        secondary=hazardcategory_administrativedivision_table,
        backref='administrativedivisions')

    #additionalinformations = relationship(
        #'AdditionalInformation',
        #secondary=administrativedivision_additionalinformation_table,
        #backref='administrativedivisions')

    def __json__(self, request):
        if self.leveltype_id == 1:
            return {'code': self.code,
                    'admin0': self.name}
        if self.leveltype_id == 2:
            return {'code': self.code,
                    'admin0': self.parent.name,
                    'admin1': self.name}
        if self.leveltype_id == 3:
            return {'code': self.code,
                    'admin0': self.parent.parent.name,
                    'admin1': self.parent.name,
                    'admin2': self.name}


class HazardCategory(Base):
    __tablename__ = 'hazardcategory'

    id = Column(Integer, primary_key=True)
    hazardtype_id = Column(Integer, ForeignKey(HazardType.id), nullable=False)
    hazardlevel_id = Column(Integer, ForeignKey(HazardLevel.id),
                             nullable=False)
    general_recommendation = Column(Unicode, nullable=False)

    hazardtype = relationship(HazardType)
    hazardlevel = relationship(HazardLevel)


#class UserFeedback(Base):
    #__tablename__ = 'userfeedback'

    #id = Column(Integer, primary_key=True)
    #description = Column(Unicode, nullable=False)
    #submissiondate = Column(DateTime, nullable=False,
                            #default=datetime.datetime.utcnow)
    #useremailaddress = Column(String(254))
    #processstatus_id = Column(Integer, ForeignKey(FeedbackStatus.id),
                              #nullable=False)

    #processstatus = relationship(FeedbackStatus)


#class AdditionalInformation(Base):
    #__tablename__ = 'additionalinformation'

    #id = Column(Integer, primary_key=True)
    #mnemonic = Column(Unicode, nullable=False)
    #title = Column(Unicode, nullable=False)
    #accessurl = Column(Unicode)
    #type_id = Column(Integer, ForeignKey(AdditionalInformationType.id),
                     #nullable=False)
    #group_id = Column(Integer, ForeignKey(AdditionalInformationGroup.id))
    #generationdate = Column(DateTime, default=datetime.datetime.utcnow)
    #description = Column(Unicode)

    #type = relationship(AdditionalInformationType)
    #group = relationship(AdditionalInformationGroup)
    #userfeedbacks = relationship(
        #'UserFeedback',
        #secondary=additionalinformation_userfeedback_table,
        #backref='additionalinformations')

    #hazardcategory_associations = relationship(
        #'HazardCategoryAdditionalInformationAssociation',
        #order_by='HazardCategoryAdditionalInformationAssociation.order',
        #lazy='joined')
