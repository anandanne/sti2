#
# Copyright (c) 2021, NVIDIA CORPORATION. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import os
import ctypes
import numpy as np
from cuda import cudart  # 使用 cuda runtime API
import tensorrt as trt
import onnx
import onnx_graphsurgeon as gs
import numpy as np

soFilePath      = './so/plugins/libPostEmbeddingPlugin.so'
nBS             = 4
nEmbedding      = 20
epsilon         = 1e-5
npDataType      = np.float32
np.random.seed(97)
global_emb_0     = npDataType(np.random.randn(11, nEmbedding))
global_emb_1     = npDataType(np.random.randn(13, nEmbedding))
global_emb_2     = npDataType(np.random.randn(11, nEmbedding))
global_emb_3     = npDataType(np.random.randn(1432, nEmbedding))
global_emb_4     = npDataType(np.random.randn(11, nEmbedding))
global_emb_5     = npDataType(np.random.randn(11, nEmbedding))
global_emb_6     = npDataType(np.random.randn(11, nEmbedding))
global_emb_7     = npDataType(np.random.randn(11, nEmbedding))

globalBeta     = npDataType(np.random.randn(nEmbedding))

def check(a, b, weak = False):
    if weak:
        return np.all( np.abs(a - b) < epsilon)
    else:
        return np.all( a == b )

def cpu_kernel(bufferH):
        
    _x_0 = np.int32(bufferH[0]).reshape(nBS)
    _x_1 = np.int32(bufferH[1]).reshape(nBS)
    _x_2 = np.int32(bufferH[2]).reshape(nBS)
    _x_3 = np.int32(bufferH[3]).reshape(nBS)
    _x_4 = np.int32(bufferH[4]).reshape(nBS)
    _x_5 = np.int32(bufferH[5]).reshape(nBS)
    _x_6 = np.int32(bufferH[6]).reshape(nBS)
    _x_7 = np.int32(bufferH[7]).reshape(nBS)
    
    _emb_0 = global_emb_0[_x_0,:]
    _emb_1 = global_emb_1[_x_1,:]
    _emb_2 = global_emb_2[_x_2,:]
    _emb_3 = global_emb_3[_x_3,:]
    _emb_4 = global_emb_4[_x_4,:]
    _emb_5 = global_emb_5[_x_5,:]
    _emb_6 = global_emb_6[_x_6,:]
    _emb_7 = global_emb_7[_x_7,:]
    rst = np.concatenate([_emb_0, _emb_1, _emb_2,_emb_3,_emb_4,_emb_5,_emb_6,_emb_7], axis=1)

    return rst

def getPostEmbeddingOnnx():
    onnx_file = "temp.onnx"
    shape = ('B', 1, 1)
    
    x_0 = gs.Variable(name="x_0", dtype=np.float32, shape=shape)
    x_1 = gs.Variable(name="x_1", dtype=np.float32, shape=shape)
    x_2 = gs.Variable(name="x_2", dtype=np.float32, shape=shape)
    x_3 = gs.Variable(name="x_3", dtype=np.float32, shape=shape)
    x_4 = gs.Variable(name="x_4", dtype=np.float32, shape=shape)
    x_5 = gs.Variable(name="x_5", dtype=np.float32, shape=shape)
    x_6 = gs.Variable(name="x_6", dtype=np.float32, shape=shape)
    x_7 = gs.Variable(name="x_7", dtype=np.float32, shape=shape)

    emb_0 = gs.Constant(name="emb_0", values=global_emb_0)
    emb_1 = gs.Constant(name="emb_1", values=global_emb_1)
    emb_2 = gs.Constant(name="emb_2", values=global_emb_2)
    emb_3 = gs.Constant(name="emb_3", values=global_emb_3)
    emb_4 = gs.Constant(name="emb_4", values=global_emb_4)
    emb_5 = gs.Constant(name="emb_5", values=global_emb_5)
    emb_6 = gs.Constant(name="emb_6", values=global_emb_6)
    emb_7 = gs.Constant(name="emb_7", values=global_emb_7)

    y = gs.Variable(name="y", dtype=npDataType, shape=('B', 8 * nEmbedding))
    embedding = gs.Node(op="PostEmbedding", 
                        name="PostEmbedding_1", 
                        inputs=[x_0, x_1, x_2, x_3, x_4, x_5, x_6, x_7, # TODO: Fused to a large input
                                emb_0, emb_1, emb_2, emb_3, emb_4, emb_5, emb_6, emb_7], 
                        outputs=[y])
    graph = gs.Graph(nodes=[embedding], inputs=[x_0, x_1, x_2, x_3, x_4, x_5, x_6, x_7,
                                                emb_0, emb_1, emb_2, emb_3, emb_4, emb_5, emb_6, emb_7], outputs=[y])
    onnx.save(gs.export_onnx(graph), onnx_file)
    return onnx_file

