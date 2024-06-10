REM FPGA_SETUP.bat establishes an ssh connection with your RFSoC4x2 and clones QICK-DAWG on your RFSoC4x2.

REM To run this file, open the command prompt on your computer that is connected to the RFSoC4x2. 
REM In the command prompt change your directory to the folder of your unzipped copy of QICKDAWG that contains this file--FPGA_SETUP.bat. 
REM Once you are in the correct directory, type <FPGA_SETUP.bat> into the command prompt and hit enter. 
REM You will be prompted to enter the IP address of your RFSoC4x2 FPGA.

REM After running this file you should run Install_Packages.ipynb, located in the installation folder, from the Jupyter Notebooks interface.

@echo off 

set /p IP=Enter IP address:

ssh xilinx@%IP%:/home/xilinx/jupyter_notebooks -pw xilinx ; git clone https://github.com/sandialabs/qick-dawg

