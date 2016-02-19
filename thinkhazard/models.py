# -*- coding: utf-8 -*-
#
# Copyright (C) 2015-2016 by the GFDRR / World Bank
#
# This file is part of ThinkHazard.
#
# ThinkHazard is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option)
# any later version.
#
# ThinkHazard is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for
# more details.
#
# You should have received a copy of the GNU General Public License along with
# ThinkHazard.  If not, see <http://www.gnu.org/licenses/>.

import threading
import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    inspect,
    Integer,
    String,
    Table,
    Unicode,
    )
from sqlalchemy.schema import MetaData

from sqlalchemy.ext.declarative import declarative_base

from sqlalchemy.orm import (
    scoped_session,
    sessionmaker,
    relationship,
    deferred,
    )

from geoalchemy2 import Geometry

from zope.sqlalchemy import ZopeTransactionExtension

DBSession = scoped_session(sessionmaker(extension=ZopeTransactionExtension()))
Base = declarative_base(metadata=MetaData(schema='datamart'))


adminleveltypes = threading.local().__dict__
hazardlevels = threading.local().__dict__
hazardtypes = threading.local().__dict__


class AdminLevelType(Base):
    __tablename__ = 'enum_adminleveltype'

    id = Column(Integer, primary_key=True)
    mnemonic = Column(Unicode, unique=True)
    title = Column(Unicode, nullable=False)
    description = Column(Unicode)

    @classmethod
    def get(cls, mnemonic):
        if mnemonic in adminleveltypes:
            adminleveltype = adminleveltypes[mnemonic]
            insp = inspect(adminleveltype)
            if not insp.detached:
                return adminleveltype
        with DBSession.no_autoflush:
            adminleveltype = DBSession.query(cls) \
                .filter(cls.mnemonic == mnemonic) \
                .one_or_none()
            if adminleveltype is not None:
                adminleveltypes[mnemonic] = adminleveltype
            return adminleveltype


level_weights = {
    None: 0,
    u'VLO': 1,
    u'LOW': 2,
    u'MED': 3,
    u'HIG': 4
}


class HazardLevel(Base):
    __tablename__ = 'enum_hazardlevel'

    id = Column(Integer, primary_key=True)
    mnemonic = Column(Unicode, unique=True)
    title = Column(Unicode, nullable=False)
    order = Column(Integer)

    def __cmp__(self, other):
        if other is None:
            return 1
        return cmp(level_weights[self.mnemonic],
                   level_weights[other.mnemonic])

    @classmethod
    def get(cls, mnemonic):
        if mnemonic in hazardlevels:
            hazardlevel = hazardlevels[mnemonic]
            insp = inspect(hazardlevel)
            if not insp.detached:
                return hazardlevel
        with DBSession.no_autoflush:
            hazardlevel = DBSession.query(cls) \
                .filter(cls.mnemonic == mnemonic) \
                .one_or_none()
            if hazardlevel is not None:
                hazardlevels[mnemonic] = hazardlevel
            return hazardlevel


class HazardType(Base):
    __tablename__ = 'enum_hazardtype'

    id = Column(Integer, primary_key=True)
    mnemonic = Column(Unicode, unique=True)
    title = Column(Unicode, nullable=False)
    order = Column(Integer)

    @classmethod
    def get(cls, mnemonic):
        if mnemonic in hazardtypes:
            hazardtype = hazardtypes[mnemonic]
            insp = inspect(hazardtype)
            if not insp.detached:
                return hazardtype
        with DBSession.no_autoflush:
            hazardtype = DBSession.query(cls) \
                .filter(cls.mnemonic == mnemonic) \
                .one_or_none()
            if hazardtype is not None:
                hazardtypes[mnemonic] = hazardtype
            return hazardtype


hazardcategory_administrativedivision_hazardset_table = Table(
    'rel_hazardcategory_administrativedivision_hazardset', Base.metadata,
    Column('rel_hazardcategory_administrativedivision_id', Integer,
           ForeignKey('rel_hazardcategory_administrativedivision.id'),
           primary_key=True),
    Column('hazardset_id', String,
           ForeignKey('processing.hazardset.id', ondelete="CASCADE"),
           primary_key=True))


