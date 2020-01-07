# -*- coding: utf-8 -*-
#
# Copyright (C) 2015-2017 by the GFDRR / World Bank
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
import pytz
from slugify import slugify

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
    Index,
    select,
)
from sqlalchemy.schema import MetaData

from sqlalchemy.ext.declarative import declarative_base

from sqlalchemy.orm import backref, scoped_session, sessionmaker, relationship, deferred

from sqlalchemy.sql.expression import true

from sqlalchemy.event import listens_for

from geoalchemy2 import Geometry

from zope.sqlalchemy import register

DBSession = scoped_session(sessionmaker())
register(DBSession)
Base = declarative_base(metadata=MetaData(schema="datamart"))


adminleveltypes = threading.local().__dict__
hazardlevels = threading.local().__dict__
hazardtypes = threading.local().__dict__


class AdminLevelType(Base):
    __tablename__ = "enum_adminleveltype"

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
            adminleveltype = (
                DBSession.query(cls).filter(cls.mnemonic == mnemonic).one_or_none()
            )
            if adminleveltype is not None:
                adminleveltypes[mnemonic] = adminleveltype
            return adminleveltype


level_weights = {None: 0, "VLO": 1, "LOW": 2, "MED": 3, "HIG": 4}


class HazardLevel(Base):
    __tablename__ = "enum_hazardlevel"

    id = Column(Integer, primary_key=True)
    mnemonic = Column(Unicode, unique=True)
    title = Column(Unicode, nullable=False)
    order = Column(Integer)

    def __cmp__(self, other):
        if other is None:
            return 1
        return cmp(level_weights[self.mnemonic], level_weights[other.mnemonic])

    @classmethod
    def get(cls, mnemonic):
        if mnemonic in hazardlevels:
            hazardlevel = hazardlevels[mnemonic]
            insp = inspect(hazardlevel)
            if not insp.detached:
                return hazardlevel
        with DBSession.no_autoflush:
            hazardlevel = (
                DBSession.query(cls).filter(cls.mnemonic == mnemonic).one_or_none()
            )
            if hazardlevel is not None:
                hazardlevels[mnemonic] = hazardlevel
            return hazardlevel

    def __json__(self, request):
        return {"mnemonic": self.mnemonic, "title": self.title}


class HazardType(Base):
    __tablename__ = "enum_hazardtype"

    id = Column(Integer, primary_key=True)
    mnemonic = Column(Unicode, unique=True)
    title = Column(Unicode, nullable=False)
    order = Column(Integer)
    # whether the hazard type should be listed in the UI or not
    ready = Column(Boolean)

    @classmethod
    def get(cls, mnemonic):
        if mnemonic in hazardtypes:
            hazardtype = hazardtypes[mnemonic]
            insp = inspect(hazardtype)
            if not insp.detached:
                return hazardtype
        with DBSession.no_autoflush:
            hazardtype = (
                DBSession.query(cls).filter(cls.mnemonic == mnemonic).one_or_none()
            )
            if hazardtype is not None:
                hazardtypes[mnemonic] = hazardtype
            return hazardtype

    def __json__(self, request):
        return {"mnemonic": self.mnemonic, "hazardtype": self.title}


