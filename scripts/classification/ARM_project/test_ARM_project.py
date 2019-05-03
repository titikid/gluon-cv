import mxnet as mx
import numpy as np
import os, time, logging, argparse, shutil

from mxnet import gluon, image, init, nd
from mxnet import autograd as ag
from mxnet.gluon import nn
from mxnet.gluon.data.vision import transforms
from gluoncv.utils import makedirs, TrainingHistory
from gluoncv.model_zoo import get_model
from datetime import datetime
from arm_network import get_arm_network

data_dir='/media/atsg/Data/datasets/SUN_ARM_project'
model='squeezenet1.0'
model='arm_network_v3.3'
best_param_dir = 'arm_network_v3.3_112_8273/2019-04-21_07.21_8273'
classes = 2
input_sz=112
batch_size=64
ctx=[mx.gpu()]
num_workers=4

test_path = os.path.join(data_dir, 'test')
resize_factor=1.5


def test(net, val_data, ctx):
    metric = mx.metric.Accuracy()
    #metric = mx.metric._BinaryClassificationMetrics()
    for i, batch in enumerate(val_data):
        data = gluon.utils.split_and_load(batch[0], ctx_list=ctx, batch_axis=0, even_split=False)
        label = gluon.utils.split_and_load(batch[1], ctx_list=ctx, batch_axis=0, even_split=False)
        outputs = [net(X) for X in data]
        metric.update(label, outputs)

    return metric.get()

def setup_logger(log_file_path):
    # set up logger
    logging.basicConfig()
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    log_dir = os.path.dirname(log_file_path)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)
    fh = logging.FileHandler(log_file_path)
    logger.addHandler(fh)
    return logger


def get_network(model):
    if('arm_network' in model):
        version=model.replace('arm_network_v','')
        network=get_arm_network(version,classes,ctx)
        #network.hybridize()
    else:
        network = get_model(model, pretrained=True)
        with network.name_scope():
            network.output = nn.Dense(classes)
            network.output.initialize(init.Xavier(), ctx=ctx)
            network.collect_params().reset_ctx(ctx)
            network.hybridize()
    return network

def test_network(model, params_path, val_path):
    finetune_net = get_network(model)
    finetune_net.load_parameters(params_path)

    transform_test = transforms.Compose([
        transforms.Resize(input_sz),
        # transforms.Resize(opts.input_sz, keep_ratio=True),
        transforms.CenterCrop(input_sz),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ])
    test_data = gluon.data.DataLoader(
        gluon.data.vision.ImageFolderDataset(val_path).transform_first(transform_test),
        batch_size=batch_size, shuffle=False, num_workers = num_workers)

    _, test_acc = test(finetune_net, test_data, ctx)
    print 'Test accuracy: '+str(test_acc)


if __name__ == "__main__":
    test_network(model,os.path.join(best_param_dir,'best.params'),test_path)
    mx.image.random_crop()
