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


class TermStatus(Base):
    __tablename__ = 'enum_termstatus'

    id = Column(Integer, primary_key=True)
    mnemonic = Column(Unicode)
    title = Column(Unicode, nullable=False)
    description = Column(Unicode)


class AdminLevelType(Base):
    __tablename__ = 'enum_adminleveltype'

    id = Column(Integer, primary_key=True)
    mnemonic = Column(Unicode)
    title = Column(Unicode, nullable=False)
    description = Column(Unicode)
    status_id = Column(Integer, ForeignKey(TermStatus.id), nullable=False)

    status = relationship(TermStatus)


class MetadataDateType(Base):
    __tablename__ = 'enum_md_datetype'

    id = Column(Integer, primary_key=True)
    title = Column(Unicode)
    description = Column(Unicode)


class MetadataRole(Base):
    __tablename__ = 'enum_md_role'

    id = Column(Integer, primary_key=True)
    title = Column(Unicode)
    description = Column(Unicode)


class MetadataTopicCategory(Base):
    __tablename__ = 'enum_md_topiccategory'

    id = Column(Integer, primary_key=True)
    title = Column(Unicode)
    description = Column(Unicode)


class MetadataUseConstraints(Base):
    __tablename__ = 'enum_md_useconstraints'

    id = Column(Integer, primary_key=True)
    title = Column(Unicode)
    description = Column(Unicode)


class MetadataMaintenanceFrequency(Base):
    __tablename__ = 'enum_md_maintenancefrequency'

    id = Column(Integer, primary_key=True)
    title = Column(Unicode)
    description = Column(Unicode)


class MetadataLanguage(Base):
    __tablename__ = 'enum_md_language'

    id = Column(Integer, primary_key=True)
    title = Column(Unicode)
    description = Column(Unicode)


class MetadataLicensing(Base):
    __tablename__ = 'enum_md_licensing'

    id = Column(Integer, primary_key=True)
    title = Column(Unicode)
    description = Column(Unicode)


class CategoryType(Base):
    __tablename__ = 'enum_categorytype'

    id = Column(Integer, primary_key=True)
    mnemonic = Column(Unicode)
    title = Column(Unicode, nullable=False)
    color = Column(Unicode, nullable=False)
    description = Column(Unicode)
    order = Column(Integer)
    status_id = Column(Integer, ForeignKey(TermStatus.id), nullable=False)
    status = relationship(TermStatus)


class HazardType(Base):
    __tablename__ = 'enum_hazardtype'

    id = Column(Integer, primary_key=True)
    mnemonic = Column(Unicode)
    title = Column(Unicode, nullable=False)
    description = Column(Unicode)
    status_id = Column(Integer, ForeignKey(TermStatus.id), nullable=False)
    status = relationship(TermStatus)


class IntensityThreshold(Base):
    __tablename__ = 'enum_intensitythreshold'

    id = Column(Integer, primary_key=True)
    mnemonic = Column(Unicode)
    title = Column(Unicode, nullable=False)
    value = Column(Float, nullable=False)
    unit = Column(Unicode, nullable=False)
    description = Column(Unicode)
    status_id = Column(Integer, ForeignKey(TermStatus.id), nullable=False)
    hazardtype_id = Column(Integer, ForeignKey(HazardType.id), nullable=False)

    status = relationship(TermStatus)
    hazardtype = relationship(HazardType)


class ReturnPeriod(Base):
    __tablename__ = 'enum_returnperiod'

    id = Column(Integer, primary_key=True)
    mnemonic = Column(Unicode)
    title = Column(Unicode, nullable=False)
    description = Column(Unicode)
    status_id = Column(Integer, ForeignKey(TermStatus.id), nullable=False)
    hazardtype_id = Column(Integer, ForeignKey(HazardType.id), nullable=False)

    status = relationship(TermStatus)
    hazardtype = relationship(HazardType)


