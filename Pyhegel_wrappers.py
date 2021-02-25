#!/bin/env/python
#! -*- coding: utf-8 -*-

####################
# Pyhegel wrapeprs #
####################

class Pyhegel_wrapper(object):
    """ 
        default values for every mandatory methods
    """
    __version__ = {'Pyhegel_wrapper':0.2}
    def get_pyhegel_instance(self):
        pass
    def set_init_state(self,val):
        pass
    def set_close_state(self):
        pass
    def get(self):
        pass
    def set(self,val):
        pass

class Lakeshore_wrapper(Pyhegel_wrapper):
    """ 
        Lakeshore_wrapper is a logical device derived from lakeshore_370
        
        Warning : this is just what works for me. I did not code this denfensivly
        use at you're own risk.
        
        It is intended to automatically control the temparature using the lakeshore's internal 
        closed loop along with presets (static tables) that I've made myself.
        
        Usgin object.stabilize_temperature(t) will give back the control of to the command line
        only when the temperature is reached and has stabilized (see : time_tolerance and temperature_tolerance)
        
        If temperatures out of the intended range are used it defaults to 
        cooldown (i.e. self.heater_range is set to 0).
        
        Notes :
            - I changes getout_tunder() heating_power from 12.0e-6 to 6.0e-6 because 
              it was overshooting to much.
        Todos :
            - Makes sure the tables is calibrated properly
                - Make the tables static
            - Implement warning properly
        Bugs :
            - Lorsque cooldown a ete appeler (fin du script) et que je relance le même script
            le lakeshore ne semble pas chauffé. J'ai du fermer le heater et le réouvrir en mettant un range pour que ça fonctionne comme d'hab.
    """
    __version__ = {'Lakeshore_wrapper':0.4}
    __version__.update(Pyhegel_wrapper.__version__)
    # These tables could be fine tuned
    # And are calibrated on  dilu 3
    _temperature_range       =   [ 0.007005 , 0.015     , 0.020     , 0.050     , 0.100    , 0.200     , 0.400  , 0.700 ] # The upperbound of the interval
    _temperature_tolerance   =   [ 0.0      , 0.0005    , 0.00025   , 0.0005    , 0.00025  , 0.001     , 0.005  , 0.010 ] # The upperbound of temperature error after _stabilization_loop
    _time_tolerance          =   [ 0.0      , 120       , 222*3     , 105*3     , 250*3    , 420*3     , 600*3  , 600*3 ] # The amount of time the temperature error as to be below the temperature_tolerance to say the stabvilization is acheived
    _heater_range            =   [ 0.0      , 0.000316  , 0.000316  , 0.001     , 0.00316  , 0.01      , 0.01   , 0.01  ] # see instruments.lakeshore_370.heater_range for all possible values
    _proportional            =   [ 25       , 25        , 25        , 25        , 12.5     , 6.25      , 6.25   , 6.25  ]
    _integral                =   [ 120      , 120       , 120       , 120       , 120      , 120       , 120    , 120   ]
    _derivative              =   [ 0        , 0         , 0         , 0         , 0        , 0         , 0      , 0     ]
    _observed_time_cst       =   [ 1600     , None      , 220       , 105       , 250      , 420       , 600    , 600   ] # [s] very approximate
    _base_flow               =   0.50                                                                                     # mmol/s Base flow on this fridge for this calibration table
    def __init__(self, visa_addr ='ASRL1',**options):
        self._set_options(**options)
        if self._debug :
            self._lakeshore = None
        else :
            self._lakeshore =  instruments.lakeshore_370(visa_addr)
            self.set_current_ch(6) # The 6th channel is the temperature of the sample
        if self._verbose :
            print "Current channel is : {} \n and has temperature = {} K".format( self._lakeshore.current_ch.get(), self.get_temperature())
    #############
    # User interface #
    #############
    def get_pyhegel_instance(self):
        return self._lakeshore
    def getout_tunder(self,**options):
        """
            Notes :
                - There was a bug in the set_to_close_loop().
                    The heater wasn't turned off and the lakeshore needs to be set to
                    control_mode == 'off' and not 'open_loop'
                - PID Oscillates arround 10 mK need to tone down P (set to 12.5)
            Todos :
                - Investigate getout_tunder followed by stabilize_temperature followed by coldown followed by getout_tunder followed by stabilize_temperature
            Bugs :
                - Verbose not showing in command line
        """
        if self._debug :
            pass
        else :
            if (self._verbose or verbose) :
                print "get out of t.under"
            ch_sample       = 6         # ch=6 : mixing chamber
            T_target_out    = 0.015     # = 15[mK] : get the value from table 
            heating_power   = 6.0e-6    # [W] 100% of ther targeted range   
            t_th            = 0.0071    # Thereshold to say we are out of t.under 
            wait_time       = 5.0       # Before checking if we're out of t.under
            t_stab          = 0.0085     # Target temperature after we're out of t.under
            if self.get_temperature() < t_th :
                self._set_autoscan(False)
                self._set_autoscan_ch(ch_sample)    
                self._set_to_open_loop()
                self._set_heater_range(T_target_out)    
                self._set_heater(heating_power)
                while True :
                    t = self.get_temperature()
                    if t > t_th :
                        break
                    if (self._verbose or verbose) :
                        print "Waiting to get out of t.under"
                    wait(wait_time)
            if (self._verbose or verbose) :
                print "setting lakeshore to close loop"
            self._set_to_close_loop()
            self.stabilize_temperature(t_stab,verbose=verbose)
    def cooldown(self):
        if self._debug :
            pass
        else :
            self._set_heater_range(0)    # Need to turn the heater off first
            self._set_control_off()      # Then set the control mode to off (no temperature control)
    def set_close_state(self):
        if self._debug :
            pass
        else :
            self.cooldown()
    def set_current_ch(self,channel):
        if self._debug :
            pass
        else :
            set(self._lakeshore.current_ch,channel)
    def get_current_ch(self):
        if self._debug :
            return None
        else :
            return get(self._lakeshore.current_ch)
    def get_temperature(self):
        if self._debug :
            return 0.0
        else :
            return get(self._lakeshore.t)
    # def get(self):
        # return self.get_temperature()
    # def set(self,T):
        # return self.stabilize_temperature(T)
    def set_temperature(self,t):
        if self._debug :
            pass
        else :
            set(self._lakeshore.sp,t)
    def stabilize_temperature(self,T,verbose=False):
        if self._debug :
            pass
        else :
            if (self._verbose or verbose) :
                print "Stabilizing to {}[K]".format(T)
            self._set_heater_range(T)
            self._set_PID(T)
            self.set_temperature(T)
            self._stabilization_loop(T)
    #############
    # private #
    #############
    def _set_options(self,**options):
        self._debug     = options.get('debug')
        self._verbose   = options.get('verbose')
    def _set_autoscan(self,val_bool):
        set(self._lakeshore.scan,autoscan_en=val_bool)
    def _set_autoscan_ch(self,ch):
        set(self._lakeshore.scan,ch=ch)
    def _set_control_off(self):
        set(self._lakeshore.control_mode,'off') 
    def _set_to_open_loop(self): 
        set(self._lakeshore.control_mode,'open_loop')
    def _set_to_close_loop(self): 
        set(self._lakeshore.control_mode,'pid')
        # bug patch try
        self._set_heater_range(0)
        self._set_heater_range(0.010)
    def _get_table_index(self,T):
        t_table = self._temperature_range
        index = 0
        if not( ( T<=t_table[-1] ) and ( T>t_table[0] ) ) :
            print "Temperature outside of heater_range_table"   
            return index  
        for i , t in enumerate(t_table):
            if T <= t :
                index = i  
                break 
        return index  
    def _stabilization_loop(self, T_target):
        t_tol       = self._temperature_tolerance[self._get_table_index(T_target)]
        time_tol    = self._time_tolerance[self._get_table_index(T_target)]
        T           = self.get_temperature()
        delta_T     = numpy.abs(T - T_target)
        keep_going  = True
        converged   = False
        # delta_T     >=t_tol
        while keep_going :
            t_0 = time.time()
            t_1 = t_0
            while delta_T<=t_tol :
                wait(5)
                T       = self.get_temperature() 
                delta_T = numpy.abs(T - T_target)
                t_1 = time.time()
                if not delta_T<=t_tol :
                    break 
                elif (t_1-t_0)>=time_tol :
                    converged = True
                    break 
            if converged == True : 
                keep_going = False
                break
            wait(10)
            T       = self.get_temperature() 
            delta_T = abs(T - T_target)       
    def _set_heater(self,power):
        """ Power in [W]"""
        set(self._lakeshore.manual_out_raw,power)
    def _set_heater_range(self, T):
        index = self._get_table_index(T)
        set(self._lakeshore.heater_range,self._heater_range[index])
    def _set_PID(self,T):
        index = self._get_table_index(T)
        set(self._lakeshore.pid, P = self._proportional[index] )
        set(self._lakeshore.pid, I = self._integral[index]     )
        set(self._lakeshore.pid, D = self._derivative[index]   )
        
