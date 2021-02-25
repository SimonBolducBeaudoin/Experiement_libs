#!/bin/env/python
#! -*- coding: utf-8 -*-

from    scipy.optimize import leastsq
import  scipy.odr as odr  
import  numpy

####################
# User inputs Utilities #
####################

def yes_or_no(question,default_ans='y'):
    while "the answer is invalid":
        reply = str(raw_input(question+' (y/n):').encode('utf-8')).lower().strip() or default_ans
        if reply[:1] == 'y':
            return True
        elif reply[:1] == 'n':
            return False
        else :
            return True if default_ans=='y' else False

####################
# math Utilities #
####################

def lin_to_dB(x):
    return 10*log10(x)

def dB_to_lin(x):
    return 10.0**(x/10.0)
    
def fourier_transform(F,dt):
    """
    This gives and approximation of F(f) or fourier transform of F(t) if you prefer
    and is not directly the DFT of F(t)    
    """
    return numpy.absolute( dt*numpy.fft.rfft(F) )
    
 
class fit:
    
    '''
    Modifier à partir de la version de Max
    
    La classe 'fit' crée un objet contenant deux méthodes de fit, soient
    fit.leastsq et fit.odr qui renvoient toutes deux le résultat dans
    fit.para avec comme erreurs fit.err. Si l'option verbose est activée
    (activée par défaut), le fit imprime à l'écran des valeurs importantes
    (dont la matrice de corrélation et chi^2).
    
    Elle s'utilise comme suit :
    def Fonction(x,P):
        return     La_fonction_de_la_variable_x_et_du_tableau_de_paramètres_p

    a = fit(ValeursDeX, ValeursDeY, ParamètresInitiaux, Fonction, xerr=ErreursEnX, yerr=ErreursEnY)
    a.leastsq() OU a.odr()

    Aussi, appeler l'objet de 'fit' correspond à appeler la fonction avec
    les paramètres stockés dans fit.para (paramètres initiaux au paramètres
    de fit)
    a(x) est absolument équivalent à Fonction(x,a.para)

    Aussi, on peut aller chercher directement les paramètres du fit en
    considérant l'objet comme un tableau:
    a[i] est absolument équivalen.let à a.para[i]

    Les classes 'lsqfit' et 'odrfit' sont absolument identiques à la classe
    'fit' (elles héritent de toutes ses méthodes et variables), sauf qu'elle
    performent la régression au moment de l'initialisation. Ainsi :
    def Fonction(x,P):
        return La_fonction_de_la_variable_x_et_du_tableau_de_paramètres_p

    a = odrfit(ValeursDeX, ValeursDeY, ParamètresInitiaux, Fonction, xerr=ErreursEnX, yerr=ErreursEnY)
    
    Todos :
        - Trouver une manière élégante de faire des paquets de fits
        - Trouver une manière élégante de faire des fits 2D
        - Déplacer dans General tools
    Bugs :
    '''
    __version__ = {'fit':0.1}
    def __init__(self,x,y,p0,f,fullo=1,xerr=None,yerr=None,verbose=True,npts=1000):
        self.x = numpy.array(x)
        if xerr is None:
            self.xerr = [1.]*len(self.x)
        else:
            self.xerr = numpy.array(xerr)
        self.y = y
        if yerr is None:
            self.yerr = [1.]*len(self.y)
        else:
            self.yerr = yerr
        self.para = p0         # Paramètres initiaux
        self.f = f        # Fonction pour la régression
        self.fullo = fullo     # 'Full output' de leastsq
        self.verbose = verbose    # Imprime des résultats importants à l'écran
        self.xFit = numpy.linspace(min(self.x),max(self.x),npts)
    # Appeler l'objet comme une fonction revient à évaluer la fonction avec les paramètres stockés dans
    # self.para (soit les paramètres du fit si celui-ci à déjà été fait)    
    def __call__(self,x=None):
        if x is None:
            x = self.xFit
        return self.f(x,self.para)
    def __getitem__(self,i):
        return self.para[i]
    def __len__(self):
        return len(self.para)
    def _residuals(self,p):
        return (self.y-self.f(self.x,p))/self.yerr
    def diff(self):
        return self.y - self.f(self.x,self.para)
    def leastsq(self):
        self.lsq = leastsq(self._residuals,self.para,full_output=self.fullo)
        if self.lsq[1] is None:
            if self.verbose: print '\n --- FIT DID NOT CONVERGE ---\n'
            self.err = None
            self.chi2r = None
            return False
        else:
            # Paramètres :
            self.para = self.lsq[0]
            self.cv = self.lsq[1]
            # Nombre d'itérations :
            self.it = self.lsq[2]['nfev'] 
            self.computevalues()
            self.err = self.sdcv*numpy.sqrt(self.chi2r)
