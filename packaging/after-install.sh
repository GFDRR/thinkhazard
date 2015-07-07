#!/bin/bash
shopt -s extglob
rm -rf <%= prefix %>/venv/lib/python2.*/site-packages/PythonProject-!(<%= version %>)-py2.*.egg-info
shopt -u extglob
