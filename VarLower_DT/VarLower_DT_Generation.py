# -*- coding: utf-8 -*-
"""
Created on Thu Mar  5 14:42:49 2020

@author: emapr
"""

from Decision_Tree import DT
from Case import system_input
import pandas as pd
import ast
import numpy as np
import sys
import os.path

################################################## PARAMETERS TO BE MODIFIED ##################################################
###############################################################################################################################
n_bus = 9 # Number of bus of the system: Choice of the application system

#DT Hyperparameters
min_sp_split=2
min_sp_leaf=2
leaf = 223 # Max Leaves in DTs
feat=None
depth=10

#DT_d Hyperparameters (sub decision trees)
min_sp_split_d=2
min_sp_leaf_d=2
leaf_d = 223 # Max Leaves in DTs
feat_d=None
depth_d=15

# Mode: 0 for Hyperparameter tunning and 1 for running DT
mode = 1 # For general DT: First set to 0 to determine the best value for the hyperparameters, then change the hyperparameters above and set to 1
mode_d = 1 # For sub-DT: First set to 0 to determine the best value for the hyperparameters, then change the hyperparameters above and set to 1

###############################################################################################################################
###############################################################################################################################

data = system_input(0,[0]*n_bus,n_bus)
nodes = data['nodes']
load_nodes=data['load_nodes']

### General DT ###

# Prepare data

# Load data
name_DB = 'VarLower_DB_{}bus.csv'.format(n_bus)
name_AS = 'VarLower_Active_Sets_DB_{}bus.csv'.format(n_bus)

if os.path.exists(name_DB):
    with open(name_DB, mode='r') as f:
        y_train=[]
        Load=[]
        cS=[]
        reader_train = pd.read_csv(name_DB,header=0)
else: 
    sys.exit('The database in csv is not available. Please add the file {} to the current directory or create it with the script VarLower_DB_DiscoverMass.py'.format(name_DB))

# Create y array for the DT: x -> y, y being the active set associated with each data point
y_train = reader_train['Active set ID'].tolist() 
y_train=np.array(y_train)

# Create x array for the DT: x -> y, x being the data point with load and cost of the strategic generator

# Retrieve the load at each point as a list
pt = reader_train['Load'].tolist()
for p in pt:
    p_list = list(ast.literal_eval(p))
    cS.append(p_list.pop(-1))
    Load.append(p_list)

features = pd.DataFrame(data={'cS':cS})
for n in range(n_bus):
    new_col=[]
    for l in Load:
        elt = l[n]
        new_col.append(elt)
    features.insert(len(features.columns)-1, nodes[n], new_col)
# Also add the total load as a feature
features.insert(len(features.columns)-1,'total load',features.sum(axis='columns')-features['cS'])

# Only keep the nodes that have a load associated in the features
for n in nodes:
    if n not in load_nodes:
        features=features.drop(columns=n)
    
X_train=features

# Create DT
name='VarLower_DT_{}bus_cS'.format(n_bus)

if mode == 0: # Determination of the best hyperparameters
    
    # Number of sets of active constraints detected
    if os.path.exists(name_AS):
        with open(name_AS, mode='r') as f:
            read_csv = pd.read_csv(name_AS,header=0)
            AS_list = read_csv['Active set'].tolist()
            AS_tuple=[]
    else: 
        sys.exit('The list of active sets in csv is not available. Please add the file or create it with the script VarLower_DB_DiscoverMass.py')
    
    for p in AS_list:
        AS_tuple.append(ast.literal_eval(p))
    set_nb = read_csv['ID'].tolist()
    AS = {AS_tuple[k]:set_nb[k] for k in range(len(AS_tuple)) if AS_tuple[k] is not None}
    print('There are {} different sets of active constraints in the DB'.format(len(AS)))
    print('----------------------------------------')
    
    # Test of the best hyperparameters
    DT(nodes,load_nodes,n_bus,mode,leaf,feat,depth,min_sp_leaf,min_sp_split,X_train,y_train,name)
    
elif mode == 1: # Build the general DT
    n_nodes, children_left, children_right, feature, threshold = DT(nodes,load_nodes,n_bus,mode,leaf,feat,depth,min_sp_leaf,min_sp_split,X_train,y_train,name)

    # Retrieve critical values of cS
    cS_index=X_train.shape[1]-1
    cS_thsd=[]
    for i in range(n_nodes):
        if feature[i]==cS_index:
            if threshold[i] not in cS_thsd:
                cS_thsd.append(threshold[i])
    cS_thsd.sort()
            
    ### DTs per interval of cS ###
    
    dt_nb = 1
    
    if cS_thsd: # Only if critical values were identified
        
        for i in range(len(cS_thsd)):
            
            if i == 0:
                X_train_d = X_train.copy()
                y_train_d = y_train.copy()
                Index=[]
                for index, row in X_train_d.iterrows():
                    if row['cS'] > cS_thsd[0]:    
                        X_train_d.drop(index, inplace=True)
                        Index.append(index)
                y_train_d=np.delete(y_train_d,Index)
            else:
                X_train_d = X_train.copy()
                y_train_d = y_train.copy()
                Index=[]
                for index, row in X_train_d.iterrows():
                    if cS_thsd[i-1] > row['cS'] or row['cS'] >= cS_thsd[i]:
                        X_train_d.drop(index, inplace=True)
                        Index.append(index)
                y_train_d=np.delete(y_train_d,Index)
            if y_train_d.size != 0:
                X_train_d.drop('cS', axis=1, inplace=True)
                name='VarLower_DT_{}bus_sub{}'.format(n_bus,dt_nb)
                dt_nb+=1
                DT(nodes,load_nodes,n_bus,mode_d,leaf_d,feat_d,depth_d,min_sp_leaf_d,min_sp_split_d,X_train_d,y_train_d,name)
        
        # Last interval
        i+=1
        Index=[]
        X_train_d = X_train.copy()
        y_train_d = y_train.copy()
        for index, row in X_train_d.iterrows():
            if row['cS'] < cS_thsd[i-1]:
                X_train_d.drop(index, inplace=True)
                Index.append(index)
        y_train_d=np.delete(y_train_d,Index)
        if y_train_d.size != 0:
            X_train_d.drop('cS', axis=1, inplace=True)
            name='VarLower_DT_{}bus_sub{}'.format(n_bus,dt_nb)
            dt_nb+=1
            DT(nodes,load_nodes,n_bus,mode_d,leaf_d,feat_d,depth_d,min_sp_leaf_d,min_sp_split_d,X_train_d,y_train_d,name)
        
    else: # If there are no critical values of cg1, one DT with load only is sufficient
        X_train_d = X_train.copy()
        y_train_d = y_train.copy()
        X_train_d.drop('cS', axis=1, inplace=True)
        name='VarLower_DT_{}bus_sub1'.format(n_bus)
        DT(nodes,load_nodes,n_bus,mode_d,leaf_d,feat_d,depth_d,min_sp_leaf_d,min_sp_split_d,X_train_d,y_train_d,name)