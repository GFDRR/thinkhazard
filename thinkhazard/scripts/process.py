import sys
import argparse
from sqlalchemy import engine_from_config

from ..models import DBSession
from ..processing import settings
from ..processing.processing import process


def main(argv=sys.argv):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--hazardset_id',  dest='hazardset_id', action='store',
        help='The hazardset identifier')
    parser.add_argument(
        '--force', dest='force',
        action='store_const', const=True, default=False,
        help='Force execution even if hazardset has already been processed')
    parser.add_argument(
        '--dry-run', dest='dry_run',
        action='store_const', const=True, default=False,
        help='Perform a trial run that does not commit changes')
    args = parser.parse_args(argv[1:])

    engine = engine_from_config(settings, 'sqlalchemy.')
    DBSession.configure(bind=engine)

    process(
        hazardset_id=args.hazardset_id,
        force=args.force,
        dry_run=args.dry_run)
