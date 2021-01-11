#!/bin/env/python
#! -*- coding: utf-8 -*-

# Virtual intruments

# temperature_control_sample
class lakeshore_wrapper(object):
    """ 
        lakeshore_wrapper is a logical device derived from lakeshore_370
        
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
    """
    __version__ = {'lakeshore_wrapper':0.1}
    # These tables could be fine tuned
    # And are calibrated on  dilu 3
    temperature_range       =   [ 0.007 , 0.020     , 0.050 , 0.100    , 0.200     ] # The upperbound of the interval
    temperature_tolerance   =   [ 0.0   , 0.001     , 0.001 , 0.001    , 0.001     ] # The upperbound of temperature error after _stabilization_loop
    time_tolerance          =   [ 0.0   , 60        , 60    , 60       , 60        ] # The amount of time the temperature error as to be below the temperature_tolerance to say the stabvilization is acheived
    heater_range            =   [ 0.0   , 0.000316  , 0.001 , 0.00316  , 0.01      ] # see instruments.lakeshore_370.heater_range for all possible values
    proportional            =   [ 25    , 25        , 25    , 12.5     , 6.25      ]
    integral                =   [ 120   , 120       , 120   , 120      , 120       ]
    derivative              =   [ 0     , 0         , 0     , 0        , 0         ]
    def __init__(self, visa_addr ='ASRL1' ):
        self._lakeshore =  instruments.lakeshore_370(visa_addr)
        self.set_current_ch(6) # The 6th channel is the temperature of the sample
        print "Current channel is : {} \n and has temperature = {} K".format( self.current_ch.get(), self.get_temperature())
    def set_current_ch(self,channel):
        set(self._lakeshore.current_ch,channel)
    def get_current_ch(self):
        return get(self._lakeshore.current_ch)
    def get_temperature(self):
        return get(self._lakeshore.t)
    def set_temperature(self,t):
        return set(self._lakeshore.sp,t)
    def _get_table_index(self,T):
        t_table = self.temperature_range
        index = 0
        if not( ( T<=t_table[-1] ) and ( T>t_table[0] ) ) :
            print "Temperature outside of heater_range_table"   
            return index  
        for i , t in enumerate(t_table):
            if T <= t :
                index = i  
                break 
        return index  
    def stabilize_temperature(self,T):
        self._set_heater_range(T)
        self.set_temperature(T)
        self._stabilization_loop(T)
    def _stabilization_loop(self, T_target):
        t_tol       = self.temperature_tolerance[self._get_table_index(T_target)]
        time_tol    = self.time_tolerance[self._get_table_index(T_target)]
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
    def _set_heater_range(self, T):
        index = self._get_table_index(T) 
        set(self._lakeshore.heater_range,self.heater_range[index])
        set(self._lakeshore.pid, P = self.proportional[index] )
        set(self._lakeshore.pid, I = self.integral[index]     )
        set(self._lakeshore.pid, D = self.derivative[index]   )
        
class Yoko_wrapper(object):
    """
        Todos :
            - Make it inherit from pyhegel so that everything works as usual
    """
    __version__ = {'Yoko_wrapper':0.1}
    def __init__(self,visa_addr='USB0::0x0B21::0x0039::91KB11655'):
        self._yoko = instruments.yokogawa_gs200(visa_addr)
        self.set(0)
    """
        Wrapper of existing behavior
    """
    def get(self):
        return get(yoko)
    def set(self,V):
        set(self._yoko,V)
    def set_output(self,booleen):
        set(self._yoko.output_en, booleen)
    def set_range(self,val):
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
        set(self._yoko,V)
        time.sleep(Waittime)  # Waiting until voltage is stable
        
