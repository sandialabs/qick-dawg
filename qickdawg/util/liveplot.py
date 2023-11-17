"""
live_plot
========================================================================
A function that updates a plot with new measurements

"""


import matplotlib.pyplot as plt
import numpy as np
from time import sleep, time
from IPython import display


def live_plot(measure_function, histogram_range=100, dt=0.001):
    '''
    Takes a function that returns a value and updates a plot at time invervals 'dt'
    until function is interrupted

    Parameters
    ---------------------------------------------------------------------------------
    measure_function
        function that generates a data point or array of points
    histogram_range
        total number of data points plotted before overwriting
    dt 
        time between datapoints being taken
    '''

    plt.axis()
    plt.ion()


    x_data = []
    y_data = []
    data = []
    y = None
    
    t0=time()
    
    i = 0
    try:
        while True:
            sleep(dt)

            d = measure_function()

            if issubclass(type(d), (int, float)):
                dims = 0
                new_data = d
                x = time() - t0
                y_name = 'Data'
                x_name = 'time (s)'

            elif issubclass(type(d), (list, np.ndarray, tuple)):
                if len(d) == 2:
                    dims = 1
                    x, new_data = d
                    y_name = None
                    x_name = None
                elif len(d) == 3:
                    dims = 2
                    x, y, new_data = d
                    x_name = None
                    y_name = None
                else:
                    if len(d[0]) == 1:
                        dims = 1
                        new_data = d
                        x = list(range(len(new_data)))
                    else:
                        print("Bad measure function return type")
                        return 0
            else:
                print("Bad measure function return type")
                return 0

            if dims==0:
                if histogram_range == 1:
                    data = new_data
                    x_data = x
                    if np.any(np.array(y)):
                        y_data = y
                elif i < histogram_range:
                    data = np.append(data, [new_data])
                    x_data = np.append(x_data, [x])
                    if y:
                        y_data = np.append(y_data, [y])
                else:
                    data = np.append(data[1:], [new_data])
                    x_data = np.append(x_data[1:], [x])
                    if y:   
                        y_data = np.append(y_data[1:], [y])
            elif dims==1:
                data = new_data
                x_data=x
            elif dims==2:
                data = new_data
                x_data=x
                y_data = y
            plt.gca().cla()

            plt.title("Live Plot {}".format(i))

            if dims == 0:
                plt.plot(x_data, data)
                plt.xlabel("Time (s)")
                ypad=(np.max(data)-np.min(data))/20
                plt.ylim(np.min(data)-ypad,np.max(data)+ypad)
                plt.xlim(x_data[0],x_data[-1])

            if dims == 1:
                plt.plot(x_data.T, data.T)
                plt.xlabel(x_name)
                ypad=(np.max(data)-np.min(data))/20
                plt.ylim(np.min(data)-ypad,np.max(data)+ypad)
                plt.xlim(x_data[0],x_data[-1])

            if dims == 2:
                plt.pcolormesh(x_data, y_data, data.T)
                plt.xlabel(x_name)
                plt.xlim(x_data[0],x_data[-1])
                plt.ylim(y_data[0], y_data[-1])

            plt.ylabel(y_name)
            display.display(plt.gcf())
            display.clear_output(wait=True)

            i += 1
    except KeyboardInterrupt:
        return None
