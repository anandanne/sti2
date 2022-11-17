import onnx
import onnx_graphsurgeon as gs
from onnx import shape_inference
import numpy as np
import argparse

def get_args():
    parser = argparse.ArgumentParser('Export ERNIE TensorRT', add_help=False)
    parser.add_argument('--ln', action='store_true', default=False, help='Replace ops with LayernormPlugin or not')
    parser.add_argument('--slreshape', action='store_true', default=False, help='Replace ops with SliceReshapePlugin or not')
    parser.add_argument('--debug', '-D', action='store_true', default=False, help='Enable debug mode')
    args = parser.parse_args()
    return args

args = get_args()
ENABLE_LAYERNORM_PLUGIN = args.ln
ENABLE_SLICERESHAPE_PLUGIN = args.slreshape
DEBUG = args.debug

layernorm_count = 0
def replace_with_layernorm(nodes_dict, mean_node):
    global layernorm_count
    node_id = int(mean_node.name.split(".")[-1])
    if not (('p2o.Sub.{}'.format(node_id//2) in nodes_dict)  
    and ('p2o.Pow.{}'.format(node_id//2) in nodes_dict) 
    and ('p2o.Div.{}'.format(node_id//2) in nodes_dict)  
    and ('p2o.Sqrt.{}'.format(node_id//2) in nodes_dict)):
        return None

    sub_node = nodes_dict['p2o.Sub.{}'.format(node_id//2)]
    div_node = nodes_dict['p2o.Div.{}'.format(node_id//2)]
    mul_node = div_node.outputs[0].outputs[0]
    add_node = mul_node.outputs[0].outputs[0]

    gamma = mul_node.inputs[1]
    beta = add_node.inputs[1]

    
    name = 'LayerNorm.{}'.format(node_id)
    layernorm = gs.Node(op="LayerNorm", 
                        name=name, 
                        inputs=[mean_node.inputs[0],gamma,beta], 
                        outputs=[add_node.outputs[0]], 
                        attrs={"epsilon": 1e-5})
    mean_node.inputs.clear()
    sub_node.inputs.clear()
    add_node.outputs.clear()
    layernorm_count =layernorm_count + 1
    return layernorm

slice_reshape_count=0
def replace_with_slice_reshape(nodes_dict, shape_node):
    global slice_reshape_count
    node_id = int(shape_node.name.split(".")[-1])
    if not (('p2o.Slice.{}'.format(node_id//2) in nodes_dict)):
        return None

    slice_node = shape_node.outputs[0].outputs[0]

    # slice_node = nodes_dict['p2o.Slice.{}'.format(node_id//2)]
    # slice2_node = nodes_dict['p2o.Slice.{}'.format(node_id//2 + 1)]
    # shape2_node = slice2_node.inputs[0].inputs[0]
    concat_node = slice_node.outputs[0].outputs[0]
    reshape_node = concat_node.outputs[0].outputs[0]
    flatten_node = reshape_node.inputs[0].inputs[0].inputs[0].inputs[0]
    add_node = reshape_node.outputs[0].outputs[0]
    name = 'SliceReshape.{}'.format(node_id)
    slicereshape = gs.Node(op="SliceReshape", 
                        name=name, 
                        inputs=[shape_node.inputs[0],concat_node.inputs[1], flatten_node.inputs[0]], 
                        outputs=[add_node.outputs[0]], 
                        attrs={"epsilon": 1e-6})
    shape_node.inputs.clear()
    concat_node.inputs.clear()
    flatten_node.inputs.clear()
    add_node.outputs.clear()
    slice_reshape_count = slice_reshape_count + 1
    return slicereshape
    

src_onnx_path = './model/model.onnx'
dst_onnx_path = './model/modified_model.onnx'

print("Load onnx model from {}".format(src_onnx_path))
graph = gs.import_onnx(onnx.load(src_onnx_path))
print("Nodes:{}".format(len(graph.nodes)))
graph.fold_constants().cleanup()
nodes = graph.nodes

nodes_dict = {}
for node in nodes:
    name = node.name
    nodes_dict.update({name: node})

if ENABLE_LAYERNORM_PLUGIN:
    print("Fuse ops into LayerNorm")
    for op_name in nodes_dict:
        if 'ReduceMean' not in op_name:
            continue
        layernorm = replace_with_layernorm(nodes_dict, nodes_dict[op_name])
        if layernorm:
            nodes.append(layernorm)
    dst_onnx_path =  dst_onnx_path.replace(".onnx", "_ln.onnx")

if ENABLE_SLICERESHAPE_PLUGIN:
    print("Fuse ops into slicereshape")
    for op_name in nodes_dict:
        if 'Shape' not in op_name:
            continue
        slicereshape = replace_with_slice_reshape(nodes_dict, nodes_dict[op_name])
        if slicereshape:
            nodes.append(slicereshape)
    dst_onnx_path =  dst_onnx_path.replace(".onnx", "_slreshape.onnx")


if DEBUG:
    graph.cleanup().toposort()
    dst_onnx_path = './model/debug.onnx'
    # graph.toposort()
else:
    graph.cleanup().toposort()

print("Nodes:{}".format(len(graph.nodes)))
onnx.save(gs.export_onnx(graph), dst_onnx_path)
onnx.save(onnx.shape_inference.infer_shapes(onnx.load(dst_onnx_path)), dst_onnx_path)
print("Save modified onnx model to {}".format(dst_onnx_path))
print("layernorm_count:"+str(layernorm_count))
print("slice_reshape_count:"+str(slice_reshape_count))