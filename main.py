#!/usr/bin/env python3
#=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~==~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=#
#
# main.py for an example game
# last modified 2017/03/31
# created 2017/03/23 by tassaron
#
#=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~==~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=#
#
# Licence would go here if anyone cared
#
#=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~==~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=#
import os
import funplayer

# path for this game's resources (not funtimes resources)
# currently nonexistent because the game is too simple/unfinished
#CONFIGPATH = "%s/.config/file.conf" % os.getenv("HOME")
SRCPATH = ( os.path.join(os.path.realpath(__file__), 'src'))

'''
class MainMenuWindow(Gtk.Window):
    def __init__(self):
        super().__init__()
        self.connect("delete-event", Gtk.main_quit)
'''

def main(startat='entry'):
    funplayer.set_variables(forExitcode(startat))
    funplayer.play(startat)
    
    while True:
        output = funplayer.main()
        if type(output)==int:
            # user closed window
            quit(0)
        newpred = wtfIsThis(output)
        funplayer.set_variables(forExitcode(newpred))
        funplayer.play(newpred)

def wtfIsThis(exitcode):
    if exitcode=='punchedfollower':
        return 'somewhereelse'
    else:
        # idk so quit the game
        return 'kill'

def forExitcode(predname):
    varsForPredname = {
    'entry' : {
        'finalQ' : 6,
        'badguyQ-redirect' : 'walkaround2N',
        'badguyQ' : 0,
        'badguyQlabel' : 'Respond to Probe',
        'heardthatnoise' : 0,
        'followed' : 0,
        },
    'kill' : {},
    'somewhereelse' : {
        'finalQ' : 6,
        'badguyQ-redirect' : 'somewhereelse2',
        'badguyQ' : 0,
        'badguyQlabel' : 'Respond to Probe',
        'nomorekey' : 0,
        'tick' : 0
        },
    }

    return varsForPredname[predname]

if __name__ == '__main__':
    main()
