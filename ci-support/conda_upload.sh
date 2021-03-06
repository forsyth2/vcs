#!/usr/bin/env bash
PKG_NAME=vcs
USER=cdat
VERSION="8.0"
echo "Trying to upload to conda"
echo ""
echo "Activating base env"
source activate base
echo "Making sure conda-build is installed"
conda install conda-build
echo "Updating conda"
conda update -y -q conda
if [ `uname` == "Linux" ]; then
    OS=linux-64
    echo "Linux OS"
else
    echo "Mac OS"
    OS=osx-64
fi

mkdir ~/conda-bld
conda config --set anaconda_upload no
export CONDA_BLD_PATH=${HOME}/conda-bld
echo "Cloning recipes"
git clone git://github.com/CDAT/conda-recipes
cd conda-recipes
# uvcdat creates issues for build -c uvcdat confises package and channel
rm -rf uvcdat
python ./prep_for_build.py
conda build $PKG_NAME -c conda-forge -c cdat -c uvcdat --python=27
conda build $PKG_NAME -c cdat/label/nightly -c conda-forge -c cdat -c uvcdat --python=3.6
anaconda -t $CONDA_UPLOAD_TOKEN upload -u $USER -l nightly $CONDA_BLD_PATH/$OS/$PKG_NAME-$VERSION.`date +%Y*`0.tar.bz2 --force
