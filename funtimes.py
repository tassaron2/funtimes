#!/usr/bin/env python3
'''
FUNTIMES parser for creating Predicaments and Dudes from text files.
Creates objects interpreted by funplayer.py to make a playable game.

Copies PREDDIR and DUDEDIR to a TMPDIR so they can be edited non-destructively.
Passes around a file object called "fp" and uses getNonBlankLine() to read it.
Does nothing to /src, just references it in replaceTilde() for game resources.
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
# last modified 2017/04/12
# resurrected by tassaron 2017/03/23
# from code by ninedotnine & tassaron 2013/05/24-2013/06/30
# inspired by a batch file game made in 2008
#
#=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~==~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~#
# TODO: different fatality levels for FuntimesError & option to ignore minor
# TODO: fix pred functions not applying their mapnames for some weird reason
# TODO: allow action to run some code on this pred instead of going to a new pred
# TODO: goto and functions can run the same code so they could be same thing?
# TODO: markup =
# TODO: make certain actions take more ticks to execute
# TODO: capturing key input
# TODO: class collision between dudes would handle most cases (including warping)
#
#=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~==~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~#

from funtoolkit import *
import os
import random
from tempfile import gettempdir
from itertools import chain
from contextlib import suppress


#=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~==~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=#
#
# PARSER CLASSES
#
#=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~==~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=#

class Parser:
    '''Parent for anything that parses a file to define itself.
    Holds parsing methods used by both dudes and predicaments.'''

    def _parse_everything(self, filetype, mydir):
        '''
        Central hub from which all pred and dude file parsing is done.
              All the other _parse_ methods get called from here!
        '''
        def init_trackers(isPredicament, isDude):
            # this list stores functions to call when parsing is done
            self._on_parser_finish = []
            if isPredicament and not self.isFunction:
                # reset if tracker variables
                Parser.readingIfLevel = 0
                Parser.tempIfLevel = 0
            if isPredicament:
                readingTick = -1
                readingTickPassThru = None
            elif isDude:
                readingTick = 0
                readingTickPassThru = self
            return readingTick, readingTickPassThru

        def init_env_predname(isPredicament):
            '''For convenient use in preds, the %predname% environment
            variable is set as soon as possible in file-parsing.
            But it may need to be reset if this predicament ends up
            being a goto (to allow using %predname% within a goto).
            So this stores the old predname in case self._parse_type
            needs it later.'''
            oldpredname = None
            if isPredicament and not self.isFunction:
                # set environment variable for tracking current predicament
                try:
                    #store old predname in case this ends up being a goto
                    oldpredname = str(Predicament.variables['predname'])
                except KeyError:
                    # this is the first predicament so whatever
                    oldpredname = str(self.name)
                if not self.goto:
                    Predicament.variables['predname']=self.name
            return oldpredname

        def whoAmI(filetype):
            if filetype == 'pred':
                isDude = False
                isPredicament = True
                whatIAm = 'predicament'
            else:
                isDude = True
                isPredicament = False
                whatIAm = 'dude'
            return whatIAm, isPredicament, isDude

        def cleanUp(isPredicament, busy):
            # happens at the end of file-parsing; first make sure we're done
            if Parser.readingIfLevel and isPredicament and not self.isFunction:
                raise FuntimesError(13, self.filename, self.name)
            elif busy:
                # should always hit error 4 before this, so it may be redundant
                raise FuntimesError(7, self.filename, self.name)
            # run any functions
            for func in self._on_parser_finish:
                func()
            if self.isFunction:
                self._on_parser_finish = []

        def getFilenameAndLine(dir_, filetype, name):
            # get the info we have in the global dicts...
            try:
                if filetype=='pred':
                    filename, lineNo, virtualLines = predicaments[name]
                elif filetype=='dude':
                    filename, lineNo, virtualLines = dudes[name]
                else:
                    raise KeyError
            except KeyError:
                # if the predicament isn't in our master dictionary...
                raise FuntimesError(3, filetype, name)
            try:
                open(os.path.join(dir_, filename), 'r')
            except:
                raise FuntimesError(15, filename, name)

            return filename, lineNo, virtualLines

        def findStartPoint(fp, lineNo, lookingFor, name):
            # cProfile says this causes barely any overhead with 1000s of lines
            # we could do something like this: http://stackoverflow.com/a/620492
            # however it adds extra complexity w/o gain, unless file is collosal
            busy = False # whether we are currently reading something
            # now get to the right line and test it
            for line in fp:
                # count down to the correct line
                if lineNo > 1:
                    lineNo -= 1
                    continue
                line = line.strip()
                '''
                TODO: fix this part
                # we know this is the right line
                # but don't trust the dictionary & check anyway!
                if line.find('%s =' % lookingFor) != 0:
                    raise FuntimesError(1, name)
                # if it's the wrong thing, freak the hell out
                elif name != line.split('=')[1].strip():
                    raise FuntimesError(2, name)
                '''
                busy = True
                break
            if not busy:
                raise FuntimesError(5, self.filename, name)
            return True

        def addDudesToMap():
            '''called by _on_parser_finish'''
            allthepredmap = str(self.predmap)
            for symbol in self.dudeSymbols:
                if symbol in allthepredmap:
                    continue
                elif symbol in self.dudeLocations:
                    x, y = self.dudeLocations[symbol]
                    row = self.predmap[y]
                    self.predmap[y] = '%s%s%s' % \
                        (row[:x], symbol, row[x+1:])
            if self.dudeLocations:
                # DEBUG
                print(self.dudeLocations)

        def giveAllDudesLocations():
            for symbol in self.dudeSymbols:
                if symbol not in self.dudeLocations:
                    mapLength = len(self.predmap)
                    while True:
                        # picks a random index of a string across a random row
                        randomY = random.randint(1,mapLength-1)
                        randomRowLine = self.predmap[randomY]
                        randomX = random.randint(1, len(randomRowLine)-1)
                        # make sure it's a free spot
                        if randomRowLine[randomX] != ' ':
                            continue
                        else:
                            self.dudeLocations[symbol] = (randomX, randomY)
                            break

        def writeLines():
            writeLinesToFile(virtualLines, self.name)

        whatIAm, isPredicament, isDude = whoAmI(filetype)

        #=~=~=~ TRY TO OPEN THE FILE CONTAINING THIS PREDICAMENT OR DUDE
        self.filename, lineNo, virtualLines = getFilenameAndLine(
            mydir, filetype, self.name)

        with open(os.path.join(mydir, self.filename), 'r') as fp:
            # find line in file where this predicament begins...
            busy = findStartPoint(fp, lineNo, whatIAm, self.name)
            # initialize some tracking variables
            readingTick, readingTickPassThru = \
                init_trackers(isPredicament, isDude)
            oldpredname = init_env_predname(isPredicament)
            if isPredicament:
                self._on_parser_finish.append(addDudesToMap)
            if virtualLines:
                self._on_parser_finish.append(writeLines)

            # finally, we start actually assigning the data
            # line should be true (it should still be the new line)
            line=True
            doneReadingFile=False
            while line:
                if isDude and readingTick != 0\
                and readingTick not in self.ticks:
                    # new tick? append to list of ticks this dude wants in on
                    self.ticks.append(readingTick)

                if not doneReadingFile:
                    line = getNonBlankLine(fp)
                elif doneReadingFile and self.virtualLines:
                    # apparently using deque would 'give better performance'
                    # but for now I'll pop from the beginning of a list
                    line = self.virtualLines.pop(0)
                else:
                    # finished reading!
                    busy = False
                    break

                #=~  FIRST DO STUFF WITHOUT = IN IT
                if line.find("/%s" % whatIAm) == 0:
                    doneReadingFile=True
                    if isPredicament:
                        giveAllDudesLocations()
                    continue
                if line.strip() == 'quit':
                    self._parse_quit(readingTick)
                    continue
                if isDude and line.find("/tick") == 0\
                or isDude and line.find("/init") == 0:
                    readingTick=0
                    continue
                if Parser.doWeirdLines(fp, self.filename, self.name, line,
                        readingTick, readingTickPassThru):
                    # if this returns True then it did the parsing work for us
                    continue

                #=~=~=~=~ NORMAL STUFF THAT USES =
                try:
                    key, value = line.split('=',1)
                except ValueError:
                    raise FuntimesError(18, self.filename, self.name, line)

                if isPredicament and key.strip() in self.dudeSymbols:
                    # check for Dude symbols (sprite positions) first
                    # because they're case sensitive
                    self._parse_dudesymbol(key.strip(), value)
                    continue

                # everything else is case insensitive...
                key = key.rstrip().lower()
                value = value.strip()
                if key == whatIAm:
                    # we're in a new predicament without closing the last one.
                    # the pred file must be invalid.
                    raise FuntimesError(4, self.filename,
                        whatIAm, self.name, whatIAm)
                elif key == 'exit':
                    self._parse_exit(value, readingTick)
                    continue
                elif key == 'tick' and isDude:
                    try:
                        readingTick = int(value)
                        continue
                    except TypeError:
                        raise FuntimesError(43, filename, self.name, value)
                elif key == 'text':
                    self._parse_text(value, False, readingTick)
                    continue
                elif key == 'tile' and isDude:
                    self.tile = value
                    continue
                elif key == 'init' and isDude:
                    readingTick = -1
                    continue
                elif key == 'entry' and isPredicament:
                    self._parse_text(value,True, readingTick)
                    continue
                elif key == 'action':
                    self._parse_action(value,line, readingTick)
                    continue
                elif key in ('function','parent','embed') and isPredicament:
                    self._parse_function(value)
                    continue
                elif key == 'sound':
                    self._parse_sound(value)
                    continue
                elif key == 'type' and isPredicament:
                    self._parse_type(value, oldpredname)
                    continue
                elif key == 'map' and isPredicament:
                    self._parse_map(fp, line, value)
                    continue
                elif key == 'name':
                    self._parse_name(value, readingTick)
                    continue
                elif key == 'dude' and isPredicament:
                    self._parse_dude(value)
                    continue
                elif key in ('up', 'down', 'left', 'right') and isPredicament:
                    self._parse_arrow(fp, key, value)
                    continue
                else:
                    raise FuntimesError(14, whatIAm,\
                        self.filename, self.name, key)

        cleanUp(isPredicament, busy)

    def _parse_text(self,value,isEntry,readingTick):
        # remove only the first space if any
        if value and value[0] == ' ':
            value = value[1:]
        # add each line of text onto the prev line of text
        if readingTick == -1:
            value = replaceVariables(value)
        if readingTick == -1 and not isEntry:
            self._text.append(value)
        elif readingTick == -1 and isEntry:
            # make a fake dude to play this text on tick1
            self.fakeDudes.append(Dude.forEntrytext(value))
        elif readingTick > -1:
            # a regular dude
            self.addEvent(readingTick, 'text', value)

    def _parse_action(self,value,line,readingTick=-1):
        try:
            action, goto = value.split('->')
        except ValueError:
            raise FuntimesError(23, self.name, line)
        action = action.strip()
        goto = goto.strip()
        if readingTick==-1:
            # predicament
            self.actionLabel.append(action)
            self.actionGoto.append(goto)
        elif readingTick>-1:
            # dude
            self.addEvent(readingTick, 'action', '%s=%s' % (action, goto))

    def _parse_arrow(self, fp, key, value, readingTick=-1):
        def sendToPredicament(label, goto):
            for i, d in enumerate(('up', 'down', 'left', 'right')):
                if key == d:
                    if label:
                        # change label from default if one is set
                        self.arrowLabel[i] = label.strip()
                    self.arrowGoto[i] = goto.strip()
                    continue

        def doCode():
            line=True
            newlines=[]
            while line:
                line = getNonBlankLine(fp)
                if line.find('/%s' % key)==0:
                    # skip this line & end
                    break
                newlines.append(line)
            newpred = registerNewVirtualPred(self.name, newlines)
            return None, newpred

        try:
            label, goto = value.split('->')
        except ValueError:
            if value.strip()=='code':
                label, goto = doCode()
        else:
            label, goto = None, value
        sendToPredicament(label, goto)

    def _parse_name(self, value, readingTick):
        if readingTick==-1:
            # predicament
            self.mapname = replaceVariables(value)
        else:
            self.nick = replaceVariables(value)

    def _parse_sound(self,value):
        if not self.sound:
            self.sound=[value]
        else:
            self.sound.append(value)

    def _parse_quit(self, readingTick):
        # tell funplayer to quit the game
        if readingTick==-1:
            self.inputtype = 'quit' #predicament
        elif readingTick>-1:
            self.addEvent(readingTick, 'quit','') #dude

    def _parse_exit(self, value, readingTick):
        # tell funplayer to close the window
        if readingTick==-1:
            self.inputtype = 'exit%s' % value  #predicament
        elif readingTick>-1:
            self.addEvent(readingTick, 'exit', value)

    @staticmethod
    def doEvent(eventType, event):
        '''
        Does stuff in this module to alter the persistent state of
        the predicaments and dudes. This method is run as state is
        being returned to Funplayer for display.
        '''
        #=~=~=~ SET AND MATH
        if eventType in ('set','add','subtract'):
            key, value = event.split('=')
            newvalue = value
            try:
                if type(Predicament.variables[key]) in (int, float):
                    newvalue=giveNumberIfPossible(value)
            except KeyError:
                # nonexisteaent variable
                newvalue=giveNumberIfPossible(value)
            if eventType=='set':
                Predicament.variables[key]=newvalue
            elif eventType=='add':
                Predicament.variables[key]+=newvalue
            elif eventType=='subtract':
                Predicament.variables[key]-=newvalue
        #=~=~=~ JUST REPLACE %VARIABLES%
        elif eventType in ('text', 'action'):
            event = replaceVariables(event)
        return eventType, event

    @staticmethod
    def doWeirdLines(fp, filename, name, line, readingTick=-1,self=None):
        # returns True if it successfully parses a weird line
        # readingTick defaults to -1 for Predicaments
        # when readingTick is 0 or higher, it's for use by Dudes

        def doSet(filename, predname, line, readingTick=-1,self=None):
            # readingTick defaults to -1 for Predicaments
            # when readingTick is 0 or higher, it's for use by Dudes
            try:
                key, value = line.split('=')
            except ValueError:
                try:
                    key, value = line.split(' to ')
                except ValueError:
                    raise FuntimesError(31, filename, predname, line)
            # strip out the 'set ' part
            key = key[4:].strip()
            value = value.strip()
            # store it in the Predicament class dictionary right away
            # OR create a Dude event for it if this is a Dude
            # change value to a real number or something else if necessary

            key = replaceVariables(key)
            newvalue = replaceVariables(value)
            if value == 'random':
                newvalue = random.randint(1,100)

            try:
                if type(Predicament.variables[key]) in (int, float):
                    newvalue = int(newvalue)
            except KeyError:
                # nonexistaent variable!
                newvalue = giveNumberIfPossible(newvalue)
            except ValueError:
                # TODO: setting number variable to a string variable
                pass

            if readingTick==-1:
                # this is happening immediately
                Predicament.variables[key] = newvalue
            elif readingTick==0:
                #dude object has been passed to us
                self.everytick.append(('set','%s=%s' % (key, newvalue)))
            elif readingTick>0:
                self._events.append(('set','%s=%s' % (key, newvalue)))
                self.eventNums.append(readingTick)

        def doMath(filename, name, line, operator, preposition, readingTick=-1,self=None):
            '''args: filename, name, line, add/subtract, to/from, readingTick, DudeObject'''
            # readingTick defaults to -1 for Predicaments
            # when readingTick is 0 or higher, it's for use by Dudes
            # TODO: reduce stupid number of arguments
            try:
                # variable assignment literally backwards, because that's more fun
                # square bracket weirdness removes the operator from the line
                start = len(operator)+1
                value, key = line[start:].split(' %s ' % preposition)
                value = value.strip()
                key = key.strip()
            except ValueError:
                raise FuntimesError(35, filename, name, line,preposition,preposition)
            if type(Predicament.variables[key]) != int:
                raise FuntimesError(38, filename, name, line, key, '%s %s' % (operator, preposition))
            # make sure variable exists
            if key not in Predicament.variables:
                raise FuntimesError(10, filename, name, line, key)

            # if we're doing this immediately
            if readingTick==-1:
                # make it a number
                try:
                    value = int(value)
                except ValueError:
                    # is it not a goddamn number?
                    try:
                        value = int(replaceVariables(value))
                    except ValueError:
                        # yeah, it's not a goddamn number
                        raise FuntimesError(37, filename, name, line, value)
                if operator=='add':
                    Predicament.variables[key]+=value
                elif operator=='subtract':
                    Predicament.variables[key]-=value
                else:
                    raise FuntimesError()
            elif readingTick==0:
                #dude object has been passed to us
                self.everytick.append(('%s' % operator,
                                       '%s=%s' % (key, value)))
            elif readingTick>0:
                self._events.append(('%s' % operator,
                                     '%s=%s' % (key, value)))
                self.eventNums.append(readingTick)

        def computeIf(fp, name, line, readingTick=None):
            def doIf(fp, name, line, readingTick=None):
                # code from 2013
                # figures out whether to read conditional stuff in pred definitions
                # first, parse the line itself to get key and value

                # try splitting the if on 'is' or '='
                # nested trys are ugly, we could maybe do something better
                # try this
                for splitter in (' is ', '='):
                    try:
                        key, value = line.split(splitter)
                    except ValueError:
                        continue
                    break
                else:
                    raise FuntimesError(26, fp.name, name, line)
                # remove the 'if ' from the key
                potentialKey = replaceVariables(key[3:].strip())
                if potentialKey in Predicament.variables:
                    # expand % first
                    key = potentialKey
                else:
                    # if that won't work try stripping out %
                    key = findVariables(key[3:].strip())
                value = replaceVariables(value)

                # why is this happening in here? global vars >:O
                Parser.tempIfLevel = Parser.readingIfLevel + 1

                # make sure key exists
                if key not in Predicament.variables.keys():
                    # if the var doesn't exist, freak the hell out
                    raise FuntimesError(10, fp.name, name, line, key)

                # wtf
                if value.startswith('>') or value.startswith('<'):
                    if type(Predicament.variables[key]) not in (int, float):
                        # the key isn't a comparable type
                        raise FuntimesError(24, fp.name, name, line, key)
                    try:
                        comparee = eval(value[1:])
                    except NameError:
                        # it's not a comparable value.
                            raise FuntimesError(25, fp.name, name, line,
                                                      key, value[1:].strip())
                    if value[1:].strip() in dir():
                    #if value[1:].strip() in dir(__name__):
                        # uh oh. a consequence of using eval...
                        # the pred file can refer to variables in this code
                        # this doesn't even catch all of these cases
                        # it might, if we hadn't called something else predicaments
                        raise FuntimesError(96)
                    if type(comparee) not in (int, float):
                        # the value isn't a comparable type
                        raise FuntimesError(25, fp.name, name, value,
                                                  Predicament.variables[key], comparee)
                    if value.startswith('>'):
                        conditionIsTrue = ( Predicament.variables[key] > comparee )
                    if value.startswith('<'):
                        conditionIsTrue = ( Predicament.variables[key] < comparee )
                # if the value doesn't start with > or < ...
                else:
                    negate = False
                    if value.startswith('not '):
                        value = value[4:] # remove the 'not ' part
                        negate = True
                    if value.startswith('<') or value.startswith('>'):
                        # can't be arsed supporting negated comparisons
                        raise FuntimesError(29, fp.name, name, line)
                    if type(Predicament.variables[key]) == int:
                        try:
                            conditionIsTrue = ( Predicament.variables[key] == int(value) )
                        except ValueError:
                            conditionIsTrue = False
                            #raise FuntimesError(25, fp.name, name, line, key, value)
                    else:
                        conditionIsTrue = ( Predicament.variables[key] == value )
                    if negate:
                        conditionIsTrue = not conditionIsTrue
                # end of wtf

                followup = getNonBlankLine(fp).lower() # get 'then', 'and', 'or'
                if followup.startswith("then not"):
                    # don't use this, it breaks if more than one statement is processed
                    # for the simplest statements, it's okay.
                    return not conditionIsTrue
                elif followup.startswith("then"):
                    return conditionIsTrue
                line = getNonBlankLine(fp)
                if not line.startswith("if "):
                    raise FuntimesError(11, fp.name, name, "'%s'" % followup)
                if followup.startswith("and not"):
                    return ( not doIf(fp, name, line) and conditionIsTrue )
                elif followup.startswith("and"):
                    return ( doIf(fp, name, line) and conditionIsTrue )
                elif followup.startswith("or not"):
                    return ( not doIf(fp, name, line) or conditionIsTrue )
                elif followup.startswith("or"):
                    return ( doIf(fp, name, line) or conditionIsTrue )
                raise FuntimesError(11, fp.name, name, line)

            def skipIf(fp, predname):
                while Parser.readingIfLevel < Parser.tempIfLevel:
                    nextline = getNonBlankLine(fp)
                    if nextline.startswith("/if"):
                        Parser.tempIfLevel -= 1
                    elif nextline.startswith("if "):
                        Parser.tempIfLevel += 1
                    elif nextline.find("/predicament") == 0 \
                    or nextline.find("/tick") == 0:
                        raise FuntimesError(13, 'idk', predname)

            # here's where I jumped through a flaming hoop
            # to avoid changing ninedotnine's doIf() code :P
            if doIf(fp, name, line, readingTick):
                # if the condition is true, read normally
                Parser.readingIfLevel += 1
            else:
                # if the condition isn't true,
                # discard lines until we reach end if
                skipIf(fp, name)

        line = line.strip()
        #=~=~=~=~ '/' BLOCK TERMINATORS
        if line.find("/if") == 0:
            if Parser.readingIfLevel > 0:
                Parser.readingIfLevel -= 1
                return True
            raise FuntimesError(12, filename, name)
        #=~=~=~=~ IF
        elif line.startswith("if "):
            computeIf(fp, name, line, readingTick)
            return True
        #=~=~=~=~ SET
        elif line.startswith("set "):
            doSet(filename, name, line, readingTick,self)
            return True
        elif line.startswith("add "):
            doMath(filename, name, line, 'add', 'to', readingTick,self)
            return True
        elif line.startswith("subtract "):
            doMath(filename, name, line, 'subtract', 'from', readingTick,self)
            return True
        # Turns out this isn't a weird line!
        return False

class Predicament(Parser):
    """
    when creating a Predicament, pass in a string holding the name.
    the constructor will find the .pred file with this name in the PREDDIR
    by checking the predicaments dictionary created at runtime.
    to play this predicament, use play() in funplayer.py
    """

    # pointless class variable: number of generated Predicaments
    numPredicaments = 0
    # tiles for objects that are not dudes
    tiles = { '#' : '~/wall.png',
              '>' : '~/wall.png',
              '^' : '~/wall.png',
              ' ' : '',
            }
    # dictionary of pred variables
    variables = {}

    def __init__(self, name, **kwargs):
        # gotta have more comments than code
        Predicament.numPredicaments += 1

        self.isFunction=False
        with suppress(KeyError):
            self.isFunction = kwargs['isFunction']

        # predname used to create this
        self.name = name
        # messages displayed in the description box
        self._text = []
        # inputtypes: normal, textinput, goto
        self.inputtype = 'normal'
        #=~=~ Movement
        # remember when funtimes had four options per screen? :p
        self.actionLabel = []
        self.actionGoto = []
        # 2nd 'arrow' list is confusing without the first:
        self.arrowLabel = ['^', 'v', '<', '>']
        self.arrowGoto = [None, None, None, None]
        #=~=~ Dudes
        # a list of dudenames
        self._dudes = []
        # symbols that represent the parellel dude on a map
        self.dudeSymbols = []
        self.dudeLocations = {}
        # Funplayer may want to generate Dudes on-the-fly but
        # we need information about dudes so we must also pregen them
        self._pregenDudes = []
        # Fake dudes... don't have names, used for entrytext currently
        self.fakeDudes = []

        self.xdirection='+'
        self.ydirection='+'
        # destination that funplayer should goto right away
        # i.e. if not None then user won't see this pred
        self.goto = None
        # variable outputed by 'textinput' inputtype
        self.result = None
        # sound played at Predicament creation
        self.sound = None
        # MAP DATA
        # list of lines of tiles to draw for the map
        self.predmap = []
        # name displayed over the map
        self.mapname = None

        # fetch any virtual lines for this predicament...
        self.virtualLines = list(predicaments[self.name][2])

        # now read the pred file to fill in these attributes
        self._parse_everything('pred',PREDDIR)

    '''
        Parsing methods for the initialization
    '''

    def _parse_function(self, value):
        # a predicament embedded within another predicament
        if value not in predicaments:
            raise FuntimesError(999)
        else:
            newfunction = Predicament(value,isFunction=True)
        for thing in newfunction.__dict__:
            forbidden = ('name', 'sound','inputtype','filename','result')
            if thing in forbidden:
                continue
            functhing = getattr(newfunction, thing)
            realthing = getattr(self, thing)
            if type(functhing)==list:
                if thing in ('arrowLabel','arrowGoto'):
                    for i, arrow in enumerate(functhing):
                        if arrow:
                            realthing[i] = arrow
                else:
                    for line in functhing:
                        realthing.append(line)
            elif type(functhing)==dict:
                for key, value in functhing.items():
                    realthing[key] = value
            elif type(functhing)==str and thing=='mapname':
                # TODO: this doesn't work
                realthing = functhing

    def _parse_dudesymbol(self, key, value):
        def getRealCoord(x, y):
            '''takes x,y as strings; returns as integers'''
            x = x.strip()
            y = y.strip()

            def addOrSubtract(newCoord, XorY):
                if newCoord.startswith('+'):
                    if XorY=='x':
                        self.xdirection='+'
                    else:
                        self.ydirection='+'
                else:
                    if XorY=='x':
                        self.xdirection='-'
                    else:
                        self.ydirection='-'
                if XorY=='x':
                    oldCoord = self.dudeLocations[key][0]
                elif XorY=='y':
                    oldCoord = self.dudeLocations[key][1]

                try:
                    if newCoord.startswith('+'):
                        newCoord = oldCoord+int(newCoord[1:])
                    elif newCoord.startswith('-'):
                        direction = '-'
                        newCoord = oldCoord-int(newCoord[1:])
                except ValueError:
                    raise FuntimesError(5665432)
                return newCoord

            def getNumber(coord, XorY):
                try:
                    return int(coord)
                except ValueError:
                    if XorY=='x' and coord=='~':
                        return self.dudeLocations[key][0]
                    elif XorY=='y' and coord=='~':
                        return self.dudeLocations[key][1]
                    raise FuntimesError(729268777456789)

            def emptySpaceClosestTo(x, y):
                # find a free spot
                while True:
                    try:
                        row = self.predmap[y]
                        try:
                            if row[x]==' ':
                                break
                            if self.xdirection=='+':
                                x+=1
                            else:
                                x-=1
                        except IndexError:
                            x=1
                            if self.ydirection=='+':
                                y+=1
                            else:
                                y-=1
                    except IndexError:
                        raise FuntimesError(46787654)
                # found a suitable location for the dude!
                return x, y

            def moveMapTile(symbol, x, y):
                for i, line in enumerate(self.predmap):
                    if symbol in line:
                        symIndex = line.index(symbol)
                        self.predmap[i] = '%s %s' % \
                                (line[:symIndex], line[symIndex+1:])
                        break
                row = list(self.predmap[y])
                row[x] = symbol
                self.predmap[y] = "".join(row)

            try:
                if x[:1] not in ('+','-'):
                    x = getNumber(x, 'x')
                else:
                    x = addOrSubtract(x, 'x')

                if y[:1] not in ('+','-'):
                    y = getNumber(y, 'y')
                else:
                    y = addOrSubtract(y, 'y')
            except KeyError:
                # doing math on a dude with no previous location
                raise FuntimesError(34564523)
            x, y = emptySpaceClosestTo(x, y)
            if key in str(self.predmap):
                moveMapTile(key, x, y)
            return x, y

        try:
            x, y = value.split(',')
        except ValueError:
            raise FuntimesError(681)
        x, y = getRealCoord(x, y)
        self.dudeLocations[key] = (x, y)

    def _parse_type(self,value,oldpredname):
        # TODO: type = textinput -> result
        self.inputtype = value
        if value.startswith('goto'):
            # this is a goto! reset the environment variable pronto
            Predicament.variables['predname'] = oldpredname
            try:
                keyw, dest = value.split('->')
                self.inputtype = keyw.strip()
                self.goto  = replaceVariables(dest.strip())
            except ValueError:
                raise FuntimesError(41, self.filename, self.name)
        if self.inputtype not in ('normal', 'inputtext', 'goto'):
            raise FuntimesError(6, self.filename, self.name, value)

    def _parse_dude(self,value):
        try:
            thisDudesSymbol, thisDudesName = value.split('->')
        except ValueError:
            raise FuntimesError(42, self.filename, self.name, value)
        if thisDudesSymbol.strip() not in self.dudeSymbols:
            self._pregenDudes.append(Dude(thisDudesName.strip()))
            self._dudes.append(thisDudesName.strip())
            self.dudeSymbols.append(thisDudesSymbol.strip())
        else:
            raise FuntimesError(44, self.filename, self.name)

    def _parse_map(self, fp, line, value):
        def readMap(fp, line):
            def getDudeLocations():
                # TODO: fix this, it never works
                for y, line in enumerate(self.predmap):
                    for symbol in self.dudeSymbols:
                        if symbol in line:
                            self.dudeLocations[symbol] = line.index(symbol), y
                            print(self.dudeLocations[symbol])

            # fp and line are things we need to iterate through the pred file
            maplist = []
            while line:
                # move down 1 line
                line = fp.readline()
                # stop reading if we encounter an end-block
                if line.find('/map') != -1:
                    break
                elif line.find('/predicament') != -1:
                    raise FuntimesError(40, self.filename, self.name, line.strip())
                else:
                    # if the map isn't done yet, add this line onto the map
                    # strip out the terminating newline character on the right
                    maplist.append(line[:-1])

            # deduce how much indentation to remove from the left
            longest = max(maplist)
            indentSize = len(longest) - len(longest.lstrip())
            self.predmap = [line[indentSize:] for line in maplist]
            getDudeLocations()

        def doAutoMap():
            # automatically create a 9x9 map with doors
            hasUp, hasDown, hasLeft, hasRight = False, False, False, False
            for i, arrow in enumerate(self.arrowGoto):
                if arrow:
                    if i==0:
                        hasUp = True
                    elif i==1:
                        hasDown = True
                    elif i==2:
                        hasLeft = True
                    elif i==3:
                        hasRight = True
            maplist = []
            if hasUp:
                maplist.append('>>>   >>>')
            else:
                maplist.append('>>>>>>>>>')
            maplist.append('>       >')
            maplist.append('>       >')
            if hasLeft and not hasRight:
                centerline = '        >'
            elif hasRight and not hasLeft:
                centerline = '>        '
            elif hasLeft and hasRight:
                centerline = '         '
            else:
                centerline = '>       >'
            for i in range(3):
                maplist.append(centerline)
            maplist.append('>       >')
            maplist.append('>       >')
            if hasDown:
                maplist.append('>>>   >>>')
            else:
                maplist.append('>>>>>>>>>')
            self.predmap = maplist

        # read lines until /map if there is no value after 'map='
        if not value:
            readMap(fp, line)
        elif value=='auto':
            # put AutoMap function in this queue...
            self._on_parser_finish.append(doAutoMap)
            # so it can use pred data parsed after this line
        else:
            raise FuntimesError(45, self.filename, self.name, line)

    # this isn't used anywhere, but handy for debugging
    def __str__(self):
        return '< Predicament %s: %s >' % (self.name, self._text)

    @property
    def actions(self):
        return ((replaceVariables(label), replaceVariables(goto))\
                for label, goto in zip(self.actionLabel, self.actionGoto))

    @property
    def arrows(self):
        return ((replaceVariables(label), replaceVariables(goto))\
                for label, goto in zip(self.arrowLabel, self.arrowGoto))

    @property
    def text(self):
        return (line for line in self._text)

    @property
    def tilemap(self):
        return self.predmap

    def tileForChar(self, char):
        '''
        Receives a character from funplayer while it's drawing a tilemap
        This function returns the tile for the dude corresponding to the
        char provided for this Predicament.
        '''
        # first check if it's a wall or floor
        if char in Predicament.tiles:
            return replaceTilde(Predicament.tiles[char])
        # it must be a dude!
        for dudeSymbol, dudeObj in zip(self.dudeSymbols, self._pregenDudes):
            if dudeSymbol==char:
                # aha! it's this dude
                return replaceTilde(dudeObj.tile)
        return char

    def dudesForTick(self, tickNum):
        '''
        returns list of dudenames who want to do something this tickNum
        also small arachnids, part of the order Parasitiformes
        '''
        # iterate through our dudes
        for dudeObj in chain(self._pregenDudes, self.fakeDudes):
            if tickNum=='everytick':
                if not dudeObj.everytick:
                    continue
            elif tickNum not in dudeObj.ticks:
                continue
            # return this dude if relevant to the requested tick
            yield dudeObj.name

    @staticmethod
    def uniqueName():
        while True:
            newname = randomString()
            if newname not in predicaments:
                break
        return newname

class Dude(Parser):
    '''
    when creating a Dude, pass in a string containing the dude's name.
    the constructor will find the .dude file with this name in the DUDEDIR
    by checking the dudes dictionary created at runtime.
    Dudes have events defined within 'tick' blocks that should be executed
    on a certain 'tick'. The first 'play' of a Predicament is the first
    tick, and so on. Use funplayer.py to play a Predicament
    '''
    numDudes = 0
    def __init__(self, name):
        Dude.numDudes+=1

        # name used to generate this dude
        self.name = name
        # potential displayable name for this dude
        self.nick = None
        # fullpath to tilefile, always a string
        self.tile = 'None'
        # list of ticks this Dude wants in on
        self.ticks = []
        # events this dude wants to inject at certain tickNo
        self._events = [] # a list of ('key','value') pairs
        # parellel list of tickNumbers for events
        self.eventNums = []
        # events this dude is really persistent about
        self.everytick = [] # a list of ('key','value') pairs

        # things that don't matter
        self.sound=None
        self.isFunction=False

        if self.name:
            # fetch any virtual lines for this dude...
            self.virtualLines = list(dudes[self.name][2])
            # read dude file
            self._parse_everything('dude',DUDEDIR)
        else:
            # no dudename? must be a fake dude created by the engine
            # there's no file to parse so let's get outta here!
            pass

    @staticmethod
    def forEntrytext(text):
        '''creates a fake dude with a text event for tick 1
        which stores a line of entrytext from a predicament'''
        imposter = Dude(name=None)
        imposter._parse_text(text, False, 1)
        imposter.ticks.append(1)
        return imposter

    '''
        EVENTS
    '''
    def events(self, tick):
        '''public method returns events for the given tick number'''
        if tick=='everytick':
            for eventType, event in self.everytick:
                yield Parser.doEvent(eventType, event)
            #(self.doEvent(eventType, event) for eventType, event in self.everytick)
        else:
            for eventNum, event in zip(self.eventNums, self._events):
                # if this event is for the given tick...
                if eventNum==tick:
                    yield Parser.doEvent(event[0],event[1])

    def addEvent(self, readingTick, eventType, event):
        if readingTick == 0:
            # this event is for every tick
            self.everytick.append((eventType, event))
        elif readingTick > 0:
             # this event is for specific tick
            self._events.append((eventType, event))
            self.eventNums.append(readingTick)


#=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~==~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=#
#
# FUNCTIONS AND GLOBAL VARIABLES, WHERE IT ALL BEGINS
#
#=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~==~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=#

def replaceVariables(text):
    return replaceVariables_(text, Predicament.variables)

def findAllDefinitions(dir_, filetype):
    # populate a dictionary with locations of all known definitions of this filetype
    if not os.path.isdir(dir_):
        raise FuntimesError(8, dir_)
    predicaments = {}
    # search recursively within the directory
    for dirpath, _, filenames in os.walk(dir_):
        for filename in filenames:
            basename, ext = os.path.splitext(filename)
            if ext != '.%s' % filetype:
                #skip files that don't end in .pred or.dude
                continue
            pointless = True # whether this boolean is pointless
            lineNo = 0
            with open(os.path.join(dir_, dirpath, filename), 'r') as fp:
                for line in fp:
                    lineNo += 1
                    line = line.strip()
                    if line.find("predicament =") == 0 and filetype=='pred'\
                    or line.find("dude =") == 0 and filetype=='dude':
                        name = line.split('=')[1]
                        # create entry in predicaments dictionary
                        # 'predname' : ('which pred file it is in',lineNo,virtualLines)
                        name = name.strip()
                        predicaments[name] = (os.path.join(dirpath, filename), lineNo,[])
    return predicaments

def registerNewVirtualPred(oldpredname, newlines):
    global predicaments
    newpredname = Predicament.uniqueName()
    filename, lineNo, extralines = predicaments[oldpredname]
    alllines = newlines
    #alllines = list(chain(extralines, newlines))
    predicaments[newpredname] = (filename, lineNo, alllines)
    return newpredname

def compressLines():
    # garbage code I might rewrite, currently unused
    prevLine = 'fhqwhgads'
    for line in dudeSymbols:
        print(line)
        # combine series of +/-1s into a larger number
        if stringSimilarity(prevLine[1:], line[1:]) > 0.7:
            # >70% only includes string with numbers on same side
            # ('~,+1' and '+1,~' are 56% similar)
            lineDudesymbol, line = line.split('=')
            prevLineDudesymbol, prevLine = prevLine.split('=')
            if lineDudesymbol.strip() != prevLineDudesymbol.strip():
                # whoops! these are different dudes. don't confuse em
                continue
            lineX, lineY = line.split(',')
            prevLineX, prevLineY = line.split(',')
            newLineX, newLineY = False, False
            if stringSimilarity(lineX, prevLineX) == 1.0:
                try:
                    newLineX = int(lineX) + int(prevLineX)
                except ValueError:
                    newLineX = lineX
            if stringSimilarity(lineY, prevLineY) == 1.0:
                try:
                    newLineY = int(lineY) + int(prevLineY)
                except ValueError:
                    newLineY = lineY
            if newLineX is int or newLineY is int:
                print('test')
            else:
                # both sides are the same?
                newLine = False
        else:
            newLine = False

def writeLinesToFile(newLines, defname, deftype='predicament'):
    if deftype == 'predicament':
        filename, targetLineNo, _ = predicaments[defname]
    elif deftype == 'dude':
        filename, targetLineNo, _ = dudes[defname]
    defEnder = '/%s' % deftype
    with open(os.path.join(TMPDIR, filename), 'r') as f:
        fileLines = [line for line in f]

    # now finally we start creating the new file
    with open(os.path.join(TMPDIR, filename), 'w') as f:
        lineNo = 0; finishedWork = False
        for line in fileLines:
            lineNo += 1
            f.seek(f.tell())
            if lineNo < targetLineNo or finishedWork:
                # not the definition we care about
                f.write(line)
                continue
            if line.find(defEnder) != 0:
                # we care about this but it's not the end yet
                f.write(line)
                continue
            elif line.find(defEnder) == 0:
                # TIME TO DO SOME WORK!!!
                finishedWork = True
                for line in newLines:
                    f.write('%s\n' % line)
                f.seek(f.tell())
                f.write('%s\n' % defEnder)

def makePredicament(predname):
    '''called by funplayer'''
    return Predicament(predname)

# directory paths to data
PREDDIR = os.path.join(MYPATH, 'pred')
DUDEDIR = PREDDIR
TMPDIR  = os.path.join(gettempdir(), 'funtimesenginedata')

def makeTempFiles():
    global PREDDIR
    global DUDEDIR
    overwriteTree(PREDDIR, TMPDIR)
    if DUDEDIR != PREDDIR:
        overwriteTree(DUDEDIR, TMPDIR)
    PREDDIR = TMPDIR
    DUDEDIR = TMPDIR
# run this function immediately
makeTempFiles()

# filename and line-number dicts
predicaments = findAllDefinitions(PREDDIR, 'pred')
dudes = findAllDefinitions(DUDEDIR, 'dude')

if __name__ == '__main__':
    print("content of", PREDDIR, ": ", os.listdir(PREDDIR))
    print('----')
    print("number of predicaments:", len(predicaments))
    for key in predicaments:
        print(key + ":", predicaments[key])
    print('----')
    print("content of", DUDEDIR, ": ", os.listdir(DUDEDIR))
    print('----')
    print("number of dudes:", len(dudes))
    for key in dudes:
        print(key + ":", dudes[key])
