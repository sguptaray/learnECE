# Pairwise Causality Guided Transformers for Event Sequences

## Main Folder

This folder contains six Python scripts (Two for each model - PAIN/TES/PC_TES), three Python notebooks (Show how to run the models from Google Colab as a whole and as subprocesses), five subfolders and a markdown readme file.

### Subfolders
1. data

The data folder contains three Python notebooks used to obtain, explore, analize and preprocess the data to the right format. This folder also holds the train,dev,and test pickle files used to run the models.

2. preprocess

The preprocess folder contains a Python script to load the data in the format of event streams.

3. prior

This folder contains a pickle file of the prior distribution that is used to run the PAIN model.

4 transformer

This folder contains eight Python scripts that define the transformer architectures used on the PAIN, TES, and PC_TES models.

5. results

This folder holds three CSV files containing the results from training the models

## Instructions to run the models

In order to run the models, simply run the python scripts with the necessary flags.

###Running on Google Colab:

Examples:

`PAIN`

!python PAIN_Main_MAVEN_ERE.py -data data/MAVEN_ERE/ -prior prior/MAVEN_ERE/sparse/ -epoch 1 -batch_size 16 -d_model 512 -d_inner 256 -d_k 256 -d_v 256 -n_head 4 -n_layers 4 -dropout 0.1 -lr 1e-4 -num_samples 1 - event_interest 7 -threshold 0.4
     

`TES`

!python TES_Main_MAVEN_ERE.py -data data/MAVEN_ERE/ -epoch 5 -batch_size 32 -d_model 512 -d_inner 256 -d_k 256 -d_v 256 -n_head 4 -n_layers 4 -dropout 0.1 -lr 1e-4 -event_interest 7


`PC_TES`

!python PC_TES_Main_MAVEN_ERE.py -data data/MAVEN_ERE/ -epoch 3 -batch_size 32 -d_model 512 -d_inner 256 -d_k 256 -d_v 256 -n_head 4 -n_layers 4 -dropout 0.1 -lr 1e-4 -type_z 5 -type_y 8 -sle 1 -excites 1 -alpha 0.001

