# -*- coding: utf-8 -*-
"""
Created on Thu Jan 16 09:34:27 2020

@author: emapr
"""

import pickle
import numpy as np
from sklearn.tree import DecisionTreeClassifier
import time
import gurobipy as gb
from statistics import mean
import pandas as pd
import ast
import sys
import os.path

def AllSets(n_bus, Demand, data, mode):

    # Start timer
    start_time = time.time()
    
    generators = data['generators']       # index for conventional generators
    nodes = data['nodes']                 # index for nodes
    load_nodes = data['load_nodes']       # index for nodes with load
    lines = data['lines']                 # index for lines
    lines_cstr = data['lines_cstr']       # index for constrained lines
    
    # 1 - Prepare identification of the sets of sets of active constraints
    name_SAS = 'AllSets_Sets_of_Active_Sets_DB_{}bus.csv'.format(n_bus)
    if os.path.exists(name_SAS):
        with open(name_SAS, mode='r') as f:
            read_csv = pd.read_csv(name_SAS,header=0)
            SAS_list = read_csv['Set of active sets'].tolist()
            SAS_tuple=[]
        for p in SAS_list:
            SAS_tuple.append(ast.literal_eval(p))
        set_nb = read_csv['ID'].tolist()
        SAS = {SAS_tuple[k]:set_nb[k] for k in range(len(SAS_tuple)) if SAS_tuple[k] is not None}
    else:
        sys.exit('The list of sets of active sets in csv is not available. Please add the file {} to the current directory or create it with the script AllSets_DB_DiscoverMass.py'.format(name_SAS))

    # list out keys and values separately 
    SAS_key = list(SAS.keys()) 
    SAS_val = list(SAS.values()) 
    
    # 2 - Give load values
    x=[]
    pt=[]
    for n in range(len(nodes)):
        if nodes[n] in load_nodes:
            pt.append(Demand[n])
    pt.append(sum(Demand))
    x.append(pt)
    x=np.array(x)
    
    # 3 - Output of DT for this load
    dt_output=[]
    name_DT = 'AllSets_DT_{}bus.pkl'.format(n_bus)
    if os.path.exists(name_DT):
        if mode == 'basic':
            # Apply DT
            with open(name_DT, 'rb') as f:
                DT = pickle.load(f)
                output=DT.predict(x)
                dt_output.append(output[0])
                
        elif mode == 'enhanced':
            with open(name_DT, 'rb') as f:
                DT = pickle.load(f)
                children_left = DT.tree_.children_left
                children_right = DT.tree_.children_right
                value = DT.tree_.value
                leave_id = DT.apply(x)
            
            if os.path.exists('Classes_{}'.format(name_DT)):
                with open('Classes_{}'.format(name_DT), 'rb') as f:
                    classes= pickle.load(f)
                # Identify parent node of the leaf and retrieve the corresponding active sets
                parent=None
                for left in range(len(children_left)):
                    if leave_id == children_left[left]:
                        parent = left
                        break
                if parent == None:
                    for right in range(len(children_right)):
                        if leave_id == children_right[right]:
                            parent = right
                            break
                value_parent=value[parent,0,:]
                if parent == None:
                    value_parent=value[0,0,:]
                for v in range(len(value_parent)):
                    if value_parent[v] > 2:
                        dt_output.append(classes[v])
            else: 
                sys.exit('Please add the file {} to the directory and run again. If it does not exist, run AllSets_DT_Generation.py first. '.format('Classes_{}.pkl'.format(name_DT)))
        else:
            sys.exit('{} is not an accepted mode. Please select a proper mode: "basic" or "enhanced" and run again.'.format(mode))
    else:
        sys.exit('The decision tree {} does not exist. Run AllSets_DT_Generation.py first to create it.'.format(name_DT))
        
    dt_output.sort() # Sort in ascending order
    dt_output=list(dict.fromkeys(dt_output)) #Remove duplicates
    
    # Retrieve the corresponding active constraints
    Set_act_cstr=[]
    
    for sas in dt_output:
        for aset in SAS_key[SAS_val.index(sas)]:
            Set_act_cstr.append(aset)
            
    Set_act_cstr=list(dict.fromkeys(Set_act_cstr)) #Remove duplicates

    # 4 - Run one LP for each set of active constraints identified
    
    Results=[] # To store the results of all the LPs
    obj_comp=[] # For the comparison of the objective function
    duration_loop=[]
    k = 0 # Number of LPs solved
            
    duration_1 = time.time() - start_time # (the following can be parallelized)
    
    for Act_cstr in Set_act_cstr:
    
        start_time_loop = time.time()
        k+=1
        
        # Model alias
        model = gb.Model('AllSets_Bilevel_{}'.format(k))
        
        # Display model output: 0=No, 1=Yes
        model.Params.OutputFlag = 0
        
        # Adjust tolerance of the model
        model.Params.OptimalityTol = 1e-9 # Dual
        model.Params.FeasibilityTol = 1e-9 # Primal
        model.Params.IntFeasTol = 1e-9 # Integer
        model.Params.DualReductions = 0 # To distinguish between infeasible and unbounded
        model.Params.TimeLimit = 5*60 # Runs for max 5min (in s)
        
    #-------------------------------------------------------------------------------------------------------------------------------------------------------
    
        ##### Definition of the variables #####
        
        # Strategic price offer for generator 1 
        cS = model.addVar(lb=data['cost_strategic'], ub=data['cost_strategic_max'], name='cS')
            
        # Production of generators
        P_g = {}
        for g in generators:
            P_g[g] = model.addVar(lb=-gb.GRB.INFINITY, ub=gb.GRB.INFINITY, name='P_{}'.format(g))
        
        # Angles of the buses
        theta = {}
        for i in nodes: 
            theta[i] = model.addVar(lb=-gb.GRB.INFINITY, ub=gb.GRB.INFINITY, name='theta_{}'.format(i))
        
        # Duals of lower level
        alpha = {}
        for i in nodes: 
            alpha[i] = model.addVar(lb=-gb.GRB.INFINITY, ub=gb.GRB.INFINITY, name='alpha_{}'.format(i))
        
        gamma = model.addVar(lb=-gb.GRB.INFINITY, ub=gb.GRB.INFINITY,name='gamma')
        
        phi_min = {}
        for g in generators:
            phi_min[g] = model.addVar(lb=0, ub=gb.GRB.INFINITY, name='phi_min_{}'.format(g))
            
        phi_max = {}
        for g in generators:
            phi_max[g] = model.addVar(lb=0, ub=gb.GRB.INFINITY, name='phi_max_{}'.format(g))       
        
        rho_min = {}
        for l in lines_cstr:
             rho_min[l] = model.addVar(lb=0, ub=gb.GRB.INFINITY, name='rho_min_{}'.format(l))
                
        rho_max = {}
        for l in lines_cstr:
             rho_max[l] = model.addVar(lb=0, ub=gb.GRB.INFINITY, name='rho_max_{}'.format(l))
    
        # Update of the model with the variables
        model.update()
        
    #-------------------------------------------------------------------------------------------------------------------------------------------------------
        
        ##### Objective function #####
        
        # Set the objective of upper level problem: maximize the profit of g1, with linearization
        obj = gb.LinExpr()
        obj.add(gb.quicksum(data[g]['cost']*P_g[g]+data[g]['g_max']*phi_max[g]-data[g]['g_min']*phi_min[g] for g in generators))
        obj.add(-data['g1']['g_max']*phi_max['g1']+data['g1']['g_min']*phi_min['g1'])
        obj.add(-gb.quicksum(alpha[i]*data[i]['demand'] for i in nodes))
        obj.add(gb.quicksum(data[l]['lineCapacity']*(rho_min[l]+rho_max[l]) for l in lines_cstr))
        model.setObjective(obj,gb.GRB.MINIMIZE)
        
    #-------------------------------------------------------------------------------------------------------------------------------------------------------
        
        ##### Constraints #####
        
        # 1 - No upper level constraints
        
        # 2 - Lagrangian derivatives of lower level
        
        L_g={}
        for g in generators:
            if g=='g1': # For generator under study, consider bidding cost instead of operating cost
                L_g[g] = model.addConstr(cS - alpha[data[g]['node']] - phi_min[g] + phi_max[g],
                                            gb.GRB.EQUAL,0,name='L_P{}'.format(g))
            else:
                L_g[g] = model.addConstr(data[g]['cost'] - alpha[data[g]['node']] - phi_min[g] + phi_max[g],
                                             gb.GRB.EQUAL,0,name='L_P{}'.format(g))
            
        L_theta={}
        for i in nodes:
            expr = gb.LinExpr()
            for l in data[i]['l_from']:
                expr.add(data[l]['B']*(alpha[i]-alpha[data[l]['to']]))
                if l in lines_cstr:
                        expr.add(data[l]['B']*(-rho_min[l]+rho_max[l]))
            for l in data[i]['l_to']:
                expr.add(data[l]['B']*(alpha[i]-alpha[data[l]['from']]))
                if l in lines_cstr:
                    expr.add(data[l]['B']*(rho_min[l]-rho_max[l]))
            if data[i]['ref']==1: # For slack bus, add Gamma
                expr.add(gamma)
            L_theta[i] = model.addConstr(expr,gb.GRB.EQUAL,0,name='L_theta_{}'.format(i))    
      
        # 3 - Lower level constraints
        
        # Power balance
        P_balance = {}
        for i in nodes:
            f = gb.LinExpr()
            for l in lines:
                if i==data[l]['from']:
                    f.add(data[l]['B']*(theta[i]-theta[data[l]['to']]))
                elif i==data[l]['to']:
                    f.add(data[l]['B']*(theta[i]-theta[data[l]['from']]))
                else:
                    pass
            P_balance[i] = model.addConstr(gb.quicksum(P_g[g] for g in data[i]['generators']) 
                                                   - data[i]['demand'] 
                                                   - f,
                                                   gb.GRB.EQUAL,0,name='h1_P_balance({})'.format(i))
        
        # Constraint for the initialization of angles: angle at slack bus set to 0   
        for i in nodes:
            if data[i]['ref']==1:
                model.addConstr(theta[i],gb.GRB.EQUAL,0,name='h2_Slack_bus')
            else:
                pass
        
        # Inequalities: 
        # If active: Replace with equality and no constraint for dual variable 
        # If inactive: Remove and dual variable is equal to zero
        
        # Min and max power
        P_min={}
        g1_dual={}
        
        P_max={}
        g2_dual={}
        
        for g in generators:
            # Min
            if 'phi_min_{}'.format(g) in Act_cstr:
                P_min[g]=model.addConstr(P_g[g],gb.GRB.EQUAL,data[g]['g_min'],name='g1_P({})_min'.format(g))
            else:
                g1_dual[g]=model.addConstr(phi_min[g], gb.GRB.EQUAL,0, name='Pgmin_dual_{}'.format(g))
                
            # Max
            if 'phi_max_{}'.format(g) in Act_cstr:
                P_max[g]=model.addConstr(P_g[g],gb.GRB.EQUAL,data[g]['g_max'],name='g2_P({})_max'.format(g))
            else:
                g2_dual[g]=model.addConstr(phi_max[g], gb.GRB.EQUAL,0, name='Pgmax_dual_{}'.format(g)) 
            
        # Max power flow in the lines
        f_max_pos={}
        g4_dual={}
        for l in lines_cstr:
            if 'rho_max_{}'.format(l) in Act_cstr:
                f_max_pos[l]=model.addConstr(data[l]['B']*(theta[data[l]['from']]-theta[data[l]['to']]),gb.GRB.EQUAL,data[l]['lineCapacity'],name='g4_Line_Capacity({})_pos'.format(l))
            else:
                g4_dual[l]=model.addConstr(rho_max[l], gb.GRB.EQUAL,0, name='g4_dual_{}'.format(l))
         
        f_max_neg={}
        g3_dual={}
        for l in lines_cstr:
            if 'rho_min_{}'.format(l) in Act_cstr:
                f_max_neg[l]=model.addConstr(data[l]['B']*(theta[data[l]['from']]-theta[data[l]['to']]),gb.GRB.EQUAL,-data[l]['lineCapacity'],name='g3_Line_Capacity({})_neg'.format(l))
            else:
                g3_dual[l]=model.addConstr(rho_min[l], gb.GRB.EQUAL,0, name='g3_dual_{}'.format(l))                
               
    #-------------------------------------------------------------------------------------------------------------------------------------------------------
        
        model.update()    # update of the model with the constraints and objective function
    
        ##### Optimization and Results #####      
        
        model.optimize()
    
        #Results display
        
        # model.write('AllSets_Bilevel_{}_Model.lp'.format(k)) # Equations
        # model.write('AllSets_Bilevel_{}_Results.sol'.format(k)) # Results
        
        feas=model.Status
        nb_cstr=model.NumConstrs
        res_tp={}
        
        if feas == 2:
            Results_tp=[model.ObjVal,cS.x,alpha[data['g1']['node']].x,P_g['g1'].x,k,nb_cstr]
            for v in model.getVars():
                res_tp[v.varName] =  v.x
            
        else:
            Results_tp=['NaN_{}'.format(feas),'NaN_{}'.format(feas),'NaN_{}'.format(feas),'NaN_{}'.format(feas),k,nb_cstr]
        
        if res_tp: # If the problem was feasible, check that the original inequalities are satisfied
            epsilon=0.00001
    
            # Min and max generation and demand:
            for g in generators:
                if res_tp['P_{}'.format(g)]+epsilon < data[g]['g_min'] or res_tp['P_{}'.format(g)]-epsilon > data[g]['g_max']:
                    feas=g
                    break # Leave the loop if a constraint is violated
        
            # Max power flow in the lines
            if feas == 2: # If no constraint on the generators is violated
                for l in lines_cstr:
                    t_to=res_tp['theta_{}'.format(data[l]['to'])]
                    t_from=res_tp['theta_{}'.format(data[l]['from'])]
                    if data[l]['B']*(t_from-t_to) - epsilon > data[l]['lineCapacity'] or data[l]['B']*(t_from-t_to) + epsilon < -data[l]['lineCapacity']:
                        feas=l
                        break  # Leave the loop if a constraint is violated
                    
            if feas == 2:
                obj_comp.append(Results_tp[0])
            else: 
                obj_comp.append(1000000000) # Set the objective function very high if the results of the bilevel are infeasible for the DCOPF
                Results_tp[0]='NaN_{}'.format(feas) # obj value 
                Results_tp[1]='NaN_{}'.format(feas) # cS
                Results_tp[2]='NaN_{}'.format(feas) # alpha
                Results_tp[3]='NaN_{}'.format(feas) # Pg
        else: 
            obj_comp.append(1000000000) # Set the objective function very high if the results of the  bilevel are infeasible
            
        Results.append(Results_tp)
        
        duration_loop.append(time.time() - start_time_loop)
    
    duration_loop_av = mean(duration_loop)
    
    last_start = time.time()
    
    # 5 - Identify the best output
    best = obj_comp.index(min(obj_comp))
    Best_Results = Results[best]
    Best_Results[4] = k

    # 6 - Calculate duration
    duration_loop_av = mean(duration_loop)
    duration_end = time.time() - last_start
    duration = duration_1 + duration_loop_av + duration_end
    
    return Best_Results, duration