#!/usr/bin/python

import matplotlib.pyplot as plt
import os
import sys

options = {
    1: 'msl_altitude',
    2: 'indicated_airspeed',
    3: 'vertical_airspeed',
    4: 'heading',
    5: 'pitch_attitude',
    6: 'roll_attitude',
    7: 'eng_1_rpm',
    8: 'vertical_acceleration',
    9: 'groundspeed',
    10: 'latitude',
    11: 'longitude'
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
    headers, indexes, labels, dataMatrix = [], [], [], []
    dataMatrix.append([])  # First empty list for times

    graphsFolder = './graphs/'
    for i in range(len(choices)):
        dataMatrix.append([])
        labels.append(options[choices[i]])
        if i == 0:
            graphsFolder = graphsFolder + labels[i]
        else:
            graphsFolder += 'AND' + labels[i]

    os.system('mkdir graphs')         # Make graphs folder if it doesn't exist
    os.system('mkdir ' + graphsFolder) # Make folder within graphs for this query

    firstTime = True
    for filename in files:
        if '.csv' not in filename: continue # Skip file if it isn't a .csv
        flight = filename.split('.')[0]
        print 'Generating graph for: {0:}'.format(filename)

        with open(folder + '/' + filename, 'r') as file:
            clearData(dataMatrix) # Clear the dataMatrix for next file
            for x in range(9):    # First 9 lines are garbage
                file.readline()
            if firstTime:         # If this is first time, get the data headers (line 10)
                headers = file.readline().split(', ')
                for lbl in labels: # Find the corresponding header index for each label
                    indexes.append(headers.index(lbl))
                firstTime = False
            else:
                file.readline()

            for line in file:
                row = line.split(', ')
                dataMatrix[0].append(float(row[3])/60000)
                for i in range(len(indexes)):
                    dataMatrix[i+1].append(float(row[indexes[i]]))



        makeGraph(dataMatrix, labels, flight, graphsFolder)
    print 'Complete!!!'


###
 # Function clears the contents of each sub-list in the passed in list.
 # It does not delete the sub-lists themselves.
 # For example, after this function: data = [ [], [], ... ]
 # This happens by reference so data does not need to be returned.
 ##
def clearData(data):
    for i in range(len(data)):
        del data[i][:]  # Deletes everything in each sub-list


def makeGraph(data, labels, flightID, folder):
    fig, ax =  plt.subplots()
    axes = [ax]
    axes[0].set_xlabel('Time (minutes)')

    title = 'Time vs {0:} for Flight: {1:}'
    msg = labels[0]
    for i in range(1, len(labels)):  # Loop to add y-axes & append onto msg
        axes.append(axes[0].twinx())
        msg += ' & ' + labels[i]
        if i > 1:
            # Move the last y-axis spine over to the right by 10% of the width of the axes
            axes[-1].spines['right'].set_position(('axes', 1 + (.1 * (i-1))))

            # To make the border of the right-most axis visible, we need to turn the frame
            # on. This hides the other plots, however, so we need to turn its fill off.
            axes[-1].set_frame_on(True)
            axes[-1].patch.set_visible(False)

    if len(labels) > 2:
        #offset = len(labels) - 2 # NOT BEING USED RIGHT NOW
        # Make some space on the right side for the extra y-axis.
        fig.subplots_adjust(right=(0.75))

    COLORS = ('b', 'r', 'g', 'c', 'm', 'y', 'k', 'salmon', 'chartreuse', 'maroon', 'crimson')

    for i, ax, lbl, color in zip(range(len(labels)), axes, labels, COLORS):
        ax.plot(data[0], data[i+1], color)
        ax.set_ylabel(lbl, color=color)
        ax.tick_params(axis='y', colors=color)

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