class Yoko_wrapper(Pyhegel_wrapper):
    """
        Todos :
            - Add debug option 
    """
    __version__ = {'Yoko_wrapper':0.3}
    __version__.update(Pyhegel_wrapper.__version__)
    def __init__(self,visa_addr='USB0::0x0B21::0x0039::91KB11655',**options):
        self._set_options(**options)
        if self._debug :
            self._yoko = None
            self._V_dummy = 0.0
        else :
            self._yoko = instruments.yokogawa_gs200(visa_addr)
        self.set(0)
    """
        Wrapper of existing behavior
    """
    def _set_options(self,**options):
        self._debug  = options.get('debug')
    def get(self):
        if self._debug :
            return self._V_dummy
        else :
            return get(self._yoko)
    def set(self,V):
        if self._debug :
            self._V_dummy = V
        else :
            set(self._yoko,V)
    def set_output(self,booleen):
        if self._debug :
            pass
        else :
            set(self._yoko.output_en, booleen)
    def set_range(self,val):
        if self._debug :
            pass
        else :
            set(self._yoko.range,val)
    """
        Extra behavior
    """
    def set_init_state(self,max_val):
        self.set(0)
        self.set_output(True) 
        self.set_range(max_val)
    def set_close_state(self):
        self.set(0)
        self.set_output(False) 
    def set_and_wait(self,V,Waittime = 0.4):
        self.set(V)
        time.sleep(Waittime)  # Waiting until voltage is stable
        
