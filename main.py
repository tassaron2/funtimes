#!/usr/bin/env python3
#=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~==~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~#
# very early main.py for Tarasius
# last modified 2017/04/02
# created 2017/03/23 by tassaron
#
#=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~==~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~#
# Copyright (C) 2017 Brianna Rainey
# This file is part of FUNTIMES
#
# FUNTIMES is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program, in a file named "COPYING".  If not, see
# <http://www.gnu.org/licenses/>
#
#=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~==~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~#
import os
import funplayer

# path for this game's resources (not funtimes resources)
# currently nonexistent because the game is too simple/unfinished
#CONFIGPATH = "%s/.config/file.conf" % os.getenv("HOME")
SRCPATH = ( os.path.join(os.path.realpath(__file__), 'src'))

startStats = {
    'playerDay'       : 1,
    'playerMoney'     : 20,
    'supereasyQuest1' : 0,
    'supereasyQuest2' : 0,
    'supereasyQuest3' : 0,
    'currentquest'    : '',
    'doAttackMessageProbe' : 0,
}

playerData = {
    'playerName'      : 'Tarasius',
    'playerHP'        : 100,
    'playerdead'      : 0,
    'playerSP'        : 0,
    'playerAttackDmg' : 6,
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
        if newpred.endswith('menu') or newpred.endswith('completescreen'):
            funplayer.set_mode('MENU')
        else:
            funplayer.set_mode()
        #funplayer.delete_memory()
        funplayer.play(newpred)

def forExitcode(predname):
    def makeQuestVars(questname):
        return {'currentquest' : questname,
                 questname     : 0,
              'editedFile'     : 0,
              'downloadedFile' : 0,
              'viewingFiles'   : 0,
              'viewingEmails'  : 0,
              'deletedEmail'   : 0,
            'completedMission' : 0,
        }

    varsForPredname = {
                'mainmenu' :  playerData,
    'supereasyQuest1entry' :  makeQuestVars('supereasyQuest1'),
    'supereasyQuest2entry' :  makeQuestVars('supereasyQuest2'),
    'supereasyQuest3entry' :  makeQuestVars('supereasyQuest3'),
    }
    try:
        return varsForPredname[predname]
    except KeyError:
        return {}

if __name__ == '__main__':
    main()
