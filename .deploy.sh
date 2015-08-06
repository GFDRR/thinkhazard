#!/bin/sh -xe

SSH_OPTS="-o StrictHostKeyChecking=no -i id_rsa"
SSH_HOST="reprepro@pkg.camptocamp.net"
SECTION="ci"
DISTRO="jessie"
PACKAGE_NAME="thinkhazard"

if [ -z $TRAVIS_TAG ]; then
  # TODO: pass $TRAVIS_TAG to make deb?
  make deb
  PACKAGE=$(ls ${PACKAGE_NAME}_*.deb)
  scp $SSH_OPTS $PACKAGE $SSH_HOST:/var/packages/apt/incoming
  ssh $SSH_OPTS $SSH_HOST "/usr/bin/reprepro -b /var/packages/apt -S ${SECTION} -P optional includedeb ${DISTRO}/dev /var/packages/apt/incoming/${PACKAGE}"
else
  ssh $SSH_OPTS $SSH_HOST "/usr/bin/reprepro -b /var/packages/apt copy ${DISTRO}/${TRAVIS_TAG##*/} ${DISTRO}/dev ${PACKAGE_NAME}"
fi
