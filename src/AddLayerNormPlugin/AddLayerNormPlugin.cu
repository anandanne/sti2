#include "AddLayerNormPlugin.h"

using namespace nvinfer1;

PluginFieldCollection    AddLayerNormPluginCreator::fc_ {};
std::vector<PluginField> AddLayerNormPluginCreator::attr_;

template <typename T, int TPB, int VPT>
__global__ void ln_vec(
    const int ld, const T* input1, const T* input2, const T* input3, T* output, const T* beta, const T* gamma)
{
    const int idx = ld * blockIdx.x + threadIdx.x * VPT;
    // 4 * 1024 * 4 * 2 Bytes = 16KB per block
    T in_local[VPT];
    T in_local1[VPT];
    T in_local2[VPT];
    T in_local3[VPT];


    T beta_local[VPT];
    T gamma_local[VPT];
    copy<sizeof(T) * VPT>(&input1[idx], in_local1);
    copy<sizeof(T) * VPT>(&input2[idx], in_local2);
    copy<sizeof(T) * VPT>(&input3[idx], in_local3);

    
    T local = 0.f;
    T local2 = 0.f;

    const T rld = T(1) / T(ld);
    
#pragma unroll
    for (int it = 0; it < VPT; it++)
    {
        in_local[it] = in_local2[it] + in_local3[it];;
    }
 
#pragma unroll
    for (int it = 0; it < VPT; it++)
    {
        in_local[it] = in_local[it] + in_local1[it];;
    }

#pragma unroll
    for (int it = 0; it < VPT; it++)
    {
        const T tmp = rld * in_local[it];
        local += tmp;
        local2 += tmp * in_local[it];
    }

    copy<sizeof(T) * VPT>(&gamma[threadIdx.x * VPT], gamma_local);
    copy<sizeof(T) * VPT>(&beta[threadIdx.x * VPT], beta_local);

    using BlockReduce = cub::BlockReduce<kvp<T>, TPB>;
    __shared__ typename BlockReduce::TempStorage temp_storage;
    __shared__ T mu;     // mean
    __shared__ T rsigma; // 1 / std.dev.

    const auto sumKV = BlockReduce(temp_storage).Reduce(kvp<T>(local, local2), cub::Sum());

    if (threadIdx.x == 0)
    {
        mu = sumKV.key;
        rsigma = rsqrt(sumKV.value - mu * mu );
    }
    __syncthreads();
    ///*
#pragma unroll
    for (int it = 0; it < VPT; it++)
    {
        in_local[it] = gamma_local[it] * (in_local[it] - mu) * rsigma + beta_local[it];
    }
    /* */

    copy<sizeof(T) * VPT>(in_local, &output[idx]);
}

int32_t AddLayerNormPlugin::enqueue(const PluginTensorDesc *inputDesc, const PluginTensorDesc *outputDesc, const void *const *inputs, void *const *outputs, void *workspace, cudaStream_t stream) noexcept
{
    WHERE_AM_I();
    int nBlock = 1;
    for(int i = 0; i < inputDesc[0].dims.nbDims - 1; ++i)
        nBlock *= inputDesc[0].dims.d[i];
    if (inputDesc[0].type == DataType::kFLOAT)
    {
        constexpr int VPT = 16 / sizeof(float);
        constexpr int TPB = 768 / VPT;
        ln_vec<float, TPB, VPT><<<nBlock, TPB, 0, stream>>>(768, (float *)inputs[0], (float *)inputs[1], (float *)inputs[2], (float *)outputs[0], (float *)inputs[4], (float *)inputs[3]);
    }
    else if (inputDesc[0].type == DataType::kHALF)
    {
        constexpr int VPT = 1;
        constexpr int TPB = 768 / VPT;
        ln_vec<half, TPB, VPT><<<nBlock, TPB, 0, stream>>>(768, (half *)inputs[0], (half *)inputs[1], (half *)inputs[2], (half *)outputs[0], (half *)inputs[4], (half *)inputs[3]);
    }
    return 0;
}

REGISTER_TENSORRT_PLUGIN(AddLayerNormPluginCreator);