class AdditionalInformationGroup(Base):
    __tablename__ = 'enum_additionalinformationgroup'

    id = Column(Integer, primary_key=True)
    mnemonic = Column(Unicode)
    title = Column(Unicode, nullable=False)
    description = Column(Unicode)
    status_id = Column(Integer, ForeignKey(TermStatus.id), nullable=False)

    status = relationship(TermStatus)


class AdditionalInformationType(Base):
    __tablename__ = 'enum_additionalinformationtype'

    id = Column(Integer, primary_key=True)
    mnemonic = Column(Unicode)
    title = Column(Unicode, nullable=False)
    description = Column(Unicode)
    status_id = Column(Integer, ForeignKey(TermStatus.id), nullable=False)

    status = relationship(TermStatus)


class FeedbackStatus(Base):
    __tablename__ = 'enum_feedbackstatus'

    id = Column(Integer, primary_key=True)
    mnemonic = Column(Unicode)
    title = Column(Unicode, nullable=False)
    description = Column(Unicode)
    status_id = Column(Integer, ForeignKey(TermStatus.id), nullable=False)

    status = relationship(TermStatus)


administrativedivision_additionalinformation_table = Table(
    'rel_administrativedivision_additionalinformation', Base.metadata,
    Column('id', Integer, primary_key=True),
    Column('administrativedivision_id', Integer,
           ForeignKey('administrativedivision.id'), nullable=False,
           index=True),
    Column('additionalinformation_id', Integer,
           ForeignKey('additionalinformation.id'), nullable=False, index=True))


additionalinformation_userfeedback_table = Table(
    'rel_additionalinformation_userfeedback', Base.metadata,
    Column('id', Integer, primary_key=True),
    Column('additionalinformation_id', Integer,
           ForeignKey('additionalinformation.id'), nullable=False,
           index=True),
    Column('userfeedback_id', Integer,
           ForeignKey('userfeedback.id'), nullable=False, index=True))


hazardcategory_administrativedivision_table = Table(
    'rel_hazardcategory_administrativedivision', Base.metadata,
    Column('id', Integer, primary_key=True),
    Column('administrativedivision_id', Integer,
           ForeignKey('administrativedivision.id'), nullable=False,
           index=True),
    Column('hazardcategory_id', Integer,
           ForeignKey('hazardcategory.id'), nullable=False, index=True),
    Column('coverageratio', Integer))


class HazardCategoryAdditionalInformationAssociation(Base):
    __tablename__ = 'rel_hazardcategory_additionalinformation'
    id = Column(Integer, primary_key=True)
    hazardcategory_id = Column(Integer, ForeignKey('hazardcategory.id'),
                               nullable=False, index=True)
    additionalinformation_id = Column(Integer,
                                      ForeignKey('additionalinformation.id'),
                                      nullable=False, index=True)
    order = Column(Integer, nullable=False)

    additionalinformation = relationship('AdditionalInformation',
                                         lazy='joined', innerjoin=True)


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

    additionalinformations = relationship(
        'AdditionalInformation',
        secondary=administrativedivision_additionalinformation_table,
        backref='administrativedivisions')

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


