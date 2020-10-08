# -*- coding: utf-8 -*-
"""
Created on Tue Mar 24 16:36:25 2020

@author: emapr
"""

##### Definition of the dataset based on Matpower case file #####

import pandas as pd
import sys


def system_input(cS, D, n_bus):
    
    data={} # Create the data file as a dictionnary
    
    # Read data from the csv files created from the Matpower case files
    baseMVA_csv = pd.read_csv('baseMVA_{}bus.csv'.format(n_bus),names=['baseMVA'])
    branch = pd.read_csv('branch_{}bus.csv'.format(n_bus),names=['fbus', 'tbus', 'r', 'x', 'b', 'rateA', 'rateB', 'rateC', 'ratio', 'angle', 'status', 'angmin', 'angmax'])
    bus = pd.read_csv('bus_{}bus.csv'.format(n_bus),names=['bus_i', 'type', 'Pd', 'Qd', 'Gs', 'Bs', 'area', 'Vm', 'Va', 'baseKV', 'zone', 'Vmax', 'Vmin'])
    gen = pd.read_csv('gen_{}bus.csv'.format(n_bus),names=['bus', 'Pg', 'Qg', 'Qmax', 'Qmin', 'Vg', 'mBase', 'status', 'Pmax', 'Pmin', 'Pc1', 'Pc2', 'Qc1min', 'Qc1max', 'Qc2min', 'Qc2max', 'ramp_agc', 'ramp_10', 'ramp_30', 'ramp_q', 'apf'])
    gencost = pd.read_csv('gencost_{}bus.csv'.format(n_bus),names=['2', 'startup','shutdown', 'n', 'c2', 'c1', 'c0'])
    
    (nb_gen,x) = gen.shape # Retrieve number of generators
    (nb_bus,x) = bus.shape # Retrieve number of bus
    (nb_branch,x) = branch.shape # Retrieve number of lines
    baseMVA = baseMVA_csv.at[0, 'baseMVA']  # Retrieve base MVA (S) for pu calculation
    data['baseMVA'] = baseMVA
    
    generators = [] # Create list of generators
    for g in range(nb_gen):
        generators.append('g{}'.format(g+1))
    
    nodes = [] # Create list of nodes
    load_nodes=[] # Create list of nodes which have a load connected
    for i in range(nb_bus):
        nodes.append('n{}'.format(bus.at[i, 'bus_i']))
        if bus.at[i, 'Pd']!=0:
            load_nodes.append(nodes[i])
        
    lines = [] # Create list of lines
    lines_cstr = [] # Create list of constrained lines
    for l in range(nb_branch):
        lines.append('l{}'.format(l+1))
        if branch.at[l,'rateA'] != 0:
            lines_cstr.append('l{}'.format(l+1))
            
    # Add the list of generators, bus, lines, constrained lines and nodes with a connected load to the dictionary
    data['generators'] = generators
    data['nodes'] = nodes
    data['lines'] = lines
    data['lines_cstr'] = lines_cstr
    data['load_nodes']=load_nodes
    
    # Units: 
    # - Capacities in pu
    # - Energy costs in $/pu
    # - Investment cost in $
    # - Susceptance in pu
    
    # Retrieve generators details: bus, min and max power, cost
    for g in range(nb_gen):
        gbus='n{}'.format(gen.at[g, 'bus'])
        if g==0: # For the first generator (strategic), the cost is a variable (for DB generation), but prod cost is retrieve and upper boundary is calculated
            data[generators[g]]={'node':gbus, 'g_min':(gen.at[g, 'Pmin']/baseMVA), 'g_max':(gen.at[g, 'Pmax']/baseMVA),'cost':cS}
            data['cost_strategic']=gencost.at[g, 'c1']*baseMVA
            data['cost_strategic_max']= (gencost.max(axis=0)).at['c1']*1.3*baseMVA # max: +30% of the highest generation cost
        else:
            data[generators[g]]={'node':gbus, 'g_min':(gen.at[g, 'Pmin']/baseMVA), 'g_max':(gen.at[g, 'Pmax']/baseMVA),'cost':(gencost.at[g, 'c1']*baseMVA)}

    # Retrieve lines details: capacity, susceptance, from bus, to bus
    for l in range(nb_branch):
        fbus='n{}'.format(branch.at[l, 'fbus'])
        tbus='n{}'.format(branch.at[l, 'tbus'])
        x=branch.at[l,'x']
        if x!=0:
            data[lines[l]]={'lineCapacity':(branch.at[l,'rateA']/baseMVA), 'B':1/x, 'from':fbus, 'to':tbus}   
        else:
            sys.exit('There is an error in the case data: the susceptance of line {} is equal to zero'.format(l))  
    
    # Retrieve bus details: generators connected, slack bus, lines starting at this bus and lines ending at this bus
    for i in range(nb_bus):
        g_n=[]
        for g in data['generators']:
            if data[g]['node'] == nodes[i]:
                g_n.append(g)
        if bus.at[i, 'type'] == 3:
            ref=1
        else:
            ref=0
        i_from=[]
        i_to=[]
        for l in data['lines']:
            if nodes[i]==data[l]['from']:
                i_from.append(l)
            elif nodes[i]==data[l]['to']:
                i_to.append(l)
        data[nodes[i]]={'generators':g_n, 'case_load':bus.at[i,'Pd']/baseMVA,'demand':D[i], 'ref':ref, 'l_from':i_from, 'l_to':i_to}
    
    return data