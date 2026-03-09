# ThinkHazard

A natural hazard screening tool for disaster risk management project planning. ThinkHazard! is maintained by the Global Facility for Disaster Reduction and Recovery (GFDRR). Provides classified hazard level (very low to high) for any location in the world, and advice on managing disaster risk, plus useful reports and contacts, for 11 natural hazards. 

API instructions can be found here: https://github.com/GFDRR/thinkhazard/blob/master/API.md 

## Getting Started

The following commands assume that the system is Debian/Ubuntu. Commands may need to be adapted when working on a different system.

Build docker images:

```bash
make build
```

Run the composition:

```bash
docker compose up -d
make initdb
```

Now point your browser to <http://localhost:8080>.

Run checks and automated tests:

```bash
make check test
```

## Populate the admin database

Create the required schema and tables and populate the tables in admin database:

```bash
GPKG=path_to_geopackage_file make populatedb
```

Note: this may take a while. If you don’t want to import all the world administrative divisions, you can import only a subset:

```bash
GPKG=path_to_geopackage_file make populatedb DATA=turkey
```

or:

```bash
GPKG=path_to_geopackage_file make populatedb DATA=indonesia
```

## Publication of admin database on public site

Publication consist in overwriting the public database with the admin one. This can be done using:

```bash
make publish
```

And this will execute as follow :
 * Lock the public site in maintenance mode.
 * Store a publication date in the admin database.
 * Backup the admin database in archives folder.
 * Create a new fresh public database.
 * Restore the admin backup into public database.
 * Unlock the public site from maintenance mode.

### Configure admin username/password

Authentication is based on environment variable `HTPASSWORDS` which should contain
usernames and passwords using Apache `htpasswd` file format.

To create an authentification file `.htpasswd` with `admin` as the initial user:

```bash
htpasswd -c .htpasswd admin
```

It will prompt for the passwd.

Add or modify `username2` in the password file `.htpasswd`:

```bash
htpasswd .htpasswd username2
```

Then pass the content of the file to environment variable:

```yaml
environment:
  HTPASSWORDS: |
    admin:admin
    user:user
```

### Analytics

If you want to get some analytics on the website usage (via Google analytics), you can add the tracking code using an analytics variable:

```yaml
environment:
  ANALYTICS: UA-75301865-1
```

### Feedback

The `feedback_form_url` can be configured in the `production.ini` file.

## Translations

ThinkHazard! is translated using `Transifex`.

### Workflow

We use lingua to extract translation string from `jinja2` templates.

Use the following command to update the gettext template (`.pot`):

```bash
make extract_messages
```

Note: this should be done from the production instance ONLY in order to have
the up-to-date database strings extracted!
You will have to make sure that the `~/.transifexrc` is valid and the
credentials correspond to the correct rights.

Then you can push the translation sources to transifex.

```bash
make transifex-push
```

Once the translations are OK on Transifex it's possible to pull the translations:

```bash
make transifex-pull
```

Don't forget to compile the catalog (ie. convert .po to .mo):

```bash
make compile_catalog
```

### Development

There are 3 different ways to translate strings in the templates:

- `translate` filter

    This should be used for strings corresponding to enumeration tables in
    database.

    ```
    {{ hazard.title | translate }}
    ```

- `gettext` method

    To be used for any UI string.

    ```
    {{gettext('Download PDF')}}
    ```

- model class method

    Some model classes have specific method to retrive the value from a field
    specific to chosen language.

    ```
    {{ division.translated_name(request.locale_name)}}
    ```

## Debugging with VS Code

Copy content of `docker-compose.override.sample.yaml` to `docker-compose.override.yaml`.

Then here is an example `.vscode/launch.json` file:

```yaml
{
    // Use IntelliSense to learn about possible attributes.
    // Hover to view descriptions of existing attributes.
    // For more information, visit: https://go.microsoft.com/fwlink/?linkid=830387
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python Debugger: Remote Attach Thinkhazard",
            "type": "debugpy",
            "request": "attach",
            "connect": {
                "host": "localhost",
                "port": 5678
            },
            "pathMappings": [
                {
                    "localRoot": "${workspaceFolder}",
                    "remoteRoot": "/app"
                }
            ]
        },
        {
            "name": "Python Debugger: Remote Attach Taskrunner",
            "type": "debugpy",
            "request": "attach",
            "connect": {
                "host": "localhost",
                "port": 5679
            },
            "pathMappings": [
                {
                    "localRoot": "${workspaceFolder}",
                    "remoteRoot": "/app"
                }
            ]
        },
        {
            "name": "Python Debugger: Remote Attach Tests",
            "type": "debugpy",
            "request": "attach",
            "connect": {
                "host": "localhost",
                "port": 5680
            },
            "pathMappings": [
                {
                    "localRoot": "${workspaceFolder}",
                    "remoteRoot": "/app"
                }
            ]
        }
    ]
}
```
