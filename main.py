#!/usr/bin/env python3
#=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~==~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=#
#
# main.py for an example game
# last modified 2017/03/25
# created 2017/03/23 by tassaron
#
#=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~==~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=#
#
# Licence would go here if anyone cared
#
#=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~==~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=#
import os
import funplayer

# not used yet but probably
HOME = os.getenv("HOME")
# path for this game's resources (not funtimes resources)
# currently nonexistent because the game is too simple/unfinished
SRCPATH = ( os.path.join(os.path.realpath(__file__), 'src'))

def main():
    funplayer.play('entry')
    funplayer.main()

if __name__ == '__main__':
    main()
