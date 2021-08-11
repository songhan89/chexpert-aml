# -*- coding: utf-8 -*-
import os
import sys
from pandas.core.indexes import base

sys.path.append('..')
import argparse
import datetime as dt
import pickle
import yaml
import tensorflow as tf
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import logging
from datetime import datetime
from src.data.imgproc import tf_read_image
from src.data.dataset import ImageDataset
from src.models.sklearn_models import models
from src.models.tensorflow_models import cnn_models
from sklearn.preprocessing import MinMaxScaler
from sklearn.multioutput import MultiOutputClassifier
from sklearn.metrics import roc_auc_score, roc_curve, f1_score, accuracy_score
from tensorflow.keras import mixed_precision
mixed_precision.set_global_policy('mixed_float16')

logger = logging.getLogger(__file__)

#initialise parser
parser = argparse.ArgumentParser()

#set arguments for number of models per ensemble
parser.add_argument("--num_models", type=int, default=3, choices=[3,4,5,6],
                    help="Number of models in each ensemble")

#collect arguments
args = parser.parse_args()

#set some global parameters
return_labels = ['No Finding', 
                 'Atelectasis', 
                 'Cardiomegaly', 
                 'Consolidation', 
                 'Edema',
                 'Pleural Effusion', 
                 'Support Devices']
base_path = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
models_path = os.path.join(base_path, "models\\ensembling")
trad_models = []
test_csv_path = os.path.join(base_path, "data", "raw", "CheXpert-v1.0-small", "valid.csv")
image_path = os.path.join(base_path, "data", "raw")
batch_size = 16

#get the list of .sav files
sav_list =  os.listdir(models_path)

#load dataset for traditional
#set transformations
trad_transformations = [['crop', {'size': [320,320]}],
                        ['gaussian_blur',{}],
                        ['normalize',{}],
                        ['flatten',{}]
                        ]
#set up test dataset one for each U mapping
test_dataset= ImageDataset(label_csv_path=test_csv_path,
                           image_path_base=image_path,
                           frontal_only=True,
                           transformations=trad_transformations)

#load dataset for cnn
#set transformations
cnn_transformations = [['crop', {'size': [320,320]}],
                       ['normalize',{}]]

#set up test dataset
tfds_test = tf.data.Dataset.from_tensor_slices((test_dataset.df[test_dataset._feature_header].values,
                                                test_dataset.df['Path'].values,
                                                test_dataset.df[return_labels].values))
tfds_test_keras = tfds_test.map(lambda x, y, z: tf_read_image(x, y, z, 
                                                              cnn_model="MobileNetv2_keras",
                                                              transformations=cnn_transformations),
                                num_parallel_calls=tf.data.AUTOTUNE)
tfds_test = tfds_test.map(lambda x, y, z: tf_read_image(x, y, z, 
                                                        cnn_model="DenseNet121_new",
                                                        transformations=cnn_transformations),
                          num_parallel_calls=tf.data.AUTOTUNE)

tfds_test_keras = tfds_test.batch(batch_size)
tfds_test = tfds_test.batch(batch_size)


#prefetch
tfds_test = tfds_test.prefetch(tf.data.AUTOTUNE)

y_test_multi = []
for x, test_label in tfds_test:
    for item in test_label:
        y_test_multi.append(item.numpy())

y_test_multi = np.array(y_test_multi)

#create dictionary to store the results
y_pred_multi = {}

#create a list of models
model_list = []

trad_ml_models = ['Gaussian_U-one_500_U-one_0106_30072021.sav',
                  'Gaussian_U-zero_500_U-zero_0030_31072021.sav',
                  'RandomForest_10000_U-one_1138_31072021.sav',
                  'RandomForest_10000_U-zero_1059_31072021.sav',
                  'RondomForest_10000_Random_1212_31072021.sav']

cnn_models = ['DenseNet121_keras_5_16_Random_0506_30072021.sav',
              'DenseNet121_keras_5_16_U-one_0402_30072021.sav',
              'DenseNet121_keras_5_16_U-zero_0257_30072021.sav',
              'DenseNet121_new_5_16_Random_0232_31072021.sav',
              'DenseNet121_new_5_16_U-one_2157_30072021.sav',
              'DenseNet121_new_5_16_U-zero_0714_31072021.sav',
              'MobileNetv2_keras_5_16_U-one_0153_30072021.sav',
              'MobileNetv2_keras_5_16_U-zero_0120_30072021.sav',
              'MobileNetv2_pop1_5_16_Random_0204_31072021.sav',
              'MobileNetv2_pop1_5_16_U-one_0519_31072021.sav',
              'MobileNetv2_pop2_5_16_U-one_0830_31072021.sav',
              'ResNet152_keras_3_16_Random_0825_30072021.sav',
              'ResNet152_keras_3_16_U-one_0717_30072021.sav',
              'ResNet152_keras_3_16_U-zero_0611_30072021.sav',
              'ResNet152_new_3_16_Random_1445_30072021.sav',
              'ResNet152_new_3_16_U-one_1210_30072021.sav',
              'ResNet152_new_3_16_U-zero_0935_30072021.sav']

