- [ ] Create a branch (Use major version for the name of the branch)
```
git co -b A.B
```
- [ ] Update version number in setup.py (Use minor version A.B.C),commit the changes and push branch to github
```
vim setup.py
git add setup.py
git ci -m "Bumping version A.B.C"
git push origin A.B
```
- [ ] Add a tag for minor version
```
git tag -s -a A.B.C
git push origin --tags
```
- [ ] checkout master branch, change version number in setup.py (A.D-dev) and push to github
```
git co master
vim setup.py
git add setup.py
git ci -m "Bumping version A-D-dev"
git push origin master
```
