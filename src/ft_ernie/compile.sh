CUR_DIR=`pwd`
rm -rf build
mkdir -p build
cd ${CUR_DIR}/build
cmake \
	-DCMAKE_BUILD_TYPE=Release \
	-DCMAKE_VERBOSE_MAKEFILE=OFF \
	-DCMAKE_INSTALL_PREFIX=${CUR_DIR}/install \
	-DBUILD_TF=OFF \
	-DBUILD_PYT=OFF \
	-DBUILD_TRT=ON \
	-DBUILD_MULTI_GPU=OFF \
	-DUSE_NVTX=OFF \
	..


make -j$(nproc) 

cp ${CUR_DIR}/build/lib/libErniePlugin.so ${CUR_DIR}/../../so/plugins/libErniePlugin.so
