# -*- coding: utf-8 -*-
"""
Created on Thu Jan 16 09:34:27 2020

@author: emapr
"""

import gurobipy as gb
import time
import pickle

##### Creation of the model #####
def Baseline(data,n_bus):
    
    # Start timer
    start_time = time.time()
    
    # Counter of equality constraints
    nb_eq = 0
    
    generators = data['generators']       #index for conventional generators
    nodes = data['nodes']                 #index for node
    lines = data['lines']                 #index for lines
    lines_cstr = data['lines_cstr']       #index for constrained lines
    
    # Get bigM
    with open('bigM_{}bus.pkl'.format(n_bus), 'rb') as f:
        M = pickle.load(f)
    M_p=M['M_p']
    M_d=M['M_d']
   
    # Model alias
    model = gb.Model('Bilevel_BigM')
    
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
            
    # Binaries for Fortuny-Amat McCarl Linearization of KKTs
    u_min = {}
    for g in generators:
        u_min[g] = model.addVar(vtype='B', name='u_min_{}'.format(g))
        
    u_max = {}
    for g in generators:
        u_max[g] = model.addVar(vtype='B', name='u_max_{}'.format(g))
            
    y_min = {}
    for l in lines_cstr:
            y_min[l] = model.addVar(vtype='B', name='y_min_{}'.format(l))
            
    y_max = {}
    for l in lines_cstr:
            y_max[l] = model.addVar(vtype='B', name='y_max_{}'.format(l))    
    
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
    
    # 1 - Lagrangian derivatives of lower level
    
    L_g={}
    for g in generators:
        if g=='g1': # For generator under study, consider bidding cost instead of operating cost
            nb_eq+=1
            L_g[g] = model.addConstr(cS - alpha[data[g]['node']] - phi_min[g] + phi_max[g],
                                        gb.GRB.EQUAL,0,name='L_P{}'.format(g))
        else:
            nb_eq+=1
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
        nb_eq+=1
        L_theta[i] = model.addConstr(expr,gb.GRB.EQUAL,0,name='L_theta_{}'.format(i))         
  
    # 2 - Lower level constraints
    
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
        nb_eq+=1
        P_balance[i] = model.addConstr(gb.quicksum(P_g[g] for g in data[i]['generators']) 
                                               - data[i]['demand'] 
                                               - f,
                                               gb.GRB.EQUAL,0,name='h1_P_balance({})'.format(i))
    
    # Constraint for the initialization of angles: angle at slack bus set to 0   
    for i in nodes:
        if data[i]['ref']==1:
            nb_eq+=1
            model.addConstr(theta[i],gb.GRB.EQUAL,0,name='h2_Slack_bus')
        else:
            pass
        
    # Min and max power
    
    P_min={}
    P_max={}
    for g in generators:
        P_min[g]=model.addConstr(P_g[g],gb.GRB.GREATER_EQUAL,data[g]['g_min'],name='g1_P({})_min'.format(g))
        P_max[g]=model.addConstr(P_g[g],gb.GRB.LESS_EQUAL,data[g]['g_max'],name='g2_P({})_max'.format(g))
        
    # Max power flow in the lines
    
    f_max_pos={}
    for l in lines_cstr:
        f_max_pos[l]=model.addConstr(data[l]['B']*(theta[data[l]['from']]-theta[data[l]['to']]),gb.GRB.LESS_EQUAL,data[l]['lineCapacity'],name='g6_Line_Capacity({})_pos'.format(l))

    f_max_neg={}
    for l in lines_cstr:
        f_max_neg[l]=model.addConstr(data[l]['B']*(theta[data[l]['from']]-theta[data[l]['to']]),gb.GRB.GREATER_EQUAL,-data[l]['lineCapacity'],name='g5_Line_Capacity({})_neg'.format(l))
    
    # 3 - Linearized complementarity constraints of lower level
    
    # g1
    M_g1_primal={}
    for g in generators:
        M_g1_primal[g]=model.addConstr(P_g[g]-data[g]['g_min'], gb.GRB.LESS_EQUAL, 
                                            M_p * u_min[g], name='M_Pgmin_primal_{}'.format(g))
    
    M_g1_dual={}
    for g in generators:
        M_g1_dual[g]=model.addConstr(phi_min[g], gb.GRB.LESS_EQUAL, 
                                            M_d * (1-u_min[g]), name='M_Pgmin_dual_{}'.format(g))
        
    # g2
    M_g2_primal={}
    for g in generators:
        M_g2_primal[g]=model.addConstr(data[g]['g_max']-P_g[g], gb.GRB.LESS_EQUAL, 
                                            M_p * u_max[g], name='M_Pgmax_primal_{}'.format(g))
    
    M_g2_dual={}
    for g in generators:
        M_g2_dual[g]=model.addConstr(phi_max[g], gb.GRB.LESS_EQUAL, 
                                            M_d * (1-u_max[g]), name='M_Pgmax_dual_{}'.format(g))
    
    # g3
    M_g3_primal={}
    for l in lines_cstr:
        M_g3_primal[l]=model.addConstr(data[l]['lineCapacity']+data[l]['B']*(theta[data[l]['from']]-theta[data[l]['to']]), gb.GRB.LESS_EQUAL, 
                                                M_p * y_min[l], name='M_g3_primal_({})'.format(l))
    
    M_g3_dual={}
    for l in lines_cstr:
        M_g3_dual[l]=model.addConstr(rho_min[l], gb.GRB.LESS_EQUAL, 
                                                M_d * (1-y_min[l]), name='M_g3_dual_({})'.format(l))
            
    # g4
    M_g4_primal={}
    for l in lines_cstr:
        M_g4_primal[l]=model.addConstr(data[l]['lineCapacity']-data[l]['B']*(theta[data[l]['from']]-theta[data[l]['to']]), gb.GRB.LESS_EQUAL, 
                                                M_p * y_max[l], name='M_g4_primal_({})'.format(l))
    
    M_g4_dual={}
    for l in lines_cstr:
        M_g4_dual[l]=model.addConstr(rho_max[l], gb.GRB.LESS_EQUAL, 
                                                M_d * (1-y_max[l]), name='M_g4_dual_({})'.format(l))
    
