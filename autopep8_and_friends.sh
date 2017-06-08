#!/bin/bash
find . -name '._*' | xargs rm
for f in $(find . -name '*.py' -and -not -path '*/venv/*' -and -not -path '*/h264-live-player/*')
do
    echo "================="
    echo $f
    autopep8 -ri --max-line-length=10000 $f
    flake8 $f
    isort -rc $f
    pylint $f
done
