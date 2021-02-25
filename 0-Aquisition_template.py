#!/bin/env/python
#! -*- coding: utf-8 -*-

###################
## General imports ##
###################

from    matplotlib.pyplot       import plot, xlabel, ylabel, axis, hist, figure, show,  axis, subplots, xlim, ylim, title, semilogx, legend, savefig 
from    mpl_toolkits.mplot3d    import axes3d, Axes3D 
import  numpy
import  itertools
import  os

###################
## Options  ##
###################

test                = False 
runtime_debug       = False
save_data           = True
load_data           = False
short_experiment    = False
verbose             = False
aquisition          = True 
save_scripts        = True if aquisition else False

if (os.environ['USERNAME']=='dphy-reuletlab') :
    python_2_7_scripts_root = "C:\\Projets\\Time_Domain_Optic\\Python_2_7"
else :# (os.environ['USERNAME']=='Sous-sol') :
    python_2_7_scripts_root = "C:\\Users\Sous-sol\\Desktop\\CODES\\Python_2_7"
os.chdir(python_2_7_scripts_root)   

exp_dir = 'Default'

# this as to be a list of tuple to preserve order
pyhegel_tools_local_dependencies = [
    ('SII_aCorr' , '..\\SII_aCorr\\Pyhegel_tools_local.py'),
]

#########################################################
## Set current dit / path and / initialize save folder ##
#########################################################

from Scripts_utitilities import *
scripts,paths = set_exp_environment(python_2_7_scripts_root,exp_dir=exp_dir,test=test)

if aquisition : make_dir( paths['saves'] )  # Tell to pyhegel to make the saves directory and to save data there. This is pyhegel specific cannot put into module ... 

scripts.update(pyhegel_tools_local_dependencies)

###################
## Custom imports ##
###################

from General_tools import *
from Experiment import * 
from Experiment_helper import *

# C++ bindings
# if aquisition : from acorrs_otf import * 
# if aquisition : from time_quadratures import * 
# if aquisition : from histograms import * 
# if aquisition : from special_functions import * 

########################
## LOAD PYHEGEL TOOLS ##
########################
""" 
Pyhegel functions and virtual instruments(depend on plotting functions)
"""
execfile(paths['pyhegel_wrappers'])             # TODO convert to module
for k,_ in pyhegel_tools_local_dependencies :   # I dont think this can be done in a function ?
    execfile(scripts[k])
execfile(scripts['pyhegel_tools_local']) 

#################
## SCRIPT COPY ##
#################
"""
    Save all script into paths['saves']
"""
if save_scripts : save_all_scripts(paths,scripts)

#############################
## EXPERIMENTAL PARAMETERS ##
#############################

# execfile(scripts['parameters']) # Is this necessary anymore ?

# Kernels params
l_kernel = (1<<8) + 1 

# Acquisition params
dt = 0.03125 

# Guzik params
gain_dB = 9.0

# SWEEP PARAMETERS

if short_experiment :
    Vdc = r_[linspace(0.1,1.2,3)[:-1],linspace(1.2,4,3)]
else :
    Vdc = r_[linspace(0.1,1.2,6)[:-1],linspace(1.2,4,5)]

options = {'test':test,'verbose':verbose}

if not load_data :
    device_options      = {'debug':runtime_debug}
    yoko                = Yoko_wrapper(**device_options)
    conditions          = (n_measures,Vdc,)
    devices             = (yoko,)     
    SII_mes             = SII_aCorr(conditions,devices,**options)
    SII_mes.measure()
    SII_mes.update_analysis()
    if save_data : SII_mes.save_data(paths['saves'])
    
    data                = SII_mes.get_data_dict()
    SII_anal            = SII_anal(conditions,data,**options)
    SII_anal.update_analysis()
    if save_data : SII_anal.save_data(paths['saves'])
else :
    data_folder = paths['pwd'] +'\\20-11-13_10h27' if not(test) else paths['experiments_root'] +'\\TEST'
    filename    = 'data_20-11-16_09h26.npz'
    SII_anal    = SII_anal.load_data(data_folder,filename)

