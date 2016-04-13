- [ ] Create a branch
```
git co -b A.B.C
```
- [ ] Update version number in setup.py
- [ ] git ci -m "Bumping version A.B.C"
- [ ] git tag A.B.C (for example 2.3.0)
```
git tag -a A.B.C
```
- [ ] git push upstream --tags
- [ ] checkout master branch
- [ ] change version number in setup.py to next dev version
