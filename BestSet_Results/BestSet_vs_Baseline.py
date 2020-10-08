# -*- coding: utf-8 -*-
"""
Created on Fri Mar  6 17:26:39 2020

@author: emapr
"""

import csv
import pandas as pd
import random
import os.path
import ast

from DCOPF import DCOPF
from Bilevel_BigM import Baseline
from Bilevel_BestSet import BestSet
from Case import system_input

import matplotlib.pyplot as plt
import seaborn as sns

################################################## TO BE MODIFIED ##################################################
####################################################################################################################
n_bus = 9 # Number of bus of the system: Choice of the application system
test_pts = 10 # Number of test cases to be implemented
x_Matpower_m = 0.5 # Percentage of Matpower under which the DB is created (- 50% of Matpower load value)
x_Matpower_p = 0.5 # Percentage of Matpower above which the DB is created (+ 50% of Matpower load value)
mode = 'basic' # 'basic' to use the output of the DT
               # 'enhanced' to use the information from the parent of the leaf node
####################################################################################################################
####################################################################################################################

# Retrieve infomation on the system: list of bus, production cost of strategic 
# generator and list of bus which have a load connected
data = system_input(0,[0]*n_bus,n_bus)
nodes = data['nodes']
cost_g1 = data['cost_strategic']
load_nodes=data['load_nodes']
baseMVA = data['baseMVA']
TEST = [] # List of test cases
n_test = len(TEST) # Number of test cases created

# Give load values

# Max and min total load for the system
load_max=0
load_min=0
for g in data['generators']:
    load_max+= data[g]['g_max']
    load_min+= data[g]['g_min']

# Set up min and max load per bus (with a load) for the test scenario generation
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

# Write results

# If there is already a results file, complete it. Otherwise, create it
File_name = 'BestSet_Results_{}bus_{}.csv'.format(n_bus,mode)
Headline = ['Load','Duration BL (s)','Duration BS (s)',
                        'Obj fct BL','Obj fct BS','Optimality gap (%)', 'Recovered from intractable',
                        'Cost cS BL','Cost cS BS',
                        'alpha1 BL','alpha1 BS',
                        'Pg1 BL','Pg1 BS',
                        'Nb bin BL','Nb LPs BS',
                        'Nb cstr BL','Nb eq BL',
                        'Nb ineq BL','Nb cstr BS']
if os.path.exists(File_name): 
    Results_csv = pd.read_csv(File_name,header=0)
    test_str= Results_csv['Load'].tolist()
    TEST=[]
    for t in test_str:
        TEST.append(ast.literal_eval(t))
else:
    with open(File_name,'w',newline='') as f:
        write_csv = csv.writer(f)
        write_csv.writerow(Headline)
        
while len(TEST) < test_pts:
    # Generate random load
    Demand=[]
    for y in range(n_bus):
        r=random.randint(int(baseMVA*d_min[y]),int(baseMVA*d_max[y]))
        r/=baseMVA
        Demand.append(r)
    if sum(Demand) <= load_max and sum(Demand) >= load_min: # Check that the total load is between the limits
        if Demand not in TEST: # Check that this point does not already exist
            data = system_input(cost_g1,Demand,n_bus)
            (primal, duals_ineq)= DCOPF(data) # Run DCOPF and store results
            feas = primal['feas']
            if feas == 2:  # Only run the methods if the point is feasible
                TEST.append(Demand)
# Run Optimization
                Res_bl,dur_bl = Baseline(data,n_bus)
                Res_meth,dur_meth = BestSet(n_bus,Demand,data,mode)
                opt_gap = round((Res_bl[0] - Res_meth[0])*100 / Res_meth[0],3) # Optimality gap
                if isinstance(Res_bl[0],str) or isinstance(Res_bl[0],str):
                    opt_gap = 'NaN'
                recovered = 0 # Is a solution found in the case the point is intractable for the baseline
                if Res_bl[0] == 'NaN_9':
                    if not isinstance(Res_bl[0],str):
                        recovered = 1
                Row = [Demand,round(dur_bl,3),round(dur_meth,3),
                        Res_bl[0],Res_meth[0],opt_gap,recovered,
                        Res_bl[1],Res_meth[1],
                        Res_bl[2],Res_meth[2],
                        Res_bl[3],Res_meth[3],
                        Res_bl[4],Res_meth[4],
                        Res_bl[5],Res_bl[6],Res_bl[7],
                        Res_meth[5]]
                
                with open(File_name,'a+',newline='') as f:
                    write_csv = csv.writer(f)
                    write_csv.writerow(Row)
                        
# General results

with open(File_name, mode='r') as f:
    df = pd.read_csv(File_name,header=0)

# Count intractable cases with the baseline
intract_bl = False
if 'NaN_9' in list(df['Obj fct BL'].values):
    n_intract_bl=df['Obj fct BL'].value_counts()['NaN_9']
    intract_bl = True
# And with the method
intract_meth = False
if 'NaN_9' in list(df['Obj fct BS'].values):
    n_intract_meth=df['Obj fct BS'].value_counts()['NaN_9']
    intract_meth = True