class HazardCategoryAdministrativeDivisionAssociation(Base):
    __tablename__ = 'rel_hazardcategory_administrativedivision'

    id = Column(Integer, primary_key=True)
    administrativedivision_id = Column(Integer,
                                       ForeignKey('administrativedivision.id'),
                                       nullable=False, index=True)
    hazardcategory_id = Column(Integer,
                               ForeignKey('hazardcategory.id'),
                               nullable=False, index=True)
    administrativedivision = relationship('AdministrativeDivision',
                                          back_populates='hazardcategories',
                                          lazy='joined')
    hazardcategory = relationship('HazardCategory',
                                  back_populates='administrativedivisions',
                                  lazy='joined')
    hazardsets = relationship(
        'HazardSet',
        secondary=hazardcategory_administrativedivision_hazardset_table,
        lazy="joined")


class HazardCategoryTechnicalRecommendationAssociation(Base):
    __tablename__ = 'rel_hazardcategory_technicalrecommendation'
    id = Column(Integer, primary_key=True)
    hazardcategory_id = Column(Integer, ForeignKey('hazardcategory.id'),
                               nullable=False, index=True)
    technicalrecommendation_id = Column(
        Integer, ForeignKey('technicalrecommendation.id'),
        nullable=False, index=True)
    order = Column(Integer, nullable=False)

    hazardcategory = relationship('HazardCategory')
    technicalrecommendation = relationship('TechnicalRecommendation')


class Region(Base):
    __tablename__ = 'enum_region'

    id = Column(Integer, primary_key=True)
    name = Column(Unicode, nullable=False)
    # level:
    # 0 is global
    # 1 is continent
    # 2 is sub-continent
    # 3 is country
    level = Column(Integer, nullable=False)

    administrativedivisions = relationship(
        'RegionAdministrativeDivisionAssociation')


class RegionAdministrativeDivisionAssociation(Base):
    __tablename__ = 'rel_region_administrativedivision'

    id = Column(Integer, primary_key=True)
    region_id = Column(Integer,
                       ForeignKey('datamart.enum_region.id'),
                       nullable=False, index=True)
    administrativedivision_id = Column(
        Integer,
        ForeignKey('administrativedivision.id'),
        nullable=False, index=True)

    administrativedivision = relationship('AdministrativeDivision')
    region = relationship('Region')


class HazardTypeFurtherResourceAssociation(Base):
    __tablename__ = 'rel_hazardtype_furtherresource'
    id = Column(Integer, primary_key=True)
    hazardtype_id = Column(Integer,
                           ForeignKey('datamart.enum_hazardtype.id'),
                           nullable=False, index=True)
    furtherresource_id = Column(Integer,
                                ForeignKey('furtherresource.id'),
                                nullable=False, index=True)
    # FIXME: should the region_id be nullable or not ?
    region_id = Column(Integer,
                       ForeignKey('enum_region.id'),
                       nullable=False, index=True)

    hazardtype = relationship('HazardType')
    region = relationship('Region')


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
    geom = deferred(Column(Geometry('MULTIPOLYGON', 4326)))

    leveltype = relationship(AdminLevelType)
    parent = relationship('AdministrativeDivision', uselist=False,
                          remote_side=code)
    hazardcategories = relationship(
        'HazardCategoryAdministrativeDivisionAssociation',
        back_populates='administrativedivision')

    regions = relationship(
        'RegionAdministrativeDivisionAssociation')

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

    hazardtype = relationship(HazardType, lazy="joined")
    hazardlevel = relationship(HazardLevel)
    administrativedivisions = relationship(
        'HazardCategoryAdministrativeDivisionAssociation',
        back_populates='hazardcategory')

    def name(self):
        return '{} - {}'.format(self.hazardtype.mnemonic,
                                self.hazardlevel.mnemonic)

    @classmethod
    def get(cls, hazardtype, hazardlevel):
        if not isinstance(hazardtype, HazardType):
            hazardtype = HazardType.get(unicode(hazardtype))

        if not isinstance(hazardlevel, HazardLevel):
            hazardlevel = HazardLevel.get(unicode(hazardlevel))

        return DBSession.query(cls) \
            .filter(cls.hazardtype == hazardtype) \
            .filter(cls.hazardlevel == hazardlevel) \
            .one()


