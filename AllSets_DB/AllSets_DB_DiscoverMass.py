# -*- coding: utf-8 -*-
"""
Created on Tue May 12 14:38:39 2020

@author: emapr
"""

from DCOPF import DCOPF
import pickle
import time
import pandas as pd
import random
import os.path
import csv
import ast
import math
from Case import system_input

################################################## PARAMETERS TO BE MODIFIED ##################################################
###############################################################################################################################
n_bus = 9 # Number of bus of the system: Choice of the application system
epsilon = 0.0001 # Tolerance
x_Matpower_m = 0.5 # Percentage of Matpower under which the DB is created (- 50% of Matpower load value)
x_Matpower_p = 0.5 # Percentage of Matpower above which the DB is created (+ 50% of Matpower load value)
cS_pts = 10 # Number of cS values for the DB generation
cS_round=1 # Rounding of cS values (number of decimals)
############################################## INPUT PARAMETERS FOR DiscoverMass ##############################################
alpha = 0.05 # Maximum mass of the undiscovered bases
delta = 0.01 # Confidence level
# Hyperparameters that can be tuned
epsilon_dm = 0.04
gamma = 2
###############################################################################################################################
###############################################################################################################################

# Start timer
start_time = time.time()

##################### Parameters for the algorithm #####################

# Retrieve infomation on the system: list of bus and of bus which have a load connected
data = system_input(0,[0]*n_bus,n_bus)
nodes = data['nodes']
load_nodes = data['load_nodes']
nb_loads = len(load_nodes)
baseMVA = data['baseMVA']

# Function for the intervals
def frange(start, stop, step):
    i = start
    while i <= stop:
        yield i
        i += step

# Create list of cS values
cS_min = data['cost_strategic'] # Min from data file (equal to production cost)
cS_max = data['cost_strategic_max'] # Max from data file (equal to +30% of the highest generation cost)
cS_range = (cS_max - cS_min)/(cS_pts-1)
cS_tp=list(frange(cS_min,cS_max,cS_range))
CS=[round(num, cS_round) for num in cS_tp]

# Retrieve node of g1 and to create the string for retrieving the nodal price
node_g1 = data['g1']['node']
alpha_str = 'alpha_' + node_g1

# Max and min total load for the system
load_max=0
load_min=0
for g in data['generators']:
    load_max+= data[g]['g_max']
    load_min+= data[g]['g_min']

# Set up min and max load per bus (with a load) for the database generation
d_min=[]
d_max=[]

for y in range(n_bus):
    i=nodes[y]
    if i in load_nodes:
        Load_Matpower = data[i]['case_load'] # Retrieve load from Matpower case data
        d_min.append(min(Load_Matpower * (1-x_Matpower_m),Load_Matpower * (1+x_Matpower_m))) # The smallest load for the DB generation is -x_Matpower_m% (parameter) of the Matpower case value
        d_max.append(max(Load_Matpower * (1-x_Matpower_p),Load_Matpower * (1+x_Matpower_p))) # The highest load for the DB generation is +x_Matpower_p% (parameter) of the Matpower case value
    else:
        d_min.append(0)
        d_max.append(0)

#-----------------------------------------------------------------------------

# If there is already a DB file, complete it. Otherwise, create it

name_DB = 'AllSets_DB_{}bus.csv'.format(n_bus)
name_SAS = 'AllSets_Sets_of_Active_Sets_DB_{}bus.csv'.format(n_bus)

if os.path.exists(name_DB): 
    with open(name_DB, mode='r') as f:
        read_csv = pd.read_csv(name_DB,header=0)
        ld = read_csv['Load'].tolist() # Retrieve the list of the loads that are already in the database
        OP_DB=[]
        for p in ld:
            OP_DB.append(ast.literal_eval(p))
        
    with open(name_SAS, mode='r') as f:
        read_csv = pd.read_csv(name_SAS,header=0)
        SAS = read_csv['Set of active sets'].tolist()
        SAS_tuple=[]
    for p in SAS:
        SAS_tuple.append(ast.literal_eval(p))
    set_nb = read_csv['ID'].tolist()
    Sets_Active_Sets = {SAS_tuple[k]:set_nb[k] for k in range(len(SAS_tuple)) if SAS_tuple[k] is not None} # Retrieve the dictionnary giving the active constraints in each active set
    
    with open('bigM_{}bus.pkl'.format(n_bus), 'rb') as f:
        M = pickle.load(f)
    M_p=M['M_p']
    M_d=M['M_d']
    
else:
    OP_DB = [] # Creation of the list of points added to the DB (load)
    Sets_Active_Sets = {} # Dictionnary of observed sets of active sets
    with open(name_DB,'w',newline='') as f:
        write_csv = csv.writer(f)
        write_csv.writerow(['Load','Active set ID'])
        
    with open(name_SAS,'w',newline='') as f:
        write_csv = csv.writer(f)
        write_csv.writerow(['Set of active sets','ID'])
        
    M_p = 0 # BigM for primal constraints
    M_d = 0 # BigM for constraints on dual variables
    
n_sets = len(Sets_Active_Sets) # Counter of sets of active sets
n_feas = 0 # Counter of feasible points
n_unfeas = 0 # Counter of unfeasible points

