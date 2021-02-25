#!/bin/env/python
#! -*- coding: utf-8 -*-

import  scipy.constants         as const
import  time
import  numpy
from    math                    import pi

from General_tools              import *

from time_quadratures           import TimeQuad_uint64_t

#############
# Statics   #
#############

_e      = const.e # Coulomb
_h      = const.h # Joule second
_kb     = const.Boltzmann # J/K (joules per kelvin)


#######################
# Static only classes #
#######################

class Tunnel_junction(object):
    """
       This class embeds the logic associated with the tunnel junction
       It contains usefull static methods
        Todos : 
            - Add imperfections in the junciton parasitic capacitance ect.
            - Add photoexcitation behavior
            - Add a mechanism/wrapper to fix some of the variables in the model 
                return something compatible with class fit
        Bugs :
    """
    __version__     = { 'Tunnel_junction'  : 0.3 }
    def __init__(self,R_jct):
        self.R_jct = R_jct
    @staticmethod
    def coth(x):
        """ Not defined in numpy """
        return 1.0/numpy.tanh(x)
    @staticmethod
    def cothc(x):
        """ x*coth(x) """
        ret             = x/numpy.tanh(x)
        ret[isnan(ret)] = 1.
        return ret
    @staticmethod
    def Vsquare_to_K(SII,Z_jct,freq_pos_only=True):
        """ 
        Converts from V**2/Hz to Kelvin
        Si on replie les fréquences negatives sur les fréquences positives 
        on prend le facteur 1/2k (i.e. l'abscisse n'existe pas sur les fréquence negative)
        Sinon on prend 1/4K
        """
        if freq_pos_only :
            return SII/(2.0*Z_jct*_kb)
        else :
            return SII/(4.0*Z_jct*_kb)
    @staticmethod
    def K_to_Vsquare(SII,Z_jct,freq_pos_only=True):
        """ 
        Converts from Kelvin to V**2/Hz
        """
        if freq_pos_only :
            return (2.0*Z_jct*_kb)*SII
        else :
            return (4.0*Z_jct*_kb)*SII
    @staticmethod
    def _to_K(SII,Te):
        """
        Converts a SII with no unit to Kelvin
        """
        return Te*SII
    @staticmethod
    def _to_Vsquare(SII,Z_jct,Te,freq_pos_only=True):
        """
        Converts a SII with no unit to V**2/Hzl
        """
        if freq_pos_only :
            return (2.0*Z_jct*_kb*Te)*SII
        else :
            return (4.0*Z_jct*_kb*Te)*SII
    @staticmethod
    def SII_eq(E,Te):
        """
        sans unité
        Use _to_Vsquare to convert to V**2/Hz
        Use _to_        to convert to K   /Hz
        """
        return Tunnel_junction.cothc(E/(2.0*_kb*Te))
    @staticmethod
    def V_th(f,Te=0.0,**options):
        """
            Return the V_th for which e*V_th =  h f
                when given a temperature 
                and setting using converged = True
                it return the V_th for which SII_eq as reached as an error of 1%
                with respect to its asymptote
        """
        cst = 2.65 # coth(cst) = 1.01
        if options.get('converged'):
            return max([  abs( cst*2.0*_kb*Te - _h*f ) ,  abs( cst*2.0*_kb*Te + _h*f ) ])/_e
        else :
            return _h*f/_e
    @staticmethod
    def SII_eq_Vsquare(E,R,Te,freq_pos_only=True):
        """
        [V**2/Hz]
        computes
         if freq_pos_only==True
            R 2kT (E/2kT) coth(E/2kT) ==   R E coth(E/2kT)
         else
            R 4kT (E/2kT) coth(E/2kT) == 2 R E coth(E/2kT)
        """
        Seq     =  Tunnel_junction.SII_eq(E,Te)
        return Tunnel_junction._to_Vsquare(Seq,R,Te,freq_pos_only)
    @staticmethod
    def SII_dc(V,f,Te):
        """
        sans unité
        Use _to_Vsquare to convert to V**2/Hz
        Use _to_        to convert to K   /Hz
        """
        eV,hf   = numpy.meshgrid(_e*V,_h*f,indexing='ij')
        SII_eq  = Tunnel_junction.SII_eq
        return (SII_eq(eV-hf,Te)+SII_eq(eV+hf,Te))/2.0
    @staticmethod
    def SII_dc_Vsquare(V,f,Te,R,freq_pos_only=True):
        """
        sans unité
        Use _to_Vsquare to convert to V**2/Hz
        Use _to_        to convert to K   /Hz
        """
        sii     = Tunnel_junction.SII_dc(V,f,Te)
        return Tunnel_junction._to_Vsquare(sii,R,Te,freq_pos_only)
    @staticmethod
    def SII_dc_K(V,f,Te):
        """
        sans unité
        Use _to_Vsquare to convert to V**2/Hz
        Use _to_        to convert to K   /Hz
        """
        sii     = Tunnel_junction.SII_dc(V,f,Te)
        return Tunnel_junction._to_K(sii,Te)
    @staticmethod
    def fit_model_SII_dc_Vsquare(V,f,Te,R_jct,G,b,freq_pos_only=True):
        """
        Model for SII [V**2/Hz] with dc polarisation only
        A constant parameter "b" is added and a gain parameter "G"
        """
        return G*(Tunnel_junction.SII_dc_Vsquare(V,f,Te,R_jct,freq_pos_only)[:,0]) + b
    @staticmethod
    def _decorator_fix_f_R(f,R_jct,func,freq_pos_only=True):
        """
            Returns a fit model with f and R fixed
        """
        def out(V,(Te,G,b)):
            return func(V,f,Te,R_jct,G,b,freq_pos_only)
        return out
    @staticmethod
    def _decorator_fix_f_R_b(f,R_jct,b,func,freq_pos_only=True):
        """
            Returns a fit model with f and R fixed
        """
        def out(V,(Te,G)):
            return func(V,f,Te,R_jct,G,b,freq_pos_only)
        return out