class Guzik_wrapper(object):
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
            - Add quick_histogram method
            - Add get_or_getcache
            - Can I make _is_debug work in a way that is actually usefull (i.e. reduce repetition in the code and the clutter)?
                - Also in config() I make an instance of dummy_data but I'm not covering the case where more than one channel is declared
                - This last problem propagates to the get function since idk what is the entended return format for the data when more than one channel is declared
    """
    __version__     =  {'Guzik_wrapper':0.1}
    _gz_instance =   [] 
    counter     =   [0]     
    def __init__(self,**options):
        self.counter[0] += 1
        self._debug  = options['debug'] if 'debug'  in options else False
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
    # def _is_debug(self,fct,*arg,**kwarg):
        # if not self._debug : 
            # return fct(*arg,**kwarg)
        # else :
            # return None
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
    def get_snippet(snipsize=1000):
        if not self._debug : 
            return self.get()[:snipsize]
        else :
            return self._dummy_data[0,:snipsize]
   
class logger(object):
    __version__ = {'logger':0.1}
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
        
def dictionnary_to_attributes(self,dict,user_key_to_attribute_key={}):
    """
        Used in a constructor to automatically set many attributes defined in a dictionnary
    """
    conv = user_key_to_attribute_key 
    for key in dict :
        setattr(self,conv[key],dict[key]) if key in conv else setattr(self,key,dict[key])

class Experiment_log(object):
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
    __version__     = { 'Experiment_log'  : 0.1 }
    __version__.update(logger.__version__)  
 
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
            dictionnary_to_attributes(self,self._default_log,self._user_key_to_attribute_key)
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
        self._experiment = logger()
        self._loop       = logger(len(self._loop_sizes))
        self._is_event   = 'events' in log_dict
        if self._is_event :
            self._events_dict = log_dict['events']
            self._events_len  = len(self._events_dict.keys())
            self._events      = logger(self._events_len)
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
                - _set_data_default  : sets self.data to a initiale state 
                - _init_log          : defines the dehavior of the logger (Falcultative)
                - _set_data_default  : defines the initial state of the self._data list
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
            
            see : Experiment._main_loop_iterator for the exact implementation
            
            User minimally defines in child class :
                - child._core_loop_iterator(self)
                - child._loop_core(self,index_tuple,condition_tuple)
            But can also define
                - child._main_loop_iterator(self)
                - child._repetition_loop_start(self,n)
                - child._repetition_loop_end(self,n)
                - child._all_loop_close(self)
                and _log events (to change the log behavior) 
                                
            The _super_enumerate utility is meant to help writing _core_loop_iterator      
                        
        - analysis 
            User can call child.update_analysis() to analyse data after all the repetitions are completed
            For this to work user as to define
                - _compute_1st_analysis_step_from_objects()
                    Is converting the data contained in the computing objects to esally saveable np.arrays.
                - _update_data_attributes()
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
            - Update the loading message so it shows the class type that's being loaded
            - Make it such that the loading show an error message when loading fails somewhere ...
            - Make a verbose option that show more text in run time
            
        Bugs :
            - The current way of saving and loading stuff can convert int -> float
            which can lead to some problem some times. No global fix for now. 
            I've patched it in the child class by enforcing type in the constructor methods using int()
            - Computing before measurement can sometime lead to crash dependin on what type of computation is done during analysis
    """
    __version__     = { 'Experiment'  : 0.1 }
    __version__.update(Experiment_log.__version__)
    # Bunch of indirections to manage current and futur constructor overloading
    def __init__(self,conditions,devices,meta_info=None,**options):
        """
            - conditions    : example == (n_measures,Vdc,) 
            - devices       : example == (guzik,yoko,)
            - meta_info     : example == (l_kernel,l_data,R_jct,dt,)
            - option        : kwarg depends on the specific child class
        """   
        self.__SET_options(options)
        self.__SET_conditions(conditions)
        self.__SET_meta_info(meta_info)
        self.__BUILD_attributes()
        self.__SET_devices(devices)
        self.__INIT_objects()
        self.__SET_data_default()
        self.__INIT_log()
    def __SET_options(self,options):
        print '{} is setting options'.format(self.__class__.__name__)
        self._is_data_from_experiment(options)
        self._test  = options['test']    if 'test'  in options else True 
        self._debug = options['debug']   if 'debug' in options else False 
        self._SET_options(options)
    def _SET_options(self,options):
        self._set_options(options)
    def __SET_conditions(self,conditions):
        print '{} is setting conditions'.format(self.__class__.__name__)
        self._SET_conditions(conditions)
    def _SET_conditions(self,conditions):
        self._set_conditions(conditions)       
    def __SET_meta_info(self,meta_info):
        print '{} is setting meta_info'.format(self.__class__.__name__)
        self. _SET_meta_info(meta_info)
    def _SET_meta_info(self,meta_info):
        self._set_meta_info(meta_info)
    def __BUILD_attributes(self):
        print '{} is building attributes'.format(self.__class__.__name__)
        self._BUILD_attributes()
    def _BUILD_attributes(self):
        self._build_attributes() 
    def __SET_devices(self,devices):
        if devices == None or devices == () or self._data_from_experiment == False :
            self._devices = None
        else :
            print '{} is setting devices'.format(self.__class__.__name__)
            self._SET_devices(devices)
    def _SET_devices(self,devices):
        self._set_devices(devices)
    def __INIT_objects(self):
        if self._data_from_experiment == False :
            pass
        else :
            print '{} is initializing objects'.format(self.__class__.__name__)
            self._INIT_objects()
            self._Experiment__update_analysis_from_aquisition() 
    def _INIT_objects(self):
        self._init_objects()
    def __SET_data_default(self):
        print '{} is setting default data'.format(self.__class__.__name__)
        self._SET_data_default()
    def _SET_data_default(self):
        self._set_data_default()
    def __INIT_log(self):
        if self._data_from_experiment == False :
            pass
        else :
            print '{} is initializing log'.format(self.__class__.__name__)
            self._INIT_log()
    def _INIT_log(self):
        self._init_log()
    
    # Default behavior/Modifiables construtor methods for child class
    def _set_options(self,options):
        self._options        =   options
    def _set_conditions(self,conditions):
        self._conditions     =   conditions
        self._n_measures     =   conditions[0] 
    def _set_meta_info(self,meta_info):
        self._meta_info      =   meta_info
    def _build_attributes(self):
        pass
    def _set_devices(self,devices):
        self._devices        =   devices
    def _init_objects(self):
        pass
    def _init_log(self):
        self._log            =   Experiment_log((),()) # Default logger
    def _set_data_default(self):
        self._data           =   []
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
        index_vec = ()
        for a in args :
            index_vec += ( range(len(a)) , )
        return itertools.product(*index_vec) , itertools.product(*args)
    @staticmethod
    def _compute_Vdc_interlaced(Vdc):
        Vdc_interlaced = zeros(2*len(Vdc))
        Vdc_interlaced[1::2] = Vdc
        return Vdc_interlaced
    @staticmethod
    def _compute_Vdc_default(Vdc):
        return numpy.concatenate(([0],Vdc))
    @staticmethod
    def _compute_next_Vdc(Vdc):
        """
            Cyclic translation of 1
        """
        out       = numpy.copy(Vdc)
        out[0:-1] = Vdc[1:]
        out[-1]   = Vdc[0]
        return out
    def _compute_n_mesure(self):
        return 1 if self._test else self._n_measures
    def _is_data_from_experiment(self,options):
        self._data_from_experiment = False if 'loading_data' in options else True
    #################
    # Loop behavior #
    #################
    def _repetition_loop_start(self,n):
        pass
    def _repetition_loop_end(self,n):
        pass
    def _all_loop_open(self):
        pass
    def _all_loop_close(self):
        pass
    def _core_loop_iterator(self):
        Vdc     = 0.5*arange(10)     # dummy default behavior
        return Experiment._super_enumerate(Vdc)
    def _main_loop_iterator(self):
        return range(self._compute_n_mesure())
    def _loop_core(self,index_tuple,condition_tuple):
        # dummy default behavior
        i,          = index_tuple
        vdc,    = condition_tuple
        print "loop index {} dummy vdc = {}".format(i,vdc)
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
        return sqrt(numpy.abs(mu2k-muk)/float(n))
    ############
    # Analysis #
    ############
    def _compute_1st_analysis_step_from_objects(self):
        pass
    def _update_data_attributes(self):
        pass
    def _update_data(self):
        self._data = [] # dummy default behavior
    def _load_data_list(self,data_list):
        pass
    ###################
    # Plots Utilities #
    ###################
    
    #########
    # Plots #
    #########
    
    ########################################################
    # Should never change/double underscore unless public #
    ########################################################
    def save_data(self,path_save):    
        time_stamp = time.strftime('%y-%m-%d_%Hh%M') # File name will correspond to when the experiment ended
        filename   = 'data_{}.npz'.format(time_stamp)
        savez_compressed\
        (\
            os.path.join( path_save, filename ) ,\
            versions_saved  =   self.__version__,\
            options         =   self._options    ,\
            conditions      =   self._conditions ,\
            meta_info       =   self._meta_info  ,\
            data            =   self._data
        )
        print "Data saved \n \t folder : {} \n \t {}".format(path_save,filename)  
    @classmethod
    def load_data(cls,folder,filename):
        """
            To load data create an experiment object using
            experiment = class_name().load_data(folder,filename)
        """
        data = numpy.load(folder+'\\'+filename,allow_pickle=True)
        conditions  = data['conditions']
        devices     = None
        meta_info   = data['meta_info']
        options     = data['options'][()]
        options['loading_data'] = True 
        
        self = cls(conditions,devices,meta_info,**options)
        self._data_from_experiment    = False 
        self._versions_saved = data['versions_saved'][()]
        self.__check__cls_vs_data_versions()
        self._load_data_list(data['data'])
        return self      
    def measure(self):
        self.__measurement_loop()
    def update_analysis(self):
        return self.__update_analysis_from_aquisition() if self._data_from_experiment else self.__update_analysis_from_load()
    def __repetition_loop_start(self,n):
        self._log.loop(0,n)
        self._repetition_loop_start(n)
    def __loop_core(self,index_tuple,condition_tuple):
        self._loop_core(index_tuple,condition_tuple)
        self._log.events_print(condition_tuple)
    def __repetition_loop_end(self,n):
        self._repetition_loop_end(n)
    def __all_loop_open(self):
        self._log.open()
        self._all_loop_open() 
    def __all_loop_close(self):
        self._all_loop_close() 
        self._log.close()
    def __measurement_loop(self):
        main_it = self._main_loop_iterator()
        self.__all_loop_open()
        for n  in main_it :
            index_it , condition_it = self._core_loop_iterator()
            self.__repetition_loop_start(n) 
            for index_tuple, condition_tuple in zip(index_it,condition_it):
                self.__loop_core(index_tuple,condition_tuple)
            self.__repetition_loop_end(n)
        self.__all_loop_close()
    def __update_analysis_from_aquisition(self) :
        self._compute_1st_analysis_step_from_objects()
        self._update_data_attributes()
        self._update_data()
    def __update_analysis_from_load(self):
        self._update_data_attributes()
        self._update_data()
    def __check__cls_vs_data_versions(self):
        print 'Loading {}'.format(self.__class__.__name__)
        s_load = "\t Loaded versions {}".format(self._versions_saved)
        s_current = "\t Current versions {}".format(self.__version__)
        if not ( self.__version__ == self._versions_saved ):
            s = "saved versions and current versions are not equal. \n"
            raise Exception(s+s_load+'\n'+s_current)
        else :
            print(s_load)

