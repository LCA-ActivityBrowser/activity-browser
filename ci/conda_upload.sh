#!/usr/bin/env bash
# Script for building and uploading the dev and/or stable packages to conda

# Only upload from linux, and use different variables for dev and stable builds
if [ "$TRAVIS_OS_NAME" == "linux" -a "$TRAVIS_PYTHON_VERSION" == "3.7" ]; then
    USER=bsteubing
    mkdir -p ~/conda-bld
    conda config --set anaconda_upload no
    export CONDA_BLD_PATH=~/conda-bld

    # Check if TRAVIS_TAG variable is set or empty.
    if [ -z "$TRAVIS_TAG" ]; then
        export PKG_NAME="activity-browser-dev"
        export VERSION=`date +%Y.%m.%d`
        BUILD_ARGS="--old-build-string"
        UPLOAD_ARGS="--force"
    else
        export PKG_NAME="activity-browser"
        export VERSION="$TRAVIS_TAG"
        export SUMMARY="GUI for brightway2"
        BUILD_ARGS=""
        UPLOAD_ARGS=""
        # Strip the last sentence (as this is the stable version) out of the meta.yaml file.
        # NOTE: this can get fiddly.
        sed -i -e "`wc -l $TRAVIS_BUILD_DIR/ci/travis/recipe/meta.yaml | cut -d ' ' -f 1`d" $TRAVIS_BUILD_DIR/ci/travis/recipe/meta.yaml
    fi

    conda install -q conda-build anaconda-client conda-verify
    echo "RUNNING BUILD"
    conda build -c conda-forge -c cmutel -c haasad $TRAVIS_BUILD_DIR/ci/travis/recipe $BUILD_ARGS
    echo "BUILD FINISHED"

    ls $CONDA_BLD_PATH/noarch/

    echo "UPLOADING BUILD: $USER"
    anaconda -t $CONDA_UPLOAD_TOKEN upload -u $USER -l main $CONDA_BLD_PATH/noarch/$PKG_NAME-$VERSION-py_0.tar.bz2 $UPLOAD_ARGS
    echo "BUILD UPLOADED: $USER"
else
    echo "No uploads from MacOS or Linux python 3.6"
fi