class Metadata(Base):
    __tablename__ = 'metadata'

    id = Column(Integer, primary_key=True)
    localcode = Column(Unicode)
    title = Column(Unicode, nullable=False)
    date = Column(Unicode, nullable=False)
    datetype_id = Column(Integer, ForeignKey(MetadataDateType.id),
                         nullable=False)
    abstract = Column(Unicode, nullable=False)
    keywords = Column(Unicode, nullable=False)
    pointofcontactindividualname = Column(Unicode, nullable=False)
    organizationname = Column(Unicode, nullable=False)
    role_id = Column(Integer, ForeignKey(MetadataRole.id), nullable=False)
    useconstraints_id = Column(Integer, ForeignKey(MetadataUseConstraints.id),
                               nullable=False)
    licensing_id = Column(Integer, ForeignKey(MetadataLicensing.id))
    licensingsupplemental = Column(Unicode)
    maintenancefrequency_id = Column(Integer, ForeignKey(
        MetadataMaintenanceFrequency.id))
    language_id = Column(Integer, ForeignKey(MetadataLanguage.id),
                         nullable=False)
    sourceurl = Column(Unicode)
    dataqualityinfo = Column(Unicode)
    topiccategory_id = Column(Integer, ForeignKey(MetadataTopicCategory.id),
                              nullable=False)
    countryregion_id = Column(Integer, ForeignKey(AdministrativeDivision.id),
                              nullable=False)
    hazardtype_id = Column(Integer, ForeignKey(HazardType.id), nullable=False)
    hazardsetid = Column(Integer)
    glidenumber = Column(Integer)
    intensityunit = Column(Unicode)
    returnperiod_id = Column(Integer, ForeignKey(ReturnPeriod.id))
    mdauthorindividualorganisationnames = Column(Unicode)

    datetype = relationship(MetadataDateType)
    role = relationship(MetadataRole)
    useconstraints = relationship(MetadataUseConstraints)
    licensing = relationship(MetadataLicensing)
    maintenancefrequency = relationship(MetadataMaintenanceFrequency)
    language = relationship(MetadataLanguage)
    topiccategory = relationship(MetadataTopicCategory)
    countryregion = relationship(AdministrativeDivision)
    returnperiod = relationship(ReturnPeriod)
    hazardtype = relationship(HazardType)


class HazardCategory(Base):
    __tablename__ = 'hazardcategory'

    id = Column(Integer, primary_key=True)
    hazardtype_id = Column(Integer, ForeignKey(HazardType.id), nullable=False)
    intensitythreshold_id = Column(Integer, ForeignKey(IntensityThreshold.id),
                                   nullable=False)
    categorytype_id = Column(Integer, ForeignKey(CategoryType.id),
                             nullable=False)
    description = Column(Unicode, nullable=False)
    status_id = Column(Integer, ForeignKey(TermStatus.id), nullable=False)

    hazardtype = relationship(HazardType)
    intensitythreshold = relationship(IntensityThreshold)
    categorytype = relationship(CategoryType)
    status = relationship(TermStatus)


class UserFeedback(Base):
    __tablename__ = 'userfeedback'

    id = Column(Integer, primary_key=True)
    description = Column(Unicode, nullable=False)
    submissiondate = Column(DateTime, nullable=False,
                            default=datetime.datetime.utcnow)
    useremailaddress = Column(String(254))
    processstatus_id = Column(Integer, ForeignKey(FeedbackStatus.id),
                              nullable=False)

    processstatus = relationship(FeedbackStatus)


class AdditionalInformation(Base):
    __tablename__ = 'additionalinformation'

    id = Column(Integer, primary_key=True)
    mnemonic = Column(Unicode, nullable=False)
    title = Column(Unicode, nullable=False)
    accessurl = Column(Unicode)
    metadata_id = Column(Integer, ForeignKey(Metadata.id))
    type_id = Column(Integer, ForeignKey(AdditionalInformationType.id),
                     nullable=False)
    group_id = Column(Integer, ForeignKey(AdditionalInformationGroup.id))
    status_id = Column(Integer, ForeignKey(TermStatus.id), nullable=False)
    generationdate = Column(DateTime, default=datetime.datetime.utcnow)
    description = Column(Unicode)

    metadata_ = relationship(Metadata)

    type = relationship(AdditionalInformationType)
    group = relationship(AdditionalInformationGroup)
    status = relationship(TermStatus)
    userfeedbacks = relationship(
        'UserFeedback',
        secondary=additionalinformation_userfeedback_table,
        backref='additionalinformations')

    hazardcategory_associations = relationship(
        'HazardCategoryAdditionalInformationAssociation',
        order_by='HazardCategoryAdditionalInformationAssociation.order',
        lazy='joined')