class Tunnel_junction(Experiment):
    """
        v0.1
       This class is meants to encapsulated everything that all tunnel junction measurement have in common
       For now I'll do only the stationnary/no phase lock case
        Options :
            Interlacing     : reference condition in between each conditions
            Vdc_pos_and_neg : anntisymetrize Vdc  
            test            : if true repeats experiment only once (all Vdcs once)
            debug           : trigger debug
            _estimated_time_per_loop : 1.0 by default
        Todos : 
           
        Bugs :
    """
    _e = 1.60217663e-19 # Coulomb
    _h = 6.62607015e-34 # Joule second
    __version__     = { 'Tunnel_junction'  : 0.1 }
    __version__.update(Experiment.__version__) 
    def _SET_options(self,options):
        self._is_data_from_experiment(options)
        self._options                   =   options
        self._interlacing               =   options['interlacing']      if 'interlacing'        in options else False
        self._Vdc_pos_and_neg           =   options['Vdc_pos_and_neg']  if 'Vdc_pos_and_neg'    in options else True
        self._test                      =   options['test']             if 'test'               in options else True 
        self._debug                     =   options['debug']            if 'debug'              in options else False 
        self._estimated_time_per_loop   =   options['time_per_loop']    if 'time_per_loop'      in options else 1.0
        self._set_options(options)      
    def _SET_conditions(self,conditions):
        self._conditions        =   conditions      
        self._n_measures        =   conditions[0]
        self.Vdc                =   conditions[1]
    def _SET_meta_info(self,meta_info):
        self._meta_info         =   meta_info
        self._circuit_info      =   meta_info[0]        # R_jct , R_1M , ...
        self._compute_info      =   meta_info[1]        # n_threads , ...
        self._aqc_info          =   meta_info[2]        # l_data    , dt , ...
        self._quads_info        =   meta_info[3]        # l_kernel , ...
        self._set_meta_info(meta_info)
    def _SET_devices(self,devices):
        # I dont like this because I had to overwrite the _SET_devices function from experiement
        # I also had to redo the logic that avoids to load devices when data is loaded
        if devices == None or devices == () or self._data_from_experiment == False :
            self._devices = None
        else :
            self._devices            =   devices
            self._gz                 =   devices[0] 
            self._yoko               =   devices[1]
            self._yoko.set_init_state(abs(self.Vdc).max())
            self._set_devices(devices)
    def _INIT_log(self):
        self._log_dict       = \
        {
        'loop_sizes'    : ( self._n_measures , len(self.Vdc) ),
        'events'        : \
                        {
                            "Aquisition": "Acquisition : {:04.2F} [s]", 
                            "Computing" : "Computing : {:04.2F} [s] "
                        },
        'rate'          : ( self._l_data*1.0e-9 ,"Rate : {:04.2F} [GSa/s] " )\
        }
        tmp = self._estimated_time_per_loop 
        self._log                = Experiment_log((self._n_measures*tmp,tmp) , self._log_dict)
        self._init_log()
    def _BUILD_attributes(self):
        self._BUILD_from_circuit    (self._circuit_info)
        self._BUILD_from_compute    (self._compute_info)
        self._BUILD_from_aqc        (self._aqc_info)    
        self._BUILD_from_quads      (self._quads_info)
        self._Vdc_antisym       =   self._compute_Vdc_antisym(self.Vdc)
        self._Vdc_exp           =   self._compute_Vdc_experimental(self.Vdc)
        self._build_attributes()
    def _BUILD_from_circuit(self,circuit_info):
        self._R_jct             =   circuit_info[0]
        self._R_1M              =   circuit_info[1]
        self._R_tl              =   circuit_info[2]
        self._build_from_circuit(circuit_info)
    def _BUILD_from_compute(self,compute_info):
        self._n_threads         =   compute_info[0]
        self._build_from_compute(compute_info)
    def _BUILD_from_aqc(self,aqc_info):
        self._l_data            =   int(aqc_info[0])
        self._dt                =   aqc_info[1]
        self._build_from_aqc(aqc_info)
    def _BUILD_from_quads(self,quads_info):
        self._l_kernel          =   int(quads_info[0])
        self._l_hc              =   self._l_kernel/2 + 1
        self._build_from_quads(quads_info)       
    def _init_log(self):
        pass
    def _build_attributes(self):
        pass
    def _build_from_circuit(self,circuit_info):
        pass
    def _build_from_compute(self,compute_info):
        pass
    def _build_from_aqc(self,aqc_info):
        pass
    def _build_from_quads(self,quads_info):
        pass
    def __del__(self):
        self._yoko.set_close_state()
    #######################
    # Extra Gets and sets #
    #######################
    #############
    # Utilities #
    #############
    def _compute_Vdc_ref_conditions(self,Vdc):
        if self._interlacing :
            return self._compute_Vdc_interlaced(Vdc)
        else :
            return self._compute_Vdc_default(Vdc)
    def _compute_Vdc_antisym(self,Vdc):
        if self._Vdc_pos_and_neg:
            self._Vdc_antisym = numpy.concatenate(([(-1.0)*Vdc[::-1],Vdc]))
            return self._Vdc_antisym
        else :
            self._Vdc_antisym = Vdc
            return self._Vdc_antisym
    def _compute_Vdc_experimental(self,Vdc):
        Vdc_exp          =   self._compute_Vdc_antisym(Vdc)
        self._Vdc_exp    =   self._compute_Vdc_ref_conditions(Vdc_exp)
        return self._Vdc_exp
    @staticmethod
    def _compute_Vdc_jct(Vdc,R_jct,R_1M):
        return Vdc*R_jct/(R_1M+R_jct)
    @staticmethod
    def _compute_I_jct(Vdc,R_1M):
        return Vdc/R_1M
    #################
    # Loop behavior #
    #################
    
    ############
    # Analysis #
    ############
    def _window_after_2ns(self,S2_sample):
        """
            Damping everything more than 2 ns
            At a sampling rate of 0.03125 it means everything after the 64th point
            
            This will need to be rewritten if used with another aquisition card...
        """ 
        def damp(x,epsilon,x_0):
            return exp((-1)*epsilon*(x-x_0))
        def compute_epsilon(red,after_lenght):
            return -log(1.0/red)/(after_lenght)
        red = 1000
        L_0 = 65
        epsilon = compute_epsilon(red,after_lenght=L_0)
        shape = S2_sample.shape
        len = shape[-1]
        out = zeros(shape)
        out = S2_sample
        for index in range(L_0,len):
            out[:,index] = S2_sample[:,index]*damp(index,epsilon,L_0-1)
        return out
    def _symetrize_S2(self,S2):
        return numpy.concatenate( (S2[:,-1:0:-1],S2),axis=1 )
    def _compute_S2diffs(self,S2_sym):
        Vdc     = self._compute_Vdc_antisym(self.Vdc)
        if self._Vdc_pos_and_neg : 
            S2_diff     = zeros((2,len(Vdc)-2,S2_sym.shape[-1]))
            pos         = S2_sym[numpy.where(Vdc>0)]
            neg         = S2_sym[numpy.where(Vdc<0)]        
            S2_diff[0,:,:]= r_[pos[1: ]   ,neg[:-1]   ]
            S2_diff[1,:,:]= r_[pos[:-1]   ,neg[1: ]   ]
        else :
            S2_diff = zeros((2,len(Vdc)-1))
            pos = S2_sym                   
            S2_diff[0,:,:]= r_[pos[1: ]   ]
            S2_diff[1,:,:]= r_[pos[:-1]   ]
        return S2_diff  
    def _compute_Vdiffs(self):
        Vdc     = self._compute_Vdc_antisym(self.Vdc)
        Vdc     = self._compute_Vdc_jct(Vdc,self._R_jct,self._R_1M)
        if self._Vdc_pos_and_neg : 
            V_diff      = zeros((2,len(Vdc)-2))       
            V_pos       = Vdc[numpy.where(Vdc>0)]                                                                  
            V_neg       = Vdc[numpy.where(Vdc<0)]                                                                  
            V_diff[0,:] = r_[V_pos[1:]  ,V_neg[1:]  ]
            V_diff[1,:] = r_[V_pos[:-1] ,V_neg[:-1] ]
        else :
            V_diff      = zeros((2,len(Vdc)-1))
            V           = Vdc                                
            V_diff[0,:] = r_[V[1:]      ]
            V_diff[1,:] = r_[V[:-1]     ]
        return V_diff  
    ###################
    # Plots Utilities #
    ###################
    def _gen_t_abscisse(self):
        t=arange(self._l_kernel)*self._dt
        return numpy.concatenate((-t[-1:0:-1],t))
    def _gen_f_abscisse(self):
        return numpy.fft.rfftfreq(self._l_kernel-1,self._dt)
    def _get_V_index(self, Vdc, V ):
        """
        Returns the single index for wich Vdc = V
        Returns false if it doesn't exist
        """
        tmp = where(Vdc==V)[0]
        if tmp.size==0: return False
        return tmp[0]
    #########
    # Plots #
    #########
    ################################
    # Privates/Should never change #
    ################################