#            self.donnee = []
#            for i in range(len(self.para)):
#                self.donnee.append(d.donnee(self.para[i],self.err[i]))
            if self.verbose:
                print self
            return True
    def fct(self,p,x):
        return self.f(x,p)
    def odr(self, **kwargs):
        self.model = odr.Model(self.fct)
        self.mydata = odr.Data(self.x,y=self.y,we=self.yerr,wd=self.xerr)
        self.myodr = odr.ODR(self.mydata,self.model,self.para)
        self.myoutput = self.myodr.run()
        self.cv = self.myoutput.cov_beta
        self.para = self.myoutput.beta
        self.computevalues()
        self.err = self.myoutput.sd_beta
#        self.donnee = []
#        for i in range(len(self.para)):
#            self.donnee.append(d.donnee(self.para[i],self.err[i]))
#        if kwargs.has_key('verbose'):
#            if kwargs['verbose']:
#                print self
#            else:
#                return
        if self.myodr.output.stopreason[0] in ['Iteration limit reached']:
            if self.verbose: print '\n --- FIT DID NOT CONVERGE ---\n'
            return False
        elif self.verbose:
            print self
            return True
    def computevalues(self):
        self.sdcv = numpy.sqrt(numpy.diag(self.cv))
        # Matrice de corrélation
        self.corrM = self.cv/self.sdcv/self.sdcv[:,None]
        self.chi2 = sum(((self.y-self.f(self.x,self.para))/self.yerr)**2.)
        # Chi^2 réduit
        self.chi2r = self.chi2/(len(self.y)-len(self.para))
    def __str__(self):
        return '\n--- FIT ON FUNCTION {} ---\n\nFit parameters are {}\nFit errors are {}\nFit covariance\n{}\nFit correlation matrix\n{}\nReduced chi2 is {}\n\n'.format(self.f.__name__,self.para,self.err,self.cv,self.corrM,self.chi2r)
class lsqfit(fit):
    def __init__(self,x,y,p0,f,fullo=1,xerr=None,yerr=None,verbose=True):
        fit.__init__(self,x,y,p0,f,fullo=fullo,xerr=xerr,yerr=yerr,verbose=verbose)
        self.leastsq()
class odrfit(fit):
    def __init__(self,x,y,p0,f,fullo=1,xerr=None,yerr=None,verbose=True):
        fit.__init__(self,x,y,p0,f,fullo=fullo,xerr=xerr,yerr=yerr,verbose=verbose)
        self.odr()

####################
# Python tricks Utilities #
####################
    
def build_array_of_objects(shape,constructor,*args,**kargs):
    A = numpy.r_[[constructor(*args,**kargs) for i in range(numpy.prod(shape))]]
    A.shape = shape
    return A

####################
# Numpy tricks #
####################

def get_index(Xs,x):
    """
    Returns the single index for wich Vdc = V
    Returns false if it doesn't exist
    """
    tmp = where(Vdc==V)[0]
    return False if tmp.size==0 else tmp[0]

def find_nearest_A_to_a(a,A):
    a = numpy.array(a)
    A = numpy.array(A)
    a_shape = a.shape
    a       = a.flatten()
    X       = numpy.empty(a.shape)
    X_idxs  = numpy.empty(a.shape,dtype=int)
    for i,x in enumerate(a) :
        index       = numpy.abs(A-x).argmin()
        X_idxs[i]   = index 
        X[i]        = A[index]
    X.shape         = a_shape
    X_idxs.shape    = a_shape
    return X , X_idxs 

def symetrize(X):
    """
        Symetrize along the last axis
    """
    return numpy.concatenate((X[...,-1:0:-1],X),axis=-1)
        
def compute_differential(X):
    """
        Returns y2-y1 
        in an array of shape (2,shape_of_X_with_a_-1_on_the_last_axis) 
        with [0,...] corresponding to the y2
        and  [1,...] corresponding to the y1
        The user can do y2-y1 afterward to get the differiential
    """
    shape           = X.shape
    shape           = (2,) + shape[:-1] + ( shape[-1]-1, )
    X_diff          = numpy.zeros(shape)
    X_diff[0,...]   = X[...,1:]
    X_diff[1,...]   = X[...,:-1]
    return X_diff
    
def cyclic_tansformation(X):
    """
        Cyclic translation of nd array
    """
    shape     = X.shape
    out       = numpy.zeros(X.size)
    flat_input = X.flatten()
    out[0:-1] = flat_input[1:]
    out[-1]   = flat_input[0]
    out.shape = shape
    return out

####################
# Matplotlib tricks Utilities #
####################    

color_list      = ['b', 'g', 'r', 'c','m','y','k']
linestyle_list  = ['-','--','-.',':']
marker_list     = ['*','+','x','o','.','D','s',',','v','^','<','>','1','2','3','4']  

def gen_cycler(**options):
    return cycler(color=color_list[:4],linestyle=linestyle_list[:4],marker=marker_list[:4])

"""
    See :
    Executing modules as scripts
    https://docs.python.org/3/tutorial/modules.html
"""
if __name__ == "__main__":
    import sys
    fib(int(sys.argv[1]))
  