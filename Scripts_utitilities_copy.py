#!/bin/env/python
#! -*- coding: utf-8 -*-

import  sys, os, platform
import time

def Copy_script(path_original,path_copy):
    """
    Missing reference...
    example :
    path_original = C:\\Projets\\Time_Domain_Optic\\Time_domain\\Python\\5-Experiments\\PQsVsVDC\\PQsvsVDC.py
    path_copy = C:\\Projets\\Time_Domain_Optic\\Time_domain\\Python\\5-Experiments\\TEST\\PQsvsVDC.py
    """
    with open(path_original, 'r') as f:
        with open(path_copy, 'w') as out:
            for line in (f.readlines()):
                out.write(line)
                    
def save_all_scripts(paths,scripts) :
    for value in scripts.values():
        Copy_script( paths['scripts']+os.sep+value , paths['saves']+os.sep+value)

def gen_exp_default_paths(python_2_7_scripts_root,exp_dir,**options):
    """
        Contient l'information de ma structure de fichier
    """     
    _test_dir   = "TEST"
    # Default arguments
    test        = options.get('test',True)
    paths = \
    {
        ### MODIFY ###
        '_experiments_root'     : "5-Experiments",                  # Relative to python_scripts_root
        '_current_experiment'   : exp_dir,                          # Relative to experiments_root
        '_lib'                  : "lib",                            # Relative to python_scripts_root
        '_pyhegel_wrappers'     : "Pyhegel_wrappers.py",               # Relative to _lib
        '_test_dir'             : _test_dir,                        # Relative experiments_root
        '_saves'                : time.strftime('%y%m%d-%H%M'),     # Relative to pwd/current_experiment or Test
        'mingw_binaries'        : 'C:\\cygwin64\\usr\\x86_64-w64-mingw32\\sys-root\\mingw\\bin' 
    }
    paths['python_scripts_root']= python_2_7_scripts_root
    paths['experiments_root']   = paths['python_scripts_root']  + os.sep + paths['_experiments_root']  
    paths['current_experiment'] = paths['experiments_root']     + os.sep + paths['_current_experiment']  
    paths['custom_libraries']   = paths['python_scripts_root']  + os.sep + paths['_lib'] # Where My .pyd are
    paths['pyhegel_wrappers']      = paths['python_scripts_root']  + os.sep + paths['_lib'] + os.sep + paths['_pyhegel_wrappers']
    paths['scripts']            = paths['experiments_root']     + os.sep + paths['_current_experiment'] 
    paths['pwd']                = paths['current_experiment'] 
    paths['test']               = paths['experiments_root']     + os.sep + paths['_test_dir']
    if test :
        paths['saves'] = paths['test']
    else :
        paths['saves'] = paths['pwd']+ os.sep + paths['_saves']
    return paths
        
def gen_exp_default_scripts():
    """
        Les scripts par default d'une experience
    """     
    scripts = \
    {
        'aquisition'            : '0-Aquisition.py',
        'pyhegel_tools_local'   : 'Pyhegel_tools_local.py',
    }
    return scripts
    
def set_exp_environment(python_2_7_scripts_root,exp_dir,**options):
    """
    Todos : 
        - __doc__
        -
    """        
    paths = gen_exp_default_paths(python_2_7_scripts_root,exp_dir,**options)
    scripts = gen_exp_default_scripts()
    os.chdir(paths['pwd'])
    if paths['custom_libraries'] not in sys.path :
        sys.path.append(paths['custom_libraries'])
    if ( platform.system() == 'Windows' ) and ( paths['mingw_binaries'] not in os.environ['PATH'] ) :
        os.environ['PATH'] = paths['mingw_binaries']+os.path.pathsep+os.environ['PATH']
    return scripts,paths    
    