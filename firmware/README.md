QICK-DAWG firmware
=================================================

### Available QICK-DAWG firmwares:
#### RFSoC4x2
* `qickdawg_4x2`        - DAC sampling rate is 6.5536 GSPS. The DAC and ADC runs at 409.6 MHz.
* `qickdawg_4x2_2xDAC`  - DAC sampling rate is 6.5536 GSPS  9.8 GSPS. DAC is 2x faster than the ADC and tprocessor. DAC clk = 614.40 MHz, and ADC clk = 307.2 MHz.

#### ZCU216
* `qickdawg_216`        - DAC sampling rate is 4.9152 GSPS. The DAC and ADC runs at 307.2 MHz.
* `qickdawg_216_2xDAC`  - DAC is 2x faster than the ADC and tprocessor. DAC sampling rate is 9.8 GSPS. DAC clk = 614.40 MHz, ADC clk = 307.2 MHz.
  
#### ZCU111
* `qickdawg_111` - DAC sampling rate is 4.9152 GSPS. The DAC and ADC runs at 307.2 MHz.

# Building the firmware

If you want to make changes to the firmware or look at the design, you can build the 2x DAC speed firmware yourself.
* Navigate to the board directory you want to build and then to the `/src/` directory. You will find a project script `proj_v2.tcl` and a block design script `bd_2022-1_2.tcl` or a similar version.
* Install the version of Vivado specified by the block design filename (older or newer versions will fail!). Start Vivado.
* In the Tcl console at the bottom of the screen navigate to the `firmware/<selected board>/src` directory then run the following command:
```
 source ./proj_v2.tcl
 ```
This will create the block diagram design of the firmware. Do not run `bd_2022-1_2.tcl`.  

* After the block diagram is built, select "Generate Bitstream"  in the navigation menu on the left side of the window. This will compile the firmware.
* You will need to put both the .bit (named d_1_wrapper by default) and .hwh file (named d_1.hwh by default) on the RFSoC, which can be found in the 'top' project directory.
  * The .bit file can be found in `<RFSoC board directory>/src/top/top.runs/impl_1/.bit`
  * The .hwh file can be found in `<RFSoC board directory>/src/top/top.gen/sources_1/bd/d_1/hw_handoff/ .hwh`

To save your block design:
```
write_bd_tcl -force -include_layout bd.tcl
```

