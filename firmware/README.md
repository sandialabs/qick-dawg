QICK-DAWG firmware
=================================================

List of QICK-DAWG firmware:
#### RFSoC4x2
* qickdawg_4x2_commonClk - All clocks including the DAC, ADC and tprocessor are synced at 409.6 MHz.
* qickdawg_4x2_commonClk - DAC clk = 614.40 MHz, ADC clk = 307.2 MHz, tproc = 307.2 MHz. DAC is 2x faster than the ADC and tproc.

#### ZCU216
* qickdawg_216_commonClk - All clocks including the DAC, ADC and tprocessor are synced at 307.2 MHz.
* qickdawg_216_commonClk - DAC clk = 599.40 MHz, ADC clk = 299.52 MHz, tproc = 299.52 MHz. DAC is 2x faster than the ADC and tproc
  
#### ZCU111
* qickdawg_111_commonClk - All clocks including the DAC, ADC and tprocessor are synced at 409.6 MHz.


# Building the firmware yourself

If you want to make changes to the firmware, or you just want to look at the design and dig around:

* Pick the firmware project you want to build. The projects for the standard images for ZCU111, ZCU216, and RFSoC4x2 (`qick_111.bit`, `qick_216.bit`, `qick_4x2.bit`) are in subdirectories of the `projects` directory, as are projects for ZCU111 images with support for the v1 and v2 RF boards. You will find a project script (`proj.tcl`) and a block design script (`bd_2022-1.tcl` or similar).
* Install the version of Vivado specified by the block design filename (e.g. 2022.1 - older or newer will fail!), with a license that is valid for the FPGA you are using (you will have received such a license with your board). Start Vivado.
* In the Tcl console at the bottom of the screen navigate to this directory, then run the project script (e.g. `source ./proj.tcl`). This will create the firmware project and will end by showing you a block diagram of the firmware.
* Now click "Generate Bitstream" in the navigation menu at the left: this will compile the firmware.
* You need the .bit and .hwh files. These are not easy to find but the `out` directory has symlinks to their locations.

To save your block design:

```
write_bd_tcl -force -include_layout bd.tcl
```

