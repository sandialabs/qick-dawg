QICK-DAWG firmware
=================================================

### Available QICK-DAWG firmwares:
#### RFSoC4x2
* `qickdawg_4x2_commonClk` - All clocks including the DAC, ADC and tprocessor are synced at 409.6 MHz.
* `qickdawg_4x2_2xDAC` - DAC clk = 614.40 MHz, ADC clk = 307.2 MHz, tproc = 307.2 MHz. DAC is 2x faster than the ADC and tproc.

#### ZCU216
* `qickdawg_216_commonClk` - All clocks including the DAC, ADC and tprocessor are synced at 307.2 MHz.
* `qickdawg_216_2xDAC` - DAC clk = 614.40 MHz, ADC clk = 307.2 MHz, tproc = 307.2 MHz. DAC is 2x faster than the ADC and tproc.
  
#### ZCU111
* `qickdawg_111_commonClk` - All clocks including the DAC, ADC and tprocessor are synced at 409.6 MHz.

# Building the firmware

If you want to make changes to the firmware or look at the design, you can build the 2x DAC speed firmware yourself.
* Available build files are for the 4x2, zcu111 and zcu216. Navigate to the board directory you want to build and then to the `/src/` directory. You will find a project script `proj_v2.tcl` and a block design script `bd_2022-1_2.tcl` or a similar version.
* Install the version of Vivado specified by the block design filename (older or newer versions will fail!). Start Vivado.
* In the Tcl console at the bottom of the screen navigate to the `firmware/<selected board>/src` directory then run the following command:
```
 source ./proj_v2.tcl
 ```
This will create the block diagram design of the of the firmware. Do not run `bd_2022-1_2.tcl`.  

* After the block diagram is built, select "Generate Bitstream"  in the navigation menu on the left side of the window. This will compile the firmware.
* You need both the .bit (named d_1_wrapper by default) and .hwh files named d_1.hwh by default).
  * The .bit file can be found in `top/top.runs/impl_1/.bit`
  * The .hwh file can be found in `top/top.gen/sources_1/bd/d_1/hw_handoff/ .hwh`

To save your block design:
```
write_bd_tcl -force -include_layout bd.tcl
```