climatechangerec_administrativedivision = Table(
    'rel_climatechangerecommendation_administrativedivision',
    Base.metadata,
    Column('climatechangerecommendation_id', Integer,
           ForeignKey('climatechangerecommendation.id',
                      ondelete="CASCADE"),
           primary_key=True),
    Column('administrativedivision_id', Integer,
           ForeignKey('administrativedivision.id'),
           primary_key=True))


class ClimateChangeRecommendation(Base):
    __tablename__ = 'climatechangerecommendation'
    id = Column(Integer, primary_key=True)
    text = Column(Unicode, nullable=False)
    hazardtype_id = Column(Integer,
                           ForeignKey('enum_hazardtype.id'),
                           nullable=False)

    hazardtype = relationship('HazardType')

    administrativedivisions = \
        relationship("AdministrativeDivision",
                     secondary=climatechangerec_administrativedivision)


class TechnicalRecommendation(Base):
    __tablename__ = 'technicalrecommendation'
    id = Column(Integer, primary_key=True)
    text = Column(Unicode, nullable=False)

    hazardcategory_associations = relationship(
        'HazardCategoryTechnicalRecommendationAssociation',
        order_by='HazardCategoryTechnicalRecommendationAssociation.order',
        lazy='joined')

    def has_association(self, hazardtype, hazardlevel):
        """Test if this technical recommendation is associated with specified
        hazardcategory
        @param hazardtype: HazardType instance or mnemonic
        @param hazardlevel: HazardLevel instance or mnemonic
        @return boolean: True if association exists
        """
        if not isinstance(hazardtype, HazardType):
            hazardtype = HazardType.get(unicode(hazardtype))

        if not isinstance(hazardlevel, HazardLevel):
            hazardlevel = HazardLevel.get(unicode(hazardlevel))

        for association in self.hazardcategory_associations:
            if (
                    association.hazardcategory.hazardtype == hazardtype and
                    association.hazardcategory.hazardlevel == hazardlevel):
                if inspect(association).deleted:
                    return False
                return True
        return False


class FurtherResource(Base):
    __tablename__ = 'furtherresource'

    # the resource is referenced in geonode with an id:
    id = Column(Integer, primary_key=True)
    text = Column(Unicode, nullable=False)

    hazardtype_associations = relationship(
        'HazardTypeFurtherResourceAssociation',
        lazy='joined')


class HazardSet(Base):
    __tablename__ = 'hazardset'
    __table_args__ = {u'schema': 'processing'}

    # id is the string id common to the 3 layers,
    # as reported by geonode ("hazard_set" field), eg: "EQ-PA"
    id = Column(String, primary_key=True)

    # a hazardset is related to a hazard type:
    hazardtype_id = Column(Integer,
                           ForeignKey('datamart.enum_hazardtype.id'),
                           nullable=False)

    # "local" is set to false when bounds = -180/-90/180/90
    # this value comes from the linked layers
    local = Column(Boolean)
    # date the data was last updated (defaults to created):
    # this value comes from the linked layers
    data_lastupdated_date = Column(DateTime)
    # date the metadata was last updated (defaults to created):
    # this value comes from the linked layers
    metadata_lastupdated_date = Column(DateTime)
    # quality rating for the hazard calculation method
    # ranges from 0 (bad) to 10 (excellent).
    # this value comes from the linked layers
    calculation_method_quality = Column(Integer)
    # quality rating for the study
    # ranges from 0 (bad) to 2 (excellent)
    # this value comes from the linked layers
    scientific_quality = Column(Integer)
    # url to website where the data or information about them can be found
    distribution_url = Column(String)
    # name or the organization from which the data comes
    owner_organization = Column(String)

    # processing steps:
    # a hazardset starts incomplete.
    # then it becomes complete, which means:
    #   * all layers have been downloaded
    #   * the date, quality, etc fields of the hazardset has been updated
    complete = Column(Boolean, nullable=False, default=False)
    # finally it is processed:
    processed = Column(Boolean, nullable=False, default=False)

    hazardtype = relationship('HazardType', backref="hazardsets")

    def layer_by_level(self, level):
        hazardlevel = HazardLevel.get(level)
        return DBSession.query(Layer) \
            .filter(Layer.hazardset_id == self.id) \
            .filter(Layer.hazardlevel_id == hazardlevel.id) \
            .one_or_none()