class Guzik_wrapper(Pyhegel_wrapper):
    """
        This is a wrapper arround pyhegel's guzik class
        It doest not fallow pyhegel's convention because I could not solve 
        some issues that arose when trying to write a child class for 
        instruments.guzik_adp7104
        
        What it does :
            - Makes sure that only one instance of instruments.guzik_adp7104 exists
            - Add some custom behavior
            
        Options :
            - The debug option bypasse the actual initialization of the card
                this is used to avoid the long ~10 sec wait time when the goal is juste to find typos and runtime bugs...
        
        You can get direct access to the pyhegel object using
            get_pyhegel_instance()
            
        Example :
            gz = Guzik_wrapper() 
            gz.config(stuff..) 
            
            new_gz = Guzik_wrapper()  # Points to the same instance of instruments.guzik_adp7104
            
            Guzik_wrapper.couter # returns [2]
            
            del new_gz  
            
            Guzik_wrapper.couter # returns [1]
            
            pyhegel_gz = gz.get_pyhegel_instance() # This can be used with pyhegel functions
            
            data    = gz.get() # Gets the data
            snippet = gz.get_snippet() # Gets the first 1000 points. Does not mess with the config
            
            del gz  # The pyhelgel object gets deleted
            
        Undefined behavior :
            - If you try to make an instance of instruments.guzik_adp7104() 
            not using this class while this class as already an existing instance/object.
            
        Knowned bugs :
            - 
            
        Todos :
            - Add get_or_getcache
            - Can I make _is_debug work in a way that is actually usefull (i.e. reduce repetition in the code and the clutter)?
                - Also in config() I make an instance of dummy_data but I'm not covering the case where more than one channel is declared
                - This last problem propagates to the get function since idk what is the entended return format for the data when more than one channel is declared
        Bugs :
            - See comment In quick historam
    """
    __version__     =  {'Guzik_wrapper':0.2}
    __version__.update(Pyhegel_wrapper.__version__)
    _gz_instance =   [] 
    counter     =   [0]     
    def __init__(self,**options):
        self.counter[0] += 1
        self._debug  = options.get('debug')
        self.__load_guzik__()
        self._gz = self._gz_instance[0] 
    def __del__(self):
        self.counter[0] -= 1 
        self._gz = None 
        if self.counter[0] <=0 :
            del self._gz_instance[0] 
            self._gz_instance.pop 
    def __load_guzik__(self):
        """
            This ensures that only one instance of instruments.guzik_adp7104 exist
            for all objects of the Guzik_wrapper class
        """
        if not self._debug : 
            try:
                if not isinstance(self._gz_instance[0], instruments.guzik.guzik_adp7104):
                    print "\nLoading guzik :"
                    self._gz_instance.append( instruments.guzik_adp7104() )
            except:
                print "\nLoading guzik :"
                self._gz_instance.append( instruments.guzik_adp7104() )
        else :
            self._gz_instance.append(None)
    def config(self, channels=None, n_S_ch=1024, bits_16=True, gain_dB=0., offset=0., equalizer_en=True, force_slower_sampling=False, ext_ref='default', _hdr_func=None):
        if not self._debug : 
            return self._gz.config(channels,n_S_ch,bits_16,gain_dB,offset,equalizer_en,force_slower_sampling,ext_ref,_hdr_func)
        else :
            self._dummy_data = zeros((1,n_S_ch),dtype='int16') # this doesn't cover all the corner cases
            return None
    def read_config(self):
        if not self._debug : 
            return self._gz._read_config()
        else :
            return None
    def get(self):
        if not self._debug : 
            return get(self._gz)
        else :
            return self._dummy_data[0,:]
    def get_pyhegel_instance(self):
        return self._gz
    def get_snippet(self,snipsize=1000):
        if not self._debug : 
            return self.get()[:snipsize]
        else :
            return self._dummy_data[0,:snipsize]
    def quick_histogram_int16(self,n_threads=32):
        hist = Histogram_uint64_t_int16_t(n_threads,bit=16) # Bug : not using bit=16 does work but crashes in accumulate
        if not self._debug : 
            data = self.get()
        else :
            data = self._dummy_data
        hist.accumulate(data)
        plot(arange(-2.0**15,2.0**15),hist.get())
        xlim(0,1023)

   