class Three_points_polarisation(object):
    """
       This class embeds the logic associated with 3 points measurment/polarisation
       (Voltmeter)      (Vdc)
       |                  |  
       |                 (R_pol) == 1MOhm : polarisation resistance
       |                  | 
       ----------|---------
                 |
                (R_s) : sample resistance
                 |
                (R_grnd) : ground/parasitic resistance
                 |
                ---
                 -
        Todos : 
            - Add imperfections in the junciton parasitic resistance capacitance ect.
            - Add photoexcitation behavior
        Bugs :
    """
    __version__     = { 'Three_points_polarisation'  : 0.1 }
    def __init__(self,R_s,R_pol):
        self.R_s    = R_s
        self.R_pol  = R_pol
        # self.R_grnd = R_grnd
    @staticmethod
    def compute_V_sample(Vdc,R_s,R_pol):
        return Vdc*R_s/(R_pol+R_s)
    @staticmethod
    def compute_I_sample(Vdc,R_pol):
        return Vdc/R_pol

class moments_cumulants_helper():
    __version__     = { 'moments_cumulants_helper'  : 0.1 }
    @staticmethod
    def compute_s0_square_s1_square_sample(C4_0_sample,C4_1_sample,C4_0_and_1_sample,mu_01_square_sample=0.0):
        """
        (see Notes Bertrand n1n2 vs cumulants.pdf for details)
        Returns <<s0**2s1**2>>_sample = <<s0**2s1**2>>(V) - <<s0**2s1**2>>(V=0) 
        
        For a signal like
            p_i = s_i + a 
                where p_i is the signal after amplification
                s_i is the sample signal
                a is the signal added by the amplifications
                
        Notation :
            <<X^n>>(V) =  <<X^n>>_sample + <<X^n>>_0
        
        C4_0_sample         = <<p_0^4>>(V) - <<p_0^4>>(0)
        C4_0_and_1_sample   = <<p_0^4 + p_1^4>>(V) - <<p_0^4 + p_1^4>>(0)
        mu_01_square_sample = <s_0s_1>**2(V) - <s_0s_1>**2(V=0)
        
        For any two centered statistical variables p_0 and p_1
        we have :
            6*<<s0**2s1**2>>_sample 
        =   <<p_0+p_1)^4>>_sample  - <<p_0^4>>_sample - <<p_1^4>>_sample + 2 mu_01_square_sample
        If p_0 and p_1 are statistically independent then mu_01_square_sample = 0 hence the default value 
        """
        return (1.0/6.0)*(C4_0_and_1_sample-C4_0_sample-C4_1_sample + 2.0*mu_01_square_sample) 