class Layer(Base):
    __tablename__ = 'layer'
    __table_args__ = {u'schema': 'processing'}

    # the layer is referenced in geonode with an id:
    geonode_id = Column(Integer, primary_key=True)

    # a layer is identified by it's return_period and hazard_set:
    hazardset_id = Column(String, ForeignKey('processing.hazardset.id'),
                          nullable=False)
    # the related hazard_level, inferred from return_period
    hazardlevel_id = Column(Integer,
                            ForeignKey('datamart.enum_hazardlevel.id'))
    # the return period is typically 100, 475, 2475 years but it can vary
    return_period = Column(Integer)

    # Flood hazardtype requires a mask layer
    mask = Column(Boolean, nullable=False)

    # pixel values have a unit:
    hazardunit = Column(String)

    # date the data was last updated (defaults to created):
    data_lastupdated_date = Column(DateTime, nullable=False)
    # date the metadata was last updated (defaults to created):
    metadata_lastupdated_date = Column(DateTime, nullable=False)

    # the data can be downloaded at this URL:
    download_url = Column(String, nullable=False)

    # quality rating for the hazard calculation method
    # ranges from 0 (bad) to 10 (excellent)
    calculation_method_quality = Column(Integer, nullable=False)
    # quality rating for the study
    # ranges from 0 (bad) to 2 (excellent)
    scientific_quality = Column(Integer, nullable=False)

    # "local" is set to false when bounds = -180/-90/180/90
    # true otherwise
    local = Column(Boolean, nullable=False)

    # "downloaded" is set to true
    # when the geotiff file has been downloaded
    downloaded = Column(Boolean, nullable=False, default=False)

    hazardset = relationship('HazardSet', backref='layers')
    hazardlevel = relationship('HazardLevel')

    def name(self):
        if self.return_period is None:
            if self.mask:
                return '{}-MASK'.format(self.hazardset_id)
            return self.hazardset_id
        else:
            return '{}-{}'.format(self.hazardset_id, self.return_period)

    def filename(self):
        return self.download_url.split('/').pop()


class Output(Base):
    __tablename__ = 'output'
    __table_args__ = {u'schema': 'processing'}
    # processing results are identified by:
    #  * the hazardset they come from
    #  * the administrative division that they qualify
    hazardset_id = Column(String,
                          ForeignKey('processing.hazardset.id'),
                          primary_key=True)
    admin_id = Column(Integer,
                      ForeignKey('datamart.administrativedivision.id'),
                      primary_key=True)
    # the coverage_ratio ranges from 0 to 100
    # it represents the percentage of the admin division area
    # covered by the data in the hazardset
    # (NO-DATA values are not taken into account here)
    coverage_ratio = Column(Integer, nullable=False)
    # hazard_level_id is the processing result
    hazardlevel_id = Column(Integer,
                            ForeignKey('datamart.enum_hazardlevel.id'),
                            nullable=False)

    hazardset = relationship('HazardSet')
    administrativedivision = relationship('AdministrativeDivision')
    hazardlevel = relationship('HazardLevel')


class FeedbackStatus(Base):
    __tablename__ = 'enum_feedbackstatus'

    id = Column(Integer, primary_key=True)
    mnemonic = Column(Unicode)
    title = Column(Unicode, nullable=False)


class UserFeedback(Base):
    __tablename__ = 'userfeedback'

    id = Column(Integer, primary_key=True)
    description = Column(Unicode, nullable=False)
    submissiondate = Column(DateTime, nullable=False,
                            default=datetime.datetime.utcnow)
    useremailaddress = Column(String(254))
    url = Column(Unicode, nullable=False)
    feedbackstatus_id = Column(Integer, ForeignKey(FeedbackStatus.id),
                               nullable=False)

    feedbackstatus = relationship(FeedbackStatus)