# Count number of optimal solutions retrieved
Opt_gap = df['Optimality gap (%)']
opt_nb = Opt_gap[abs(Opt_gap) < 0.000001].count()
opt_perc = 100 * opt_nb / test_pts
# Count number of infeasible solutions with the method
feas_list=[str(x) for x in df['Obj fct BS'].tolist()]
n_infeas=sum('NaN' in i for i in feas_list)


# Printed results
print('-------------------------------------------------------------------------------------------------------', end='\n')
print('---------- Results for a {} bus system with the method BestSet, with {} points tested ----------'.format(n_bus,test_pts), end='\n')
print('-------------------------------------------------------------------------------------------------------', end='\n \n')
print('Baseline:', end='\n * ')
print('Duration:', end='\n    * ')
print('Average: {}s'.format(round(df['Duration BL (s)'].mean(),3)), end='\n    * ')
print('Min: {}s'.format(round(df['Duration BL (s)'].min(),3)), end='\n    * ')
print('Max: {}s'.format(round(df['Duration BL (s)'].max(),3)), end='\n    * ')
if intract_bl == True:
    print('Intractable cases: {} ({}%)'.format(n_intract_bl,round(100*n_intract_bl/test_pts,1)), end='\n * ')
else:
    print('No intractable cases', end='\n * ')
print('Number of binary variables: {}'.format(int(df['Nb bin BL'].mean())), end='\n * ')
print('Number of constraints: {}'.format(int(df['Nb cstr BL'].mean())), end='\n    * ')
print('{} equalities'.format(int(df['Nb eq BL'].mean())), end='\n    * ')
print('{} inequalities'.format(int(df['Nb ineq BL'].mean())), end='\n \n')
    
print('BestSet:', end='\n * ')
print('Duration:', end='\n    * ')
print('Average: {}s'.format(round(df['Duration BS (s)'].mean(),3)), end='\n    * ')
print('Min: {}s'.format(round(df['Duration BS (s)'].min(),3)), end='\n    * ')
print('Max: {}s'.format(round(df['Duration BS (s)'].max(),3)), end='\n    * ')
print('Compared to baseline: {}%'.format(round(100*df['Duration BS (s)'].mean()/df['Duration BL (s)'].mean(),1)), end='\n    * ')
if intract_meth == True:
    print('Intractable cases: {} ({}%)'.format(n_intract_meth,round(100*n_intract_meth/test_pts,1)), end='\n * ')
else:
    print('No intractable cases', end='\n * ')
print('Number of LPs solved: {}'.format(int(df['Nb LPs BS'].mean())), end='\n * ')
print('Number of constraints (equalities): {}'.format(int(df['Nb cstr BS'].mean())), end='\n * ')
print('Comparison to the cases that are tractable with the baseline:', end='\n    * ')
print('Optimal solution retrieved for {} cases ({}%)'.format(opt_nb,opt_perc), end='\n    * ')
print('Optimality gap (when the solution with the method is feasible):', end='\n        * ')
print('Average: {}%'.format(round(df['Optimality gap (%)'].mean(),1)), end='\n        * ')
print('Min: {}%'.format(round(df['Optimality gap (%)'].min(),1)), end='\n        * ')
print('Max: {}%'.format(round(df['Optimality gap (%)'].max(),1)), end='\n * ')
print('Infeasible solutions: {} ({}%)'.format(n_infeas,round(100*n_infeas/test_pts,1)))

if intract_bl == True:
    print(' * Comparison to the cases that are intractable with the baseline:', end='\n    * ')
    print('Solution recovered: {} ({}%)'.format(df['Recovered from intractable'].sum(),round(100*df['Recovered from intractable'].sum()/intract_bl,1)))

# Boxplot for the duration

dur_B = pd.DataFrame({'Duration (s)':df['Duration BL (s)'], 'Test case':'{} bus'.format(n_bus), 'Solving method':'Baseline'})
dur_M = pd.DataFrame({'Duration (s)':df['Duration BS (s)'], 'Test case':'{} bus'.format(n_bus), 'Solving method':'BestSet'})
dur = pd.concat([dur_B,dur_M])

fig, ax = plt.subplots()

sns.set(style='whitegrid')

# Colors used
gold = '#C48820'
blue = '#166FA0'
pal = {'Baseline': blue, 'BestSet': gold}
hue_order= ['Baseline', 'BestSet']

boxprops = {'edgecolor': 'k', 'linewidth': 1, 'facecolor': 'w'}
lineprops = {'color': 'k', 'linewidth': 1}

boxplot_kwargs = dict({'boxprops': boxprops, 'medianprops': lineprops,
                       'whiskerprops': lineprops, 'capprops': lineprops,
                       'width': 0.5,'palette': pal,
                       'hue_order': hue_order})

bplot = sns.boxplot(x='Test case', y='Duration (s)',
                  data=dur, 
                  hue='Solving method',
                  fliersize=0.5,
                  **boxplot_kwargs)

for i, artist in enumerate(ax.artists):
    if i % 2 == 0:
        col = blue
    else:
        col = gold
    artist.set_edgecolor(col)
    for j in range(i*6,i*6+6):
        line = ax.lines[j]
        line.set_color(col)
        line.set_mfc(col)
        line.set_mec(col)
        
plt.savefig('Boxplot_BestSet_{}_{}.jpg'.format(n_bus,mode), format='jpg', dpi=1200)