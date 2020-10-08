# -*- coding: utf-8 -*-
"""
Created on Tue Feb 25 13:35:54 2020

@author: emapr
"""
from sklearn.tree import DecisionTreeClassifier
from sklearn.model_selection import train_test_split
from sklearn import metrics
import numpy as np
from sklearn.model_selection import RandomizedSearchCV
import pickle

###########################DATA####################################################################

def DT(nodes,load_nodes,n_bus,mode,leaf,feat,depth,min_sp_leaf,min_sp_split, X_train, y_train, name):
    
    #Separation of test and training
    #Split dataset into training set and test set
    X_train, X_test, y_train, y_test = train_test_split(X_train, y_train, test_size=0.3) # 70% training and 30% test
    y_test=np.array(y_test)
    classes = np.unique(y_train) # Name of the possible classes
    
    ###################################################################################################
    
    ############################### HYPERPARAMETERS CHOICE ###############################
    
    if mode == 0:
        
        # Maximum number of levels in tree
        max_depth = [int(x) for x in np.linspace(5, 20, num = 10)]
        max_depth.append(None)
        # Minimum number of samples required to split a node
        min_samples_split = [2,4,5]
        # Minimum number of samples required at each leaf node
        min_samples_leaf = [2,4,5]
        # Number of features to consider at every split
        max_features = [None]
        # Maximum number of leaves in tree
        max_leaf_nodes = [int(x) for x in np.linspace(2, 500, num = 10)]
        max_leaf_nodes.append(None)
        
        # Create the random grid
        parameters = {'max_depth': max_depth,
                      'min_samples_split': min_samples_split,
                      'min_samples_leaf': min_samples_leaf,
                      'max_features': max_features,
                      'max_leaf_nodes':max_leaf_nodes}
        
        # Use the random grid to search for best hyperparameters
        # First create the base model to tune
        dt = DecisionTreeClassifier()
        # Random search of parameters, using 5 fold cross validation, 
        # search across 100 different combinations, and use all available cores
        dt_random = RandomizedSearchCV(estimator = dt, param_distributions = parameters, n_iter = 100, n_jobs = -1, cv = 5, verbose = 2)
        # Fit the random search model
        dt_random.fit(X_train, y_train)
        
        print('----------------------------------------')
        print('The best parameters for {} are:'.format(name))
        print(dt_random.best_params_)
        
        #Predict the response for test dataset
        y_pred = dt_random.best_estimator_.predict(X_test)
        
        # Model Accuracy, how often is the classifier correct?
        print("Accuracy:",metrics.accuracy_score(y_test, y_pred))
        print('----------------------------------------')
    
    ############################### CLASSIFIER ###############################
    
    elif mode == 1:
        
        clf = DecisionTreeClassifier(min_samples_split=min_sp_split, min_samples_leaf=min_sp_leaf,max_features=feat, max_depth=depth,max_leaf_nodes=leaf)
        
        # Train Decision Tree Classifer
        clf = clf.fit(X_train,y_train)
        
        # Predict the response for test dataset
        y_pred = clf.predict(X_test)
        
        n_nodes = clf.tree_.node_count
        children_left = clf.tree_.children_left
        children_right = clf.tree_.children_right
        feature = clf.tree_.feature
        threshold = clf.tree_.threshold
        value = clf.tree_.value
        leave_id = clf.apply(X_test)
        
        # Including the information from the parent node
        predictions_parent=[]
        
        for x in range(len(X_test)):
            
            parent=None
            for left in range(len(children_left)):
                if leave_id[x] == children_left[left]:
                    parent = left
                    break
            if parent == None:
                for right in range(len(children_right)):
                    if leave_id[x] == children_right[right]:
                        parent = right
                        break
            
            outputs=[]
            value_parent=value[parent,0,:]
            
            if parent == None:
                value_parent=value[0,0,:]
                        
            for v in range(len(value_parent)):
                if value_parent[v] > 2:
                    outputs.append(classes[v])
            outputs.sort()
            predictions_parent.append(outputs)
            
        acc_dt = 0
        acc_parent = 0
        
        for y in range(len(y_test)):
            if y_test[y] == y_pred[y]:
                acc_dt += 1
            if y_test[y] in predictions_parent[y]:
                acc_parent += 1
        
        acc_dt = ( acc_dt / len(y_test) ) * 100
        acc_parent = ( acc_parent / len(y_test) ) * 100
        
        print('{} :'.format(name))
        print('Parameters DT: \n - min_samples_split = {} \n - min_samples_leaf = {} \n - max_features = {} \n - max_depth = {} \n - max_leaf_nodes = {}'.format(min_sp_split,min_sp_leaf,feat,depth,leaf))
        print("Accuracy DT : {}%".format(acc_dt))
        print("Accuracy parent: {}%".format(acc_parent))
        print('----------------------------------------')
        
        # Export of the decision tree
        f = open('{}.pkl'.format(name),'wb')
        pickle.dump(clf,f)
        f.close()
        
        # Export of the classes
        f = open('Classes_{}.pkl'.format(name),'wb')
        pickle.dump(classes,f)
        f.close()
    
        return n_nodes, children_left, children_right, feature, threshold
        