#loop through the .sav files
for model in sav_list:
    model_name = str.split(model,'.')[0]
    #add model to list
    model_list.append(model_name)
    
    #for trad ml
    if model in trad_ml_models:
        #load PCA
        try:
            #only this PCA is used
            pca_f_path = os.path.join(models_path, 'IncrementalPCA_FullData_200_500_U-zero_0752_30072021.sav')
            with open(pca_f_path, 'rb') as file:
                pca = pickle.load(file)
            logger.info(f'Pretrained pca {pca_f_path} .sav file loaded.')
            logger.info(f'Pretrained pca: {pca}')
        except:
            logger.error(f'Pretrained pca {pca_f_path} .sav file cannot be loaded!')
        
        #load models
        try:
            model_f_path = os.path.join(models_path, model)
            with open(model_f_path, 'rb') as file:
                model_used = pickle.load(file)
            logger.info(f'Pretrained model {model_f_path} .sav file loaded.')
            logger.info(f'Pretrained model: {model}')
        except:
            logger.error(f'Pretrained model {model_f_path} .sav file cannot be loaded!')
        
        x_features_test, x_image_test, y_test_multi = test_dataset.load(return_labels)
        x_image_test = MinMaxScaler().fit_transform(pca.transform(x_image_test))
        X_test = pd.concat([pd.DataFrame(x_features_test), pd.DataFrame(x_image_test)], axis=1)
        
        #reshape the output
        y_pred_helper = np.array(model_used.predict_proba(X_test))
        y_pred_helper = [y_pred_helper[idx, :, 1] for idx in range(len(return_labels))]
        y_pred_helper = np.array(y_pred_helper)
        y_pred_helper = np.transpose(y_pred_helper)
        
        #create new dictionary entry for the results
        y_pred_multi[model_name] = y_pred_helper

#for cnn
    elif model in cnn_models:
        try:
            cnn_pretrained_path = os.path.join(models_path, model)
            logger.info(f'Loading pretrained cnn model: {cnn_pretrained_path}')
            model_used = tf.keras.models.load_model(cnn_pretrained_path)
            logger.info(model.summary())
        except:
            logger.error(f'Unable to load pretrained cnn model: {cnn_pretrained_path} !')
        
        #create new dictionary entry for the results
        #use 3 channel if keras model
        if str.split(model_name,'_')[1] == 'keras':
            y_pred_multi[model_name] = model_used.predict(tfds_test_keras, 
                                                          verbose=1, 
                                                          use_multiprocessing=True, 
                                                          workers=8)
        else: 
            y_pred_multi[model_name] = model_used.predict(tfds_test, 
                                                          verbose=1, 
                                                          use_multiprocessing=True, 
                                                          workers=8)
        
        
#create a list of permutations
#import itertools
from itertools import permutations

#def function to generate all combinations of models
def combinations(iterable, r):
    pool = tuple(iterable)
    n = len(pool)
    for indices in permutations(range(n), r):
        if sorted(indices) == list(indices):
            yield tuple(pool[i] for i in indices)
            
#generate combinations
combinations = list(combinations(range(len(model_list)),args.num_models))

#create dictionary of combined predictions
y_pred_ensem = {}

#create list of model stats
results_ensem = []

#for loop to cycle through all combinations
for combo in combinations:
    for i in range(args.num_models):
        if i == 0:
            combined_pred = pd.DataFrame(y_pred_multi[model_name[combo[i]]])
        else:
            combined_pred = pd.concat(combined_pred,
                                      axis = 1
                                      )
    #average the predicted logits
    #create a groupby index
    group_index = list(np.ravel(np.repeat([range(return_labels)],args.num_models, axis=0)))
    combined_pred = combined_pred.groupby(group_index,
                                          axis=1).mean()
    
    #create ensemble name
    ensem_name = [model_list[combo[i]] for i in range(args.num_models)]
    
    #add predictions to predicted dictionary
    y_pred_ensem[ensem_name] = combined_pred
        
    #calculate model stats
    for idx, label in enumerate(return_labels):
        y_test = y_test_multi[:, idx]
        y_pred = combined_pred[:, idx]
        y_pred_label = np.zeros(shape=y_pred.shape)
        auc = roc_auc_score(y_true=y_test, y_score=y_pred)
        fpr, tpr, thresholds = roc_curve(y_true=y_test, y_score=y_pred)
        gmeans = np.sqrt(tpr * (1 - fpr))
        # locate the index of the largest g-mean
        ix = np.argmax(gmeans)
        # assign the prob above threshold to be label 1
        cutoff = thresholds[ix]
        y_pred_label[y_pred >= cutoff] = 1
        #calc accuracy and f1-score
        accuracy_dummy = accuracy_score(y_true=y_test, y_pred=np.ones(shape=y_pred.shape))
        accuracy = accuracy_score(y_true=y_test, y_pred=y_pred_label)
        f1 = f1_score(y_true=y_test, y_pred=y_pred_label)
        f1_dummy = f1_score(y_true=y_test, y_pred=np.ones(shape=y_pred.shape))
        
        #append results in the results list
        results_ensem.append([ensem_name,
                              label,
                              auc,
                              cutoff,
                              accuracy_dummy,
                              accuracy,
                              f1_dummy,
                              f1])
        
        #print out the results for the combinations
        logger.info(f'========================================')
        logger.info(f'{label}')
        logger.info(f'========================================')
        logger.info(f'Ensemble: {ensem_name}')
        logger.info(f'roc_auc_score: {auc}')
        logger.info(f'best threshold: {cutoff}')
        logger.info(f'accuracy: {accuracy}')
        logger.info(f'accuracy (dummy): {accuracy_dummy}')
        logger.info(f'f1-score: {f1}')
        logger.info(f'f1-score (dummy): {f1_dummy}')

#export all the results