#-------------------------------------------------------------------------------------------------------------------------------------------------------
    model.update()    # update of the model with the constraints and objective function

    ##### Optimization and Results #####      
    
    model.optimize()
    
    # Calculations

    #Results display
    
    # model.write('Bilevel_BigM_Equations.lp') # write equations in an .lp file
    # model.write('Bilevel_BigM_Results.sol') # write solutions in an .sol file
    
    feas=model.Status
    nb_cstr=model.NumConstrs
    nb_ineq=nb_cstr-nb_eq
    M_d_lim=0
    
    if feas == 2: # If the problem is feasible
        
        # Calculate M_d_lim as the maximum of the dulas of inequality constraints. M_d has to be greater (and not equal)
        for g in generators:
            if phi_min[g].x > M_d_lim:
                M_d_lim = phi_min[g].x
            if phi_max[g].x > M_d_lim:
                M_d_lim = phi_max[g].x
                
        for l in lines_cstr:
            if rho_min[l].x > M_d_lim:
                M_d_lim = rho_min[l].x
            if rho_max[l].x > M_d_lim:
                M_d_lim = rho_max[l].x
                
        points=[model.ObjVal,cS.x,alpha[data['g1']['node']].x,P_g['g1'].x,model.NumBinVars,nb_cstr,nb_eq,nb_ineq]
        
    else:
        points=['NaN_{}'.format(feas),'NaN_{}'.format(feas),'NaN_{}'.format(feas),'NaN_{}'.format(feas),model.NumBinVars,nb_cstr,nb_eq,nb_ineq]
    
    duration=time.time() - start_time
    
    return points,duration