class Ns_helper(object):
    """
        Puts together a bunch of static methods that are used to compute 
        ns from O1 moments
        
        Assuming moments have the shape 
            (ordre,kernel index, ...)   
            where ... are the experimental conditions 
            either (vdc) or (vdc,temperatures)
            <Ordre>
              0       <q>
              1       <q**2>
              2       <q**4>
              3       <q**8>
    """
    __version__     = { 'Ns_helper'  : 0.5 }
    __version__.update(Three_points_polarisation.__version__)   
    @staticmethod  
    def compute_errors(moments,n):
        shape = (moments.shape[0]-1,)
        shape += moments.shape[1:]
        errors = numpy.zeros(shape,dtype=float) 
        errors[:,...] = Analysis.SE(moments[1:,...],moments[0:-1,...],n)
        return errors
    @staticmethod
    def compute_cumulants(moments):
        shape = (moments.shape[0]-1,)
        shape += moments.shape[1:]
        cumulants           = numpy.zeros( shape ,dtype=float)
        cumulants[0,...]    = moments[0,...] 
        cumulants[1,...]    = moments[1,...] 
        cumulants[2,...]    = moments[2,...]     - 3.0*(moments[1,...] + 0.5 )**2  # <p**4> -3 <p**2> **2
        return cumulants
    @staticmethod
    def compute_cumulants_std(moments,moments_std):
        shape = moments_std.shape
        cumulants_std           = numpy.zeros( shape ,dtype=float)
        cumulants_std[0,...]    = moments_std[0,...] 
        cumulants_std[1,...]    = moments_std[1,...] 
        cumulants_std[2,...]    = moments_std[2,...] - 6.0*(moments[1,...] + 0.5 )*(moments_std[1,...])  # <p**4> -3 <p**2> **2
        return cumulants_std
    @staticmethod
    def compute_C4(cumulants_sample):
        C4 = numpy.empty( cumulants_sample[0,...].shape ,dtype=float) 
        C4[...] = cumulants_sample[2,...] 
        return C4 
    @staticmethod
    def compute_ns(cumulants_sample):
        """
            0 : <n>
            1 : <n**2>
            2 : <dn**2>
            3 
        """
        n_kernels   = cumulants_sample.shape[1]
        ns          = numpy.empty((4,n_kernels,cumulants_sample.shape[-1]),dtype=float)
        ns[0,...]   = cumulants_sample[1,...] 
        ns[1,...]   = (2.0/3.0)*cumulants_sample[2,...] + 2.0*cumulants_sample[1,...]**2 - cumulants_sample[1,...] 
        ns[2,...]   = (2.0/3.0)*cumulants_sample[2,...] +     cumulants_sample[1,...]**2 
        ns[3,...]   = ns[2,...]/ns[0,...]
        return ns
    @staticmethod
    def compute_n0n1_sample(C4_0_sample,C4_1_sample,C4_0_and_1_sample):
        """
            Returns <<n0n1>>(V) - <<n0n1>>(V=0)
            
            Notes :
            (see Notes Bertrand n1n2 vs cumulants.pdf for details)
            
            Here I assume that
            the combination is s_0 and s_1 is of the form
            s_tot = (s_0+s_1)/sqrt(2)
            thefore 
            C4_0_and_1_sample mus be *4.0 to get the right definition
            to fit with moments_cumulants_helper.compute_s0_square_s1_square_sample
        """
        return moments_cumulants_helper.compute_s0_square_s1_square_sample(C4_0_sample,C4_1_sample,4.0*C4_0_and_1_sample)
    @staticmethod
    def linear_fit_of_C4(n,C4,V_jct,V_th):
        # V_th : threshold above which eV>>hf
        C4 = C4[:,V_jct>V_th] 
        n  = n[:,V_jct>V_th] 
        fit_params = numpy.zeros((2,n.shape[0])) 
        for i,(nn,cc) in enumerate(zip(n,C4)) :
            try :
                fit_params[:,i] = numpy.polyfit(transpose(nn),transpose(cc),1)
            except numpy.linalg.LinAlgError :
                pass
        return fit_params 
    @staticmethod
    def slope_of_linear_fit_of_C4(n,C4,V_jct,V_th):
        return Ns_helper.linear_fit_of_C4(n,C4,V_jct,V_th)[0,:] 
    @staticmethod
    def gen_C4_fit_vector(n,C4,V_jct,V_th):
        fit_params = Ns_helper.linear_fit_of_C4(n,C4,V_jct,V_th)
        a = fit_params[0,:]
        b = fit_params[1,:]
        return n*a[:,None] + b[:,None] 
    @staticmethod
    def compute_ns_corrected(ns,cumulants_sample,Vdc_source,R_jct,R_1M,V_th):
        C4      = Ns_helper.compute_C4(cumulants_sample) 
        V_jct   = Three_points_polarisation.compute_V_sample(Vdc_source,R_jct,R_1M)
        n       = cumulants_sample[1,...]
        a       = Ns_helper.slope_of_linear_fit_of_C4(n,C4,V_jct,V_th)
        ns_corr = numpy.empty((ns.shape),dtype=float)    
        ns_corr[0,...] = n 
        ns_corr[1,...] = (2.0/3.0)*(cumulants_sample[2,...]- a[:,None]*n) + 2.0*n**2 - n 
        ns_corr[2,...] = (2.0/3.0)*(cumulants_sample[2,...]- a[:,None]*n) +     n**2 
        ns_corr[3,...] = ns[2,...]/n 
        return ns_corr  
    @staticmethod
    def compute_ns_std(ns,cumulants_sample,cumulants_sample_std):
        n_kernels = cumulants_sample.shape[1]
        ns_std = numpy.empty((4,n_kernels,cumulants_sample_std.shape[-1]),dtype=float)
        ns_std[0,...] = (cumulants_sample_std[1,...])
        ns_std[1,...] = (2.0/3.0)*cumulants_sample_std[2,...] + 4.0*cumulants_sample_std[1,...]*cumulants_sample[1,...] - cumulants_sample_std[1,...]
        ns_std[2,...] = (2.0/3.0)*cumulants_sample_std[2,...] + 2.0*cumulants_sample_std[1,...]*cumulants_sample[1,...] 
        ns_std[3,...] = ns_std[2,...]/ns[0,...]   + ns[2,...]*(ns_std[0,...]/ns[0,...]**2)
        return ns_std       