duration = 0 # Initialize duration for the DB generation

################################# DiscoverMass ################################

# Calculated parameters of the DiscoverMass algorithm
c_dm = 2 * gamma / (epsilon_dm**2)
M_min = 1 + (gamma /(delta * (gamma-1))) ** (1 / (gamma-1))

# Initialize the DiscoverMass algorithm
M = 1 # Number of samples drawn
R = 1000000 # Rate of dicovery

# For a continuing calculation, retrieve parameters from the last execution
name_DM = 'AllSets_DiscoverMass_{}bus.pkl'.format(n_bus) 
if os.path.exists(name_DM):
    with open(name_DM,'rb') as f:
        Param = pickle.load(f)
    M = Param['M']
    R = Param['R']
    duration = Param['duration']
    n_feas = Param['n_feas']
    n_unfeas = Param['n_unfeas']

# Repeat
while R >= alpha - epsilon_dm and M <= 22000:
    
    # Calculate window size
    W = c_dm * max (math.log(M_min),math.log(M))
    
    # Draw additional samples from the probability distribution
    while len(OP_DB) < (M+W):
        
         # The point generated has to be between the loads limits, feasible,and not already in the DB
        feas = 0 # Optimization status initialization
        while feas!=2:
            # Generate load
            D=[]
            for y in range(n_bus):
                r=random.randint(int(baseMVA*d_min[y]),int(baseMVA*d_max[y]))
                r/=baseMVA
                D.append(r)
                
            if (sum(D) <= load_max) and (sum(D) >= load_min): # Check that the load randomly generated is inside the limits
                D = tuple(D)
                if D not in OP_DB:
                    (primal, cstr)= DCOPF(system_input(cS_min,D,n_bus)) # Run DCOPF
                    feas = primal['feas'] # Optimization status
                    if feas != 2:
                        n_unfeas+=1

# Get DCOPF results for each new sample

        Active_Sets_temp = []  # Set of sets of active constraints
   
        for cS in CS:
            (primal, cstr)= DCOPF(system_input(cS,D,n_bus)) # Run DCOPF and store results
            feas = primal['feas'] # Flag corresponding to the run
        
            if feas == 2: # if the operating point is feasible
                n_feas+=1
                active_cstr = [] # Active set for this cost
                
                # Creation of the set of active constraints
                for c in cstr:
                    if primal[c] > epsilon or primal[c] < - epsilon: # If the dual variable is not zero (with a tolerance of epsilon)
                        active_cstr.append(c) # Add the dual variable at the end of the list
                    
                # Add the active set if it's a new one for this load
                if active_cstr not in Active_Sets_temp:
                    Active_Sets_temp.append(active_cstr)
                    
                # Choice of big-Ms
                if primal['M_d'] > M_d: # If M_d for this point is higher than the stored value, replace it (same with M_p)
                    M_d=primal['M_d']
                if primal['M_p'] > M_p:
                    M_p=primal['M_p']
                    
            else: # (Not feasible)
                n_unfeas+=1
                
        Active_Sets = tuple(tuple(l) for l in Active_Sets_temp)

        # Add the newly observed sets of active sets to Sets_Active_Sets
        if Active_Sets in Sets_Active_Sets:
            n_set = Sets_Active_Sets[Active_Sets]
        else:
            Sets_Active_Sets[Active_Sets]=n_sets
            n_set = n_sets
            Row=[Active_Sets,n_sets]
            with open(name_SAS,'a+',newline='') as f:
                write_csv = csv.writer(f)
                write_csv.writerow(Row)
            n_sets=len(Sets_Active_Sets)
    
        # Add point to the database
        OP_DB.append(D)   
        Row=[D,n_set]
        with open(name_DB,'a+',newline='') as f:
                write_csv = csv.writer(f)
                write_csv.writerow(Row)

        # Save bigM
        big_M={'M_d':M_d,'M_p':M_p}
        f = open('bigM_{}bus.pkl'.format(n_bus),'wb')
        pickle.dump(big_M,f)
        f.close()
    
    # Compute R
    M_sets = []
    DB = pd.read_csv(name_DB,names=['Load','Active set ID'])
    i = 0
    X = 0 # Initialize the number of newly observed sets of active constraints
    
    while i < M: # Draw M samples from the DB
        M_A = DB.at[i, 'Active set ID'] 
        if M_A not in M_sets:
            M_sets.append(M_A)
        i+=1
                            
    while i < W+M: # Draw W samples from the DB to calculate X
        AC = DB.at[i, 'Active set ID'] 
        if AC not in M_sets:
            X+=1
        i+=1
                        
    R = 1/W * X
    
    # Update M
    M+=1
    
    # Save M and R, duration, number of feasible and unfeasible points sofar
    duration+=(time.time() - start_time)/60
    start_time = time.time()
    Param={'M':M, 'R':R, 'duration':duration,'n_feas':n_feas,'n_unfeas':n_unfeas}
    f = open(name_DM,'wb')
    pickle.dump(Param,f)
    f.close()

# Display time and number of points
print('Running time: {} minutes'.format(int(duration)))
print('{} feasible points and {} unfeasible points'.format(n_feas, n_unfeas))