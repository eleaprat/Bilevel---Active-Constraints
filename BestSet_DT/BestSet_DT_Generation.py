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
min_sp_split = 2
min_sp_leaf = 2
leaf = 444 # Max Leaves in DTs
feat = None
depth = 18

# Mode: 0 for Hyperparameter tunning and 1 for running DT
mode = 1 # For general DT: First set to 0 to determine the best value for the hyperparameters, then change the hyperparameters above and set to 1
###############################################################################################################################
###############################################################################################################################

data = system_input(0,[0]*n_bus,n_bus)
nodes = data['nodes']
load_nodes=data['load_nodes']

# Prepare data

# Load data
name_DB = 'BestSet_DB_{}bus.csv'.format(n_bus)
name_AS = 'BestSet_Active_Sets_DB_{}bus.csv'.format(n_bus)

if os.path.exists(name_DB):
    with open(name_DB, mode='r') as f:
        y_train=[]
        Load=[]
        reader_train = pd.read_csv(name_DB,header=0)
else:
    sys.exit('The database in csv is not available. Please add the file {} to the current directory or create it with the script BestSet_DB_DiscoverMass.py'.format(name_DB))

# Create y array for the DT: x -> y, y being the active set associated with each data point
y_train = reader_train['Active set ID'].tolist()
y_train=np.array(y_train)

# Create x array for the DT: x -> y, x being the data point with load of the strategic generator

# Retrieve the load at each point as a list
pt = reader_train['Load'].tolist()
for p in pt:
    p_list = list(ast.literal_eval(p))
    Load.append(p_list)
    
for n in range(n_bus):
    if n == 0: # Create the dataframe
        new_col=[]
        for l in Load:
            elt = l[n]
            new_col.append(elt)
        features= pd.DataFrame(data={nodes[n]:new_col})
    else: # Add to the existing dataframe
        new_col=[]
        for l in Load:
            elt = l[n]
            new_col.append(elt)
        features.insert(len(features.columns), nodes[n], new_col)
features.insert(len(features.columns),'total load',features.sum(axis='columns'))

for n in nodes:
    if n not in load_nodes:
        features=features.drop(columns=n)
    
X_train=features

### Create DT
name='BestSet_DT_{}bus'.format(n_bus)

if mode == 0:
    
    # Number of sets of active constraints detected
    if os.path.exists(name_AS):
        with open(name_AS, mode='r') as f:
            read_csv = pd.read_csv(name_AS,header=0)
            AS_list = read_csv['Active set'].tolist()
            AS_tuple=[]
    else: 
        sys.exit('The list of active sets in csv is not available. Please add the file or create it with the script AllSets_DB_DiscoverMass.py')

    for p in AS_list:
        AS_tuple.append(ast.literal_eval(p))
    set_nb = read_csv['ID'].tolist()
    AS = {AS_tuple[k]:set_nb[k] for k in range(len(AS_tuple)) if AS_tuple[k] is not None}
    print('There are {} different sets of active constraints in the DB'.format(len(AS)))
    print('----------------------------------------')
    
    # Test of the best hyperparameters
    DT(nodes,load_nodes,n_bus,mode,leaf,feat,depth,min_sp_leaf,min_sp_split,X_train,y_train,name)
    
elif mode == 1:
    n_nodes, children_left, children_right, feature, threshold = DT(nodes,load_nodes,n_bus,mode,leaf,feat,depth,min_sp_leaf,min_sp_split,X_train,y_train,name)