def run():
    logger = trt.Logger(trt.Logger.VERBOSE)
    trt.init_libnvinfer_plugins(logger, '')
    ctypes.cdll.LoadLibrary(soFilePath)

    builder         = trt.Builder(logger)
    network         = builder.create_network(1 << int(trt.NetworkDefinitionCreationFlag.EXPLICIT_BATCH))
    config          = builder.create_builder_config()
    config.max_workspace_size = 6 << 30
    config.flags    = 1 << int(trt.BuilderFlag.FP16) if int(npDataType == np.float16) else 0
    profile = builder.create_optimization_profile()
    
    parser = trt.OnnxParser(network, logger)
    onnxFile = getPostEmbeddingOnnx()
    if not os.path.exists(onnxFile):
        print("Failed finding onnx file!")
        exit()
    print("Succeeded finding onnx file!")
    with open(onnxFile, 'rb') as model:
        if not parser.parse(model.read()):
            print("Failed parsing onnx file!")
            for error in range(parser.num_errors):
                print(parser.get_error(error))
            exit()
        print("Succeeded parsing onnx file!")
    
    inputTensor = network.get_input(0)  # x_0
    print("inputTensor.name:{}".format(inputTensor.name))
    profile.set_shape(inputTensor.name, (1, 1, 1), (4, 1, 1), (10, 1, 1))     

    inputTensor = network.get_input(1)  # x_1
    print("inputTensor.name:{}".format(inputTensor.name))
    profile.set_shape(inputTensor.name, (1, 1, 1), (4, 1, 1), (10, 1, 1))

    inputTensor = network.get_input(2)  # x_2
    print("inputTensor.name:{}".format(inputTensor.name))
    profile.set_shape(inputTensor.name, (1, 1, 1), (4, 1, 1), (10, 1, 1))

    inputTensor = network.get_input(3)  # x_3
    print("inputTensor.name:{}".format(inputTensor.name))
    profile.set_shape(inputTensor.name, (1, 1, 1), (4, 1, 1), (10, 1, 1))

    inputTensor = network.get_input(4)  # x_4
    print("inputTensor.name:{}".format(inputTensor.name))
    profile.set_shape(inputTensor.name, (1, 1, 1), (4, 1, 1), (10, 1, 1))

    inputTensor = network.get_input(5)  # x_5
    print("inputTensor.name:{}".format(inputTensor.name))
    profile.set_shape(inputTensor.name, (1, 1, 1), (4, 1, 1), (10, 1, 1))

    inputTensor = network.get_input(6)  # x_6
    print("inputTensor.name:{}".format(inputTensor.name))
    profile.set_shape(inputTensor.name, (1, 1, 1), (4, 1, 1), (10, 1, 1))

    inputTensor = network.get_input(7)  # x_7
    print("inputTensor.name:{}".format(inputTensor.name))
    profile.set_shape(inputTensor.name, (1, 1, 1), (4, 1, 1), (10, 1, 1))    

    config.add_optimization_profile(profile)

    engineString = builder.build_serialized_network(network, config)
    engine = trt.Runtime(logger).deserialize_cuda_engine(engineString)

    context = engine.create_execution_context()
    context.set_binding_shape(0,[nBS,1,1])
    context.set_binding_shape(1,[nBS,1,1])
    context.set_binding_shape(2,[nBS,1,1])
    context.set_binding_shape(3,[nBS,1,1])
    context.set_binding_shape(4,[nBS,1,1])
    context.set_binding_shape(5,[nBS,1,1])
    context.set_binding_shape(6,[nBS,1,1])
    context.set_binding_shape(7,[nBS,1,1])
    print("Binding all? %s"%(["No","Yes"][int(context.all_binding_shapes_specified)]))
    
    nInput = np.sum([ engine.binding_is_input(i) for i in range(engine.num_bindings) ])
    nOutput = engine.num_bindings - nInput
    for i in range(engine.num_bindings):
        print("input ->" if engine.binding_is_input(i) else "output->",engine.get_binding_dtype(i),engine.get_binding_shape(i),context.get_binding_shape(i))

    bufferH = []
    for i in range(nInput):
        bufferH.append( np.array(np.random.randint(0, 10, [nBS, 1, 1]), dtype=np.float32))

    bufferH.append(np.empty(context.get_binding_shape(8),dtype=trt.nptype(engine.get_binding_dtype(8))))

    bufferD = []
    for i in range(engine.num_bindings):
        bufferD.append(cudart.cudaMalloc(bufferH[i].nbytes)[1])

    for i in range(nInput):
        cudart.cudaMemcpy(bufferD[i], bufferH[i].ctypes.data, bufferH[i].nbytes, cudart.cudaMemcpyKind.cudaMemcpyHostToDevice)

    context.execute_v2(bufferD)

    for i in range(nInput, nInput + nOutput):
        cudart.cudaMemcpy(bufferH[i].ctypes.data, bufferD[i], bufferH[i].nbytes, cudart.cudaMemcpyKind.cudaMemcpyDeviceToHost)

    print("check result:")
    temp1 = bufferH[-1]
    temp2 = cpu_kernel(bufferH)
    print(check(temp1,temp2,True), "max diff=%f"%(np.max(np.abs(temp1 - temp2))) )
    
    for b in bufferD:
        cudart.cudaFree(b)

if __name__ == '__main__':
    np.set_printoptions(precision = 4, linewidth = 200, suppress = True)
    run()