class Quads_helper(object):
    """
        Help to generate inputs for the constructor
            gen_xxx_info()
        Todos : 
            - Could this class be made stand alone like Tunnel_junction 
               to simplify inheritance tree ?
               - All super case must be eximined
               - The way meta_info is constructed must be studied
               - It might cause inheritance problem
               - others...
        Bugs :
    """
    __version__ = {'Quads_helper': 0.4}
    __filters__ = {'gauss':0,'bigauss':1,'flatband':2}
    """
        Public
    """
    @staticmethod
    def gen_t_abscisse(l_kernel,dt):
        t=arange(l_kernel/2+1)*dt
        return numpy.concatenate((-t[-1:0:-1],t))
    @staticmethod
    def gen_f_abscisse(l_kernel,dt):
        return numpy.fft.rfftfreq(l_kernel,dt)
    @staticmethod
    def gen_l_hc(l_kernel):
        return l_kernel//2+1 
    @staticmethod
    def gen_quads_info(l_kernel,alpha,filters_info,kernel_conf=0):
        l_kernel    = int(l_kernel)
        l_hc        = Quads_helper.gen_l_hc(l_kernel)
        kernel_conf = int(kernel_conf)
        return {'l_kernel':l_kernel,'l_hc':l_hc,'alpha':alpha,'filters_info':filters_info,'kernel_conf':kernel_conf}
    @staticmethod
    def gen_filter_info(gauss_info,bigauss_info,flatband_info):
        """
            todos :
                - make it work for any number of inputs ?
        """
        filter_info             = {'gauss':gauss_info,'bigauss':bigauss_info,'flatband':flatband_info}
        filter_info['labels']   = Quads_helper._gen_labels(filter_info)
        filter_info['gauss']['slice'],filter_info['bigauss']['slice'],filter_info['flatband']['slice'] = Quads_helper._gen_filters_slices(filter_info)
        filter_info['strides']  = Quads_helper._gen_filters_strides(filter_info)
        filter_info['lengths']  = Quads_helper._get_filters_len(filter_info)
        filter_info['length']   = numpy.array(filter_info['lengths']).sum()
        return filter_info
    @staticmethod
    def gen_gauss_info(fs,dfs,snap_on=True): 
        """
            bigauss_indexes is a n by 1 array
            fs[0] = f_0, # central frequencie of the gaussian
            fs[1] = ...
            dfs.shape == fs.shape
        """
        fs  = numpy.array(fs)
        if fs.size == 0 : # the array is empty
            return {'fs':numpy.array([]),'dfs':numpy.array([]),'snap_on':snap_on}
        else: 
            dfs = numpy.array(dfs)
            if dfs.size == 1 :  # all the same df
                dfs = dfs*numpy.ones(fs.shape)  
            gauss_info              = {'fs':fs,'dfs':dfs,'snap_on':snap_on}
        gauss_info['labels']    = Quads_helper._gen_gauss_labels   (gauss_info) 
        return gauss_info
    @staticmethod
    def gen_bigauss_info(fs,dfs,snap_on=True):
        """
            bigauss_indexes is a n by 2 array
            fs[0,:] = f_0, f_1 # central frequencies of the first and seconde gaussian
            fs[1,:] = ...
        """
        fs  = numpy.array(fs)
        if fs.size == 0 : # the array is empty
            bigauss_info = {'fs':numpy.array([]),'dfs':numpy.array([]),'snap_on':snap_on}
        else :
            dfs = numpy.array(dfs)
            if dfs.size == 1 :  # all the same df
                dfs = dfs*numpy.ones(fs.shape)
            bigauss_info            = {'fs':fs,'dfs':dfs,'snap_on':snap_on}
        bigauss_info['labels']  = Quads_helper._gen_bigauss_labels (bigauss_info)
        return bigauss_info
    @staticmethod
    def gen_flatband_info(fs,rise,fall,snap_on=True):
        """
            fs[0,:]         = f_0, f_1 # central frequencies of the first and seconde gaussian
            fs[1,:]         = ...
            rise_fall[0,:]  = rise, fall
            rise_fall[1,:]  = ...
        """
        fs  = numpy.array(fs)
        if fs.size == 0 : # the array is empty
            flatband_info = {'fs':numpy.array([]),'rise_fall':numpy.array([]),'snap_on':snap_on}
        else :
            rise_fall = numpy.zeros(fs.shape)
            rise_fall[:,0] = rise
            rise_fall[:,1] = fall
            flatband_info  = {'fs':fs,'rise_fall':rise_fall,'snap_on':snap_on}
        flatband_info['labels'] = Quads_helper._gen_flatband_labels(flatband_info)
        return flatband_info
    @staticmethod
    def gen_Filters(l_kernel,dt,filter_info):
        """
            todos :
                - make it work for any number of inputs ?
        """
        Filters_gauss                           = Quads_helper.gen_gauss_Filters   (l_kernel,dt,filter_info['gauss']   )
        Filters_bigauss                         = Quads_helper.gen_bigauss_Filters (l_kernel,dt,filter_info['bigauss'] )
        Filter_flatband                         = Quads_helper.gen_flatband        (l_kernel,dt,filter_info['flatband'])
        return Quads_helper._concatenate_Filters(Filters_gauss,Filters_bigauss,Filter_flatband)
    @staticmethod
    def gen_gauss_Filters(l_kernel,dt,gauss_info):
        fs , dfs    = Quads_helper._extract_gauss_info(gauss_info)
        snap_on     = Quads_helper._checks_snap_on(**gauss_info)
        if fs.size == 0 :
            return numpy.array([])
        if snap_on :
            F   = Quads_helper.gen_f_abscisse(l_kernel,dt)
            fs,_  = find_nearest_A_to_a(fs,F)
            gauss_info['fs'] = fs # Modifying the dict
        Filters = numpy.empty( (len(fs),l_kernel//2+1) , dtype=complex , order='C' ) 
        for i,(f,df) in enumerate(zip(fs,dfs)):
            Filters[i,:] = Quads_helper.Gaussian_filter_normalized( f , df , l_kernel, dt )
        return Filters  
    @staticmethod
    def gen_bigauss_Filters(l_kernel,dt,bigauss_info):
        fs , dfs    = Quads_helper._extract_bigauss_info(bigauss_info)
        snap_on     = Quads_helper._checks_snap_on(**bigauss_info)
        if fs.shape[1] !=2 :
            raise Exception('bigauss_indexes needs to be n by 2.')
        if fs.size == 0 :
            return numpy.array([])
        if snap_on :
            F   = Quads_helper.gen_f_abscisse(l_kernel,dt)
            fs,_  = find_nearest_A_to_a(fs,F)
            bigauss_info['fs'] = fs # Modifying the dict
        Filters =  numpy.empty( (fs.shape[0],l_kernel//2+1) , dtype=complex , order='C' ) 
        for i,(f,df) in enumerate(zip(fs,dfs)) :
            Filters[i,:] = Quads_helper._Bi_Gaussian_filter_normalized(f[0],f[1],df[0],df[1],l_kernel,dt) 
        return Filters
    @staticmethod
    def gen_flatband(l_kernel,dt,flatband_info):
        l_hc            = Quads_helper.gen_l_hc(l_kernel)
        fs,rise_fall    = Quads_helper._extract_flatband_info(flatband_info)
        if fs.size ==0 :
            return numpy.array([])
        Filters     = numpy.empty( (fs.shape[0],l_hc),dtype=complex,order='C' ) 
        for i,(flat,r_f) in enumerate(zip(fs,rise_fall)) :  
            Filters[i,:]    = TimeQuad_uint64_t.compute_flatband(l_hc,dt,flat[0]-r_f[0],flat[0],flat[1],flat[1]+r_f[1])
        return Filters
    """
        Private
    """
    @staticmethod
    def _checks_snap_on(**options):
        return options['snap_on'] if 'snap_on'  in options else True
    @staticmethod
    def _extract_filter_info(filter_info):
        return filter_info['gauss'],filter_info['bigauss'],filter_info['flatband'],
    @staticmethod
    def _extract_gauss_info(gauss_info): 
        return gauss_info['fs'] , gauss_info['dfs']
    @staticmethod
    def _extract_bigauss_info(bigauss_info):
        return Quads_helper._extract_gauss_info(bigauss_info)
    @staticmethod
    def _extract_flatband_info(flatband_info): 
        return flatband_info['fs'],flatband_info['rise_fall'] 
    @staticmethod
    def _get_filters_len(filter_info):
        gauss_info,bigauss_info,flatband_info = Quads_helper._extract_filter_info(filter_info)
        fs_g,_          =   Quads_helper._extract_gauss_info(gauss_info)
        fs_bg,_         =   Quads_helper._extract_bigauss_info(bigauss_info)
        fs_fb,_         =   Quads_helper._extract_flatband_info(flatband_info)
        return fs_g.shape[0],fs_bg.shape[0],fs_fb.shape[0]
    @staticmethod
    def _gen_filters_strides(filter_info):
        l_g,l_bg,l_fb       = Quads_helper._get_filters_len(filter_info)
        gauss_stride        = 0
        bigauss_stride      = gauss_stride   + l_g
        flatband_stride     = bigauss_stride + l_bg
        return (gauss_stride,bigauss_stride,flatband_stride)
    @staticmethod
    def _gen_filters_slices(filter_info):
        l_g,l_bg,l_fb   =   Quads_helper._get_filters_len(filter_info) 
        gauss_slice     =   slice(None        ,l_g            ,None)
        bigauss_slice   =   slice(l_g         ,l_g+l_bg       ,None)
        flatband_slice  =   slice(l_g+l_bg    ,l_g+l_bg+l_fb  ,None)
        return gauss_slice,bigauss_slice,flatband_slice
    @staticmethod
    def _gen_labels(filter_info):
        gauss_info,bigauss_info,flatband_info = Quads_helper._extract_filter_info(filter_info)
        return gauss_info['labels'] + bigauss_info['labels'] + flatband_info['labels']
    @staticmethod
    def _gen_gauss_labels(gauss_info,label_frmt="{:0.1f}"):
        fs , dfs    = Quads_helper._extract_gauss_info(gauss_info)
        labels = []
        for (f,df) in zip(fs,dfs) :
            label = label_frmt.format(f)
            labels.append(label)
        return labels
    @staticmethod
    def _gen_bigauss_labels(bigauss_info,label_frmt="{:0.1f}&{:0.1f}"):
        fs , dfs    = Quads_helper._extract_bigauss_info(bigauss_info)
        labels = []
        for (f,df) in zip(fs,dfs) :
            label = label_frmt.format(f[0],f[1])
            labels.append(label)
        return labels
    @staticmethod
    def _gen_flatband_labels(flatband_info,label_frmt="{:0.1f}-{:0.1f}"):
        fs,_ =Quads_helper._extract_flatband_info(flatband_info)
        labels = []
        for f in fs :
            label = label_frmt.format(f[0],f[1])
            labels.append(label)
        return labels
    @staticmethod
    def _gen_composition_indexes(filters_info,composition):
        """
            A composition has shape m,2,n
            m : composition index
            n : combinations index
            the 2nd index is for type and subindex
        """
        filter_type_indexes = composition[:,0,:]
        filter_index        = composition[:,1,:]
        strides             = filter_info['strides'] 
        kernel_indexes      = numpy.zeros(filter_index.shape)
        for i,stride in enumerate(strides):
            kernel_indexes[numpy.where(filter_type_indexes==i)] = stride
        kernel_indexes += filter_index
        return kernel_indexes.astype(int) 
    @staticmethod
    def Wave_function_of_f_normalization(Y,df):
        """
            Note that betas are given to TimeQuad c++ class are 
            normalized internally in construction and are accessible
            through TimeQuad's attributes.
            This function is for conveniance.
        """
        sum = numpy.sqrt( 2*df*(numpy.square(numpy.abs(Y))).sum() )
        return Y/(sum)
    @staticmethod
    def Gaussian (x,mu=0.0,sigma=1.0) :
        return (1.0/(sigma*numpy.sqrt(2.0*pi))) * numpy.exp( (-(x-mu)**2)/(2.0*sigma**2) )
    @staticmethod
    def Gaussian_filter_normalized(f,df,l_kernel,dt) :
        """
        Returns a numpy array of complex number corresponding to a gaussian filter
        of avg f and std dev df on positive frequencies and with vector length equal to  l_kernel//2 + 1.
        """
        l_hc = l_kernel//2+1 

        Y = numpy.empty( l_hc , dtype = complex , order='C') 
        x_f = numpy.fft.rfftfreq(l_kernel , dt)
        for i in range( l_hc ) :
            Y[i] =  Quads_helper.Gaussian ( x_f[i] , f , df ) 
        Delta_f = x_f[1]-x_f[0]
        Y = Quads_helper.Wave_function_of_f_normalization(Y,Delta_f)
        return Y 
    @staticmethod
    def _Bi_Gaussian_filter_normalized(f1,f2,df1,df2,l_kernel,dt) :
        l_hc = l_kernel//2+1 
        Y = numpy.empty( l_hc , dtype = complex , order='C') 
        x_f = numpy.fft.rfftfreq(l_kernel , dt)
        for i in range( l_hc ) :
            Y[i] =  (df1*numpy.sqrt(2.0*pi))*Quads_helper.Gaussian ( x_f[i] , f1 , df1 ) + (df2*numpy.sqrt(2.0*pi))*Quads_helper.Gaussian(x_f[i] , f2 , df2) 
        Delta_f = (x_f[1]-x_f[0])    
        Y = Quads_helper.Wave_function_of_f_normalization(Y,Delta_f)
        return Y   
    @staticmethod
    def _concatenate_Filters(*args):
        t = tuple()
        for arg in args :
            if not (arg.size==0) :
                t += (arg,)
        return numpy.concatenate( t, axis = 0 ) 
    @staticmethod
    def _moments_correction(moments,half_norms,powers):
        """
            Correcting for half normalization
            
            moments     .shape should be  (moment_index,kernel_index,...)
            half_norms  .shape should be  (kernel_index)
            powers      .shape should be  (moment_index)
        """
        powers      = numpy.array(powers)       # moment_index
        h           = numpy.array(half_norms)   # kernel index 
        shape       = moments.shape
        dim         = len(shape)
        corrections  = (h[None,:]**powers[:,None])   # moment_index , kernel_index
        exp_axis = tuple(range(2,dim)) 
        for ax in exp_axis :
            corrections = numpy.expand_dims(corrections,ax)         # shape now match moments shape
        moments_corrected = numpy.empty(moments.shape,dtype=float)  # moment_index, kernel index , cdn index
        moments_corrected = corrections * moments 
        return moments_corrected 
    @staticmethod
    def _plot_Filters( Filters , labels, ax , l_dft , dt ):
        freqs = numpy.fft.rfftfreq(l_dft,dt) 
        for i,f in enumerate(Filters) :
            ax.plot( freqs , f , label = labels[i] , marker='o') 
        ax.set_xlabel(" GHz ")
        ax.legend()
    @staticmethod
    def _plot_Kernels(ts,ks,labels,ax,dt):   
        for j in range(ks.shape[1]):
            color = next(ax._get_lines.prop_cycler)['color']
            for k in range(ks.shape[0]):
                if k==0:
                    ax.plot( ts , ks[k,j,:] , color=color , label = labels[j] ) 
                else :
                    ax.plot( ts , ks[k,j,:] , color=color , linestyle='--' ) 
        ax.set_xlabel("ns")
        ax.legend()
    @staticmethod
    def _plot_Kernels_FFT(freqs,ks,labels,ax,dt):    
        for j in range(ks.shape[1]):
            color = next(ax._get_lines.prop_cycler)['color']
            for k in range(ks.shape[0]):
                if k==0:
                    ax.plot( freqs, absolute(rfft(ks[k,j,:])) , color=color , label = labels[j]) 
                else :
                    ax.plot( freqs, absolute(rfft(ks[k,j,:])) , color=color , linestyle='--'  ) 
        ax.set_xlabel("GHz")
        ax.legend()

        