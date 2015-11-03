#!/usr/bin/python

import matplotlib.pyplot as plt
import os
import sys

parameters = {
    0: {'param': 'time',
        'data' : [],
        'index': -1,
        'label': 'Time',
        'units': 'minutes'},
    1: {'param': 'msl_altitude',
        'data' : [],
        'index': -1,
        'label': 'Altitude',
        'units': 'ft'},
    2: {'param': 'indicated_airspeed',
        'data' : [],
        'index': -1,
        'label': 'Airspeed',
        'units': 'kts'},
    3: {'param': 'vertical_airspeed',
        'data' : [],
        'index': -1,
        'label': 'Vertical Airspeed',
        'units': 'kts'},
    4: {'param': 'heading',
        'data' : [],
        'index': -1,
        'label': 'Heading',
        'units': 'degrees'},
    5: {'param': 'pitch_attitude',
        'data' : [],
        'index': -1,
        'label': 'Pitch Attitude',
        'units': 'degrees'},
    6: {'param': 'roll_attitude',
        'data' : [],
        'index': -1,
        'label': 'Roll Attitude',
        'units': 'degrees'},
    7: {'param': 'eng_1_rpm',
        'data' : [],
        'index': -1,
        'label': 'Engine RPM',
        'units': 'rpm'},
    8: {'param': 'vertical_acceleration',
        'data' : [],
        'index': -1,
        'label': 'Vertical Acceleration',
        'units': 'ft/s^2'},
    9: {'param': 'groundspeed',
        'data' : [],
        'index': -1,
        'label': 'Groundspeed',
        'units': 'kts'},
    10: {'param': 'latitude',
        'data' : [],
        'index': -1,
        'label': 'Latitude',
        'units': 'degrees'},
    11: {'param': 'longitude',
        'data' : [],
        'index': -1,
        'label': 'Longitude',
        'units': 'degrees'}
}

exceedances = {
    'go-around': [],
    'touch-and-go': [],
    'stop-and-go' : [],
    'unstable approach': []
}

def main(argv):
    if len(argv) != 1:
        print '''
#####################################
#                                   #
#  ./FlightDataGraphMaker <folder>  #
#                                   #
#####################################
'''
        exit()

    folder = argv[0]
    files = os.listdir(folder)

    choices = menu()
    headers = []

    graphsFolder = './graphs/'
    FIRST = True
    for c in choices:
        if FIRST:
            graphsFolder = graphsFolder + parameters[c]['param']
            FIRST = False
        else:
            graphsFolder += 'AND' + parameters[c]['param']

    os.system('mkdir graphs')          # Make graphs folder if it doesn't exist
    os.system('mkdir ' + graphsFolder) # Make folder within graphs for this query

    firstTime = True
    for filename in files:
        if '.csv' not in filename: continue # Skip file if it isn't a .csv
        flight = filename.split('.')[0]
        print 'Generating graph for: {0:}'.format(filename)

        with open(folder + '/' + filename, 'r') as file:
            clearData()        # Clear the dataMatrix for next file
            clearExceedances() # Clear exceedance tuples
            for x in range(9):    # First 9 lines are garbage
                file.readline()
            if firstTime:         # If this is first time, get the data headers (line 10)
                headers = file.readline().split(', ')
                for key in parameters.keys(): # Find the corresponding header index for each label
                    parameters[key]['index'] = headers.index( parameters[key]['param'] )
                firstTime = False
            else:
                file.readline()

            for line in file:
                row = line.split(', ')
                parameters[0]['data'].append( float(row[parameters[0]['index']]) / 60000 ) # Add time value
                for key in parameters.keys(): # Add rest of param values (everything but time)
                    if key != 0: parameters[key]['data'].append( float( row[parameters[key]['index']] ) )

        analyzeData()

        makeGraph(choices, flight, graphsFolder)
    print 'Complete!!!'


###
 # Function clears the contents of each sub-list in the passed in list.
 # It does not delete the sub-lists themselves.
 # For example, after this function: data = [ [], [], ... ]
 # This happens by reference so data does not need to be returned.
 ##
def clearData():
    for key in parameters.keys():
        del parameters[key]['data'][:]  # Deletes everything in each sub-list


def clearExceedances():
    for key in exceedances.keys():
        del exceedances[key][:]

def analyzeData():
    findFullStops()


def findFullStops():
    i = 0
    while i < len(parameters[0]['data']):  # Loop through time values
        if parameters[2]['data'][i] <= 10: # Check if 'indicated_airpseed' is less than or equal to 10 kts
            start = i                      # Store starting time index
            while i < len(parameters[0]['data']) and parameters[2]['data'][i] <= 50:
                i += 1                     # Increment while it is less than or equal to 50 kts
            end = i - 1                    # Store ending time index
            exceedances['stop-and-go'].append( (start, end) )
        else:
            i += 1


def makeGraph(choices, flightID, folder):
    fig, ax =  plt.subplots()
    axes = [ax]
    axes[0].set_xlabel('Time (minutes)')

    title = 'Time vs {0:} for Flight: {1:}'
    msg = parameters[choices[0]]['label']
    for i in range(1, len(choices)):  # Loop to add y-axes & append onto msg
        axes.append(axes[0].twinx())
        msg += ' & ' + parameters[choices[i]]['label']
        if i > 1:
            # Move the last y-axis spine over to the right by 10% of the width of the axes
            axes[-1].spines['right'].set_position(('axes', 1 + (.1 * (i-1))))

            # To make the border of the right-most axis visible, we need to turn the frame
            # on. This hides the other plots, however, so we need to turn its fill off.
            axes[-1].set_frame_on(True)
            axes[-1].patch.set_visible(False)

    if len(choices) > 2:
        # Make some space on the right side for the extra y-axis.
        fig.subplots_adjust(right=(0.75))

    COLORS = ('blue', 'red', 'green', 'indigo', 'magenta', 'lightskyblue', 'black', 'salmon', 'chartreuse', 'maroon', 'crimson')

    for ax, c, color in zip(axes, choices, COLORS):
        ax.plot(parameters[0]['data'], parameters[c]['data'], color)
        ax.set_ylabel( '{0:} ({1:})'.format(parameters[c]['label'], parameters[c]['units']), color=color )
        ax.tick_params(axis='y', colors=color)

    COLORS = ('cyan', 'orange', 'yellow', 'lime')
    for key, color in zip(exceedances.keys(), COLORS):
        for x in exceedances[key]: # Vertical Highlight for each exceedance
            axes[0].axvspan( parameters[0]['data'][x[0]], parameters[0]['data'][x[1]], alpha=0.25, color=color )

    plt.title(title.format(msg, flightID))

    figure = plt.gcf()
    figure.set_size_inches(25.6, 16)
    plt.savefig(folder + '/{0:}.png'.format(flightID), dpi = 100)
    plt.clf()


def menu():
    print '''
1. MSL Altitude
2. Indicated Airspeed
3. Vertical Airspeed
4. Heading
5. Pitch Attitude
6. Roll Attitude
7. Engine 1 RPM
8. Vertical Acceleration
9. Groundspeed
10. Latitude
11. Longitude
'''

    choices = []
    choice = -1

    while choice < 1 or choice > 11:
        choice = input('Which attribute for y1? ')
    choices.append(choice)

    counter = 1
    while counter < 11:
        choice = input('(optional -- enter 0 to opt out) which attribute for y{0:}? '.format(counter+1))
        if (choice not in choices) and (choice < 11 and choice > 1):
            choices.append(choice)
            counter += 1
        elif choice == 0:
            break

    return choices


if __name__ == "__main__":
    main(sys.argv[1:])