class Gain_amplitude(Tunnel_junction):
    """
        v0.1
        - conditions == (n_measures,Vdc,) 
            - n_measures: the maximum number of time to repeat the experiment
            - Vdc       : 1D array of Vdc to use on yokogawa
                - This array must be given 
                    - without interlacing
                    - without a zero as the first element
                    Those will be added automatically
        - devices   == (guzik,yoko) : devices tuple
            - guzik     : a Guzik_wrapper object
            - yoko      : a yokogawa_gs200 object
        - meta_info == (l_kernel,l_data,R_jct,dt)
            - l_kernel  : time_domain length of the autocorrelation function
            - l_data    :  number of data points to be acquired
            - R_jct     :  [ohm]
            - dt        :  [ns]
            #- time_estimates = (total_time,loop_core_time)
 
        Options :
            Interlacing     : reference condition in between each conditions
            Vdc_pos_and_neg : anntisymetrize Vdc  
            test            : if true repeats experiment only once (all Vdcs once)
 
        Todos : 
            - Add convergance parameter in the iterator ?
            - Add an simple/easy way to tell to either use saved data or to recalibrate
                Not sure how i'll implement ...
        Bugs :
            - When calling the same script twice the computed values for S2_sample are bad. 
                Dunno how to fix... not a problem for now
    """
    __version__     = { 'Gain_amplitude'  : 0.1 }
    __version__.update(Tunnel_junction.__version__)
    __version__.update(Yoko_wrapper.__version__)
    __version__.update(Guzik_wrapper.__version__)
    def _init_objects(self):
        self._init_acorr()
    def _build_from_quads(self,quads_info):
        self._l_kernel  = self._l_kernel/2 + 1
        self._l_hc      = self._l_kernel/2 + 1
    def __del__(self):
        self._yoko.set_close_state()
    #######################
    # Extra Gets and sets #
    #######################
    def get_G_mean(self):
        return self.G_of_f.mean(axis=0)
    def get_g_mean(self):
        return sqrt(absolute(self.get_G_mean()),dtype=complex128)
    #############
    # Utilities #
    #############
    def _init_acorr(self):
        self._data          = self._gz.get() # int16
        l_vdc               = len(self._compute_Vdc_experimental(self.Vdc))
        acorr_shape         = ( l_vdc ,) 
        self._acorr         = r_[[ACorrUpTo(self._l_kernel,self._data) for i in range(prod(acorr_shape))]]
        self._acorr.shape   = acorr_shape
    def _compute_Vdc_core_loop(self,Vdc):
        Vdc_loop = self._compute_Vdc_experimental(Vdc)
        return self._compute_next_Vdc(Vdc_loop)
    #################
    # Loop behavior #
    #################
    def _repetition_loop_start(self,n):
        Vdc_0   =   self._compute_Vdc_experimental(self.Vdc)[0]
        print 'Preparing loop : Vdc = {:0.1F}'.format(Vdc_0)
        self._yoko.set_and_wait(Vdc_0) # 1st Vdc
    def _all_loop_close(self):
        print 'closing loop : Vdc = {:0.1F}'.format(0)
        self._yoko.set(0)    
    def _core_loop_iterator(self):
        Vdc = self._compute_Vdc_core_loop(self.Vdc)
        return Experiment._super_enumerate(Vdc)
    def _loop_core(self,index_tuple,condition_tuple):
        """
            Works conditionnaly to the computing being slower than 0.4 sec
        """
        j,          = index_tuple     
        vdc_next,   = condition_tuple   
        self._data = self._gz.get() # int16 
        self._yoko.set(vdc_next)
        self._log.event(0)
        self._acorr[j](self._data)
        self._log.event(1)
    ############
    # Analysis #
    ############
    def _compute_S2_sample(self):
        if self._interlacing :
            a_reference = self._acorr[0:None:2]
            a_condition = self._acorr[1:None:2]
            S2_sample   = zeros( (a_condition.shape[0] , a_condition[0].res.size)  )
            for i, (ref,cond) in enumerate(zip(a_reference,a_condition)) :
                S2_sample[i,:]  =  cond.res - ref.res
        else :
            a_reference = self._acorr[0]
            ref = a_reference
            a_condition = self._acorr[1::]
            S2_sample   = zeros( (a_condition.shape[0] , a_condition[0].res.size)  )
            for i, cond in enumerate( a_condition ) :
                S2_sample[i,:]  =  cond.res - ref.res
        return S2_sample
    def _compute_G(self,S2_sym,R_jct):
        """
        if R is in ohm 
        and _e in coulomb
        then G is in second-1
        """
        V_diff  = self._compute_Vdiffs()
        S2_diff = self._compute_S2diffs(S2_sym)
        dV      = numpy.absolute( V_diff [1,:] - V_diff [0,:] )
        dS2     = S2_diff[0,:] - S2_diff[1,:]
        return  dS2/(dV[:,None]*2.0*self._e*R_jct)
    def _compute_G_of_f(self,G,dt):
        """
        This gives and approximation of G(f) or fourier transform of G(t) if you prefer
        and is not directly the DFT of G(t)    
        """
        return numpy.absolute( dt*numpy.fft.rfft(G) )
    def _compute_G_of_f_unitless(self,G):
        return numpy.absolute( numpy.fft.rfft(G) )
    def _compute_1st_analysis_step_from_objects(self):
        self.S2_sample = self._compute_S2_sample()    
    def _update_data_attributes(self):
        self.S2_windowed        = self._window_after_2ns         (self.S2_sample)
        self.S2_sym             = self._symetrize_S2             (self.S2_windowed)
        self.G_of_t             = self._compute_G                (self.S2_sym,self._R_jct)
        self.G_of_f             = self._compute_G_of_f           (self.G_of_t,dt*10**(-9)) #Has units of dt * units of G(t) here  [Hz-1]*Hz
        self.G_of_f_unitless    = self._compute_G_of_f_unitless  (self.G_of_t)    #[]
    def _update_data(self):
        self._data = [self.S2_sample,self.G_of_t,self.G_of_f,self.G_of_f_unitless]
    def _load_data_list(self,data_list):
        self.S2_sample          = data_list[0]
        self.G_of_t             = data_list[1]
        self.G_of_f             = data_list[2]
        self.G_of_f_unitless    = data_list[3]
    ###################
    # Plots Utilities #
    ###################
    #########
    # Plots #
    #########
    def fig_all_S2_sample_f(self):
        fig     = figure()
        freq    = self._gen_f_abscisse()
        for s2 in self.S2_sym :
            plot(freq,numpy.absolute( numpy.fft.rfft(s2[:]) ))
        return fig
    def fig_all_G_of_t(self):
        fig     =   figure()
        Vdc     =   self._Vdc_antisym
        V_diff  =   (10.0**6)*self._compute_Vdiffs()
        l       =   len(Vdc)/2
        t       =   self._gen_t_abscisse()
        for i, g_2 in enumerate(self.G_of_t):
            plot(t,g_2[:],label="Vdc {:.2f}&{:.2f}".format(V_diff[0,i],V_diff[1,i]))
        legend()
        ax= fig.axes[0]
        ax.set_title('Gain du montage (tout inclue)')
        ax.set_ylabel('G(t)[s-1]')
        ax.set_xlabel('t [ns]')
        return fig
    def fig_all_G_of_f(self):
        fig = figure()
        Vdc     =   self._Vdc_antisym
        V_diff  =   (10.0**6)*self._compute_Vdiffs()
        l       =   len(Vdc)/2
        freq    =   self._gen_f_abscisse()
        for i, g_2 in enumerate(self.G_of_f):
            plot(freq,numpy.absolute( g_2 ),label="Vdc {:.2f}&{:.2f}".format(V_diff[0,i],V_diff[1,i]))
        legend()
        ax= fig.axes[0]
        ax.set_title('Gain du montage (tout inclue)')
        ax.set_ylabel('G(f)[dB]')
        ax.set_xlabel('f [GHz]')
        return fig    
    ################################
    # Privates/Should never change #
    ################################

