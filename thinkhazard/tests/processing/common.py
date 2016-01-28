from sqlalchemy import func

from ...models import (
    DBSession,
    Layer,
    )


def new_geonode_id():
    row = DBSession.query(func.max(Layer.geonode_id)).one_or_none()
    if row[0] is None:
        return 1
    return row[0] + 1
