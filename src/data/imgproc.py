from abc import ABC, abstractmethod
import numpy as np
import tensorflow as tf

class ImageProcessing(ABC):

    def __init__(self) -> None:
        super().__init__()

    @abstractmethod
    def imread(self, path):
        pass

    @abstractmethod
    def resize(self, path, size):
        pass

    def flatten(self, image):
        flatted = np.ndarray.flatten(image)
        return flatted

    def transform(self, image, transformations):
        for trans, args in transformations:
            image = getattr(self, trans)(image, **args)
        return image

def get_proc_class(module_name):
    if module_name == 'skimage':
        from .imgproc_skimage import SKImageProcessing
        return SKImageProcessing()
    elif module_name == 'tfimage':
        from .imgproc_skimage import TfImageProcessing
        return TfImageProcessing()
    else:
        raise Exception(f'Unkown module name {module_name} for image process class')

def tf_read_image(x_features, filename, label, channels=1, proc_module='tfimage',
                  transformations=[
                      ('resize', {'size': (320, 320)},
                       ('normalize', {}))
                  ]):
    image_string = tf.io.read_file(filename)
    imgproc = get_proc_class(proc_module)

    #Don't use tf.image.decode_image, or the output shape will be undefined
    image = tf.io.decode_jpeg(image_string, channels=channels)
    image = imgproc.transform(image, transformations)
    image = tf.image.grayscale_to_rgb(image)
    image = tf.reshape(image, [1, 320, 320, 3])
    x_features = tf.reshape(x_features, [1,x_features.shape[0]])
    label = tf.reshape(label, [1, label.shape[0]])
    return (x_features, image), label

