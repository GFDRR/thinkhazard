import sys
import argparse
from sqlalchemy import engine_from_config

from ..models import DBSession

from ..processing import settings
from ..processing.downloading import download


def main(argv=sys.argv):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--title', dest='title', action='store',
        help='The layer title')
    parser.add_argument(
        '--force', dest='force',
        action='store_const', const=True, default=False,
        help='Force download even if layer has already been downloaded')
    parser.add_argument(
        '--dry-run', dest='dry_run',
        action='store_const', const=True, default=False,
        help='Perform a trial run that does not commit changes')
    args = parser.parse_args(argv[1:])

    engine = engine_from_config(settings, 'sqlalchemy.')
    DBSession.configure(bind=engine)

    download(
        title=args.title,
        force=args.force,
        dry_run=args.dry_run)
