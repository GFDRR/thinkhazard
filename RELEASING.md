- [ ] Create a branch (Use major version for the name of the branch)

```bash
git co -b A.B
```

- [ ] Update version number in setup.py (Use minor version A.B.C),commit the changes and push branch to github

```bash
vim setup.py
git add setup.py
git ci -m "Bumping version A.B.C"
git push origin A.B
```

- [ ] Add a tag for minor version

```bash
git tag -s -a A.B.C
git push origin --tags
```

- [ ] checkout master branch, change version number in setup.py (A.D-dev) and push to github

```bash
git co master
vim setup.py
git add setup.py
git ci -m "Bumping version A-D-dev"
git push origin master
```

- [] Create new resources on Transifex

As only one branch is supported by project in OpenSource plan we will created
dedicated resources for each branch.

In file `.tx/config` define resources for the new branch, example:

```conf
[o:gfdrr-labs:p:gfdrr-thinkhazard:r:A-B-ui]
resource_name = A-B ui
type = PO
source_file = /tmp/thinkhazard.pot
source_lang = en
file_filter = thinkhazard/locale/<lang>/LC_MESSAGES/thinkhazard.po

[o:gfdrr-labs:p:gfdrr-thinkhazard:r:A-B-database]
resource_name = A-B database
type = PO
source_file = /tmp/thinkhazard-database.pot
source_lang = en
file_filter = /tmp/thinkhazard-database-<lang>.po
```

Create new resources on transifex (pull old branch and push to new branch):

```bash
cat <<EOF | docker compose run --rm --user `id -u` thinkhazard bash
/app/thinkhazard/scripts/tx-init

tx pull --source --resources=gfdrr-thinkhazard.2-1-ui
tx pull --translations --languages=es,fr --resources=gfdrr-thinkhazard.2-1-ui
tx pull --source --resources=gfdrr-thinkhazard.2-1-database
tx pull --translations --languages=es,fr --resources=gfdrr-thinkhazard.2-1-database

tx push --source --resources=gfdrr-thinkhazard.3-0-ui --force
tx push --translation --languages=es,fr --resources=gfdrr-thinkhazard.3-0-ui --force
tx push --source --resources=gfdrr-thinkhazard.3-0-database --force
tx push --translation --languages=es,fr --resources=gfdrr-thinkhazard.3-0-database --force
EOF
```

Open [Transifex](https://app.transifex.com/gfdrr-labs/gfdrr-thinkhazard)
and mark all translations as reviewed.

In file `Makefile` set `TX_RESOURCES_PREFIX` variable:

```Makefile
export TX_BRANCH ?= 3.0
```

In file `.tx/config` remove config for the old branch (keep only the new branch).

Remove all `.po` files from `thinkhazard/locale` folder:

```bash
find thinkhazard/locale -type f -name *.po -delete
```