class PsVsVDC(Tunnel_junction):
    """
        v0.1
        
        Todos : 
            - Build tool that make the productions of gauss_indexes,bigauss_indexes,flat_band easier
            - Puts all the building filters tools in a dedicated class ..?
                - Right now some kernel tools are here and some are in the TimeQuad class
                    What would be the easy uniform way for doing that ?
        Bugs :
    """
    __version__     = { 'Commutator_direct_mesurement'  : 0.1 }
    __version__.update(Tunnel_junction.__version__)
    __version__.update(Yoko_wrapper.__version__)
    __version__.update(Guzik_wrapper.__version__)
    def _set_meta_info(self,meta_info):
        self._hist_info         =   meta_info[4]        # nb_of_bin , max
    def _build_attributes(self):
        self._build_from_hist       (self._hist_info)
    def _build_from_circuit(self,circuit_info):
        self._g     = circuit_info[3]   # R_jct , R_1M , R_tl, g ,V_th
        self._V_th  = circuit_info[4]
    def _build_from_compute(self,compute_info):
        self._l_fft     = compute_info[1]
    def _build_from_quads(self,quads_info):
        # l_kernel, l_hc, df, alpha, gauss_indexes, bigauss_indexes, flat_band
        self._df                =   quads_info[1]
        self._alpha             =   quads_info[2]
        self._kernel_conf       =   0                       # Static for now ==> only one quadrature
        self._filter_params     =   quads_info[3]
        self._gauss_indexes     =   self._filter_params[0]
        self._bigauss_indexes   =   self._filter_params[1]
        self._flat_band         =   self._filter_params[2]
        self._build_filters(self._l_kernel,self._l_hc,self._dt,self._df,self._gauss_indexes,self._bigauss_indexes,self._flat_band)
    def _build_from_hist(self,hist_info):
        self._nb_of_bin         =   int(hist_info[0])
        self._max               =   hist_info[1]  
    def _build_filters(self,l_kernel,l_hc,dt,df,gauss_indexes,bigauss_indexes,flat_band):
        Filters_gauss   , fs_gauss      , labels_gauss      = self._gen_gauss_Filters     (l_kernel,dt,gauss_indexes     ,df)
        Filters_bigauss , fs_bigauss    , labels_bigauss    = self._gen_bigauss_Filters   (l_kernel,dt,bigauss_indexes   ,df)
        Filter_flat_band, fs_flat_band  , label_flat_band   = self._gen_flat_band         (l_hc,dt,flat_band[0],flat_band[1],flat_band[2])
        l_g     =   len(gauss_indexes)
        l_bg    =   len(bigauss_indexes)
        l_fb    =   len(flat_band[0])
        self._gauss_slice       = slice(None        ,l_g            ,None)
        self._bigauss_slice     = slice(l_g         ,l_g+l_bg       ,None)
        self._flat_band_slice   = slice(l_g+l_bg    ,l_g+l_bg+l_fb  ,None)
        self._Filters   = PsVsVDC._concatenate_Filters(Filters_gauss,Filters_bigauss,Filter_flat_band)
        self._n_kernels = self._Filters.shape[0]
        self._fs        = PsVsVDC._concatenate_fs(fs_gauss,fs_bigauss,fs_flat_band)
        self._labels    = labels_gauss + labels_bigauss + label_flat_band
    def _init_objects(self):
        self._init_TimeQuad()
        self._init_Histograms()
    def _init_log(self):
        self._log_dict       = \
        {
        'loop_sizes'    : ( self._n_measures , len(self.Vdc) ),
        'events'        : \
                        {
                            "Aquisition": "Acquisition : {:04.2F} [s]", 
                            "Computing" : "Computing : {:04.2F} [s] "
                        },
        'rate'          : ( self._l_data*1.0e-9 ,"Rate : {:04.2F} [GSa/s] " )\
        }
        # self._time_estimates = for now this is done statically in the class
        Estimated_time_per_loop = 59.33 
        self._time_estimates     = (self._n_measures*Estimated_time_per_loop,Estimated_time_per_loop)
        self._log                = Experiment_log(self._time_estimates , self._log_dict)
    def __del__(self):
        self._yoko.set_close_state()
    #######################
    # Extra Gets and sets #
    #######################
    #############
    # Utilities #
    #############
    @staticmethod
    def find_index_nearest_to_f(f,l_kernel,dt):
        x_f = numpy.fft.rfftfreq(l_kernel , dt)
        if f < min(x_f) or f > max(x_f):
            raise Exception('Outside frequencie range')
        i   = (numpy.abs(x_f-f)).argmin()
        return i
    @staticmethod
    def gen_gauss_input(t_f,l_kernel,dt):
        L = []
        for f in t_f :
            L += [PsVsVDC.find_index_nearest_to_f(f,l_kernel,dt),]
        return numpy.array(L)
    @staticmethod
    def gen_bigauss_input(T_f,l_kernel,dt):
        bigauss_indexes = zeros((len(T_f),2),int)
        for i,t_f in enumerate(T_f) :
            bigauss_indexes[i,:] = PsVsVDC.gen_gauss_input(t_f,l_kernel,dt)
        return bigauss_indexes
    @staticmethod
    def gen_flat_band_input(T_f,l_kernel,dt,rise=0.5,fall=0.5):
        x_f = numpy.fft.rfftfreq(l_kernel , dt)
        flat_band = zeros((len(T_f),2))
        for i,t_f in enumerate(T_f) :
            cdn_0  = all( x-rise > x_f[0] for x in t_f )
            cdn_1  = all( x+fall > x_f[-1] for x in t_f )
            if not(cdn_0 and cdn_1):
                raise Exception('Outside frequencie range')
            flat_band[i,:] = numpy.array(t_f)
        return flat_band , rise , fall
    @staticmethod
    def Wave_function_of_f_normalization(Y,df):
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
            Y[i] =  PsVsVDC.Gaussian ( x_f[i] , f , df ) 
        Delta_f = x_f[1]-x_f[0]
        Y = PsVsVDC.Wave_function_of_f_normalization(Y,Delta_f)
        return Y 
    @staticmethod
    def _Bi_Gaussian_filter_normalized(f1,f2,df1,df2,l_kernel,dt) :
        l_hc = l_kernel//2+1 
        Y = empty( l_hc , dtype = complex , order='C') 
        x_f = numpy.fft.rfftfreq(l_kernel , dt)
        for i in range( l_hc ) :
            Y[i] =  (df1*sqrt(2.0*pi))*PsVsVDC.Gaussian ( x_f[i] , f1 , df1 ) + (df2*sqrt(2.0*pi))*PsVsVDC.Gaussian(x_f[i] , f2 , df2) 
        Delta_f = (x_f[1]-x_f[0])    
        Y = PsVsVDC.Wave_function_of_f_normalization(Y,Delta_f)
        return Y   
    @staticmethod
    def _concatenate_Filters(Filters_gauss,Filters_bigauss,Filter_flat_band):
        if  ((Filters_gauss.size==0)and(Filter_flat_band==0)): 
            return Filters_bigauss 
        elif ((Filters_bigauss.size==0)and(Filter_flat_band==0)):
            return Filters_gauss 
        elif ((Filters_bigauss.size==0)and(Filters_gauss.size==0)):
            return Filter_flat_band 
        else :
            return numpy.concatenate( (Filters_gauss,Filters_bigauss,Filter_flat_band), axis = 0 ) 
    @staticmethod
    def _concatenate_fs(fs_gauss,fs_bigauss,fs_flat_band):
        fs_shape = (fs_gauss.shape[0] + fs_bigauss.shape[0] + fs_flat_band.shape[0] ,2) 
        fs = zeros(fs_shape)
        fs[                         :fs_gauss.shape[0]                  :   ,0] = fs_gauss 
        fs[fs_gauss.shape[0]        :fs_gauss.shape[0]+fs_gauss.shape[0]:   ,:] = fs_bigauss 
        fs[-fs_flat_band.shape[0]   :                                       ,0] = fs_flat_band 
        return fs 
    @staticmethod
    def _gen_gauss_Filters(l_kernel,dt,gauss_indexes,df):
        if gauss_indexes.size == 0 :
            return array([]),array([]),[]
        fs = numpy.fft.rfftfreq(l_kernel,dt)[gauss_indexes]
        labels = []
        Filters = empty( (len(gauss_indexes),l_kernel//2+1) , dtype=complex , order='C' ) 
        for i,f in enumerate(fs) :
            Filters[i,:] = PsVsVDC.Gaussian_filter_normalized( f , df , l_kernel, dt ) 
            label = "{:0.1f} \pm {:0.1f}".format(f, df)
            labels.append(label)
        return Filters , fs , labels    
    @staticmethod
    def _gen_bigauss_Filters(l_kernel,dt,bigauss_indexes,df):
        """
            bigauss_indexes is a n by 2 array
        """
        if bigauss_indexes.size ==0 :
            return array([]),array([]), []
        if bigauss_indexes.shape[1] !=2 :
            raise Exception('bigauss_indexes needs to be n by 2.')
        fs = zeros(bigauss_indexes.shape)
        fs[:,0] = numpy.fft.rfftfreq(l_kernel,dt)[bigauss_indexes[:,0]]
        fs[:,1] = numpy.fft.rfftfreq(l_kernel,dt)[bigauss_indexes[:,1]]
        labels = []
        Filters = empty( (bigauss_indexes.shape[0],l_kernel//2+1) , dtype=complex , order='C' ) 
        for i,f in enumerate(fs) :
            Filters[i,:] = PsVsVDC._Bi_Gaussian_filter_normalized(f[0],f[1],df,df,l_kernel,dt) 
            label = "{:0.1f}&{:0.1f} \pm {:0.1f}".format(f[0],f[1],df)
            labels.append(label)
        return Filters , fs , labels 
    @staticmethod
    def _gen_flat_band(l_hc,dt,flat_band,rise,fall):
        # rise    = 0.5    # size of the transition for the edge of the filter in GHz
        if flat_band.size ==0 :
            return array([]),array([]),[]
        fs          = zeros(flat_band.shape[0])
        labels      = []
        Filters     = empty( (flat_band.shape[0],l_hc),dtype=complex,order='C' ) 
        for i,flat in enumerate(flat_band) :
            fs[i]           = (flat[0]+flat[1])/2.0 
            label           = "{:0.1f}-{:0.1f}".format(flat[0], flat[1]) 
            labels.append(label)    
            Filters[i,:]    = TimeQuad_uint64_t.compute_flat_band (l_hc,dt,flat[0]-rise,flat[0],flat[1],flat[1]+fall) 
        return Filters , fs , labels       
    def _init_TimeQuad(self):
        self._X       = TimeQuad_uint64_t(self._R_tl,self._dt,self._l_data,self._kernel_conf,self._Filters,self._g,self._alpha,self._l_fft,self._n_threads)
        self.betas   = self._X.betas()
        self.filters = self._X.filters()
        self.ks      = self._X.ks()
        self.qs      = self._X.quads()[0,:,:]
        self._data   = self._gz.get() # int16
        self._X.execute( self._data )
    def _init_Histograms(self):
        l_Vdc = len(self._compute_Vdc_experimental(self.Vdc))
        
        Hs_shape = (l_Vdc , self._n_kernels )
        self.Hs = r_[[Histogram_uint64_t_double(nb_of_bin,n_threads,max) for i in range(prod(Hs_shape))]] 
        self.Hs.shape = Hs_shape 
        self._H_x = self.Hs[0,0].abscisse(max)  #Should be made static and called static 
        for j in range (l_Vdc):
            for i in range(self._n_kernels):
                self.Hs[j,i].accumulate( self.qs[i,:]) # dummy data
    def _reset_Hs(self):
        l_Vdc = len(self._compute_Vdc_experimental(self.Vdc))
        for j in range (l_Vdc):
            for i in range(self._n_kernels):
                self.Hs[j,i].reset()
    def _compute_Vdc_core_loop(self,Vdc):
        Vdc_loop = self._compute_Vdc_experimental(Vdc)
        return self._compute_next_Vdc(Vdc_loop)
    def _compute_moments(self):
        """
            Ordre>
              0       <q>
              1       <q**2>
              2       <q**4>
              3       <q**8>
        """
        n_kernels = self._n_kernels
        n_threads = self._n_threads
        l_Vdc = len(self._compute_Vdc_experimental(self.Vdc))
        moments = numpy.zeros((4,n_kernels,l_Vdc),dtype=float) 
        
        Hs  = self.Hs
        H_x = self._H_x
        
        n_total = int( Hs[0,0].moment_no_clip(bins=H_x,exp=0,n_total=1,n_threads=n_threads) )
        for i in range(n_kernels) :
            for j in range(len(self._Vdc_exp)) :
                moments[0,i,j] = Hs[j,i].moment_no_clip(bins=H_x,exp=1,n_total=n_total,n_threads=n_threads)
                moments[1,i,j] = Hs[j,i].moment_no_clip(bins=H_x,exp=2,n_total=n_total,n_threads=n_threads)
                moments[2,i,j] = Hs[j,i].moment_no_clip(bins=H_x,exp=4,n_total=n_total,n_threads=n_threads)
                moments[3,i,j] = Hs[j,i].moment_no_clip(bins=H_x,exp=8,n_total=n_total,n_threads=n_threads)
                # Hs[j,i].reset()
        return moments
    @staticmethod  
    def _compute_errors(moments,n):
        shape = moments.shape
        errors = numpy.zeros((shape[0]-1,shape[1],shape[2]),dtype=float) 
        errors[0,:,:] = Experiment.SE(moments[1,:,:],moments[0,:,:],n)
        errors[1,:,:] = Experiment.SE(moments[2,:,:],moments[1,:,:],n)
        errors[2,:,:] = Experiment.SE(moments[3,:,:],moments[2,:,:],n)
        return errors
    #################
    # Loop behavior #
    #################
    def _all_loop_open(self):
        self._reset_Hs()
    def _repetition_loop_start(self,n):
        Vdc_0   =   self._compute_Vdc_experimental(self.Vdc)[0]
        print 'Preparing loop : Vdc = {:0.1F}'.format(Vdc_0)
        self._yoko.set_and_wait(Vdc_0) # 1st Vdc
    def _core_loop_iterator(self):
        Vdc = self._compute_Vdc_core_loop(self.Vdc)
        return Experiment._super_enumerate(Vdc)
    def _loop_core(self,index_tuple,condition_tuple):
        """
            Works conditionnaly to the computing being slower than 0.4 sec
        """
        j,          = index_tuple     
        vdc_next,   = condition_tuple   
        self._data  = self._gz.get() # int16 
        self._yoko.set(vdc_next)
        self._log.event(0)
        self._X.execute(self._data)
        for i in range(self._n_kernels):
            self.Hs[j,i].accumulate( self.qs[i,:])
        self._log.event(1)
    def _all_loop_close(self):
        print 'closing loop : Vdc = {:0.1F}'.format(0)
        self._yoko.set(0)  
    ######################
    # Analysis Utilities #
    ######################
    def _moments_correction(self,moments):
        h = self._X.half_norms()[0,:]
        n_kernels = moments.shape[1]
        moments_corrected = numpy.empty(moments.shape,dtype=float)
        for i in range(n_kernels):
            moments_corrected[0,i,:] = (h[i]**1) * moments[0,i,:] 
            moments_corrected[1,i,:] = (h[i]**2) * moments[1,i,:] 
            moments_corrected[2,i,:] = (h[i]**4) * moments[2,i,:] 
            moments_corrected[3,i,:] = (h[i]**8) * moments[3,i,:] 
        return moments_corrected 
    @staticmethod
    def _compute_cumulants(moments):
        cumulants           = numpy.zeros( moments.shape ,dtype=float)
        cumulants[0,:,:]    = moments[0,:,:] 
        cumulants[1,:,:]    = moments[1,:,:] 
        cumulants[2,:,:]    = moments[2,:,:]     - 3.0*(moments[1,:,:] + 0.5 )**2  # <p**4> -3 <p**2> **2
        return cumulants
    @staticmethod
    def _compute_cumulants_std(moments,moments_std):
        cumulants_std           = numpy.zeros( moments.shape ,dtype=float)
        cumulants_std[0,:,:]    = moments_std[0,:,:] 
        cumulants_std[1,:,:]    = moments_std[1,:,:] 
        cumulants_std[2,:,:]    = moments_std[2,:,:] - 6.0*(moments[1,:,:] + 0.5 )*(moments_std[1,:,:])  # <p**4> -3 <p**2> **2
        return cumulants_std
    def _compute_cumulants_sample(self,cumulants):
        if self._interlacing :
            ref =  cumulants[:,::2]
            cdn =  cumulants[:,1::2]
            cumulants_sample = cdn - ref
        else :
            ref =  cumulants[:,:,0]
            cdn =  cumulants[:,:,1::]
            cumulants_sample = cdn - ref[:,:,None]
        return cumulants_sample
    def _compute_cumulants_sample_std(self,cumulants_std):
        if self._interlacing :
            ref =  cumulants_std[:,::2]
            cdn =  cumulants_std[:,1::2]
            cumulants_sample = cdn + ref
        else :
            ref =  cumulants_std[:,:,0]
            cdn =  cumulants_std[:,:,1::]
            cumulants_sample = cdn + ref[:,:,None]
        return cumulants_sample
    @staticmethod
    def _compute_C4(cumulants_sample):
        C4 = numpy.empty( cumulants_sample[0,:,:].shape ,dtype=float) 
        C4[:,:] = cumulants_sample[2,:,:] 
        return C4 
    @staticmethod
    def _compute_ns(cumulants_sample):
        """
            0 : <n>
            1 : <n**2>
            2 : <dn**2>
            3 : fano
        """
        n_kernels   = cumulants_sample.shape[1]
        ns          = numpy.empty((4,n_kernels,cumulants_sample.shape[-1]),dtype=float)
        ns[0,:,:]   = cumulants_sample[1,:,:] 
        ns[1,:,:]   = (2.0/3.0)*cumulants_sample[2,:,:] + 2.0*cumulants_sample[1,:,:]**2 - cumulants_sample[1,:,:] 
        ns[2,:,:]   = (2.0/3.0)*cumulants_sample[2,:,:] +     cumulants_sample[1,:,:]**2 
        ns[3,:,:]   = ns[2,:,:]/ns[0,:,:]
        return ns 
    @staticmethod
    def _linear_fit_of_C4(n,C4,V_jct,V_th):
        # V_th : threshold above which eV>>hf
        C4 = C4[:,V_jct>V_th] 
        n  = n[:,V_jct>V_th] 
        fit_params = zeros((2,n.shape[0])) 
        for i,(nn,cc) in enumerate(zip(n,C4)) :
            fit_params[:,i] = numpy.polyfit(transpose(nn),transpose(cc),1)
        return fit_params 
    @staticmethod
    def _slope_of_linear_fit_of_C4(n,C4,V_jct,V_th):
        return PsVsVDC._linear_fit_of_C4(n,C4,V_jct,V_th)[0,:] 
    @staticmethod
    def _gen_C4_fit_vector(n,C4,V_jct,V_th):
        fit_params = PsVsVDC._linear_fit_of_C4(n,C4,V_jct,V_th)
        a = fit_params[0,:]
        b = fit_params[1,:]
        return n*a[:,None] + b[:,None] 
    @staticmethod
    def _compute_ns_corrected(ns,cumulants_sample,Vdc_source,R_jct,R_1M,V_th):
        C4      = PsVsVDC._compute_C4(cumulants_sample) 
        V_jct   = PsVsVDC._compute_Vdc_jct(Vdc_source,R_jct,R_1M)
        n = cumulants_sample[1,:,:]
        a = PsVsVDC._slope_of_linear_fit_of_C4(n,C4,V_jct,V_th)
        ns_corr = numpy.empty((ns.shape),dtype=float)    
        ns_corr[0,:,:] = n 
        ns_corr[1,:,:] = (2.0/3.0)*(cumulants_sample[2,:,:]- a[:,None]*n) + 2.0*n**2 - n 
        ns_corr[2,:,:] = (2.0/3.0)*(cumulants_sample[2,:,:]- a[:,None]*n) +     n**2 
        ns_corr[3,:,:] = ns[2,:,:]/n 
        return ns_corr  
    @staticmethod
    def _compute_ns_std(ns,cumulants_sample,cumulants_sample_std):
        n_kernels = cumulants_sample.shape[1]
        ns_std = numpy.empty((4,n_kernels,cumulants_sample_std.shape[-1]),dtype=float)
        ns_std[0,:,:] = (cumulants_sample_std[1,:,:])
        ns_std[1,:,:] = (2.0/3.0)*cumulants_sample_std[2,:,:] + 4.0*cumulants_sample_std[1,:,:]*cumulants_sample[1,:,:] - cumulants_sample_std[1,:,:]
        ns_std[2,:,:] = (2.0/3.0)*cumulants_sample_std[2,:,:] + 2.0*cumulants_sample_std[1,:,:]*cumulants_sample[1,:,:] 
        ns_std[3,:,:] = ns_std[2,:,:]/ns[0,:,:]   + ns[2,:,:]*(ns_std[0,:,:]/ns[0,:,:]**2)
        return ns_std 
    ############
    # Analysis #
    ############
    def _compute_1st_analysis_step_from_objects(self):
        self.moments = self._compute_moments()
        self.moments = self._moments_correction(self.moments)    
    def _update_data_attributes(self):
        self.moments_std            = self._compute_errors(self.moments,self._n_measures*self._l_data)
        self.cumulants              = self._compute_cumulants(self.moments)
        self.cumulants_std          = self._compute_cumulants_std(self.moments,self.moments_std)
        self.cumulants_sample       = self._compute_cumulants_sample(self.cumulants)
        self.cumulants_sample_std   = self._compute_cumulants_sample_std(self.cumulants_std)
        self.ns                     = self._compute_ns(self.cumulants_sample)
        self.ns_std                 = self._compute_ns_std(self.ns,self.cumulants_sample,self.cumulants_sample_std)
        self.ns_corrected           = self._compute_ns_corrected(self.ns,self.cumulants_sample,self._compute_Vdc_antisym(self.Vdc),self._R_jct,self._R_1M,self._V_th)
        self.C4                     = self._compute_C4(self.cumulants_sample)
    def _update_data(self):
        self._data = [\
                self.moments,
                self.moments_std,
                self.cumulants,
                self.cumulants_std,
                self.cumulants_sample,
                self.cumulants_sample_std,
                self.ns ,
                self.ns_std ,
                self.ns_corrected ,
                self.C4 
                ]
    def _load_data_list(self,data_list):
        self.moments                = data_list[0]
        self.moments_std            = data_list[1]
        self.cumulants              = data_list[2]
        self.cumulants_std          = data_list[3]
        self.cumulants_sample       = data_list[4]
        self.cumulants_sample_std   = data_list[5]
        self.ns                     = data_list[7]
        self.ns_std                 = data_list[8]
        self.ns_corrected           = data_list[9]
        self.C4                     = data_list[10]
    ###################
    # Plots Utilities #
    ###################
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
    @staticmethod
    def _plot_n(I_jct,ns,ns_std,kernel_index,axs,errorbar=True,**plot_kw):
        if errorbar:
            plot_kw['capsize'] = 2.5
            axs.errorbar(I_jct*10**6,ns[0,kernel_index,:],yerr=ns_std[0,kernel_index,:],**plot_kw) 
        else :
            axs.plot(I_jct*10**6,ns[0,kernel_index,:],**plot_kw) 
        axs.title.set_text('<n> for the sample')
        axs.set_ylabel('Photon/mode')
        axs.set_xlabel('I_jct [uA]')
    @staticmethod
    def _plot_n2(I_jct,ns,ns_std,kernel_index,axs,errorbar=True,**plot_kw):
        if errorbar:
            plot_kw['capsize'] = 2.5
            axs.errorbar(I_jct*10**6,ns[1,kernel_index,:],yerr=ns_std[1,kernel_index,:],**plot_kw)
        else :
            axs.plot(I_jct*10**6,ns[1,kernel_index,:],**plot_kw)
        axs.title.set_text('<n**2> for the sample')
        axs.set_xlabel('I_jct [uA]')
    @staticmethod
    def _plot_dn2(I_jct,ns,ns_std,kernel_index,axs,errorbar=True,**plot_kw):
        if errorbar:
            plot_kw['capsize'] = 2.5
            axs.errorbar(I_jct*10**6,ns[2,kernel_index,:],ns_std[2,kernel_index,:],**plot_kw)
        else :
            axs.plot(I_jct*10**6,ns[2,kernel_index,:],**plot_kw)
        axs.title.set_text('Var(n) for the sample')
        axs.set_xlabel('I_jct [uA]')
    @staticmethod
    def _plot_dn2_vs_n(ns,ns_std,kernel_index,axs,errorbar=True,**plot_kw):
        plot_kw_2 = {'linestyle':'--','marker':'*','label':"n(n+1)"}
        if errorbar:
            plot_kw['capsize'] = 2.5
            axs.errorbar(ns[0,kernel_index,:],ns[2,kernel_index,:],ns_std[2,kernel_index,:],**plot_kw)
        else :
            axs.plot(ns[0,kernel_index,:],ns[2,kernel_index,:],**plot_kw)
        n = ns[0,kernel_index,:]
        axs.plot(n,n**2,**plot_kw_2)
        axs.legend()
        axs.set_xlabel('<n>')
        axs.set_ylabel('Var(n)')
    @staticmethod
    def _plot_diff_n_0_2_dn2(ns,ns_std,kernel_index,axs,errorbar=True,**plot_kw):
        axs.plot(ns[0,kernel_index,:],ns[0,kernel_index,:]**2-ns[2,kernel_index,:],**plot_kw)
        axs.legend()
        axs.set_xlabel('<n>')
    @staticmethod
    def _plot_sum_of_n(I_jct,ns,ns_std,i,j,axs,errorbar=True,**plot_kw):
        n1 = ns[0,i,:]
        n2 = ns[0,j,:]
        sum = (0.5)*(n1+n2)
        n1_std = ns_std[0,i,:]
        n2_std = ns_std[0,j,:]
        sum_std = (0.5)*(n1_std+n2_std)
        if errorbar:
            plot_kw['capsize'] = 2.5
            axs.errorbar(I_jct*10**6,sum,yerr=sum_std,**plot_kw) 
        else :
            axs.plot(I_jct*10**6,sum,**plot_kw) 
        axs.title.set_text('<n> for the sample')
        axs.set_ylabel('Photon/mode')
        axs.set_xlabel('I_jct [uA]')
    @staticmethod
    def _plot_sum_of_dn2(I_jct,ns,ns_std,i,j,axs,errorbar=True,**plot_kw):
        n1 = ns[2,i,:]
        n2 = ns[2,j,:]
        sum = (0.25)*(n1+n2)
        n1_std = ns_std[2,i,:]
        n2_std = ns_std[2,j,:]
        sum_std = (0.25)*(n1_std+n2_std)
        if errorbar:
            plot_kw['capsize'] = 2.5
            axs.errorbar(I_jct*10**6,sum,yerr=sum_std,**plot_kw) 
        else :
            axs.plot(I_jct*10**6,sum,**plot_kw) 
        axs.set_ylabel('Var(n)[s-2]')
        axs.set_xlabel('I_jct [uA]')
    ###########
    # Figures #
    ###########
    # Meant for validation
    def _fig_hist(self,V_indexes,kernel_indexes):
        fig = figure()
        ax = gca()
        for v in V_indexes :
            for k in kernel_indexes :
                ax.plot(self.Hs[v,k].get())
    def _fig_q(self,kernel_slice=slice(None)):
        labels          = self._labels
        fs              = self._fs
        I_jct           = self._compute_I_jct(self._Vdc_exp,self._R_1M)
        moments         = self.moments
        plot_kw = {'linestyle':'-'}
        fig , axs = subplots(1,1)
        for i, label in enumerate(labels[kernel_slice]):
            plot_kw['label'] = label 
            axs.plot(I_jct*10**6,moments[0,i,:],**plot_kw) 
            # axs.errorbar(I_jct*10**6,ns[0,i,:],yerr=ns_std[0,i,:],**plot_kw) 
        axs.legend()
        axs.title.set_text('<q>')
        axs.set_ylabel('')
        axs.set_xlabel('I_jct [uA]')
    def _fig_q2(self,kernel_slice=slice(None)):
        labels          = self._labels
        fs              = self._fs
        I_jct           = self._compute_I_jct(self._Vdc_exp,self._R_1M)
        moments         = self.moments
        plot_kw = {'linestyle':'-'}
        fig , axs = subplots(1,1)
        for i, label in enumerate(labels[kernel_slice]):
            plot_kw['label'] = label 
            axs.plot(I_jct*10**6,moments[1,i,:],**plot_kw) 
            # axs.errorbar(I_jct*10**6,ns[0,i,:],yerr=ns_std[0,i,:],**plot_kw) 
        axs.legend()
        axs.title.set_text('<q**2>')
        axs.set_ylabel('')
        axs.set_xlabel('I_jct [uA]')
    def _fig_q4(self,kernel_slice=slice(None)):
        labels          = self._labels
        fs              = self._fs
        I_jct           = self._compute_I_jct(self._Vdc_exp,self._R_1M)
        moments         = self.moments
        plot_kw = {'linestyle':'-'}
        fig , axs = subplots(1,1)
        for i, label in enumerate(labels[kernel_slice]):
            plot_kw['label'] = label 
            axs.plot(I_jct*10**6,moments[2,i,:],**plot_kw) 
            # axs.errorbar(I_jct*10**6,ns[0,i,:],yerr=ns_std[0,i,:],**plot_kw) 
        axs.legend()
        axs.title.set_text('<q**4>')
        axs.set_ylabel('')
        axs.set_xlabel('I_jct [uA]')
    def _fig_q8(self,kernel_slice=slice(None)):
        labels          = self._labels
        fs              = self._fs
        I_jct           = self._compute_I_jct(self._Vdc_exp,self._R_1M)
        moments         = self.moments
        plot_kw = {'linestyle':'-'}
        fig , axs = subplots(1,1)
        for i, label in enumerate(labels[kernel_slice]):
            plot_kw['label'] = label 
            axs.plot(I_jct*10**6,moments[3,i,:],**plot_kw) 
            # axs.errorbar(I_jct*10**6,ns[0,i,:],yerr=ns_std[0,i,:],**plot_kw) 
        axs.legend()
        axs.title.set_text('<q**8>')
        axs.set_ylabel('')
        axs.set_xlabel('I_jct [uA]')      
    # Meant for analysis
    def fig_filters(self):
        fig, ax = subplots(1,1)
        self._plot_Filters(self.filters,self._labels,ax,l_dft = self._l_kernel, dt=self._dt)
        ax.set_title('betas*1/g(f)')
        ax.set_ylabel('[GHz^-1/2]/[~]')
        return fig  
    def fig_betas(self):
        fig, ax = subplots(1,1)
        self._plot_Filters(self.betas,self._labels,ax,l_dft = self._l_kernel, dt=self._dt)
        ax.set_title('beta(f)')
        ax.set_ylabel('[GHz^-1/2]')
        return fig
    def fig_kernels_t(self):
        fig, axs = subplots(1,1)
        ts = self._gen_t_abscisse() 
        PsVsVDC._plot_Kernels(ts,self.ks,self._labels,axs,self._dt)
        fig.suptitle('half-normalized kernels')
        return fig 
    def fig_Kernels_f(self):
        fig, axs = subplots(1,1)
        freqs = self._gen_f_abscisse()
        PsVsVDC._plot_Kernels_FFT(freqs,self.ks,self._labels,axs,dt)
        fig.suptitle('half-normalized kernels')
        return fig 
    def fig_n_no_fs(self,gauss_slice=slice(None)):
        """
            Filters gaussien / f_0
        """
        if gauss_slice == slice(None):
            gauss_slice     = self._gauss_slice
        labels          = self._labels
        ns              = self.ns
        fs              = self._fs
        I_jct           = self._compute_I_jct(self._Vdc_antisym,self._R_1M)
        plot_kw     = {'linestyle':'-'}
        fig , axs = subplots(1,1)
        for i, label in enumerate(labels[gauss_slice]):
            plot_kw['label'] = label 
            axs.plot(I_jct*10**6,ns[0,i,:]*fs[i,0],**plot_kw)
        axs.legend()
        axs.title.set_text('<n>/f0')
        axs.set_xlabel('Vdc source [V]')
        return fig 
    def _fig_ns(self,kernel_slice,plot_fct):
        """
            Code commun pour les figures <n>,<n**2>,<dn**2>
        """
        labels          = self._labels
        fs              = self._fs
        I_jct           = self._compute_I_jct(self._Vdc_antisym,self._R_1M)
        ns              = self.ns
        ns_std          = self.ns_std
        plot_kw = {'linestyle':'-'}
        fig , axs = subplots(1,1)
        for i, label in enumerate(labels[kernel_slice]):
            plot_kw['label'] = label 
            plot_fct(I_jct,ns,ns_std,i,axs,errorbar=False,**plot_kw)
        axs.legend()
        return fig 
    def fig_n(self,kernel_slice=slice(None)):
        """
             <n>
        """
        plot_fct = PsVsVDC._plot_n
        fig = self._fig_ns(kernel_slice,plot_fct)
        return fig 
    def fig_n2(self,kernel_slice=slice(None)):
        """
            <n^2>
        """
        plot_fct = PsVsVDC._plot_n2
        fig = self._fig_ns(kernel_slice,plot_fct)
        return fig 
    def fig_dn2(self,kernel_slice=slice(None)):
        """
            Var n
        """
        plot_fct = PsVsVDC._plot_dn2
        fig = self._fig_ns(kernel_slice,plot_fct)
        return fig 
    def _fig_ns_vs_n(self,kernel_slice,plot_fct):
        """
            Code commun pour les figures dn2_vs_n, diff_n_0_2_dn2
        """
        labels          = self._labels
        fs              = self._fs
        ns              = self.ns
        ns_std          = self.ns_std
        plot_kw = {'linestyle':'-'}
        fig , axs = subplots(2,len(labels)/2 + len(labels)%2 )
        AXS = fig.axes 
        for i, label in enumerate(labels[kernel_slice]):
            plot_kw['label'] = label 
            plot_fct(ns,ns_std,i,AXS[i],errorbar=False,**plot_kw)
        return fig 
    def fig_dn2_vs_n(self,kernel_slice=slice(None)):
        """
            Var n vs n avec n(n+1)
        """
        plot_fct = PsVsVDC._plot_dn2_vs_n
        fig = self._fig_ns_vs_n(kernel_slice,plot_fct)
        return fig 
    def fig_diff_n_0_2_dn2(self,kernel_slice=slice(None)):
        """
            Difference entre Var n et n(n+1)
        """
        plot_fct = PsVsVDC._plot_diff_n_0_2_dn2
        fig = self._fig_ns_vs_n(kernel_slice,plot_fct)
        return fig 
    def fig_C4(self,kernel_slice=slice(None)):
        """
            C4 avant correction 
        """ 
        labels          = self._labels
        fs              = self._fs
        I_jct           = self._compute_I_jct(self._Vdc_antisym,self._R_1M)
        C4              = self.C4
        plot_kw = {'linestyle':'-'}
        fig , axs = subplots(1,1)
        for i, label in enumerate(labels[kernel_slice]):
            plot_kw['label'] = label 
            axs.plot(I_jct*10**6,C4[i,:],**plot_kw)
        axs.legend()
        axs.title.set_text('C4')
        axs.set_xlabel('I_jct [uA]')
        return fig 
    def fig_C4_and_fit_C4(self,kernel_slice=slice(None)):
        labels          = self._labels
        fs              = self._fs
        V_jct           = self._compute_Vdc_jct(self._Vdc_antisym,self._R_jct,self._R_1M)
        C4              = self.C4
        n               = self.ns[0,:,:] 
        V_th            = self._V_th
        plot_kw_0 = {'linestyle':'-','marker':'*'}
        plot_kw_1 = {'linestyle':'dotted'}
        fig , axs = subplots(1,1)
        fit_C4 = PsVsVDC._gen_C4_fit_vector(n,C4,V_jct,V_th)
        for i, label in enumerate(labels[kernel_slice]):
            color = next(axs._get_lines.prop_cycler)['color']
            plot_kw_0['label'] = label 
            plot_kw_0['color'] = color 
            plot_kw_1['color'] = color 
            axs.plot(n[i,:],C4[i,:],**plot_kw_0)
            axs.plot(n[i,:],fit_C4[i,:],**plot_kw_1)
        axs.legend()
        axs.title.set_text('C4')
        axs.set_xlabel('<n>')
        return fig
    def fig_sum_of_ns(self,kernel_slice=slice(None)):
        """
            Somme des n
        """
        gauss_slice     = self._gauss_slice
        
        labels          = self._labels
        fs              = self._fs
        I_jct           = self._compute_I_jct(self._Vdc_antisym,self._R_1M)
        ns              = self.ns
        ns_std          = self.ns_std
        plot_kw = {'linestyle':'-'}
        plot_kw_1 = {'linestyle':'--','marker':'*'}
        fig , axs = subplots(1,1)
        for i, label in enumerate(labels[kernel_slice]):
            plot_kw['label'] = label 
            PsVsVDC._plot_n(I_jct,ns,ns_std,i,axs,errorbar=False,**plot_kw)
        
        for i, label in enumerate(labels[gauss_slice]):
            for j in range(i):
                plot_kw_1['label'] = '1/2({:.1f}+{:.1f})'.format(fs[i,0],fs[j,0]) 
                PsVsVDC._plot_sum_of_n(I_jct,ns,ns_std,i,j,axs,errorbar=False,**plot_kw_1)
        axs.legend()
        return fig 
    def fig_sum_of_Var_ns(self,kernel_slice=slice(None)):
        """
            Somme des Var n
        """
        gauss_slice     = self._gauss_slice
        
        labels          = self._labels
        fs              = self._fs
        I_jct           = self._compute_I_jct(self._Vdc_antisym,self._R_1M)
        ns              = self.ns
        ns_std          = self.ns_std
        plot_kw = {'linestyle':'-'}
        plot_kw_1 = {'linestyle':'--','marker':'*'}
        fig , axs = subplots(1,1)
        for i, label in enumerate(labels[kernel_slice]):
            plot_kw['label'] = label 
            PsVsVDC._plot_dn2(I_jct,ns,ns_std,i,axs,errorbar=False,**plot_kw)
        for i, label in enumerate(labels[gauss_slice]):
            for j in range(i):
                plot_kw_1['label'] = '1/4({:.1f}+{:.1f})'.format(fs[i,0],fs[j,0]) 
                PsVsVDC._plot_sum_of_dn2(I_jct,ns,ns_std,i,j,axs,errorbar=False,**plot_kw_1)
        axs.legend()
        return fig 
    ################################
    # Privates/Should never change #
    ################################










