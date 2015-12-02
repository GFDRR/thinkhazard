import os

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, 'README.rst')) as f:
    README = f.read()
with open(os.path.join(here, 'CHANGES.rst')) as f:
    CHANGES = f.read()

requires = [
    'geoalchemy2',
    'psycopg2',
    'pyramid == 1.6.a2',
    'pyramid_jinja2',
    'pyramid_debugtoolbar',
    'pyramid_tm',
    'simplejson',
    'SQLAlchemy',
    'shapely',
    'transaction',
    'zope.sqlalchemy',
    'waitress',
    'papyrus==2.0dev3',
    'WebTest==2.0.18',
    'nose',
    'pyquery==1.2.9'
    ]

setup(name='thinkhazard',
      version='0.0',
      description='thinkhazard',
      long_description=README + '\n\n' + CHANGES,
      classifiers=[
          "Programming Language :: Python",
          "Framework :: Pyramid",
          "Topic :: Internet :: WWW/HTTP",
          "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
          ],
      author='',
      author_email='',
      url='',
      keywords='web wsgi bfg pylons pyramid',
      packages=find_packages(),
      include_package_data=True,
      zip_safe=False,
      test_suite='thinkhazard',
      install_requires=requires,
      entry_points="""\
      [paste.app_factory]
      main = thinkhazard:main
      [console_scripts]
      initialize_thinkhazard_db = thinkhazard.scripts.initializedb:main
      import_recommendations = \
        thinkhazard.scripts.import_recommendations:main
      """,
      )
