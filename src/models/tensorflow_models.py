import tensorflow as tf
from tensorflow import keras
from keras.models import Model
from keras.layers import Activation, Add, \
    AveragePooling2D, BatchNormalization, Conv2D, \
    Dense, Dropout, Flatten, GlobalMaxPooling2D, Input, \
    Lambda, MaxPooling2D, MaxPool2D, ZeroPadding2D
from keras.initializers import glorot_uniform

# define function to create identity blocks
def identity_block(X, f, filters, stage, block):
    conv_name_base = 'res' + str(stage) + block + '_branch'
    bn_name_base = 'bn' + str(stage) + block + '_branch'
    F1, F2, F3 = filters

    X_shortcut = X

    X = Conv2D(filters=F1, kernel_size=(1, 1), strides=(1, 1), padding='valid', name=conv_name_base + '2a',
               kernel_initializer=glorot_uniform(seed=0))(X)
    X = BatchNormalization(axis=3, name=bn_name_base + '2a')(X)
    X = Activation('relu')(X)

    X = Conv2D(filters=F2, kernel_size=(f, f), strides=(1, 1), padding='same', name=conv_name_base + '2b',
               kernel_initializer=glorot_uniform(seed=0))(X)
    X = BatchNormalization(axis=3, name=bn_name_base + '2b')(X)
    X = Activation('relu')(X)

    X = Conv2D(filters=F3, kernel_size=(1, 1), strides=(1, 1), padding='valid', name=conv_name_base + '2c',
               kernel_initializer=glorot_uniform(seed=0))(X)
    X = BatchNormalization(axis=3, name=bn_name_base + '2c')(X)

    X = Add()([X, X_shortcut])  # SKIP Connection
    X = Activation('relu')(X)

    return X


# define function to create convolutional blocks
def convolutional_block(X, f, filters, stage, block, s=2):
    conv_name_base = 'res' + str(stage) + block + '_branch'
    bn_name_base = 'bn' + str(stage) + block + '_branch'

    F1, F2, F3 = filters

    X_shortcut = X

    X = Conv2D(filters=F1, kernel_size=(1, 1), strides=(s, s), padding='valid', name=conv_name_base + '2a',
               kernel_initializer=glorot_uniform(seed=0))(X)
    X = BatchNormalization(axis=3, name=bn_name_base + '2a')(X)
    X = Activation('relu')(X)

    X = Conv2D(filters=F2, kernel_size=(f, f), strides=(1, 1), padding='same', name=conv_name_base + '2b',
               kernel_initializer=glorot_uniform(seed=0))(X)
    X = BatchNormalization(axis=3, name=bn_name_base + '2b')(X)
    X = Activation('relu')(X)

    X = Conv2D(filters=F3, kernel_size=(1, 1), strides=(1, 1), padding='valid', name=conv_name_base + '2c',
               kernel_initializer=glorot_uniform(seed=0))(X)
    X = BatchNormalization(axis=3, name=bn_name_base + '2c')(X)

    X_shortcut = Conv2D(filters=F3, kernel_size=(1, 1), strides=(s, s), padding='valid', name=conv_name_base + '1',
                        kernel_initializer=glorot_uniform(seed=0))(X_shortcut)
    X_shortcut = BatchNormalization(axis=3, name=bn_name_base + '1')(X_shortcut)

    X = Add()([X, X_shortcut])
    X = Activation('relu')(X)

    return X

def Resnet50_Arnold(output_size, not_transfer=False, feature_shape=(4,), image_shape=(320,320, 1)):

    inputs_feature = Input(shape=feature_shape)
    inputs_image = Input(shape=image_shape)

    # define resnet layers
    x = ZeroPadding2D((3, 3))(inputs_image)

    x = Conv2D(64, (7, 7), strides=(2, 2), name='conv1', kernel_initializer=glorot_uniform(seed=0))(x)
    x = BatchNormalization(axis=3, name='bn_conv1')(x)
    x = Activation('relu')(x)
    x = MaxPooling2D((3, 3), strides=(2, 2))(x)

    x = convolutional_block(x, f=3, filters=[64, 64, 256], stage=2, block='a', s=1)
    x = identity_block(x, 3, [64, 64, 256], stage=2, block='b')
    x = identity_block(x, 3, [64, 64, 256], stage=2, block='c')

    x = convolutional_block(x, f=3, filters=[128, 128, 512], stage=3, block='a', s=2)
    x = identity_block(x, 3, [128, 128, 512], stage=3, block='b')
    x = identity_block(x, 3, [128, 128, 512], stage=3, block='c')
    x = identity_block(x, 3, [128, 128, 512], stage=3, block='d')

    x = convolutional_block(x, f=3, filters=[256, 256, 1024], stage=4, block='a', s=2)
    x = identity_block(x, 3, [256, 256, 1024], stage=4, block='b')
    x = identity_block(x, 3, [256, 256, 1024], stage=4, block='c')
    x = identity_block(x, 3, [256, 256, 1024], stage=4, block='d')
    x = identity_block(x, 3, [256, 256, 1024], stage=4, block='e')
    x = identity_block(x, 3, [256, 256, 1024], stage=4, block='f')

    x = x = convolutional_block(x, f=3, filters=[512, 512, 2048], stage=5, block='a', s=2)
    x = identity_block(x, 3, [512, 512, 2048], stage=5, block='b')
    x = identity_block(x, 3, [512, 512, 2048], stage=5, block='c')

    x = AveragePooling2D(pool_size=(2, 2), padding='same')(x)

    # create classification layers, first flatten the convolution output
    x = Flatten()(x)

    # create hidden layers for classification
    x = Dense(128)(x)
    x = Activation("relu")(x)
    x = BatchNormalization()(x)
    x = Dropout(0.5)(x)

    # create output layer
    x = Dense(output_size)(x)
    x = Activation("sigmoid", name='predicted_observations')(
        x)  # sigmoid and not softmax because we are doing multi-label

    model = Model(inputs=[inputs_feature, inputs_image],
                  outputs=x,
                  name='ResNet50')

    return model

def MobileNetv2_Songhan(output_size, not_transfer=False, feature_shape=(4,), image_shape=(320,320, 3)):

    cnn_base = tf.keras.applications.mobilenet_v2.MobileNetV2(include_top=not_transfer,
                                                              weights='imagenet')
    cnn_base.trainable = not_transfer

    inputs_feature = tf.keras.Input(shape=feature_shape)
    inputs_image = tf.keras.Input(shape=image_shape)
    x = cnn_base(inputs_image, training=False)
    x = tf.keras.layers.GlobalAveragePooling2D()(x)
    x = tf.keras.layers.Concatenate()([x, inputs_feature])
    x = tf.keras.layers.Activation('relu')(x)

    # create output layer
    x = tf.keras.layers.Dense(output_size)(x)
    x = tf.keras.layers.Activation("sigmoid", name='predicted_observations')(
        x)

    # create model class
    model = tf.keras.Model(inputs=[inputs_feature, inputs_image], outputs=x)

    return model

cnn_models = {
    "MobileNetv2_Songhan": MobileNetv2_Songhan,
    "Resnet50_Arnold": Resnet50_Arnold
}