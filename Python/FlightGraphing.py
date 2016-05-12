import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
class FlightGrapher:
    parameters = {}
    approaches = {}
    choices = []
    folder = ""

    def __init__(self, ch, folder):
        self.choices = ch
        self.folder = folder

    def graph(self, flightID, p, a):
        self.makeGraph(flightID, p, a)

    '''
    This function uses the parameters chosen by the user and graphs
        the time-series data.
    It also makes vertical highlights for the regions where unstable approaches and landings were found.
    The graphs are then generated as .png files and saved to the passed in folder name
        within the graphs/ folder.
    @param: choices the parameters to graph
    @param: flightID the ID of the flight being graphed
    @param: folder the folder name to save the .png file
    @author: Wyatt Hedrick, Kelton Karboviak
    '''
    def makeGraph(self, flightID, p, a):
        self.parameters = p
        self.approaches = a
        fig, ax =  plt.subplots()
        axes = [ax]
        axes[0].set_xlabel('Time (minutes)')

        title = 'Time vs %s for Flight: %s'
        msg = self.parameters[self.choices[0]]['label']
        for i in range(1, len(self.choices)):  # Loop to add y-axes & append onto msg
            axes.append(axes[0].twinx())
            msg += ' & ' + self.parameters[choices[i]]['label']
            if i > 1:
                # Move the last y-axis spine over to the right by 10% of the width of the axes
                axes[-1].spines['right'].set_position(('axes', 1 + (.1 * (i-1))))

                # To make the border of the right-most axis visible, we need to turn the frame
                # on. This hides the other plots, however, so we need to turn its fill off.
                axes[-1].set_frame_on(True)
                axes[-1].patch.set_visible(False)

        if len(self.choices) > 2:
            # Make some space on the right side for the extra y-axis.
            fig.subplots_adjust(right=(0.75))

        COLORS = ('blue', 'red', 'green', 'indigo', 'magenta', 'lightskyblue', 'black', 'salmon', 'chartreuse', 'maroon', 'crimson')

        for ax, c, color in zip(axes, self.choices, COLORS):
            ax.plot(self.parameters[0]['data'], self.parameters[c]['data'], color)
            ax.set_ylabel( '%s (%s)' % (self.parameters[c]['label'],self.parameters[c]['units']), color=color )
            ax.tick_params(axis='y', colors=color)

        patches = []
        types = ('Stop and Go', 'Touch and Go', 'Go Around', 'Unstable Approach')
        COLORS = ('lime', 'cyan', 'orange', 'red')

        for landingType, color in zip(types, COLORS):
            patches.append(mpatches.Patch(color=color, label = landingType))
        for key, a in self.approaches.items():
            for x in a['unstable']:
                axes[0].axvspan( self.parameters[0]['data'][x[0]], self.parameters[0]['data'][x[1]], alpha = 0.8, color='red')
            if (a['landing-type'] == 'stop-and-go'):
                landingColor = 'lime'
            elif (a['landing-type'] == 'touch-and-go'):
                landingColor = 'cyan'
            else:
                landingColor = 'orange'
            axes[0].axvspan( self.parameters[0]['data'][a['landing-start']], self.parameters[0]['data'][a['landing-end']], alpha = 0.8, color = landingColor)


        plt.title(title % (msg, flightID))

        plt.figlegend(handles=patches, labels=types, loc='center right')

        figure = plt.gcf()
        figure.set_size_inches(25.6, 16)
        plt.savefig('%s/%s.png' % (self.folder, flightID), dpi = 100)
        plt.clf()
