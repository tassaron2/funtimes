#!/usr/bin/env python3
'''
    FUNTIMES toolkit for miscellaneous stuff and junk
'''
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
from tempfile import gettempdir
from difflib import SequenceMatcher
from string import ascii_letters
from shutil import copytree, rmtree
from contextlib import suppress
from itertools import chain
import os
import atexit
import random

MYPATH  = os.path.dirname(os.path.realpath(__file__))
prederrors = (
    '',
    "what the hell? i can't find predicament %s\ndid you modify it while the game was running?", # 1
    "wrong predicament found: %s",
    "what?? %s %s doesn't exist, \nor didn't exist when the game was started! >:(",
    "in %s,\n%s %s was not ended before another %s started.",
    "reached end of %s\nbefore finding %s\ndid you modify it while the game was running?", # 5
    "in %s, %s has a type of '%s'.\ni don't know what the hell that means.",
    "%s doesn't have an /predicament for %s",
    "data directory %s\nis nonexistent or unreadable. wtf",
    "%s has the type '%s', which is insane.",
    "in %s:\npredicament %s has the following line:\n%s\nbut the variable '%s' doesn't exist\nmaybe you made a typo somewhere", # 10
    "in %s:\n%s has %s after if.\nyou forgot to use a keyword, used an invalid keyword,\nor didn't include a condition after 'or' or 'and'.\nkeywords other than 'then' must precede an if.\nonly use 'then' after the final if condition.",
    "in %s, there is an unexpected '/if' in predicament %s",
    "in %s, reached end of %s before '/if'.\nconditionals must remain within originating predicament.",
    "in %s,\n%s %s has a '%s' directive.\ni don't know what the hell that means.",
    "%s could not be found while searching for %s\ndid you rename or delete it while the game was running?", # 15
    "", # 16
    "reached end of %s while looking for '/if'.\nthis is literally the end of the world.",
    "in %s, %s has no '=' on this line:\n%s\nmaybe you made a typo?",
    "%s refers to a '%s.wav'. there was an error accessing\nor playing this file. did you mistype the name?",
    "predicament %s tries to set %s to '%s'\nbut %s is supposed to be a number!", # 20
    "predicament %s tries to set '%s' to a value\nbut that variable could not be created!",
    "predicament %s has this line:\n%s\nwhich changes the location of %s relatively, but %s hasn't been placed yet! >:(",
    "a movement or action directive in predicament %s contains this line:\n %s\nwhich does not have a -> in it.\nmovement and action must declare the label, then ->,\nthen the name of the predicament which the labelled movement\nor action leads to. for example:\n Leave the house. -> outside",
    "in %s\npredicament %s has the following condition:\n%s\nbut %s is not of a comparable type\nif it was intended to contain a word, it will always contain a word\nsetting it to a number will not allow you to perform comparisons",
    "in %s\npredicament %s has the following condition:\n%s\nthis is trying to perform a comparison on %s,\nbut %s is neither a number nor a variable containing a number.\nyou are comparing apples and oranges, and i'm allergic.",
    # ^-- 25
    "in %s, predicament %s has this line:\n%s\nan if statement must contain 'is' or '='",
    "in %s, predicament %s has this line:\n%s\nchecking the status of a quest can only be done with keywords:\ninitial, known, started, done, failed\nor 'progress' followed by a number",
    "in %s, predicament %s has this line:\n%s\nit appears to refer to a dictionary called '%s'\nbut i don't know what that is... :/",
    "in %s, predicament %s has this line:\n%s\nnegating a comparison is pointless. just use the opposite.",
    "in %s, predicament %s has this line:\n%s\nit appears to refer to a dictionary called %s\nbut that's not a valid dictionary.", #30
    "in %s, predicament %s has this line:\n%s\nsetting must be done using 'to' or '='.",
    "in %s, predicament %s has this line:\n%s\n%s is not sensible.\nquest entries must be set to keywords:\ninitial, known, started, done, failed\nor 'progress' followed by a number",
    "in %s, predicament %s\ntries to %s %s from player.\nthis item does not exist.",
    "in %s, predicament %s\ntries to take a pack of ketchup from player.\nthe player is saving that for a rainy day.\nthey refuse to let go of it.",
    "in %s, predicament %s\ndoes not have a '%s' on this line:\n%s\nyou must operate %s a variable, using that word.", #35
    "",
    "in %s, predicament %s\nhas this invalid line:\n%s\n'%s' is not an integer. you must use a whole number\nor a variables that is a whole number.",
    "in %s, predicament %s\nhas this invalid line:\n%s\n'%s' does not refer to a number. you can't %s it.",
    "",
    "in %s, predicament %s has this line:\n%s\nbut funtimes was still reading a map at the time\nso you probably screwed up major.", #40
    # ^-- 40
    "in %s\npredicament %s is of 'goto' type\nbut it has no destination after '->'",
    "in %s\npredicament %s has this line:\n%s\nwhich is a broken dude. that's not weet.",
    "in %s\na dude named %s\nwants in on tick '%s'\nbut the tick number didn't bring its id",
    "in %s\n%s has multiple dudes with the same character\nthat's bound to cause trouble",
    "in %s,\n%s has an invalid map line:\n%s",
    # ^-- 45
    "predicament %s fell off the map\nwhile searching for a spot near %s, %s",
    "in %s,\npredicament %s has this line:\n%s\nbut variable names must be 2 characters or greater\na 1-char name would get mixed up with the dudes!"
)

