#!/usr/bin/env python3
#=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~==~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=#
#
# very early main.py for Tarasius
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

startStats = {
    'playerMoney'     : 20,
    'supereasyQuest1' : 0,
    'supereasyQuest2' : 0,
}

playerData = {
    'playerName'      : 'Tarasius',
    'playerHP'        : 100,
    'playerdead'      : 0,
    'playerSP'        : 0,
}

def main(startat='mainmenu'):
    funplayer.set_variables(startStats)
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
                'mainmenu' :  playerData,
    'supereasyQuest1entry' :   {
            'currentquest' : 'supereasyQuest1',
            'probeAngered' : 0,
            'probeTick'    : 0,
           'probeProgress' : 0,
          'probeFollowing' : 0,
        },
    }
    try:
        return varsForPredname[predname]
    except KeyError:
        print('oopsie')
        quit()

if __name__ == '__main__':
    main()
