#pragma once
#include <NvInfer.h>
#include <cub/cub.cuh>
#include <cuda_fp16.h>
#include "common.cuh"
#include <string>
#include <vector>

#define CEIL_DIVIDE(X, Y) (((X) + (Y)-1) / (Y))
#define CEIL_TO(X, Y)     (((X) + (Y)-1) / (Y) * (Y))

#if NDEBUG
    #define WHERE_AM_I()                                 \
        do                                               \
        {                                                \
            printf("[%s]: this=->%p\n", __func__, this); \
        } while (0);
#else
    #define WHERE_AM_I()
#endif // #ifndef NDEBUG

namespace nvinfer1
{
static const char *PLUGIN_NAME {"LayerNorm"};
static const char *PLUGIN_VERSION {"1"};

class AddLayerNormPlugin : public IPluginV2DynamicExt
{
private:
    std::string name_;
    std::string namespace_;
    float       epsilon_;

public:
    AddLayerNormPlugin(const std::string &name, float epsilon):
        name_(name), epsilon_(epsilon)
    {
        WHERE_AM_I();
    }

    AddLayerNormPlugin(const std::string &name, const void *data, size_t length):
        name_(name)
    {
        WHERE_AM_I();
        memcpy(&epsilon_, data, sizeof(epsilon_));
    }

    AddLayerNormPlugin() = delete;

    ~AddLayerNormPlugin()
    {
        WHERE_AM_I();
    }

    size_t getSerializationSize() const noexcept override
    {
        WHERE_AM_I();
        return sizeof(epsilon_);
    }

    void serialize(void *buffer) const noexcept override
    {
        WHERE_AM_I();
        memcpy(buffer, &epsilon_, sizeof(epsilon_));
    }

    IPluginV2DynamicExt *clone() const noexcept override
    {
        WHERE_AM_I();
        return new AddLayerNormPlugin(name_, epsilon_);
    }

    int getNbOutputs() const noexcept override
    {
        WHERE_AM_I();
        return 1;
    }

    DimsExprs getOutputDimensions(int32_t outputIndex, const DimsExprs *inputs, int32_t nbInputs, IExprBuilder &exprBuilder) noexcept override
    {
        WHERE_AM_I();
        return inputs[0];
    }

    bool supportsFormatCombination(int32_t pos, const PluginTensorDesc *inOut, int32_t nbInputs, int32_t nbOutputs) noexcept override
    {
        WHERE_AM_I();       
        if (inOut[pos].format != TensorFormat::kLINEAR)
        {
            return false;
        }

        bool res = false;
        switch (pos)
        {
        case 0: // input0
            res = (inOut[0].type == DataType::kFLOAT);
            // res = (inOut[0].type == DataType::kFLOAT) || (inOut[0].type == DataType::kHALF);
            break;
        case 1: // input1
            res = (inOut[1].type == DataType::kFLOAT);
            // res = (inOut[1].type == DataType::kFLOAT) || (inOut[1].type == DataType::kHALF);
            break;
        case 2: // input2
            res = (inOut[2].type == DataType::kFLOAT);
            // res = (inOut[2].type == DataType::kFLOAT) || (inOut[2].type == DataType::kHALF);
            break;
        case 3: // input3
            res = (inOut[3].type == DataType::kFLOAT);
            // res = (inOut[2].type == DataType::kFLOAT) || (inOut[2].type == DataType::kHALF);
            break;
        case 4: // input4
            res = (inOut[4].type == DataType::kFLOAT);
            // res = (inOut[2].type == DataType::kFLOAT) || (inOut[2].type == DataType::kHALF);
            break;                        
        case 5: // output0
            res = inOut[pos].type == inOut[0].type;
            break;
        default: // should NOT be here
            break;
        }
        return res;
    }

    DataType getOutputDataType(int outputIndex, const DataType *inputTypes, int nbInputs) const noexcept override
    {
        WHERE_AM_I();
        return inputTypes[0];
    }

    void configurePlugin(const DynamicPluginTensorDesc *in, int32_t nbInputs, const DynamicPluginTensorDesc *out, int32_t nbOutputs) noexcept override
    {
        WHERE_AM_I();
    }

    size_t getWorkspaceSize(const PluginTensorDesc *inputs, int32_t nbInputs, const PluginTensorDesc *outputs, int32_t nbOutputs) const noexcept override
    {
        WHERE_AM_I();
        return 0;
    }

    void setPluginNamespace(const char *szNamespace) noexcept override
    {
        WHERE_AM_I();
        namespace_ = szNamespace;
    }
    const char *getPluginNamespace() const noexcept override
    {
        WHERE_AM_I();
        return namespace_.c_str();
    }
    const char *getPluginType() const noexcept override
    {
        WHERE_AM_I();
        return PLUGIN_NAME;
    }
    const char *getPluginVersion() const noexcept override
    {
        WHERE_AM_I();
        return PLUGIN_VERSION;
    }
    int initialize() noexcept override
    {
        WHERE_AM_I();
        return 0;
    }
    void terminate() noexcept override
    {
        WHERE_AM_I();
        return;
    }

    void destroy() noexcept override
    {
        WHERE_AM_I();
    }

    int32_t enqueue(const PluginTensorDesc *inputDesc, const PluginTensorDesc *outputDesc, const void *const *inputs, void *const *outputs, void *workspace, cudaStream_t stream) noexcept override;
}; // class AddLayerNormPlugin

class AddLayerNormPluginCreator : public IPluginCreator
{
private:
    static PluginFieldCollection    fc_;
    static std::vector<PluginField> attr_;
    std::string                     namespace_;

public:
    AddLayerNormPluginCreator()
    {
        WHERE_AM_I();
        attr_.emplace_back(PluginField("epsilon", nullptr, PluginFieldType::kFLOAT32, 1));
        fc_.nbFields = attr_.size();
        fc_.fields   = attr_.data();
    }

    ~AddLayerNormPluginCreator() {}

    IPluginV2 *createPlugin(const char *name, const PluginFieldCollection *fc) noexcept override
    {
        WHERE_AM_I();
        float epsilon {1.0e-5f};
        for (int i = 0; i < fc->nbFields; i++)
        {
            std::string field_name(fc->fields[i].name);
            if (field_name.compare("epsilon") == 0)
            {
                epsilon = *static_cast<const float *>(fc->fields[i].data);
            }
        }
        return new AddLayerNormPlugin(name, epsilon);
    }

    IPluginV2 *deserializePlugin(const char *name, const void *serialData, size_t serialLength) noexcept override
    {
        WHERE_AM_I();
        return new AddLayerNormPlugin(name, serialData, serialLength);
    }

    void setPluginNamespace(const char *szNamespace) noexcept override
    {
        namespace_ = szNamespace;
    }

    const char *getPluginNamespace() const noexcept override
    {
        return namespace_.c_str();
    }

    const char *getPluginName() const noexcept override
    {
        return PLUGIN_NAME;
    }

    const char *getPluginVersion() const noexcept override
    {
        return PLUGIN_VERSION;
    }

    const PluginFieldCollection *getFieldNames() noexcept override
    {
        return &fc_;
    }
}; // class AddLayerNormPluginCreator
REGISTER_TENSORRT_PLUGIN(AddLayerNormPluginCreator);
} // namespace nvinfer1