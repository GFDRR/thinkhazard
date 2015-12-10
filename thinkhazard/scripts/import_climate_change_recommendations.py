import os
import sys
import transaction
import csv

from sqlalchemy import engine_from_config

from pyramid.paster import (
    get_appsettings,
    setup_logging,
    )

from thinkhazard_common.models import (
    DBSession,
    AdministrativeDivision,
    ClimateChangeRecommendation,
    HazardType,
    )

from .. import load_local_settings


def usage(argv):
    cmd = os.path.basename(argv[0])
    print('usage: %s <config_uri>\n'
          '(example: "%s development.ini")' % (cmd, cmd))
    sys.exit(1)


def main(argv=sys.argv):
    if len(argv) < 2:
        usage(argv)
    config_uri = argv[1]
    setup_logging(config_uri)
    settings = get_appsettings(config_uri)

    load_local_settings(settings)

    engine = engine_from_config(settings, 'sqlalchemy.')

    DBSession.configure(bind=engine)

    with transaction.manager:
        DBSession.query(ClimateChangeRecommendation).delete()

        # hazard types and corresponding columns
        hazard_types = [
            (u'FL', 6),
            (u'EQ', 7),
            (u'CY', 8),
            (u'SS', 9),
            (u'DG', 10),
            (u'TS', 11),
            (u'VA', 12),
            (u'LS', 13),
        ]

        with open('data/climate_change_recommendations.csv', 'rb') as csvfile:
            countries = csv.reader(csvfile, delimiter=',')
            next(countries, None)  # skip the headers
            for row in countries:
                division = DBSession.query(AdministrativeDivision) \
                    .filter(AdministrativeDivision.code == row[1]).one()

                for hazard_type, column in hazard_types:
                    text = row[column]
                    if text == 'NA':
                        continue

                    climate_rec = ClimateChangeRecommendation()
                    climate_rec.text = row[column]
                    climate_rec.administrativedivision = division
                    climate_rec.hazardtype = DBSession.query(HazardType) \
                        .filter(HazardType.mnemonic == hazard_type).one()
                    DBSession.add(climate_rec)
