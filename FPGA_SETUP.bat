REM FPGA_SETUP.bat copies the necessary files from the qickdawg package onto the FPGA. This includes, a copy of qick, packages and files needed to run the FPGA as an obejct, and our modified QICKDAWG firmware

REM To run this file, open the command prompt on your computer that is connected to the FPGA. In the command prompt change your directory to the folder of your unzipped copy of QICKDAWG that contains this file--FPGA_SETUP.bat. Once you are in the correct directory, type <FPGA_SETUP.bat> into the command prompt and hit enter. You will be prompted to enter the IP address of your FPGA and the password--xilinx.

REM After running this file you should run Install_Packages.ipynb, located in the installation folder, from the Jupyter Notebooks interface.

@echo off 

set /p IP=Enter IP address:

scp -r installation xilinx@%IP%:/home/xilinx/jupyter_notebooks
scp -r qick xilinx@%IP%:/home/xilinx/jupyter_notebooks
