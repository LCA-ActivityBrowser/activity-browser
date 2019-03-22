# Only need to change these two variables
PKG_NAME=activity-browser-dev
USER=bsteubing

mkdir ~/conda-bld
conda config --set anaconda_upload no
export CONDA_BLD_PATH=~/conda-bld
export VERSION=`date +%Y.%m.%d`

echo "RUNNING BUILD"
conda build . --old-build-string
echo "BUILD FINISHED"

ls $CONDA_BLD_PATH/noarch/


echo "UPLOADING BUILD: $USER"
anaconda -t $CONDA_UPLOAD_TOKEN upload -u $USER $CONDA_BLD_PATH/noarch/$PKG_NAME-$VERSION-py_0.tar.bz2 --force