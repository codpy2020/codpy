from codpy.core import set_verbose
from codpy.multiscale_kernel import *
from codpy.data_processing import hot_encoder
import pandas as pd

os.environ["OPENBLAS_NUM_THREADS"] = "64"
os.environ["OMP_NUM_THREADS"] = "32"

class MaximalElement(Kernel):
    def __init__(self,x, N, **kwargs):
        super().__init__(x=x,**kwargs)
        self.indices = self.select(x,N,**kwargs,all=True)
        self.cluster_centers_ = self.get_x()[self.indices]
        self.labels_ = self(self.get_x())
    def __call__(self,z, **kwargs):
        labels = core.op.Dnm(z, self.cluster_centers_).argmin(axis=1)
        return labels

def get_MNIST_data():
    import tensorflow as tf
    (x, fx), (z, fz) = tf.keras.datasets.mnist.load_data()
    x,z = x / 255.0, z / 255.0
    x,z,fx,fz = x.reshape(len(x),-1), z.reshape(len(z),-1),fx.reshape(len(fx),-1), fz.reshape(len(fz),-1)
    fx,fz = hot_encoder(pd.DataFrame(data=fx),cat_cols_include = [0],sort_columns=True),hot_encoder(pd.DataFrame(data=fz),cat_cols_include = [0],sort_columns=True)
    return (x, fx.values, z, fz.values)

def show_confusion_matrix(z,fz,predictor=None):

    from sklearn.metrics import confusion_matrix
    import numpy as np
    if predictor is None: f_z=fz
    else: f_z = predictor(z)
    fz,f_z = fz.argmax(axis=-1),f_z.argmax(axis=-1)
    out = confusion_matrix(fz, f_z) 
    print("confusion matrix:",out)
    print("score MNIST:",np.trace(out)/np.sum(out))
    pass

if __name__ == "__main__":
    set_verbose(True)
    x,fx,z,fz = get_MNIST_data()
    predictor = MultiScaleKernel(x=x,fx=fx,N=20,method=MaximalElement)
    show_confusion_matrix(z,fz,predictor)
    show_confusion_matrix(x,fx,predictor) #reproductibility test : should return 100% precision
    pass

