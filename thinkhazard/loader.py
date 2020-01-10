import os
from typing import Dict, Optional, cast

from plaster_pastedeploy import Loader as BaseLoader


class Loader(BaseLoader):  # type: ignore
    def _get_defaults(
        self, defaults: Optional[Dict[str, str]] = None
    ) -> Dict[str, str]:
        d: Dict[str, str] = {}
        d.update(os.environ)
        d.update(defaults or {})
        settings = super()._get_defaults(d)
        return cast(Dict[str, str], settings)

    def __repr__(self) -> str:
        return 'thinkhazard.loader.Loader(uri="{0}")'.format(self.uri)
