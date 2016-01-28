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

'''
This script was created to manually add further resources. It should be deleted
once we get documents extracted from geonode.
'''
import sys
import os
import transaction

from sqlalchemy import engine_from_config

from pyramid.paster import (
    get_appsettings,
    setup_logging,
    )

from pyramid.scripts.common import parse_vars

from ..models import (
    DBSession,
    HazardType,
    HazardCategory,
    FurtherResource,
    HazardCategoryFurtherResourceAssociation,
    )

from .. import load_local_settings


def usage(argv):
    cmd = os.path.basename(argv[0])
    print('usage: %s <config_uri> [var=value]\n'
          '(example: "%s development.ini")' % (cmd, cmd))
    sys.exit(1)


def main(argv=sys.argv):
    if len(argv) < 2:
        usage(argv)
    config_uri = argv[1]
    options = parse_vars(argv[2:])
    setup_logging(config_uri)
    settings = get_appsettings(config_uri, options=options)

    load_local_settings(settings)

    engine = engine_from_config(settings, 'sqlalchemy.')
    DBSession.configure(bind=engine)

    import_further_resources()


def import_further_resources():
    with transaction.manager:

        DBSession.query(HazardCategoryFurtherResourceAssociation).delete()
        DBSession.query(FurtherResource).delete()
        DBSession.flush()

        further_resource = FurtherResource(**{
            'text': u'Educational web resources on earthquakes and seismic hazard',  # NOQA
            'url': u'http://earthquake.usgs.gov/learn/?source=sitemap'
        })
        add_resource(u'EQ', further_resource)
        add_resource(u'FL', further_resource)

        further_resource = FurtherResource(**{
            'text': u'Publications by GFDRR, providing information on disaster risk assessment, risk reduction and preparedness',  # NOQA
            'url': u'https://www.gfdrr.org/publications'
        })
        add_resource(u'EQ', further_resource)

        further_resource = FurtherResource(**{
            'text': u'The Aqueduct Global Flood Analyzer. Note that this tool only provides information about river flooding (not coastal, pluvial or flash flooding)',  # NOQA
            'url': u'http://www.wri.org/floods'
        })
        add_resource(u'FL', further_resource)

        further_resource = FurtherResource(**{
            'text': u'The Climate app, providing information on possible risk reducing intervention measures under site-specific conditions',  # NOQA
            'url': u'http://www.climateapp.nl/'
        })

        add_resource(u'FL', further_resource)

        further_resource = FurtherResource(**{
            'text': u'RIMAROCC, providing a risk management framework for road managers and operators dealing with climate change',  # NOQA
            'url': u'http://www.cedr.fr/home/index.php?id=251&dlpath=2008%20Call%20Road%20Owners%20Getting%20to%20Grips%20with%20Climate%20Change%2FRIMAROCC&cHash=0d3ce2ac10a4d935d9012c515d8e1dc3'  # NOQA
        })
        add_resource(u'FL', further_resource)

        further_resource = FurtherResource(**{
            'text': u'FLOOD PROBE, research on technologies for the cost-effective flood protection of the built environment',  # NOQA
            'url': u'http://www.floodprobe.eu'
        })
        add_resource(u'FL', further_resource)

        further_resource = FurtherResource(**{
            'text': u'Climate Change Knowledge Portal',
            'url': u'http://sdwebx.worldbank.org/climateportal/'
        })
        add_resource(u'CY', further_resource)
        add_resource(u'DG', further_resource)
        add_resource(u'CF', further_resource)

        further_resource = FurtherResource(**{
            'text': u'Drought Risk Reduction: Framework and Practices',
            'url': u'https://www.gfdrr.org/sites/gfdrr/files/publication/Drought%20Risk%20Reduction-Contributing%20to%20the%20Implementation%20of%20the%20Hyogo%20Framework%20for%20Action.pdf'  # NOQA
        })
        add_resource(u'DG', further_resource)

        further_resource = FurtherResource(**{
            'text': u'Learning from Megadisasters: Lessons from the Great Japan Earthquake',  # NOQA
            'url': u'https://www.gfdrr.org/sites/gfdrr/files/publication/Learning%20from%20Megadisasters%20%20Lessons%20from%20the%20Great%20East%20Japan%20Earthquake.pdf'  # NOQA
        })
        add_resource(u'TS', further_resource)

        further_resource = FurtherResource(**{
            'text': u'Weather and Climate Resilience: Effective Preparedness through National Meteorological and Hydrological Services',  # NOQA
            'url': u'https://www.gfdrr.org/sites/gfdrr/files/publication/Weather_and_Climate_Resilience_2013.pdf'  # NOQA
        })
        add_resource(u'CY', further_resource)

        further_resource = FurtherResource(**{
            'text': u'Volcano Observatory database - World Organization of Volcano Observatories (WOVO)',  # NOQA
            'url': u'http://www.wovo.org/observatories/'
        })
        add_resource(u'VA', further_resource)

        further_resource = FurtherResource(**{
            'text': u'Database of Volcanoes - Global Volcansim Program',
            'url': u'http://www.volcano.si.edu/search_volcano.cfm'
        })
        add_resource(u'VA', further_resource)

        further_resource = FurtherResource(**{
            'text': u'Tsunami Runup database - NGDC',
            'url': u'http://ngdc.noaa.gov/nndc/struts/form?t=101650&s=167&d=166'  # NOQA
        })
        add_resource(u'TS', further_resource)

        further_resource = FurtherResource(**{
            'text': u'Volcanic Ash: what it can do and how to prevent damage',
            'url': u'http://volcanoes.usgs.gov/ash/index.html'
        })
        add_resource(u'VA', further_resource)

        further_resource = FurtherResource(**{
            'text': u'Preparing your community for tsunamis',
            'url': u'http://geohaz.org/wp/wp-content/uploads/2015/05/PreparingYourCommunityforTsunamisVersion2-1.pdf'  # NOQA
        })
        add_resource(u'TS', further_resource)

        further_resource = FurtherResource(**{
            'text': u'National Drought Management Policy Guidelines: A Template for Action',  # NOQA
            'url': u'http://www.droughtmanagement.info/literature/IDMP_NDMPG_en.pdf'  # NOQA
        })
        add_resource(u'DG', further_resource)

        further_resource = FurtherResource(**{
            'text': u'World Bank Publication Series: Turn Down the Heat',
            'url': u'http://www.worldbank.org/en/topic/climatechange/publication/turn-down-the-heat'  # NOQA
        })
        add_resource(u'CF', further_resource)


def add_resource(hazard_type, resource):
    categories = DBSession.query(HazardCategory) \
        .join(HazardType) \
        .filter(HazardType.mnemonic == hazard_type)
    for category in categories:
        association = HazardCategoryFurtherResourceAssociation(order=1)
        association.hazardcategory = category
        resource.hazardcategory_associations.append(association)
    DBSession.add(resource)