hazardcategory_administrativedivision_hazardset_table = Table(
    "rel_hazardcategory_administrativedivision_hazardset",
    Base.metadata,
    Column(
        "rel_hazardcategory_administrativedivision_id",
        Integer,
        ForeignKey("rel_hazardcategory_administrativedivision.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "hazardset_id",
        String,
        ForeignKey("processing.hazardset.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class HazardCategoryAdministrativeDivisionAssociation(Base):
    __tablename__ = "rel_hazardcategory_administrativedivision"

    id = Column(Integer, primary_key=True)
    administrativedivision_id = Column(
        Integer,
        ForeignKey("administrativedivision.id", ondelete="CASCADE"),
        nullable=False,
    )
    hazardcategory_id = Column(Integer, ForeignKey("hazardcategory.id"), nullable=False)
    administrativedivision = relationship(
        "AdministrativeDivision", back_populates="hazardcategories", lazy="joined"
    )
    hazardcategory = relationship(
        "HazardCategory", back_populates="administrativedivisions", lazy="joined"
    )
    hazardsets = relationship(
        "HazardSet",
        secondary=hazardcategory_administrativedivision_hazardset_table,
        lazy="joined",
    )

    # Explicitely choose index names to avoid truncation
    __table_args__ = (
        Index("ix_datamart_rel_hc_ad_ad", "administrativedivision_id"),
        Index("ix_datamart_rel_hc_ad_hc", "hazardcategory_id"),
        {},
    )


class HazardCategoryTechnicalRecommendationAssociation(Base):
    __tablename__ = "rel_hazardcategory_technicalrecommendation"
    id = Column(Integer, primary_key=True)
    hazardcategory_id = Column(Integer, ForeignKey("hazardcategory.id"), nullable=False)
    technicalrecommendation_id = Column(
        Integer,
        ForeignKey("technicalrecommendation.id", ondelete="CASCADE"),
        nullable=False,
    )
    order = Column(Integer, nullable=False)

    hazardcategory = relationship(
        "HazardCategory",
        backref=backref(
            "tec_rec_associations",
            order_by="HazardCategoryTechnicalRecommendationAssociation.order",
        ),
    )
    technicalrecommendation = relationship("TechnicalRecommendation")

    # Explicitely choose index names to avoid truncation
    __table_args__ = (
        Index("ix_datamart_rel_hc_tr_hc", "hazardcategory_id"),
        Index("ix_datamart_rel_hc_tr_tc", "technicalrecommendation_id"),
        {},
    )


region_administrativedivision_table = Table(
    "rel_region_administrativedivision",
    Base.metadata,
    Column(
        "region_id", Integer, ForeignKey("datamart.enum_region.id", ondelete="CASCADE")
    ),
    Column(
        "administrativedivision_id",
        Integer,
        ForeignKey("administrativedivision.id", ondelete="CASCADE"),
    ),
)


class Region(Base):
    __tablename__ = "enum_region"

    id = Column(Integer, primary_key=True)
    name = Column(Unicode, nullable=False)
    # level:
    # 0 is global
    # 1 is continent
    # 2 is sub-continent
    # 3 is country
    level = Column(Integer, nullable=False)

    administrativedivisions = relationship(
        "AdministrativeDivision",
        secondary=region_administrativedivision_table,
        backref="regions",
    )


class HazardTypeFurtherResourceAssociation(Base):
    __tablename__ = "rel_hazardtype_furtherresource"
    id = Column(Integer, primary_key=True)
    hazardtype_id = Column(
        Integer, ForeignKey("datamart.enum_hazardtype.id"), nullable=False, index=True
    )
    furtherresource_id = Column(
        Integer, ForeignKey("furtherresource.id"), nullable=False, index=True
    )
    # FIXME: should the region_id be nullable or not ?
    region_id = Column(
        Integer, ForeignKey("enum_region.id"), nullable=False, index=True
    )

    hazardtype = relationship("HazardType")
    region = relationship("Region")
    furtherresource = relationship("FurtherResource", lazy="joined")


class AdministrativeDivision(Base):
    __tablename__ = "administrativedivision"

    id = Column(Integer, primary_key=True)
    code = Column(Integer, index=True, unique=True, nullable=False)
    leveltype_id = Column(
        Integer, ForeignKey(AdminLevelType.id), nullable=False, index=True
    )
    name = Column(Unicode, nullable=False)
    name_fr = Column(Unicode)
    name_es = Column(Unicode)
    parent_code = Column(
        Integer,
        ForeignKey(
            "administrativedivision.code",
            use_alter=True,
            name="administrativedivision_parent_code_fkey",
        ),
    )
    geom = deferred(Column(Geometry("MULTIPOLYGON", 4326)))

    leveltype = relationship(AdminLevelType)
    parent = relationship(
        "AdministrativeDivision",
        uselist=False,
        lazy="joined",
        join_depth=2,
        remote_side=code,
    )
    hazardcategories = relationship(
        "HazardCategoryAdministrativeDivisionAssociation",
        back_populates="administrativedivision",
    )

    def __json__(self, request):
        lang = request.locale_name
        attr = "name" if lang == "en" else "name_" + lang
        if self.leveltype_id == 1:
            return {
                "code": self.code,
                "admin0": getattr(self, attr),
                "url": request.route_url("report_overview", division=self),
            }
        if self.leveltype_id == 2:
            return {
                "code": self.code,
                "admin0": getattr(self.parent, attr),
                "admin1": self.name,
                "url": request.route_url("report_overview", division=self),
            }
        if self.leveltype_id == 3:
            return {
                "code": self.code,
                "admin0": getattr(self.parent.parent, attr),
                "admin1": self.parent.name,
                "admin2": self.name,
                "url": request.route_url("report_overview", division=self),
            }

    def slug(self):
        tokens = [self.name]
        parent = self.parent
        while parent:
            tokens.append(parent.name)
            parent = parent.parent
        tokens.reverse()
        return slugify("-".join(tokens))

    def translated_name(self, lang):
        attr = (
            "name"
            if lang == "en" or self.leveltype.mnemonic != "COU"
            else "name_" + lang
        )
        return getattr(self, attr)


class HazardCategory(Base):
    __tablename__ = "hazardcategory"

    id = Column(Integer, primary_key=True)
    hazardtype_id = Column(Integer, ForeignKey(HazardType.id), nullable=False)
    hazardlevel_id = Column(Integer, ForeignKey(HazardLevel.id), nullable=False)
    general_recommendation = Column(Unicode, nullable=False)
    general_recommendation_fr = Column(Unicode)
    general_recommendation_es = Column(Unicode)

    hazardtype = relationship(HazardType, lazy="joined")
    hazardlevel = relationship(HazardLevel)
    administrativedivisions = relationship(
        "HazardCategoryAdministrativeDivisionAssociation",
        back_populates="hazardcategory",
    )

    def name(self):
        return "{} - {}".format(self.hazardtype.mnemonic, self.hazardlevel.mnemonic)

    def translated_general_recommendation(self, lang):
        attr = "general_recommendation"
        return getattr(self, attr if lang == "en" else "%s_%s" % (attr, lang))

    @classmethod
    def get(cls, hazardtype, hazardlevel):
        if not isinstance(hazardtype, HazardType):
            hazardtype = HazardType.get(str(hazardtype))

        if not isinstance(hazardlevel, HazardLevel):
            hazardlevel = HazardLevel.get(str(hazardlevel))

        return (
            DBSession.query(cls)
            .filter(cls.hazardtype == hazardtype)
            .filter(cls.hazardlevel == hazardlevel)
            .one()
        )

    def __json__(self, request):
        return {
            "hazard_type": self.hazardtype.title,
            "hazard_level": self.hazardlevel.title,
            "general_recommendation": self.general_recommendation,
            "technical_recommendations": [
                a.technicalrecommendation for a in self.tec_rec_associations
            ],
        }


class ClimateChangeRecommendation(Base):
    __tablename__ = "climatechangerecommendation"
    id = Column(Integer, primary_key=True)
    text = Column(Unicode, nullable=False)
    text_fr = Column(Unicode)
    text_es = Column(Unicode)
    hazardtype_id = Column(Integer, ForeignKey("enum_hazardtype.id"), nullable=False)
    hazardtype = relationship("HazardType")

    def __json__(self, request):
        return self.text

    def translated_text(self, lang):
        attr = "text"
        return getattr(self, attr if lang == "en" else "%s_%s" % (attr, lang))


class ClimateChangeRecAdministrativeDivisionAssociation(Base):
    __tablename__ = "rel_climatechangerecommendation_administrativedivision"
    administrativedivision_id = Column(
        Integer,
        ForeignKey("administrativedivision.id", ondelete="CASCADE"),
        primary_key=True,
    )
    # hazardtype_id is duplicate with climatechangerecommendation.hazardtype_id
    # but here it take part in primary key and ease associations handling
    hazardtype_id = Column(Integer, ForeignKey("enum_hazardtype.id"), primary_key=True)
    climatechangerecommendation_id = Column(
        Integer,
        ForeignKey("climatechangerecommendation.id", ondelete="CASCADE"),
        nullable=False,
    )
    administrativedivision = relationship("AdministrativeDivision")
    hazardtype = relationship("HazardType")
    climatechangerecommendation = relationship(
        "ClimateChangeRecommendation",
        foreign_keys=(
            "ClimateChangeRecAdministrativeDivisionAssociation."
            "climatechangerecommendation_id"
        ),
        backref=backref(
            "associations", cascade="all, delete-orphan", passive_deletes=True
        ),
    )


class TechnicalRecommendation(Base):
    __tablename__ = "technicalrecommendation"
    id = Column(Integer, primary_key=True)
    text = Column(Unicode, nullable=False)
    text_fr = Column(Unicode)
    text_es = Column(Unicode)
    detail = Column(Unicode)
    detail_fr = Column(Unicode)
    detail_es = Column(Unicode)

    hazardcategory_associations = relationship(
        "HazardCategoryTechnicalRecommendationAssociation",
        order_by="HazardCategoryTechnicalRecommendationAssociation.order",
        lazy="joined",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def translated_text(self, lang):
        attr = "text"
        return getattr(self, attr if lang == "en" else "%s_%s" % (attr, lang))

    def translated_detail(self, lang):
        attr = "detail"
        return getattr(self, attr if lang == "en" else "%s_%s" % (attr, lang))

    def has_association(self, hazardtype, hazardlevel):
        """Test if this technical recommendation is associated with specified
        hazardcategory
        @param hazardtype: HazardType instance or mnemonic
        @param hazardlevel: HazardLevel instance or mnemonic
        @return boolean: True if association exists
        """
        if not isinstance(hazardtype, HazardType):
            hazardtype = HazardType.get(str(hazardtype))

        if not isinstance(hazardlevel, HazardLevel):
            hazardlevel = HazardLevel.get(str(hazardlevel))

        for association in self.hazardcategory_associations:
            if (
                association.hazardcategory.hazardtype == hazardtype
                and association.hazardcategory.hazardlevel == hazardlevel
            ):
                if inspect(association).deleted:
                    return False
                return True
        return False

    def __json__(self, request):
        return {"text": self.text, "detail": self.detail}


class FurtherResource(Base):
    __tablename__ = "furtherresource"

    # the resource is referenced in geonode with an id:
    id = Column(Integer, primary_key=True)
    text = Column(Unicode, nullable=False)

    hazardtype_associations = relationship(
        "HazardTypeFurtherResourceAssociation", lazy="joined"
    )


hazardset_region_table = Table(
    "rel_hazardset_region",
    Base.metadata,
    Column(
        "hazardset_id",
        String,
        ForeignKey("processing.hazardset.id", ondelete="CASCADE"),
    ),
    Column(
        "region_id", Integer, ForeignKey("datamart.enum_region.id", ondelete="CASCADE")
    ),
    schema="processing",
)


class HazardSet(Base):
    __tablename__ = "hazardset"
    __table_args__ = {"schema": "processing"}

    # id is the string id common to the 3 layers,
    # as reported by geonode ("hazard_set" field), eg: "EQ-PA"
    id = Column(String, primary_key=True)

    # a hazardset is related to a hazard type:
    hazardtype_id = Column(
        Integer, ForeignKey("datamart.enum_hazardtype.id"), nullable=False
    )

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
    detail_url = Column(String)
    # name or the organization from which the data comes
    owner_organization = Column(String)

    # processing steps:
    # a hazardset starts incomplete.
    # then it becomes complete, which means:
    #   * all layers have been downloaded
    #   * the date, quality, etc fields of the hazardset has been updated
    complete = Column(Boolean, nullable=False, default=False)
    # If not complete, reason why
    complete_error = Column(String)
    # finally it is processed:
    processed = Column(DateTime)
    # If not processed, reason why
    processing_error = Column(String)

    hazardtype = relationship("HazardType", backref="hazardsets")

    regions = relationship("Region", secondary=hazardset_region_table)

    def layer_by_level(self, level):
        hazardlevel = HazardLevel.get(level)
        return (
            DBSession.query(Layer)
            .filter(Layer.hazardset_id == self.id)
            .filter(Layer.hazardlevel_id == hazardlevel.id)
            .one_or_none()
        )

    def __json__(self, request):
        return {
            "id": self.id,
            "owner_organization": self.owner_organization,
            "detail_url": self.detail_url,
        }


@listens_for(HazardSet.processed, "set")
def on_hazardset_processed_set(target, value, oldvalue, initiator):
    if value is None and target.id is not None:
        DBSession.query(Output).filter(Output.hazardset_id == target.id).autoflush(
            False
        ).delete()


class Layer(Base):
    __tablename__ = "layer"
    __table_args__ = {"schema": "processing"}

    # the layer is referenced in geonode with an id:
    geonode_id = Column(Integer, primary_key=True)
    typename = Column(String, unique=True)

    # a layer is identified by it's return_period and hazard_set:
    hazardset_id = Column(String, ForeignKey("processing.hazardset.id"), nullable=False)
    # the related hazard_level, inferred from return_period
    hazardlevel_id = Column(Integer, ForeignKey("datamart.enum_hazardlevel.id"))
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

    hazardlevel_order = deferred(
        select([HazardLevel.order]).where(HazardLevel.id == hazardlevel_id)
    )
    hazardset = relationship(
        "HazardSet",
        backref=backref("layers", order_by="Layer.hazardlevel_order.desc()"),
    )
    hazardlevel = relationship("HazardLevel")

    def name(self):
        if self.return_period is None:
            if self.mask:
                return "{}-MASK".format(self.hazardset_id)
            return self.hazardset_id
        else:
            return "{}-{}".format(self.hazardset_id, self.return_period)

    def filename(self):
        return self.download_url.split("/").pop()


class Output(Base):
    __tablename__ = "output"
    __table_args__ = {"schema": "processing"}
    # processing results are identified by:
    #  * the hazardset they come from
    #  * the administrative division that they qualify
    hazardset_id = Column(
        String, ForeignKey("processing.hazardset.id"), primary_key=True
    )
    admin_id = Column(
        Integer,
        ForeignKey("datamart.administrativedivision.id", ondelete="CASCADE"),
        primary_key=True,
    )
    # hazard_level_id is the processing result
    hazardlevel_id = Column(
        Integer, ForeignKey("datamart.enum_hazardlevel.id"), nullable=False
    )

    hazardset = relationship("HazardSet")
    administrativedivision = relationship("AdministrativeDivision")
    hazardlevel = relationship("HazardLevel")


class FeedbackStatus(Base):
    __tablename__ = "enum_feedbackstatus"

    id = Column(Integer, primary_key=True)
    mnemonic = Column(Unicode)
    title = Column(Unicode, nullable=False)


class UserFeedback(Base):
    __tablename__ = "userfeedback"

    id = Column(Integer, primary_key=True)
    description = Column(Unicode, nullable=False)
    submissiondate = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    useremailaddress = Column(String(254))
    url = Column(Unicode, nullable=False)
    feedbackstatus_id = Column(Integer, ForeignKey(FeedbackStatus.id), nullable=False)

    feedbackstatus = relationship(FeedbackStatus)


class Publication(Base):
    __tablename__ = "publication"
    id = Column(Integer, primary_key=True)
    date = Column(DateTime)

    @classmethod
    def last(cls):
        last = DBSession.query(cls).order_by(cls.date.desc()).first()
        return last

    @classmethod
    def new(cls):
        new = cls(date=datetime.datetime.now())
        DBSession.add(new)
        return new


class Harvesting(Base):
    __tablename__ = "harvesting"
    __table_args__ = {"schema": "processing"}
    id = Column(Integer, primary_key=True)
    date = Column(DateTime(timezone=True), nullable=False)
    complete = Column(Boolean, nullable=False)

    @classmethod
    def last_complete_date(cls):
        last_complete = (
            DBSession.query(cls)
            .filter(cls.complete == true())
            .order_by(cls.date.desc())
            .first()
        )
        if last_complete is None:
            return None
        return last_complete.date

    @classmethod
    def new(cls, complete):
        new = cls(
            date=datetime.datetime.utcnow().replace(tzinfo=pytz.utc), complete=complete
        )
        DBSession.add(new)
        return new


class Contact(Base):
    __tablename__ = "contact"

    id = Column(Integer, primary_key=True)
    name = Column(Unicode)
    url = Column(Unicode)
    phone = Column(Unicode)
    email = Column(Unicode)

    def __json__(self, request):
        return {
            "name": self.name,
            "url": self.url,
            "phone": self.phone,
            "email": self.email,
        }


class ContactAdministrativeDivisionHazardTypeAssociation(Base):
    __tablename__ = "rel_contact_administrativedivision_hazardtype"
    id = Column(Integer, primary_key=True)
    contact_id = Column(Integer, ForeignKey("contact.id"), nullable=False, index=True)
    administrativedivision_id = Column(
        Integer, ForeignKey("administrativedivision.id"), nullable=False
    )
    hazardtype_id = Column(
        Integer, ForeignKey("datamart.enum_hazardtype.id"), nullable=False, index=True
    )

    contact = relationship(Contact, backref="associations")
    administrativedivision = relationship(AdministrativeDivision)
    hazardtype = relationship(HazardType)
