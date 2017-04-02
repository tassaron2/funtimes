#!/usr/bin/env python3
#=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~==~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=#
#
# main.py for an example game
# last modified 2017/04/02
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

playerData = {
    'playerHP'        : 100,
}

def main(startat='mainmenu'):
    '''
    This is a basic main.py with just a skeleton for a
    game in it, for the sake of reference. To try it
    with predicaments that work with it, rename
    the folder /example-pred to /pred (rename the
    existing /pred of course).
    '''
    funplayer.set_variables(playerData)
    funplayer.set_variables(forExitcode(startat))
    funplayer.set_variables({'seenIntro':0})
    funplayer.set_mode('MENU')
    funplayer.play(startat)
    newpred = startat
    
    while True:
        output = funplayer.main()
        if type(output)==int:
            # user hit quit button
            if output==9 and newpred!='mainmenu':
                newpred = 'mainmenu'
            else:
                quit(0)
        else:
            newpred = output
        funplayer.set_variables(forExitcode(newpred))
        funplayer.set_variables(playerData)
        if newpred=='mainmenu':
            funplayer.set_mode('MENU')
        else:
            funplayer.set_mode()
        funplayer.delete_memory()
        funplayer.play(newpred)

def forExitcode(predname):
    varsForPredname = {
    'mainmenu' : {},
    'entry' : {
        'finalQ' : 6,
        'badguyQ' : 0,
        'badguyQlabel' : 'Respond to Probe',
        'heardthatnoise' : 0,
        'followed' : 0,
        'badfollow' : 0,
        },
    'kill' : {},
    'somewhereelse' : {
        'finalQ' : 6,
        'badguyQ' : 0,
        'badguyQlabel' : 'Respond to Probe',
        'nomorekey' : 0,
        'tick' : 0
        },
    }

    return varsForPredname[predname]

if __name__ == '__main__':
    main()
