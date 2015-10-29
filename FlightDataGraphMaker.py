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

labels = {
    
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



    headers = []
    choice1, choice2, choice3 = menu()
    choice1 = options[choice1]
    if (choice2 != 0):
        choice2 = options[choice2]
        if (choice3 != 0):
            choice3 = options[choice3]
            graphsFolder = './graphs-{0:}AND{1:}AND{2:}'.format(choice1, choice2, choice3)
        else:
            choice3 = ''
            graphsFolder = './graphs-{0:}AND{1:}'.format(choice1, choice2)
    else:
        choice2 = ''
        choice3 = ''
        graphsFolder = './graphs-{0:}'.format(choice1)


    os.system('mkdir ' + graphsFolder)
    
    firstTime = True
    for filename in files:
        times, y1, y2, y3 = [], [], [], []
        
        flight = filename.split('.')[0]
        print 'Generating graph for: {0:}'.format(filename)
        
        with open(folder + '/' + filename, 'r') as file:
            for x in range(9):
                file.readline()
            if firstTime:
                headers = file.readline().split(', ')
                y1Index = headers.index(choice1)
                if choice2 != '':
                    y2Index = headers.index(choice2)
                    if choice3 != '':
                        y3Index = headers.index(choice3)
                    else:
                        y3Index = -1;
                else:
                    y2Index = -1
                firstTime = False
            else:
                file.readline()
            if y2Index != -1:
                if y3Index != -1:
                    for line in file:
                        row = line.split(', ')
                        times.append(float(row[3])/60000)
                        y1.append(float(row[y1Index]))
                        y2.append(float(row[y2Index]))
                        y3.append(float(row[y3Index]))
                else:
                    for line in file:
                        row = line.split(', ')
                        times.append(float(row[3])/60000)
                        y1.append(float(row[y1Index]))
                        y2.append(float(row[y2Index]))

            else:
                for line in file:
                    row = line.split(', ')
                    times.append(float(row[3])/60000)
                    y1.append(float(row[y1Index]))


        makeGraph(times, y1, y2, y3, flight, choice1, choice2, choice3, graphsFolder)
    print 'Complete!!!'


def makeGraph(times, y1, y2, y3, flightID, choice1, choice2, choice3, folder):
    title = 'Time vs {0:}{1:}{2:} for Flight: {3:}'
    fig, ax =  plt.subplots()
    axes = [ax]
    if choice2 != '':
        axes.append(axes[0].twinx())
        if choice3 != '':
            axes.append(axes[0].twinx())
            fig.subplots_adjust(right=0.75)

            # Move the last y-axis spine over to the right by 20% of the width of the axes
            axes[-1].spines['right'].set_position(('axes', 1.2))
    
            # To make the border of the right-most axis visible, we need to turn the frame
            # on. This hides the other plots, however, so we need to turn its fill off.
            axes[-1].set_frame_on(True)
            axes[-1].patch.set_visible(False)

    
    axes[0].plot(times, y1, 'b-')
    axes[0].set_ylabel(choice1, color='b')
    axes[0].set_xlabel('Time (minutes)')
    axes[0].tick_params(axis='y', colors='b')
    
    if choice2 != '':
        axes[1].plot(times, y2, 'r-')
        axes[1].set_ylabel(choice2, color='r')
        axes[1].tick_params(axis='y', colors='r')
        if choice3 != '':
            axes[2].plot(times, y3, 'g-')
            axes[2].set_ylabel(choice3, color='g')
            axes[2].tick_params(axis='y', colors='g')
            plt.title(title.format(choice1, ' & ' + choice2, ' & ' + choice3, flightID))
        else:
            plt.title(title.format(choice1, ' & ' + choice2, '', flightID))
    else:
        plt.title(title.format(choice1, '', '', flightID))

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

    choice1 = 0
    choice2 = -1
    choice3 = -1
    while choice1 < 1 or choice1 > 11:
        choice1 = input('Which attribute for y1? ')
    while choice2 < 0 or choice2 > 11 or choice2 == choice1:
        choice2 = input('(optional -- enter 0 to opt out) which attribute for y2? ')
    if choice2 != 0:
        while choice3 < 0 or choice3 > 11 or choice2 == choice3 or choice3 == choice1:
            choice3 = input('(optional -- enter 0 to opt out) which attribute for y3? ')

    return choice1, choice2, choice3


if __name__ == "__main__":
    main(sys.argv[1:])