class FuntimesError(Exception):
    def __init__(self, code=0, *args):
        from subprocess import call
        from funtimes import Dude, Predicament
        print('after seeing %s dudes in %s predicaments,' %\
                (Dude.numDudes, Predicament.numPredicaments))
        print("i got this weird error code:", code)
        if code != 0 and code < len(prederrors):
            print(prederrors[code] % args)
        print("i can't work under these conditions. i quit.\n")
        call('read -n1 -r -p "press any key to delete tmp files & exit\n" key',
            shell=True, executable='/bin/bash')
        quit(code)

def overwriteTree(olddir, newdir):
    while True:
        try:
            copytree(olddir, newdir)
        except FileExistsError:
            rmtree(newdir)
        else:
            break

def emptyCoordClosestTo(x, y, xdirection, ydirection, predmap, name=''):
    '''args: int x, int y, str xdirection, str ydirection, list of str map
    Finds a free spot on a provided list of maplines, using x- & y-direction to
    determine whether to move + or - away from x,y if x,y is not empty on map'''
    while True:
        try:
            row = predmap[y]
            try:
                if row[x] == ' ':
                    break
                if xdirection == '+':
                    x += 1
                else:
                    x -= 1
            except IndexError:
                x=1
                if ydirection == '+':
                    y += 1
                else:
                    y -= 1
        except IndexError:
            raise FuntimesError(46, name, x, y)
    # found a suitable location for the dude!
    return x, y

def getNonBlankLine(fp):
    line = ''
    while line == '' or line.startswith("#"):
        line = fp.readline()
        if not line:
            # if eof is reached, that's bad.
            raise FuntimesError(17, fp.name)
        line = line.strip()
    return line

def keyOfLine(line, splitter):
    key = line
    with suppress(ValueError):
        key, value = line.split(splitter, 1)
    return key.strip()

def multiSplit(line, *args):
    for splitter in args:
        try:
            key, value = line.split(splitter)
        except ValueError:
            continue
        return key, value
    else:
        # TODO FIX ERROR MSG
        raise FuntimesError(26, fp.name, self.name, line)

def findVariables(text):
    '''
    finds text surrounded by % in a string and returns that text
    '''
    if '%' not in text or '%' not in text[text.index('%')+1:]:
        return text
    start = text.index('%')
    end = text[start+1:].index('%') + start + 1
    return text[start+1:end]

def replaceVariables_(text, vardict):
    '''
    replaces '%varname%' in a string with a class variable in Predicament
    stored in the Predicament.variables dict with varname as the key
    '''
    if text==None:
        return text
    text = text.strip()
    if '%' not in text or '%' not in text[text.index('%')+1:]:
        # '%' doesn't appear or doesn't appear again after appearing
        return text
    start = text.index('%')
    end = text[start+1:].index('%') + start + 1
    if text[start+1:end] not in vardict:
        # replace variable with nothing if it doesn't exist
        return replaceVariables_('%s %s' % (text[:start], text[end+1:]), vardict)
    else:
        return replaceVariables_(text[:start] + str(vardict[text[start+1:end]])
                            + text[end+1:], vardict)

def replaceTilde(text):
    if text.startswith('~'):

        return '%s/%s%s' % (MYPATH, 'src', text[1:])
    else:
        return text

def giveNumberIfPossible(value):
    try:
        value = int(value)
    except ValueError:
        pass
    return value

def stringSimilarity(a, b):
    return SequenceMatcher(None, a, b).quick_ratio()

def randomString():
    return "".join([random.choice(ascii_letters) for i in range(20)])
