#!/bin/env/python
#! -*- coding: utf-8 -*-

import scipy.constants as const

#############
# Statics   #
#############

_e      = const.e # Coulomb
_h      = const.h # Joule second
_kb     = const.Boltzmann # J/K (joules per kelvin)

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
        
        Todos :
            - Makes sure the tables is calibrated properly
                - Make the tables static
            - Implement a methods that automatically get out of t.under state
            - Implement warning properly
            - Add debug options..
        Bugs :
            - Make cooldown funciton properly
    """
    __version__ = {'Lakeshore_wrapper':0.2}
    __version__.update(Pyhegel_wrapper.__version__)
    # These tables could be fine tuned
    # And are calibrated on  dilu 3
    _temperature_range       =   [ 0.007 , 0.020     , 0.050 , 0.100    , 0.200     , 0.400  , 0.700 ] # The upperbound of the interval
    _temperature_tolerance   =   [ 0.0   , 0.001     , 0.0025, 0.005    , 0.010     , 0.02   , 0.035 ] # The upperbound of temperature error after _stabilization_loop
    _time_tolerance          =   [ 0.0   , 120       , 60    , 60       , 60        , 60     , 60    ] # The amount of time the temperature error as to be below the temperature_tolerance to say the stabvilization is acheived
    _heater_range            =   [ 0.0   , 0.000316  , 0.001 , 0.00316  , 0.01      , 0.01   , 0.01  ] # see instruments.lakeshore_370.heater_range for all possible values
    _proportional            =   [ 25    , 25        , 25    , 12.5     , 6.25      , 6.25   , 6.25  ]
    _integral                =   [ 120   , 120       , 120   , 120      , 120       , 120    , 120   ]
    _derivative              =   [ 0     , 0         , 0     , 0        , 0         , 0      , 0     ]
    def __init__(self, visa_addr ='ASRL1',**options):
        self._set_options(**options)
        self._lakeshore =  instruments.lakeshore_370(visa_addr)
        self.set_current_ch(6) # The 6th channel is the temperature of the sample
        if self._verbose :
            print "Current channel is : {} \n and has temperature = {} K".format( self._lakeshore.current_ch.get(), self.get_temperature())
    def get_pyhegel_instance(self):
        return self._lakeshore
    def getout_tunder(self,verbose=False):
        """
            Notes :
                - There was a bug in the set_to_close_loop().
                    The heater wasn't turned off and the lakeshore needs to be set to
                    control_mode == 'off' and not 'open_loop'
                - 
        """   
        ch_sample       = 6         # ch=6 : mixing chamber
        T_target_out    = 0.015     # = 15[mK] : get the value from table 
        heating_power   = 12.0e-6   # [W] 100% of ther targeted range
        t_th            = 0.0075    # Thereshold to say we are out of t.under 
        wait_time       = 5.0       # Before checking if we're out of t.under
        t_stab          = 0.008     # Target temperature after we're out of t.under
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
        self._set_to_close_loop()
        self.stabilize_temperature(t_stab,verbose=verbose)
    def _set_options(self,**options):
        self._verbose   = options['verbose'] if 'verbose' in options else False
    def _set_autoscan(self,val_bool):
        set(self._lakeshore.scan,autoscan_en=val_bool)
    def _set_autoscan_ch(self,ch):
        set(self._lakeshore.scan,ch=ch)
    def cooldown(self):
        self._set_heater_range(0)    # Need to turn the heater off first
        self._set_control_off()      # Then set the control mode to off (no temperature control)
    def set_close_state(self):
        self.cooldown()
    def _set_control_off(self):
        set(self._lakeshore.control_mode,'off') 
    def _set_to_open_loop(self): 
        set(self._lakeshore.control_mode,'open_loop')
    def _set_to_close_loop(self): 
        set(self._lakeshore.control_mode,'pid')
    def set_current_ch(self,channel):
        set(self._lakeshore.current_ch,channel)
    def get_current_ch(self):
        return get(self._lakeshore.current_ch)
    def get_temperature(self):
        return get(self._lakeshore.t)
    def get(self):
        return self.get_temperature()
    def set_temperature(self,t):
        return set(self._lakeshore.sp,t)
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
    def stabilize_temperature(self,T,verbose=False):
        if (self._verbose or verbose) :
            print "Stabilizing to {}[K]".format(T)
        self._set_heater_range(T)
        self._set_PID(T)
        self.set_temperature(T)
        self._stabilization_loop(T)
    def set(self,T):
        return self.stabilize_temperature(T)
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
        self._debug  = options.get('debug')
        if self._debug :
            self._yoko = None
            self._V_dummy = 0.0
        else :
            self._yoko = instruments.yokogawa_gs200(visa_addr)
        self.set(0)
    """
        Wrapper of existing behavior
    """
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
    
####################
# Pyhegel Utilities #
####################
class timer(object):
    __version__ = {'timer':0.2}
    def __init__(self,size=1):
        self.timer = zeros((2,size))
    def watch(self):
        return time.time()  
    def tic(self,index=0):
        self.timer[0,index] = self.watch()
    def toc(self,index=0):
        self.timer[1,index] = self.watch()-self.timer[0,index]
    def durations(self):
        return self.timer[1,:]
        
class logger(object):
    """
        Times an experiment 
        and print events and progress
        begin
            loop
                loop_events
        end
        
        log_dict (example)
        {
            'open'          : 'Lauching experiement'
            'close'         : 'Experience over : \n \t Estimated time [s] {:04.2F} \n \t Real time {:04.2F} [s]'
            'loop_sizes'    : (1st_loop,2nd_loop,...)
            'loop'          : 'Progess {:03}/{:03d} \t last_loop time: {:04.2F} [s] '
            'events'        : (None by default)
                            : (format example) # The first parameter is an index for the event since dictionnary are now guarentied to preserve order
                                {
                                    "Event_name" : "format_ready_str"
                                }
                            : (example) 
                                {
                                "Aquisition": "Acquisition : {:04.2F} [s]", 
                                "Computing" : "Computing : {:04.2F} [s] "
                                }
            'rate'          : ( l_data*1.0e-9.0 ,"Rate : {:04.2F} [GSa/s] " ),
        }
        times_est   = (experiment_time,loop_time)
        
        Todos :
            - Rethink this class
            - Make an options for condition formating ...
            - For V1.0 think about the possibility of using super() instead of the current way of working
         Bugs :
            - The first loop call prints a duration that makes no sense
    """   
    __version__     = { 'logger'  : 0.2 }
    __version__.update(timer.__version__)  
 
    _default_log = \
    {
        'loop_sizes': (1,),
        'open'      : 'Lauching experiment' ,
        'close'     : 'Experience over : \n \t Estimated time [s] {:04.2F} \n \t Real time {:04.2F} [s]' ,
        'loop'      : 'Progess {:03}/{:03d} \t last_loop time: {:04.2F} [s]' ,
        'conditions': '{:04.1F}'
    }
    _allowed__user_key = ('loop_sizes','open','close','loop','rate','events')
    _user_key_to_attribute_key = \
    {
        'loop_sizes'    : '_loop_sizes'  ,
        'open'          : '_open_str'    ,
        'close'         : '_close_frmt'  ,
        'loop'          : '_loop_frmt'   ,
        'is_rate'       : '_is_rate'     ,
        'rate'          : '_event_rate'  ,
        'is_event'      : '_is_event'    ,
        'events'        : '_events'      ,
        'conditions'    : '_conditions_frmt'
    }
    _default_time_est = (1.0,)
    def __init__( self, time_estimates , log_dict ):
        self._attributes_instanciation(time_estimates,log_dict)
    def _attributes_instanciation(self,time_estimates , log_dict):
        if log_dict == () or log_dict == None : # Set the default log
            dict_to_attr(self,self._default_log,self._user_key_to_attribute_key)
        else :
            self._log_dict_to_attributes(log_dict,self._user_key_to_attribute_key)
        self._event_attributes_instanciation(log_dict)
        self._set_time_estimate(time_estimates)
    def _log_dict_to_attributes(self,log_dict,conv):
        for key in self._default_log :  # set the attributes of the given log_dict or the default one when it doens't exist
            setattr(self,conv[key],log_dict[key]) if key in log_dict else setattr(self,conv[key],self._default_log[key])
    def _set_time_estimate(self,time_estimates):
        self.time_estimate =  self._default_time_est if  time_estimates  == () or time_estimates == None else time_estimates
    def _event_attributes_instanciation(self,log_dict):
        self._is_rate    =   'rate' in log_dict
        if self._is_rate :
            self._event_rate = log_dict['rate']
        self._experiment = timer()
        self._loop       = timer(len(self._loop_sizes))
        self._is_event   = 'events' in log_dict
        if self._is_event :
            self._events_dict = log_dict['events']
            self._events_len  = len(self._events_dict.keys())
            self._events      = timer(self._events_len)
            self._events_frmt = self._build_events_frmt()
    def open(self):
        self._experiment.tic()
        for i in range(len(self._loop_sizes)-1):
            self._loop.tic(i)
        if self._is_event :
             self._events.tic(0)
        print(self._open_str)
    def close(self):
        self._experiment.toc()
        if self._is_event :
             self._events.toc(self._events_len-1)
        total_t = self._experiment.durations()[0]
        print (self._close_frmt).format(self.time_estimate[0],total_t)
    def loop(self,loop_index,loop_icrmnt):
        self._loop.toc(loop_index)
        loop_time  = self._loop.durations()[loop_index]
        self._loop.tic(loop_index)
        print self._loop_frmt.format(loop_icrmnt, self._loop_sizes[loop_index] , loop_time)
    def event(self,index):
        self._events.toc(index)
        self._events.tic((index+1)%self._events_len)  
    def _build_events_frmt(self):
        drtns = self._events.durations()
        s = ''
        tab = ' | '
        d = self._events_dict
        for i,key in enumerate(d):
            s += tab
            s += d[key].format(drtns[i])
        if self._is_rate:
            s += tab
            num = self._event_rate[0]
            frmt = self._event_rate[1]
            s += frmt.format(num/(drtns[-1]+drtns[0]))
        return s     
    def events_print(self,condition_tuple):
        s = self._build_events_frmt()
        s_tuple = '('
        for t in condition_tuple :
            s_tuple += '{: .1f},'.format(t)
        s_tuple += ')'
        print s_tuple + '\t' + s

class logger_aqc_and_compute(logger):
    """
        A logger with default Aquisition and Computing events
    """
    __version__     = { 'logger_aqc_and_compute'  : 0.2 }
    __version__.update(logger.__version__)   
    def __init__(self,time_estimates,*arg,**log_dict):
        if log_dict :
            super(logger_aqc_and_compute,self).__init__(time_estimates,log_dict)
        else :
            n_measures  = arg[0]
            l_Vdc       = arg[1]
            l_data      = arg[2]
            _aqc_and_compute_log       = \
            {
            'loop_sizes'    : ( n_measures , l_Vdc ),
            'events'        : 
                            {
                                "Aquisition": "Acquisition : {:04.2F} [s]", 
                                "Computing" : "Computing : {:04.2F} [s] "
                            },
            'rate'          : ( l_data*1.0e-9 ,"Rate : {:04.2F} [GSa/s] " )
            }
            super(logger_aqc_and_compute,self).__init__(time_estimates,_aqc_and_compute_log)
    
class ExperimentErrors(Exception):
    """
        Base class for pyHegel tools errors
    """
    pass

class VersionsError(ExperimentErrors):
    def __init__(self,versions_current,versions_loaded):
        self.versions_current  = versions_current
        self.version_loaded = versions_loaded
        s_load     = "Loaded versions  : \n\t {}".format(versions_loaded)
        s_current  = "Current versions : \n\t  {}".format(versions_current)
        self.message    = s_load+'\n'+s_current
        super(VersionsError,self).__init__(self.message)

class ConditionsError(ExperimentErrors):
    """
        When the given conditions are not of the right type or shape
    """
    
class UndefinedStateError(ExperimentErrors):
    """
       When the experiment object ends in an undefined state 
    """
    pass 
   
#################
# Pyhegel tools #
#################
    
class Experiment(object):
    """
        TLDR :
            (Pseudo code : Experiment) 
                experimentals condition, meta_info, pyhegel devices and options are given to the constructor
                
                child = children_class(conditions,devices,meta_info,op1=True,op2=True,op3=x,)
                
                The constructor initialize internal variable to a safe states.
                It instanciate computing object (autocorrelation,convolutions,...)
            
                child.measure() calls the measurment loop :
                    all_loop_open
                    for n  in main_iterator :               # controls repetitions using the default main_iterator (if not overwritten)
                        repetition_loop_start(n)            # code that as to be executed before each measurement_loop
                        for ... core_loop_iterator :        # using the user defined core_loop_iterator
                            loop_core(i_tuple,cndtns_tuple) # note that i and cndtns are tuples
                        repetition_loop_end(n)
                    all_loop_close()
                
                child.update_analysis()                     # compute the relevant physical data
                
                child.fig...()                              # standard plot(s) for this experiment
                
                child.save_data(folder)                     # saves data_timestamps.npz into folder
                                                                version number are saved with the data
                                                                
                child.load_data(folder,filename)            # construct a child object from saved data
                
                data = child.get_data()                     # return child._data a list of array defined by the user
                                                                # The user can modify that data and update_analysis() followed by plots to tinker with the data
                
        HOW TO WRITE THE CHILD CLASS :
        This class is written to give flexibility and reduce the amount of code that the user as to writte for the child class.
        This section describes what the user as to write in the child class
        - __init__ function
            You should not have to write a __init__ function for the child class
            The behavior of __init__ is modified by overwriting the following methods
            - set functions
                - _set_options       : setting attributes that modifies behaviors of other methods
                - _set_conditions    : sets self.conditions (mendatory) 
                                        and unrolls 
                                        self._n_measures = conditions[0] (mendatory)
                - _set_meta_info     : sets self._meta_info (mendatory) and unrolls it
                - _build_attributes  : build other attributes (Falcultative)
                - _set_devices       : sets self.devices (mendatory) 
                                        , unrolls it
                                        and sets each devices into their initial sate (Good pratice)
                - _init_objects      : initialize memory for large objects that will be used recurently (Falcultative)
                - _build_data        : helps to build self._data dict
                - _init_log          : defines the dehavior of the timer (Falcultative)
        , defining them is in a sense falcultative as the child class will still work if some or all of those are not defined 
        but it may lead to undefined bahavior
        - __del__ function
            It is not mendatory to write a __del__ function but a good pratice is 
            to set all devices to a safe/stable close state using __del__
        - Utilities
            Contains methods that are usefull all-around
        - loop behavior
            Calling the Experiment.measure() method will launch a measurment loop 
            
            (Pseudo code : measurment loop)
                for n  in main_iterator :               # controls repetitions using the default main_iterator (if not overwritten)
                    loop_before()                      # code that as to be executed before each measurement_loop
                    for ... core_loop_iterator :        # using the user defined core_loop_iterator
                        loop_core(i_tuple,cndtns_tuple) # note that i and cndtns are tuples
                loop_close()                            # code that is executed after all the repetitions are over
            
            see : Experiment._repetition_loop_iterator for the exact implementation
            
            User minimally defines in child class :
                - child._core_loop_iterator(self)
                - child._loop_core(self,index_tuple,condition_tuple)
            But can also define
                - child._repetition_loop_iterator(self)
                - child._repetition_loop_start(self,n)
                - child._repetition_loop_end(self,n)
                - child._all_loop_close(self)
                and _log events (to change the log behavior) 
                                
            The _super_enumerate utility is meant to help writing _core_loop_iterator      
                        
        - analysis 
            User can call child.update_analysis() to analyse data after all the repetitions are completed
            For this to work user as to define
                - _compute_reduction()
                    Is converting the data contained in the computing objects to esally saveable np.arrays.
                - _compute_analysis()
                    Does the rest of the analysis job (i.e. calling function to convert np.arrays to np.arrays)
                - _update_data()
                    builds self.data list (containts its structure) from internal variables/attributes
                - _load_data_list()
                    is the inverse of update_data
                    buils internal variables/attributes from a list of np.arrays
            Writting those function defines the proper behavior when 
            updating the analysis and loading from existing data and 
                
        - Plot and figs
            - The plot section containt default plot that the user is probably going to want
            - every fig function must return a fig object for outside modification
        
        - Methods and variables
            - __variables/__methods are not modifiable
            - _CAPS_.. are overwritable by the child function (used for grand-mother, mother, child situations)
        
        Todos :
            - Update __doc__
            - Add saving options 
                - There should be a way to run only the 1st analysis step during experiment
                and save the data arising only from this part (goal to not repeat measurment for nothing)
                - The 2nd analysis step can be added afterward and the new data structure can then be saved
                and loaded in the next loading phase
                - This mean that the loading function could load only the 1st part of the data or both
                - Maybe update_analysis should be split in
                    - data_reduction :> 1st step
                        run automatically after mesure()?
                    - data_analysis  :> 2nd step
            - Should I seperate saved structure into ?
                - data_reduction_date.npz
                - data_analysis_date.npz
                - Maybe my class structure should follow that too ? 
                    - Some classes for measuring and making some reduction
                        constructed from conditions, device and meta_info
                        or from a data structure from its class
                        Those class should definitively all be in global pyhegel tools
                    - Some parrallel meant for analysis
                        constructed either from
                            - a measuring class kepts only the parts it wants
                            - loading a data structure either
                                - from a compatible measurment class
                                - from its class
            - Add reset_obj ?
            - Add reset_analysis ?
            - Remode the unecessary dunders in __init__
        Bugs :
            - The current way of saving and loading stuff can convert int -> float
            which can lead to some problem some times. No global fix for now. 
            I've patched it in the child class by enforcing type in the constructor methods using int()
            - Computing before measurement can sometime lead to crash dependin on what type of computation is done during analysis
            - After constructing from data structure the destructor stills try to clean devices ?
    """
    __version__     = { 'Experiment'  : 0.7 }
    __version__.update(logger.__version__)
    @classmethod
    def description(cls):
        print cls.__doc__
    def __init__(self,conditions,devices,meta_info=None,**options):
        """
            - conditions    : example == (n_measures, nd_array_core_loop_cnds) 
            - devices       : example == (guzik,yoko,)
            - meta_info     : example == (l_kernel,l_data,R_jct,dt,)
            - option        : kwarg depends on the specific child class
        """   
        self._SET_options(options)
        self._SET_conditions(conditions)
        self._SET_meta_info(meta_info)
        self._BUILD_attributes()
        self._SET_devices(devices)
        self._INIT_objects()
        self._INIT_log()
    def _SET_options(self,options):
        self._verbose   = options['verbose'] if 'verbose'   in options else False
        if self._verbose : 
            print '{} is setting options'.format(self.__class__.__name__)
        self._data_from_experiment  = options['loading_data']   if 'loading_data'   in options else True
        self._test                  = options['test']           if 'test'           in options else True 
        self._debug                 = options['debug']          if 'debug'          in options else False 
        self._options               = options
        self._set_options(options)
    def _SET_conditions(self,conditions):
        if self._verbose : 
            print '{} is setting conditions'.format(self.__class__.__name__)
        if type(conditions) != tuple :
            raise ConditionsError('Conditions should be a tuple')
        self._conditions                = conditions
        if type(conditions[0]) != int :
            raise ConditionsError('n_measures should be int')
        self._n_measures                = conditions[0]     # The first element of the tuple is the number of repetions
        self._conditions_core_loop_raw  = conditions[1:]    # The 2nd   element ...          is an list of 1D array
        self._set_conditions(conditions)       
    def _SET_meta_info(self,meta_info):
        if self._verbose : 
            print '{} is setting meta_info'.format(self.__class__.__name__)
        self._meta_info                 = meta_info
        self._meta_info['repetitions']  = meta_info['repetitions'] if meta_info.has_key('repetitions') else 0
        self._set_meta_info(meta_info) 
    def _BUILD_attributes(self):
        if self._verbose : 
            print '{} is building attributes'.format(self.__class__.__name__)
        self._build_attributes()
    def _SET_devices(self,devices):
        if devices == None or devices == () or self._data_from_experiment == False :
            self._devices = None
        else :
            if self._verbose :
                print '{} is setting devices'.format(self.__class__.__name__)
            self._devices  =   devices
            self._set_devices(devices)
    def _INIT_objects(self):
        if self._data_from_experiment == False :
            pass
        else :
            if self._verbose : 
                print '{} is initializing objects'.format(self.__class__.__name__)
            self._init_objects()
    def _INIT_log(self):
        if self._data_from_experiment == False :
            pass
        else :
            if self._verbose : 
                print '{} is initializing log'.format(self.__class__.__name__)
            self._init_log()    
    def _set_options(self,options):
        pass
    def _set_conditions(self,conditions):
        pass
    def _set_meta_info(self,meta_info):
        pass
    def _build_attributes(self):
        pass
    def _set_devices(self,devices):
        pass
    def _init_objects(self):
        pass
    def _init_log(self):
        self._log            =   logger((),()) # Default timer
    def get_data(self):
        return self._data
    #############
    # Utilities #
    #############
    @staticmethod
    def _super_enumerate(*args):
        """
            Args are all 1D array
        """
        if len(args) == 0 : # called empty
            return iter(()) , iter(())
        index_vec = ()
        for a in args :
            index_vec += ( range(len(a)) , )
        return itertools.product(*index_vec) , itertools.product(*args)
    def _compute_n_measure(self):
        return 1 if self._test else self._n_measures
    def _set_all_devices(self,conditions):
        """
            Should always be implemented
        """
        pass
    def _set_devices_to_close_state(self):
        """
            Should always be implemented
        """
        if self._verbose :
            print '_set_devices_to_close_state'
        for dev in self._devices :
            dev.set_close_state()
    #################
    # Loop behavior #
    #################
    # all_loop_open
    # for n  in main_iterator :               
        # repetition_loop_start(n)            
        # for ... core_loop_iterator :        
            # loop_core(i_tuple,cndtns_tuple) 
        # repetition_loop_end(n)
    # all_loop_close()
    def _all_loop_open(self):
        self._log.open()
    def _repetition_loop_iterator(self):
        return range(self._compute_n_measure())
    def _repetition_loop_start(self,n):
        self._log.loop(0,n) 
    def _core_loop_iterator(self):
        return Experiment._super_enumerate(self._conditions_core_loop_raw) # by default no modification on the raw input
    def _loop_core(self,index_tuple,condition_tuple):
        self._log.events_print(condition_tuple)
    def _repetition_loop_end(self,n):
        pass
    def _all_loop_close(self):
        if self._data_from_experiment :
            if self._verbose :
                print 'Setting device to close state'
            self._set_devices_to_close_state()
        self._log.close()
    ######################
    # Analysis Utilities #
    ######################
    @staticmethod
    def SE(mu2k,muk,n):
        """ 
            Voir notes Virally Central limit theorem
            Computation of the standard error for the moment of order K
            mu2k : is the moment of order 2 k
            muk  : is the moment of order k
            If these moments are not centered then the definition is good for none centered moment
            Idem for centered moment
        """
        return sqrt(numpy.abs(mu2k-muk**2)/float(n))
    ############
    # Analysis #
    ############
    def _compute_reduction(self):
        pass
    def _compute_analysis(self):
        pass
    def _build_data(self):
        return {} # dummy default behavior
    def _update_data(self):
        self._data = self._build_data()     
    ########################################################
    # Should never change/double underscore unless public #
    ########################################################
    def save_data(self,path_save):    
        time_stamp                  = time.strftime('%y-%m-%d_%Hh%M') # File name will correspond to when the experiment ended
        filename                    = 'data_{}.npz'.format(time_stamp)
        to_save                     = self._data
        to_save['_versions_saved']  = self.__version__
        to_save['_options']         = self._options
        to_save['_conditions']      = self._conditions
        to_save['_meta_info']       = self._meta_info
        savez_compressed(os.path.join(path_save,filename),**to_save)
        print "Data saved \n \t folder : {} \n \t {}".format(path_save,filename)  
    @classmethod
    def load_data(cls,folder,filename):
        """
            To load data create an experiment object using
            experiment = class_name().load_data(folder,filename)
        """
        data                    = numpy.load(folder+'\\'+filename,allow_pickle=True)
        data                    = dict(data)
        conditions              = data.pop('_conditions')
        devices                 = None
        meta_info               = data.pop('_meta_info')[()] # to load a dict saved by numpy.savez
        options                 = data.pop('_options')[()]   # to load a dict saved by numpy.savez
        options['loading_data'] = True
        self                    = cls(conditions,devices,meta_info,**options)
        self._versions_saved    = data.pop('_versions_saved')[()]
        try :
            self._check_cls_vs_data_versions()
        except VersionsError :
            ans = yes_or_no('Try loading anyway ?')
            if ans :
                dict_to_attr(self,data)
            else :
                s = \
                """
                Constructor called using conditions,meta_info and options
                but no devices and no data loaded.
                """
                raise UndefinedStateError(s)
        return self      
    def measure(self):
        self._measurement_loop()
    def repeat_measure(self,n_repetitions = 1):
        """
            In the current state of the class if I do
            n_measures = n_measures + condition[0]
            the repetition is going to be longer than the previous execution
            to keep track of the number of total number of repetition im going to temporarly use 
            a new variable, but this means that conputations using n_measures (like all _std ) wont be correct.
            
            Repetitions are saved/loaded automatically in meta_info
            Todos :
                - Update the std calculations to include repetitions
                - Anything else regarding that feature ?
            Bugs :
        """
        for  rep in range(n_repetitions):
            self._meta_info['repetitions'] += 1
            self._measurement_loop()
    def _n_measure_total(self):
        return self._n_measures*(1+self._meta_info['repetitions'])
    def update_analysis(self,**kargs):
        return self._update_analysis_from_aquisition(**kargs) if self._data_from_experiment else self._update_analysis_from_load(**kargs)       
    def _measurement_loop(self):
        main_it = self._repetition_loop_iterator()
        self._all_loop_open()
        for n  in main_it :
            index_it , condition_it = self._core_loop_iterator()
            self._repetition_loop_start(n)
            for index_tuple, condition_tuple in zip(index_it,condition_it):
                self._loop_core(index_tuple,condition_tuple)
            self._repetition_loop_end(n)
        self._all_loop_close()
    def _update_analysis_from_aquisition(self,**kargs) :
        self._compute_reduction()
        self._compute_analysis(**kargs)
        self._update_data()
    def _update_analysis_from_load(self,**kargs):
        self._compute_analysis(**kargs)
        self._update_data()
    def _check_cls_vs_data_versions(self):
        if self._verbose :
            key = self.__class__.__name__
            print 'Loading {} version {}'.format(key,self.__version__[key])
        if not ( self.__version__ == self._versions_saved ):
            raise VersionsError(self.__version__,self._versions_saved)

class Lagging_computation(Experiment):
    """
        Initiate the conditions iterator before the core loop, but not the index iterator.
        The first conditions is set before the core loop 
        Todos : 
            - 
        Bugs :
    """
    __version__     = { 'Lagging_computation'  : 0.4 }
    __version__.update(Experiment.__version__)
    #################
    # Loop behavior #
    #################
    def _set_and_wait_all_devices(self,conditions):
        """
            Used to make sure that devices have reached stady state before
            calling the lagging core loop
        """
        pass
    def _repetition_loop_start(self,n,condition_it):
        super(Lagging_computation,self)._repetition_loop_start(n)
        self._first_conditions = condition_it.next()
        self._log.events_print(self._first_conditions)
        self._set_and_wait_all_devices(self._first_conditions)
    def _last_loop_core_iteration(self):
        pass
    def _measurement_loop(self):
        main_it = self._repetition_loop_iterator()
        self._all_loop_open()
        for n  in main_it :
            index_it , condition_it = self._core_loop_iterator()
            self._repetition_loop_start(n,condition_it)
            core_it     = iter(zip(index_it,condition_it))
            while True :
                try :
                    index_tuple, condition_tuple = core_it.next()
                    self._loop_core(index_tuple,condition_tuple)
                except StopIteration :
                    self._last_loop_core_iteration()
                    break
            self._repetition_loop_end(n)
        self._all_loop_close()

class Conditions_logic(object):
    """
        Manages the logic arround the condition tuples and the
        experimental conditions
        
        It adds some options attributes via the _set_options function
        and some Vdc attributes via the build_attributes function 
        
        Add the folowing options :
            Interlacing     : reference condition in between each conditions
            Vdc_antisym : anntisymetrize Vdc  
        Todos : 
            - Add the options of interlacing other than every other point
                ex : every 2nd point ... ref cnd cnd        ref cnd cnd
                or   every 3rd point ... ref cnd cnd cnd    ref cnd cnd cnd
        Bugs :
    """
    __version__     = { 'Conditions_logic'  : 0.4 }
    def _set_options(self,**options):
        self._conditions_options      =   {'interlacing': options.get('interlacing') , 'antisym':options.get('Vdc_antisym') }
    def _build_attributes(self):
        # todos add options for the different scenarios of experiments
        # Vdc only experiment
        Vdc                     = self.Vdc
        antisym                 = self._conditions_options['antisym']
        interlacing             = self._conditions_options['interlacing']
        self._Vdc_antisym       = Conditions_logic.add_antisym            (Vdc               ,antisym    =antisym )
        self._Vdc_exp           = Conditions_logic.add_ref_conditions     (self._Vdc_antisym ,interlacing=interlacing )
        self._conditions_exp    = self._Vdc_exp
        # Vdc and temperature experiment
        # ....
    #############
    # Utilities #
    #############
    @staticmethod
    def add_antisym(Vdc,**sym_options):
        return numpy.concatenate(([(-1.0)*Vdc[::-1],Vdc])) if sym_options.get('antisym') else Vdc
    @staticmethod
    def add_ref_conditions(Vdc,**ref_options):    
        if  ref_options.get('interlacing'):
            return Conditions_logic.compute_interlacing(Vdc)
        else :
            return Conditions_logic.compute_default_ref(Vdc)
    @staticmethod
    def compute_interlacing(Vdc):
        Vdc_interlaced = zeros(2*len(Vdc))
        Vdc_interlaced[1::2] = Vdc
        return Vdc_interlaced
    @staticmethod
    def compute_default_ref(Vdc):
        return numpy.concatenate(([0],Vdc))
    ######################
    # Analysis Utilities #
    ######################
    @staticmethod
    def compute_cumulants_sample(cumulants,swapaxes=None,**ref_options):
        if swapaxes : 
            cumulants = cumulants.swapaxes(*swapaxes)
        if  ref_options.get('interlacing') :
            ref =  cumulants[...,::2]
            cdn =  cumulants[...,1::2]
            cumulants_sample = cdn - ref
        else :
            ref =  cumulants[...,0]
            cdn =  cumulants[...,1::]
            cumulants_sample = cdn - ref[...,None]
        if swapaxes : 
            cumulants_sample = cumulants_sample.swapaxes(*swapaxes)
        return cumulants_sample
    @staticmethod
    def compute_cumulants_sample_std(cumulants_std,swapaxes=None,**ref_options):
        if swapaxes : 
            cumulants_std = cumulants_std.swapaxes(*swapaxes)
        if ref_options.get('interlacing') :
            ref =  cumulants_std[...,::2]
            cdn =  cumulants_std[...,1::2]
            cumulants_sample_std = cdn + ref
        else :
            ref =  cumulants_std[...,0]
            cdn =  cumulants_std[...,1::]
            cumulants_sample_std = cdn + ref[...,None]
        if swapaxes : 
            cumulants_sample_std = cumulants_sample_std.swapaxes(*swapaxes)
        return cumulants_sample_std
    @staticmethod
    def compute_differential(X,Y,swapaxes=None):
        if swapaxes : 
            Y = Y.swapaxes(*swapaxes)
        pos     = compute_differential(Y[...,numpy.where(X>0)[0]])
        neg     = compute_differential(Y[...,numpy.where(X<0)[0]])
        Y_diff  = numpy.concatenate((neg,pos),axis=-1)
        if swapaxes : 
            swap = (swapaxes[0]+1,swapaxes[1]+1)
            Y_diff = Y_diff.swapaxes(*swap)
        return  Y_diff

class Conditionned_exp(Conditions_logic,Experiment):
    """
        This implement the logic imbeded into Condition_logic and
        makes it so that the core loop iterates automatically over
        the conditionned arrays.
        
        Set     automatically the _conditions_options dict
        Build   conditions  specific attributes 
        
        Todos : 
        Bugs :
    """
    __version__     = { 'Conditionned_exp'  : 0.6 }
    __version__.update(Experiment.__version__)
    __version__.update(Conditions_logic.__version__)
    def _set_options(self,options):
        Conditions_logic._set_options(self,**options)   #stactic
    def _build_attributes(self):
        Conditions_logic._build_attributes(self)        #stactic
    def _core_loop_iterator(self):
        return Experiment._super_enumerate(self._conditions_exp)

class Conditioned_Lagging_exp(Conditions_logic,Lagging_computation):
    """
        Same as Condition_logic but with Lagging_computation experiement
        Todos : 
        Bugs :
    """
    __version__     = { 'Conditioned_Lagging_exp'  : 0.5 }
    __version__.update(Lagging_computation.__version__)
    __version__.update(Conditions_logic.__version__)
    def _set_options(self,options):
        Conditions_logic._set_options(self,**options)   #stactic
    def _build_attributes(self):
        Conditions_logic._build_attributes(self)        #stactic
    def _core_loop_iterator(self):
        return Experiment._super_enumerate(self._conditions_exp)

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
                dfs = dfs*ones(fs.shape)  
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
                dfs = dfs*ones(fs.shape)
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
            rise_fall = zeros(fs.shape)
            rise_fall[:,0] = rise
            rise_fall[:,1] = fall
            flatband_info  = {'fs':fs,'rise_fall':rise_fall,'snap_on':snap_on}
        flatband_info['labels'] = Quads_helper._gen_flatband_labels(flatband_info)
        return flatband_info
    @staticmethod
    def gen_Filters(filter_info):
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
            return array([])
        if snap_on :
            F   = Quads_helper.gen_f_abscisse(l_kernel,dt)
            fs,_  = find_nearest_A_to_a(fs,F)
            gauss_info['fs'] = fs # Modifying the dict
        Filters = empty( (len(fs),l_kernel//2+1) , dtype=complex , order='C' ) 
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
            return array([])
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
            return array([])
        Filters     = empty( (fs.shape[0],l_hc),dtype=complex,order='C' ) 
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
        sum = sqrt( 2*df*(numpy.square(numpy.abs(Y))).sum() )
        return Y/(sum)
    @staticmethod
    def Gaussian (x,mu=0.0,sigma=1.0) :
        return (1.0/(sigma*sqrt(2.0*pi))) * exp( (-(x-mu)**2)/(2.0*sigma**2) )
    @staticmethod
    def Gaussian_filter_normalized(f,df,l_kernel,dt) :
        """
        Returns a numpy array of complex number corresponding to a gaussian filter
        of avg f and std dev df on positive frequencies and with vector length equal to  l_kernel//2 + 1.
        """
        l_hc = l_kernel//2+1 

        Y = empty( l_hc , dtype = complex , order='C') 
        x_f = numpy.fft.rfftfreq(l_kernel , dt)
        for i in range( l_hc ) :
            Y[i] =  Quads_helper.Gaussian ( x_f[i] , f , df ) 
        Delta_f = x_f[1]-x_f[0]
        Y = Quads_helper.Wave_function_of_f_normalization(Y,Delta_f)
        return Y 
    @staticmethod
    def _Bi_Gaussian_filter_normalized(f1,f2,df1,df2,l_kernel,dt) :
        l_hc = l_kernel//2+1 
        Y = empty( l_hc , dtype = complex , order='C') 
        x_f = numpy.fft.rfftfreq(l_kernel , dt)
        for i in range( l_hc ) :
            Y[i] =  (df1*sqrt(2.0*pi))*Quads_helper.Gaussian ( x_f[i] , f1 , df1 ) + (df2*sqrt(2.0*pi))*Quads_helper.Gaussian(x_f[i] , f2 , df2) 
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
        