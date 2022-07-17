#!/bin/sh

export X_BASE_DIR="$(dirname $0)"

cd $X_BASE_DIR


if [ "$#" = "0" ]; then
    if [ -z "$X_QUIET" ] ; then
      git diff --quiet --exit-code  || git status
    fi    
    exec poetry shell
else
    exec poetry run $@
fi


