'''
DEER
=======================================================================
An NVAveragerProgram class that generates and executes a measurement which takes
four measurements while PUT THE DESCRIPTION HERE
'''

from .nvaverageprogram import NVAveragerProgram
from .nvqicksweep import NVQickSweep

import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import os

class DEER(NVAveragerProgram):
    '''
    An NVAveragerProgram class that generates and executes a sequencePUT THE DESCRIPTION HERE 
    Parameters
    -------------------------------------------------------------------
    soccfg
        instance of qick.QickConfig class
    cfg
        instance of qickdawg.NVConfiguration class with attributes:
        .adc_channel (required)
            int channel which is reading data 0 or 1

        .mw_channel (required)
            qick channel that provides microwave excitation
            0 or 1 for RFSoC4x2
            0 to 6 for ZCU111 or ZCU216
        .mw_nqz (required)
            nyquist zone for microwave generator (1 or 2)
        .mw_gain (required)
            gain of micrwave channel, in register values, from 0 to 2**15-1

        .pre_init (required)
            boolian value that indicates whether to pre-pulse the laser to initialize
            the spin state

        .relax_delay_treg (required)
            int that indicates how long to delay between on/off cycles and reps
            in register units
        .readout_length_treg (required)
            int time for which the adc accumulates data
            the limit is 1020 points for the FPGA buffer
        .laser_readout_offset_treg (required)

        .laser_gate_pmod(required)
            int PMOD channel used to trigger laser source
            0 to 4
        .t1
            t1 time 
        .t2 
            t2 time found from a Hahn echo pulse sequence 
    returns
        an instances of LockinODMR class with assembly language compiled


    Methods
    -------
    initialize
        method that generates the assembly code that setups the adcs &  mw generators,
        and performs other one-off setps
    body
        method that generates the assembly code that exectues in the middle of each sweep
        and rep
    plot_sequence
        generates a plot labeled with self.cfg attributes or the required inputs
    time_per_rep
        returns the approximatetime for one rep to complete
    total_time
        returns the approximate total time for the entire program to complete

    '''
    required_cfg = [
            "adc_channel",
            "readout_integration_treg",
            "mw_channel",
            "mw_nqz",
            "mw_pi2_treg",
            "mw_gain",
            "scaling_mode",
            "delay_start_treg",
            "delay_end_treg",
            "nsweep_points",
            "pre_init",
            "laser_gate_pmod",
            "laser_on_treg",
            "relax_delay_treg",
            "readout_delay_treg",
            "reps",
            "readout_reference_start_treg",
            "laser_readout_offset_treg",
            "mw_readout_delay_treg",
            "t1",
            "t2",
            "pump_channel",
            "pump_nqz",
            "pump_freq"]

    def initialize(self):
        '''Method that generates the assembly code that is sets up adcs and sources.

        For HahnEchoDelaySweep this:
        1. Configures the adc to acquire points for self.cfg.readout_integration_t#
        2. Configures the microwave channel
        3. Configures the sweep parameters
        4. Initiailzes the spin state with a laser pulse
        '''
        self.check_cfg()

        self.declare_readout(ch=0,
                             freq=0,
                             length=self.cfg.readout_integration_treg,
                             sel="input")

        # Get registers for mw

        # Declaring register for mw signal 
        self.declare_gen(ch=self.cfg.mw_channel,
                         nqz=self.cfg.mw_nqz)
        # Declaring register for pump mw signal 
        self.declare_gen(ch=self.cfg.pump_channel, 
                         nqz=self.cfg.pump_nqz)
        
        # Setup pulse defaults microwave
        self.default_pulse_registers(ch=self.cfg.mw_channel,
                                     style='const',
                                     freq=self.cfg.mw_freg,
                                     length=self.cfg.mw_pi2_treg,
                                     gain=self.cfg.mw_gain)
        
        self.default_pulse_registers(ch=self.cfg.pump_channel,
                                     style='const',
                                     freq=self.cfg.pump_freg,
                                     length=self.cfg.mw_pi2_treg,
                                     gain=self.cfg.mw_gain)
        

        self.set_pulse_registers(ch=self.cfg.mw_channel,
                                 phase=0)
        
        
        self.set_pulse_registers(ch=self.cfg.pump_mw,
                                 phase=0)

        # Addd loops


        self.delay_register_pump = self.new_gen_reg(self.cfg.pump_channel,
                                               name='delay',
                                               init_val=self.cfg.delay_start_treg)

        self.time_register_pump = self.get_gen_reg(self.cfg.pump_channel,
                                                 name='t')

        
        self.delay_register_mwt1 = self.new_gen_reg(self.cfg.mw_channel,
                                               name="t1delay",
                                               init_val=self.cfg.t1_treg)
        self.time_register_mwt1 = self.get_gen_reg(self.cfg.mw_channel,
                                                 name='t1delay')
       
        self.delay_register_mwt2 = self.new_gen_reg(self.cfg.mw_channel,
                                               name="t2delay",
                                               init_val=self.cfg.t2_treg)
        self.time_register_mwt2 = self.get_gen_reg(self.cfg.mw_channel,
                                                 name='t2delay')
        
        
        

        if self.cfg.scaling_mode == 'exponential':
            self.add_sweep(NVQickSweep(
                self,
                self.delay_register_pump,
                self.cfg.delay_start_treg,
                self.cfg.delay_end_treg,
                expts=self.cfg.nsweep_points,
                scaling_mode=self.cfg.scaling_mode,
                scaling_factor=self.cfg.scaling_factor))

        elif self.cfg.scaling_mode == 'linear':
            self.add_sweep(NVQickSweep(
                self,
                self.delay_register_pump,
                self.cfg.delay_start_treg,
                self.cfg.delay_end_treg,
                self.cfg.nsweep_points))
        else:
            assert 0, 'cfg.scaling_mode must be "linear" or "exponential"'

        self.synci(400)  # give processor some time to self.cfgure pulses

        if self.cfg.pre_init:
            self.trigger(
                pins=[self.cfg.laser_gate_pmod],
                width=self.cfg.laser_on_treg,
                adc_trig_offset=0
            )
            self.sync_all(self.cfg.laser_on_treg + self.cfg.relax_delay_treg)

    def body(self):
        '''
        NEED TO MAKE THIS RIGHT 
        Method that generates the assembly code that is looped over or repeated.
        For HahnEchoDelaySweep this peforms four measurements at a time and does two pulse
        sequences differing only by the phase of the final pulse.  The sequences is:
        1. Set pulse phase to 0
        2. Pulse mw for pi/2
        3. delay by variable delay time
        4. pulse mw for 2x pi/2
        5. delay by variable delay time
        6. pulse mw for pi/2 (on second sequence change the phase to 180 degrees)
        7. Perform readout
        8. Loop over delay times
        9. Loop over reps
        10. Loop over rounds
        '''

        self.set_pulse_registers(ch=self.cfg.mw_channel, phase=self.deg2reg(0))
        ## Pulse Sequence 

        # pi/2 mw channel 
        self.pulse(ch=self.cfg.mw_channel)
        self.sync_all()
        # delay mw channel for t1 time 
        self.sync(self.delay_register_mwt1.page, self.delay_register_mwt1.addr)
        
        # pi nw channel 
        self.pulse(ch=self.cfg.mw_channel)
        self.pulse(ch=self.cfg.mw_channel)
        self.sync_all()
        # delay mw channel for t2 
        self.sync(self.delay_register_mwt2.page,self.delay_register_mwt2.addr)

        # delay sweep before the pi pump pulse 
        self.sync(self.delay_register_pump.page, self.delay_register_pump.addr)
        # pi pump channel 
        self.pulse(ch=self.pump_channel)
        self.pulse(ch=self.pump_channel)
        self.sync_all()


        # pi mw channel 
        self.pulse(ch=self.cfg.mw_channel)
        self.pulse(ch=self.cfg.mw_channel)
        self.sync_all()
       
    
        # Readout
        self.ttl_readout()


    def acquire(self, raw_data=False, *arg, **kwarg):

        data = super().acquire(reads_per_rep=4, *arg, **kwarg)

        if raw_data is False:
            data = self.analyze_pulse_sequence_results(data)

        return data

    # def plot_sequence(cfg=None):
    #     '''
    #     Function that plots the pulse sequence generated by this program

    #     Parameters
    #     ----------
    #     cfg: `.NVConfiguration` or None(default None)
    #         If None, this plots the sequence with configuration labels
    #         If a `.NVConfiguration` object is supplied, the configuration value are added to the plot
    #     '''
    #     graphics_folder = os.path.join(os.path.dirname(__file__), '../../graphics')
    #     image_path = os.path.join(graphics_folder, 'HAHN_ECHO.png')


    #     if cfg is None:
    #         plt.figure(figsize=(12, 12))
    #         plt.axis('off')
    #         plt.imshow(mpimg.imread(image_path))
    #         plt.text(500, 700, "config.reps", fontsize=14)
    #         plt.text(235, 345, "delay", fontsize=10)
    #         plt.text(300, 345, "delay", fontsize=10)
    #         plt.text(400, 385, "  config.readout_reference_start", fontsize=10)
    #         plt.text(190, 395, "mw_pi2", fontsize=10)
    #         plt.text(253, 410, "     2 x \n mw_pi2", fontsize=10)
    #         plt.text(310, 395, " mw_pi2", fontsize=10)
    #         plt.text(260, 465, "config.laser_readout_offset", fontsize=10)
    #         plt.text(390, 340, "config.readout_integration", fontsize=10)
    #         plt.text(650, 340, "config.readout_integration", fontsize=10)
    #         plt.text(850, 340, "config.relax_delay", fontsize=10)
    #         plt.text(400, 430, "config.laser_on", fontsize=10)
    #         plt.text(220, 605,
    #                  "Sweep delay from config.delay_start to config.delay_end in config.nsweep_points \n\
    #                   with scaling given by config.scaling_mode",
    #                  fontsize=12)
    #         plt.title("             Hahn Echo Pulse Sequence", fontsize=20)
    #     else:
    #         plt.figure(figsize=(12, 12))
    #         plt.axis('off')
    #         plt.imshow(mpimg.imread(image_path))
    #         plt.text(450, 700, "Repeat {} times".format(cfg.reps), fontsize=14)
    #         plt.text(235, 345, "delay", fontsize=10)
    #         plt.text(300, 345, "delay", fontsize=10)
    #         plt.text(385, 385, "  readout_reference_start = {} us".format(cfg.readout_reference_start_tus), fontsize=10)
    #         plt.text(190, 395, "pi/2", fontsize=12)
    #         plt.text(253, 395, "pi", fontsize=12)
    #         plt.text(310, 395, " pi/2", fontsize=12)
    #         plt.text(240, 465, "laser_readout_offset = {} treg".format(cfg.laser_readout_offset_treg), fontsize=10)
    #         plt.text(390, 337, "readout_integration = {} us".format(str(cfg.readout_integration_tus)[:4]), fontsize=10)
    #         plt.text(650, 357, "readout_integration \n = {} us".format(str(cfg.readout_integration_tus)[:4]), fontsize=10)
    #         plt.text(850, 357, "relax_delay \n = {} us".format(str(cfg.relax_delay_tus)[:4]), fontsize=10)
    #         plt.text(400, 430, "laser_on = {} us".format(cfg.laser_on_tus), fontsize=12)
    #         plt.text(375, 605, "    Sweep delay from {} us to {} us \n\
    #                                  in {} {} steps".format(int(cfg.delay_start_tns), int(cfg.delay_end_tns), cfg.nsweep_points, cfg.scaling_mode), fontsize=12)
    #         plt.title("               Hahn Echo Pulse Sequence", fontsize=20)

    # def time_per_rep(self):

    #     pass
