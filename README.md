# Bilevel---Active-Constraints
You can find here the code for the article "Learning Active Constraints to Efficiently Solve Bilevel Problems".
The code is organized in folders per proposed method and stage: database (DB) creation, decision tree (DT) generation. The example of the 9 bus system from [Matpower](https://ieeexplore.ieee.org/document/5491276) is used to show how to use the code. The complete datafiles used in the article can be found on [Zenodo](https://zenodo.org/deposit/4081630).

## Case_from_Matpower
This folder contains the example of a test case in the Matpower format.
  * **case9_blv.m**: Matpower case file for the 9 bus system used as example in this repository.
  * **Matpower_case_conversion.m**: Run this first in order to create the csv files that will be used in Python. The file name (line 4) has to be changed to match the case file name, here 'case9_blv'. The number of bus has to be modified too (line 5).
  * **baseMVA_9bus.csv, branch_9bus.csv, bus_9bus.csv, gen_9bus.csv, gencost_9bus.csv**: Case files in csv for use in Python. Those have to be included to the working directory.

## AllSets
### AllSets_DB
This folder contains the code to generate a database of points for the AllSets method.
 * Necessary input: Case files in csv (not included here but available in the folder '0_Case_from_Matpower').
 * **AllSets_DB_DiscoverMass.py**: Main file to run in order to generate the DB. It includes the selection of the proper parameters. In particular: the selection of the case, the selection of the load interval for the creation of the DB, the number of values considered for the price bid of the strategic producer, the parameters applied in the DiscoverMass algorithm.
 * **Case.py**: Builds the case file from the different csv files.
 * **DCOPF.py**: DCOPF formulation and solving with Gurobi. Called by 'AllSets_DB_DiscoverMass.py'.
 
 ### AllSets_DT
This folder contains the code to generate the decision tree for a given database associating to a load a set of active sets.
  * Necessary input:
    - Case files in csv (not included here but available in the folder '0_Case_from_Matpower').
    - Database in csv created with 'AllSets_DB_DiscoverMass.py'. For the example of the 9 bus system it is **'AllSets_DB_9bus.csv'**
    - Sets of active sets in csv created with 'AllSets_DB_DiscoverMass.py'. For the example of the 9 bus system it is **'AllSets_Sets_of_Active_Sets_DB_9bus.csv'**
  * **AllSets_DT_Generation.py**: Main file to run in order to generate the DT. It includes the selection of the proper parameters. Run first setting 'mode=0' to evaluate the hyperparameters to apply. Run a second time with 'mode=1' after modifying the hyperparameters. 
 * **Case.py**: Builds the case file from the different csv files.
 * **Decison_Tree.py**: Decision tree building. Called by 'AllSets_DT_Generation.py'.
 
 ### AllSets_Results
 This folder contains the code to compare the method AllSets to the baseline. The general results are dispayed, detailed results are available in csv format and a boxplot is created to compare the running time for those.
 * Necessary input:
    - Case files in csv (not included here but available in the folder '0_Case_from_Matpower').
    - Decision tree created in 'AllSets_DT_Generation.py'. For the example of the 9 bus system it is **'AllSets_DT_9bus.pkl'**.
    - Classes used in the decision tree. For the example of the 9 bus system it is **'Classes_AllSets_DT_9bus.pkl'**.
    - Sets of active sets in csv created with 'AllSets_DB_DiscoverMass.py'. For the example of the 9 bus system it is **'AllSets_Sets_of_Active_Sets_DB_9bus.csv'**.
    - Big M to be applied in 'Bilevel_BigM.py'. For the example of the 9 bus system it is **'bigM_9bus.pkl'**.
  * **AllSets_vs_Baseline.py**: Main file to run in order to test the method AllSets and compare it to the baseline. It includes the selection of the proper parameters. In particular: the selection of the case, the number of test points to be generated, the selection of the load interval for the creation of the DB and the selection of the mode 'basic' or 'enhanced'.
 * **Case.py**: Builds the case file from the different csv files.
 * **Bilevel_AllSets.py**: Application of the DT and formulation of the bilevel problem in the form of LPs. Solving with Gurobi. Called by 'AllSets_vs_Baseline.py'.
 * **Bilevel_BigM.py**: Formulation of the bilevel problem with KKTs and big-M. Solving with Gurobi. Called by 'AllSets_vs_Baseline.py'.
  * **DCOPF.py**: DCOPF formulation and solving with Gurobi (feasibility check). Called by 'AllSets_vs_Baseline.py'.
  
## BestSet
### BestSet_DB
This folder contains the code to generate a database of points for the BestSet method.
 * Necessary input: Case files in csv (not included here but available in the folder '0_Case_from_Matpower').
 * **BestSet_DB_DiscoverMass.py**: Main file to run in order to generate the DB. It includes the selection of the proper parameters. In particular: the selection of the case, the selection of the load interval for the creation of the DB, the number of values considered for the price bid of the strategic producer, the parameters applied in the DiscoverMass algorithm.
 * **Case.py**: Builds the case file from the different csv files.
 * **DCOPF.py**: DCOPF formulation and solving with Gurobi. Called by 'BestSet_DB_DiscoverMass.py'.
 
 ### BestSet_DT
This folder contains the code to generate the decision tree for a given database associating to a load a set of active constraints.
  * Necessary input:
    - Case files in csv (not included here but available in the folder '0_Case_from_Matpower').
    - Database in csv created with 'BestSet_DB_DiscoverMass.py'. For the example of the 9 bus system it is **'BestSet_DB_9bus.csv'**
    - Sets of active sets in csv created with 'BestSet_DB_DiscoverMass.py'. For the example of the 9 bus system it is **'BestSet_Active_Sets_DB_9bus.csv'**
  * **BestSet_DT_Generation.py**: Main file to run in order to generate the DT. It includes the selection of the proper parameters. Run first setting 'mode=0' to evaluate the hyperparameters to apply. Run a second time with 'mode=1' after modifying the hyperparameters. 
 * **Case.py**: Builds the case file from the different csv files.
 * **Decison_Tree.py**: Decision tree building. Called by 'BestSet_DT_Generation.py'.
 
 ### BestSet_Results
 This folder contains the code to compare the method BestSet to the baseline. The general results are dispayed, detailed results are available in csv format and a boxplot is created to compare the running time for those.
 * Necessary input:
    - Case files in csv (not included here but available in the folder '0_Case_from_Matpower').
    - Decision tree created in 'BestSet_DT_Generation.py'. For the example of the 9 bus system it is **'BestSet_DT_9bus.pkl'**.
    - Classes used in the decision tree. For the example of the 9 bus system it is **'Classes_BestSet_DT_9bus.pkl'**.
    - Sets of active sets in csv created with 'BestSet_DB_DiscoverMass.py'. For the example of the 9 bus system it is **'BestSet_Active_Sets_DB_9bus.csv'**.
    - Big M to be applied in 'Bilevel_BigM.py'. For the example of the 9 bus system it is **'bigM_9bus.pkl'**.
  * **BestSet_vs_Baseline.py**: Main file to run in order to test the method BestSet and compare it to the baseline. It includes the selection of the proper parameters. In particular: the selection of the case, the number of test points to be generated, the selection of the load interval for the creation of the DB and the selection of the mode 'basic' or 'enhanced'.
 * **Case.py**: Builds the case file from the different csv files.
 * **Bilevel_BestSet.py**: Application of the DT and formulation of the bilevel problem in the form of LPs. Solving with Gurobi. Called by 'BestSet_vs_Baseline.py'.
 * **Bilevel_BigM.py**: Formulation of the bilevel problem with KKTs and big-M. Solving with Gurobi. Called by 'BestSet_vs_Baseline.py'.
  * **DCOPF.py**: DCOPF formulation and solving with Gurobi (feasibility check). Called by 'BestSet_vs_Baseline.py'.
  
  ## VarLower
### VarLower_DB
This folder contains the code to generate a database of points for the VarLower method.
 * Necessary input: Case files in csv (not included here but available in the folder '0_Case_from_Matpower').
 * **VarLower_DB_DiscoverMass.py**: Main file to run in order to generate the DB. It includes the selection of the proper parameters. In particular: the selection of the case, the selection of the load interval for the creation of the DB, the parameters applied in the DiscoverMass algorithm.
 * **Case.py**: Builds the case file from the different csv files.
 * **DCOPF.py**: DCOPF formulation and solving with Gurobi. Called by 'VarLower_DB_DiscoverMass.py'.
 
 ### VarLower_DT
This folder contains the code to generate the decision trees for a given database associating to a load a set of active constraints.
  * Necessary input:
    - Case files in csv (not included here but available in the folder '0_Case_from_Matpower').
    - Database in csv created with 'VarLower_DB_DiscoverMass.py'. For the example of the 9 bus system it is **'VarLower_DB_9bus.csv'**
    - Sets of active sets in csv created with 'AllSets_DB_DiscoverMass.py'. For the example of the 9 bus system it is **'VarLower_Active_Sets_DB_9bus.csv'**
  * **VarLower_DT_Generation.py**: Main file to run in order to generate the DTs. It includes the selection of the proper parameters. Run first setting 'mode=0' to evaluate the hyperparameters to apply. Run a second time with 'mode=1' and 'mode_d=0' after modifying the hyperparameters and in order to identify the proper parameters to apply in the sub DTs. Run a third time with 'mode_d=1' after modifying the hyperparameters of the sub DTs.
 * **Case.py**: Builds the case file from the different csv files.
 * **Decison_Tree.py**: Decision tree building. Called by 'VarLower_DT_Generation.py'.
 
 ### VarLower_Results
 This folder contains the code to compare the method VarLower to the baseline. The general results are dispayed, detailed results are available in csv format and a boxplot is created to compare the running time for those.
 * Necessary input:
    - Case files in csv (not included here but available in the folder '0_Case_from_Matpower').
    - Sub decision trees created in 'VarLower_DT_Generation.py'. For the example of the 9 bus system those are **'VarLower_DT_9bus_sub1.pkl'**, **'VarLower_DT_9bus_sub2.pkl'**, **'VarLower_DT_9bus_sub3.pkl'**.
    - Classes used in the sub decision trees. For the example of the 9 bus system those are **'Classes_VarLower_DT_9bus_sub1.pkl'**, **'Classes_VarLower_DT_9bus_sub2.pkl'**, **'Classes_VarLower_DT_9bus_sub3.pkl'**.
    - Sets of active sets in csv created with 'VarLower_DB_DiscoverMass.py'. For the example of the 9 bus system it is **'VarLower_Active_Sets_DB_9bus.csv'**.
    - Big M to be applied in 'Bilevel_BigM.py'. For the example of the 9 bus system it is **'bigM_9bus.pkl'**.
  * **VarLower_vs_Baseline.py**: Main file to run in order to test the method VarLower and compare it to the baseline. It includes the selection of the proper parameters. In particular: the selection of the case, the number of sub DTs generated at the previous step, the number of test points to be generated, the selection of the load interval for the creation of the DB and the selection of the mode 'basic' or 'enhanced'.
 * **Case.py**: Builds the case file from the different csv files.
 * **Bilevel_VarLower.py**: Application of the DT and formulation of the bilevel problem in the form of LPs. Solving with Gurobi. Called by 'VarLower_vs_Baseline.py'.
 * **Bilevel_BigM.py**: Formulation of the bilevel problem with KKTs and big-M. Solving with Gurobi. Called by 'VarLower_vs_Baseline.py'.
  * **DCOPF.py**: DCOPF formulation and solving with Gurobi (feasibility check). Called by 'VarLower_vs_Baseline.py'.
 
## Environment
The environment used to develop this code is: Python (3.7.7, miniconda 4.7.12). (pickle, time, random, os.path, csv, ast, math
The notable additional packages are:
* Scikit-learn (0.22.1)
* [Gurobi](https://www.gurobi.com/) (requires a license)
* Pandas (1.0.5)
* Numpy (1.19.1)
* Matplotlib (3.2.2)
* Seaborn (0.10.1)
For the other packages, refer to the list of imported packages at the beginning of each code file.
