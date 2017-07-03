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

import logging
from ..models import (
    DBSession,
    AdminLevelType,
    )

from . import BaseProcessor


logger = logging.getLogger(__name__)


class DecisionMaker(BaseProcessor):

    def do_execute(self, hazardset_id=None):
        connection = DBSession.bind.connect()
        trans = connection.begin()
        try:
            logger.info("Purging previous relations")
            connection.execute(clearall_query())

            logger.info("Calculating level REG")
            connection.execute(level_reg_query())

            logger.info("Upscaling to PRO")
            connection.execute(upscaling_query(u'PRO'))

            logger.info("Upscaling to COU")
            connection.execute(upscaling_query(u'COU'))

            trans.commit()
        except:
            trans.rollback()
            logger.error('An error occurred in decision tree',
                         exc_info=True)


def clearall_query():
    return '''
DELETE FROM datamart.rel_hazardcategory_administrativedivision_hazardset;
DELETE FROM datamart.rel_hazardcategory_administrativedivision;
'''


def level_reg_query():
    return '''
/*
 * Apply decision tree on first level
 */
INSERT INTO datamart.rel_hazardcategory_administrativedivision (
    administrativedivision_id,
    hazardcategory_id
)
SELECT DISTINCT
    output.admin_id AS administrativedivision_id,
    first_value(category.id) OVER w AS hazardcategory_id
FROM
    processing.output AS output
    JOIN processing.hazardset AS set
        ON set.id = output.hazardset_id
    JOIN datamart.hazardcategory AS category
        ON category.hazardtype_id = set.hazardtype_id
        AND category.hazardlevel_id = output.hazardlevel_id
    WHERE set.complete = TRUE
WINDOW w AS (
    PARTITION BY
        output.admin_id,
        set.hazardtype_id
    ORDER BY
        set.calculation_method_quality DESC,
        set.scientific_quality DESC,
        set.local DESC,
        set.data_lastupdated_date DESC
);


/*
 * Produce relations with hazardsets (sources)
 */
INSERT INTO datamart.rel_hazardcategory_administrativedivision_hazardset (
    rel_hazardcategory_administrativedivision_id,
    hazardset_id
)
SELECT DISTINCT
    rel.id AS rel_hazardcategory_administrativedivision_id,
    first_value(set.id) OVER w AS hazardset_id
FROM
    processing.output AS output
    JOIN processing.hazardset AS set
        ON set.id = output.hazardset_id
    JOIN datamart.hazardcategory AS category
        ON category.hazardtype_id = set.hazardtype_id
        AND category.hazardlevel_id = output.hazardlevel_id
    JOIN datamart.rel_hazardcategory_administrativedivision AS rel
        ON rel.administrativedivision_id = output.admin_id
        AND rel.hazardcategory_id = category.id
WINDOW w AS (
    PARTITION BY
        output.admin_id,
        set.hazardtype_id
    ORDER BY
        set.calculation_method_quality DESC,
        set.scientific_quality DESC,
        set.local DESC,
        set.data_lastupdated_date DESC
);
'''


def upscaling_query(level):
    return '''
/*
 * Upscale hazard categories for each administrative division
 */
INSERT INTO datamart.rel_hazardcategory_administrativedivision (
    administrativedivision_id,
    hazardcategory_id
)
SELECT DISTINCT
    admindiv_parent.id AS administrativedivision_id,
    first_value(category.id) OVER w AS hazardcategory_id
FROM
    datamart.rel_hazardcategory_administrativedivision AS category_admindiv
    JOIN datamart.hazardcategory AS category
        ON category.id = category_admindiv.hazardcategory_id
    JOIN datamart.enum_hazardlevel AS level
        ON level.id =  category.hazardlevel_id
    JOIN datamart.administrativedivision AS admindiv_child
        ON admindiv_child.id = category_admindiv.administrativedivision_id
    JOIN datamart.administrativedivision AS admindiv_parent
        ON admindiv_parent.code = admindiv_child.parent_code
WHERE admindiv_parent.leveltype_id = {leveltype_id}
WINDOW w AS (
    PARTITION BY
        admindiv_parent.id,
        category.hazardtype_id
    ORDER BY
        level.order
);


/*
 * Upscale relations with hazardsets (sources)
 */
INSERT INTO datamart.rel_hazardcategory_administrativedivision_hazardset (
    rel_hazardcategory_administrativedivision_id,
    hazardset_id
)
SELECT DISTINCT
    hc_ad_parent.id,
    hc_ad_hs.hazardset_id
FROM
    -- Get hazardset_id from hc_ad_hs child level
    datamart.rel_hazardcategory_administrativedivision_hazardset AS hc_ad_hs

    -- Get hc_ad child level
    JOIN datamart.rel_hazardcategory_administrativedivision AS hc_ad_child
        ON hc_ad_child.id =
            hc_ad_hs.rel_hazardcategory_administrativedivision_id

    -- Get ad child level
    JOIN datamart.administrativedivision AS ad_child
        ON ad_child.id = hc_ad_child.administrativedivision_id

    -- Get ad parent level
    JOIN datamart.administrativedivision AS ad_parent
        ON ad_parent.code = ad_child.parent_code

    -- Get hc_ad parent level to obtain destination hc_ad identifier
    JOIN datamart.rel_hazardcategory_administrativedivision AS hc_ad_parent
        ON hc_ad_parent.administrativedivision_id = ad_parent.id
        AND hc_ad_parent.hazardcategory_id = hc_ad_child.hazardcategory_id
WHERE ad_parent.leveltype_id = {leveltype_id};
'''.format(leveltype_id=AdminLevelType.get(level).id)
