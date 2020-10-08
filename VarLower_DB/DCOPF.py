# -*- coding: utf-8 -*-
"""
Created on Thu Jan 16 09:34:27 2020

@author: emapr
"""

# Solves the DCOPF for a given system, returning the value of the power generation,
# voltage angles and dual variables, as well as the names of the dual variables for inequalities

import gurobipy as gb

def DCOPF(data):
    
    generators = data['generators']       # index for conventional generators 
    nodes = data['nodes']                 # index for nodes 	
    lines = data['lines']                 # index for lines
    lines_cstr = data['lines_cstr']       # index for constrained lines
    duals_ineq = []                       # List to store the names of the dual variables of inequalities
   
    # Model alias
    model = gb.Model('dcopf')
    
    # Display model output: 0=No, 1=Yes
    model.Params.OutputFlag = 0
    
    # Adjust tolerance of the model
    model.Params.OptimalityTol = 1e-9 # Dual
    model.Params.FeasibilityTol = 1e-9 # Primal
    model.Params.IntFeasTol = 1e-9 # Integer
    model.Params.DualReductions = 0 # To distinguish between infeasible and unbounded
    
#-------------------------------------------------------------------------------------------------------------------------------------------------------

    ##### Definition of the variables #####
        
    # Production of generators
    P_g = {}
    for g in generators:
        P_g[g] = model.addVar(lb=-gb.GRB.INFINITY, ub=gb.GRB.INFINITY, name='P_{}'.format(g))
    
    # Angles of the buses
    theta = {}
    for i in nodes: 
        theta[i] = model.addVar(lb=-gb.GRB.INFINITY, ub=gb.GRB.INFINITY, name='theta_{}'.format(i))
      
    # Update of the model with the variables
    model.update()
    
#-------------------------------------------------------------------------------------------------------------------------------------------------------
    
    ##### Objective function #####
    
    # Set the objective of the problem: maximize the social welfare
    model.setObjective(gb.quicksum(P_g[g]*data[g]['cost'] for g in generators),gb.GRB.MINIMIZE)
    
#-------------------------------------------------------------------------------------------------------------------------------------------------------
    
    ##### Constraints #####
    
    # Min and max generation
    Pg_min={}
    Pg_max={}
    for g in generators:
        Pg_min[g] = model.addConstr(P_g[g],gb.GRB.GREATER_EQUAL,data[g]['g_min'],name='phi_min_{}'.format(g))
        duals_ineq.append('phi_min_{}'.format(g))
    for g in generators:
        Pg_max[g] = model.addConstr(P_g[g],gb.GRB.LESS_EQUAL,data[g]['g_max'],name='phi_max_{}'.format(g))
        duals_ineq.append('phi_max_{}'.format(g))
    
    # Power balance
    P_balance = {}
    for i in nodes:
        f = gb.LinExpr()
        for l in lines:
            if i==data[l]['from']:
                f.add(data[l]['B']*(theta[i]-theta[data[l]['to']]))
            elif i==data[l]['to']:
                f.add(data[l]['B']*(theta[i]-theta[data[l]['from']]))
                
        P_balance[i] = model.addConstr(gb.quicksum(P_g[g] for g in data[i]['generators']) 
                                               - data[i]['demand'] 
                                               - f,
                                               gb.GRB.EQUAL,0,name='alpha_{}'.format(i))
    
    # Constraint for the initialization of angles: angle at slack bus set to 0
    for i in nodes:
        if data[i]['ref']==1:
            model.addConstr(theta[i],gb.GRB.EQUAL,0,name='gamma')
        
    # Max power flow in the lines (absolute value)
    f_max_pos={}
    for l in lines_cstr:
        f_max_pos[l]=model.addConstr(data[l]['B']*(theta[data[l]['from']]-theta[data[l]['to']]),gb.GRB.LESS_EQUAL,data[l]['lineCapacity'], name='rho_max_{}'.format(l))
        duals_ineq.append('rho_max_{}'.format(l))

    f_max_neg={}
    for l in lines_cstr:
        f_max_neg[l]=model.addConstr(data[l]['B']*(theta[data[l]['from']]-theta[data[l]['to']]),gb.GRB.GREATER_EQUAL,-data[l]['lineCapacity'], name='rho_min_{}'.format(l))
        duals_ineq.append('rho_min_{}'.format(l))
    
#-------------------------------------------------------------------------------------------------------------------------------------------------------
    
    model.update()    # update of the model with the constraints and objective function

    ##### Optimization and Results #####      
    
    model.optimize()

    #Results display
    
    # model.write('dcopf.lp') # Write the model
    # model.write('dcopf.sol') # Write the results
    
    points={}
    
    feas=model.Status
    
    if feas == 2: # If the problem is feasible, retrieve:
        points['feas'] = feas
        points['obj'] = model.ObjVal # Value of the objective function
        for v in model.getVars():
            points[v.varName] =  v.x # Value of the primal variables
        for c in model.getConstrs():
            points[c.ConstrName] = c.pi # Value of the dual variables
            
    # Calculations for big M
        # big M dual: 10 times the max of dual variables for inequalities
        M_d = 0
        for d_in in duals_ineq:
            if points[d_in] > M_d:
               M_d = points[d_in]
        points['M_d'] = 10 * M_d
        # big M primal: 10 times the maximum of inequality constraints
        M_p = 0
        for g in generators:
            if data[g]['g_max'] > M_p:
                M_p=data[g]['g_max']
        for l in lines_cstr:
            if 2*data[l]['lineCapacity'] > M_p:
                M_p=2*data[l]['lineCapacity']
        points['M_p'] = 10 * M_p
        
    else: # If the problem is infeasible, retrieve the optimization status only
        points['feas'] = feas
        
    return points, duals_ineq