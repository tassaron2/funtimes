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
# last modified 2017/05/06
# resurrected by tassaron 2017/03/23
# from code by ninedotnine & tassaron 2013/05/24-2013/06/30
# inspired by a batch file game made in 2008
#
#=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~==~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~#
# TODO: different fatality levels for FuntimesError & option to ignore minor
#       make FuntimesError take filename, predname, and line for every error
# TODO: fix pred functions not applying their mapnames for some weird reason
# TODO: goto and functions can run the same code so they could be same thing?
# TODO: markup =
# TODO: make certain actions take more ticks to execute
# TODO: capturing key input
# TODO: track when virtualpreds aren't needed anymore so they can be deleted

from funtoolkit import *

# syntax
PRIMARY_SPLITTER = '='
SECONDARY_SPLITTER = '->'
DEFAULT_MAP_WALL = '>>>>>>>>>'  # determines automap dimensions

# directory paths to data
PREDDIR = os.path.join(MYPATH, 'pred')
DUDEDIR = PREDDIR
TMPDIR  = os.path.join(gettempdir(), 'funtimesenginedata')

# dicts of filenames & lineNums for game object definitions,
predicaments = {}  # created by makeGlobalDicts()
dudes = {}         # created by makeGlobalDicts()
virtualpreds = {}  # created by ", filled in by VirtualPredicament.register()

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
            elif isDude:
                readingTick = 0
            return readingTick

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
                    if self.name in virtualpreds:
                        Predicament.variables['predname'] = virtualpreds[self.name][1]
                    else:
                        Predicament.variables['predname'] = self.name
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
            if not self.isFunction:
                '''
                self.isFunction._on_parser_finish = \
                    list(chain(self.isFunction._on_parser_finish, self._on_parser_finish))
                self._on_parser_finish = []
            else:
                '''
                # run any functions
                for func in self._on_parser_finish:
                    try:
                        func()
                    except TypeError:
                        raise FuntimesError(666)
            if isPredicament:
                addDudesToMap()
                for symbol, tuple_ in self.dudeLocations.items():
                    Predicament.variables[symbol] = tuple_

        def getFilenameAndLine(dir_, filetype, name):
            # get the info we have in the global dicts...
            try:
                if filetype == 'pred':
                    filename, lineNo, virtualLines = predicaments[name]
                elif filetype == 'dude':
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
            busy = False  # whether we are currently reading something
            for line in fp:
                # count down to the correct line
                if lineNo > 1:
                    lineNo -= 1
                    continue
                line = line.strip()
                busy = True
                break
            if not busy:
                raise FuntimesError(5, self.filename, name)
            return line

        def addDudesToMap():
            '''called by _on_parser_finish'''
            allthepredmap = str(self.predmap)
            if len(allthepredmap) > 2:
                for symbol in self.dudeSymbols:
                    if symbol in allthepredmap:
                        continue
                    elif symbol in self.dudeLocations:
                        x, y = self.dudeLocations[symbol]
                        row = self.predmap[y]
                        self.predmap[y] = '%s%s%s' % \
                            (row[:x], symbol, row[x+1:])

        def giveAllDudesLocations():
            mapLength = len(self.predmap)
            if mapLength:
                for symbol in self.dudeSymbols:
                    if symbol not in self.dudeLocations:
                        while True:
                            # picks a random index of a string across a random row
                            randomY = random.randint(1, mapLength-1)
                            randomRowLine = self.predmap[randomY]
                            randomX = random.randint(1, len(randomRowLine)-1)
                            # make sure it's a free spot
                            if randomRowLine[randomX] != ' ':
                                continue
                            else:
                                self.dudeLocations[symbol] = (randomX, randomY)
                                break

        whatIAm, isPredicament, isDude = whoAmI(filetype)

        #=~=~=~ TRY TO OPEN THE FILE CONTAINING THIS PREDICAMENT OR DUDE
        self.filename, lineNo, virtualLines = getFilenameAndLine(
            mydir, filetype, self.name)

        with open(os.path.join(mydir, self.filename), 'r') as fp:
            # find line in file where this predicament begins...
            busy = findStartPoint(fp, lineNo, whatIAm, self.name)
            # initialize some tracking variables
            readingTick = init_trackers(isPredicament, isDude)
            oldpredname = init_env_predname(isPredicament)

            # finally, we start actually assigning the data
            # line should be true (it should still be the new line)
            line = True
            doneReadingFile = False
            while line:
                if isDude and readingTick != 0\
                    and readingTick not in self.ticks:
                    # new tick? append to list of ticks this dude wants in on
                    self.ticks.append(readingTick)

                if not doneReadingFile:
                    line = getNonBlankLine(fp)
                else:
                    # finished reading!
                    busy = False
                    break

                #=~  FIRST DO STUFF WITHOUT = IN IT
                if line.find("/%s" % whatIAm) == 0:
                    # finished reading the file!
                    # (but there could still be virtualLines)
                    doneReadingFile = True
                    if isPredicament:
                        giveAllDudesLocations()
                    continue
                if line.strip() == 'quit':
                    self._parse_quit(readingTick)
                    continue
                if isDude and line.find("/tick") == 0 \
                    or isDude and line.find("/exec") == 0:
                    readingTick=0
                    continue
                if self._parse_weird_lines(fp, line, readingTick):
                    # if this returns True then it did the parsing work for us
                    continue

                #=~=~=~=~ NORMAL STUFF THAT USES =
                try:
                    key, value = line.split(PRIMARY_SPLITTER, 1)
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
                elif key == 'exec' and isDude:
                    readingTick = -1
                    continue
                elif key == 'entry' and isPredicament:
                    self._parse_text(value, True, readingTick)
                    continue
                elif key == 'action':
                    self._parse_action(fp, value, line, readingTick)
                    continue
                elif key in ('function', 'parent', 'embed') and isPredicament:
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
                    raise FuntimesError(14, self.filename,
                        whatIAm, self.name, key)
        cleanUp(isPredicament, busy)

    def _parse_text(self, value, isEntry, readingTick):
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

    def _parse_action(self, fp, value, line, readingTick=-1):
        try:
            action, goto = value.split(SECONDARY_SPLITTER, 1)
        except ValueError:
            raise FuntimesError(23, self.name, line)
        action = action.strip()
        goto = goto.strip()
        if not goto:
            # read until '/action' if there's no destination for this
            goto = VirtualPredicament.register(self.name, fp, '/action')
        if readingTick == -1:
            # predicament
            self.actionLabel.append(action)
            self.actionGoto.append(goto)
        elif readingTick > -1:
            # dude
            self.addEvent(readingTick, 'action', '%s=%s' % (action, goto))

    def _parse_arrow(self, fp, key, value, readingTick=-1):
        '''args: file object, 'up'/'down'/etc, goto predname, applicable tick'''
        def sendToPredicament(label, goto):
            for i, d in enumerate(('up', 'down', 'left', 'right')):
                if key == d:
                    if label:
                        # change label from default if one is set
                        self.arrowLabel[i] = label.strip()
                    self.arrowGoto[i] = goto.strip()
                    continue

        def mapOverwriter(direction):
            if direction == 'left':
                def mapDrawer():
                    for i in range(3, 6):
                        self.predmap[i] = '#%s' % self.predmap[i][1:]
            elif direction == 'right':
                def mapDrawer():
                    for i in range(3, 6):
                        try:
                            self.predmap[i] = '%s#' % self.predmap[i][:-1]
                        except IndexError:
                            print(self.name, " broke")
            elif direction in ('up', 'down'):
                magicnumber = (direction == 'down') * -1
                def mapDrawer():
                    self.predmap[magicnumber] = DEFAULT_MAP_WALL
            return mapDrawer

        def doCode(keyword):
            newpred = VirtualPredicament.register(self.name, fp, '/%s' % key)
            if keyword:
                if keyword == 'disable map':
                    self._on_parser_finish.append( mapOverwriter(key) )
            return None, newpred

        magicKeywords = [ 'disable map' ]
        value = value.strip()
        try:
            label, goto = value.split(SECONDARY_SPLITTER, 1)
        except ValueError:
            if not value or value in magicKeywords:
                label, goto = doCode(value)
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
        if readingTick == -1:
            self.inputtype = 'quit' #predicament
        elif readingTick > -1:
            self.addEvent(readingTick, 'quit', '')  #dude

    def _parse_exit(self, value, readingTick):
        # tell funplayer to close the window
        if readingTick == -1:
            self.inputtype = 'exit%s' % value  #predicament
        elif readingTick > -1:
            self.addEvent(readingTick, 'exit', value)

    @staticmethod
    def parseCoords(self, dudesymbol, line):
        '''Interprets a comma-separated string of x, y coords
        These can be relative coords if they start with +/-
        A tilde is equivalent to +0 (coord remains the same)'''
        try:
            x, y = line.split(',')
        except ValueError:
            raise FuntimesError(681)
        x = x.strip()
        y = y.strip()

        def addOrSubtract(newCoord, XorY):
            if newCoord.startswith('+'):
                if XorY == 'x':
                    self.xdirection='+'
                else:
                    self.ydirection='+'
            else:
                if XorY == 'x':
                    self.xdirection='-'
                else:
                    self.ydirection='-'
            if XorY == 'x':
                oldCoord = self.dudeLocations[dudesymbol][0]
            elif XorY == 'y':
                oldCoord = self.dudeLocations[dudesymbol][1]

            try:
                if newCoord.startswith('-'):
                    direction = '-'
                newCoord = oldCoord + eval(newCoord)
            except ValueError:
                raise FuntimesError(5665432)
            return newCoord

        def getNumber(coord, XorY):
            try:
                return int(coord)
            except ValueError:
                if XorY == 'x' and coord == '~':
                    return self.dudeLocations[dudesymbol][0]
                elif XorY == 'y' and coord == '~':
                    return self.dudeLocations[dudesymbol][1]
                raise FuntimesError(719)

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
            line = '%s%s%s' % (dudesymbol, PRIMARY_SPLITTER, line)
            raise FuntimesError(22, self.name, line, dudesymbol, dudesymbol)
        return x, y


    def _parse_weird_lines(self, fp, line, readingTick):
        # returns True if it successfully parses a weird line
        # readingTick defaults to -1 for Predicaments, otherwise this is a Dude

        def doSet(line, readingTick=-1):
            key, value = multiSplit(line, ' to ', PRIMARY_SPLITTER)
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

            if len(key)<2:
                raise FuntimesError(47, self.filename, self.name, line)

            try:
                if type(Predicament.variables[key]) in (int, float):
                    newvalue = int(newvalue)
            except KeyError:
                # nonexistaent variable!
                newvalue = giveNumberIfPossible(newvalue)
            except ValueError:
                # TODO: setting number variable to a string variable
                pass

            if readingTick == -1:
                # this is happening immediately
                Predicament.variables[key] = newvalue
            elif readingTick > -1:
                self.addEvent(readingTick, 'set', '%s=%s' % (key, newvalue))

        def doMath(line, operator, preposition, readingTick=-1):
            '''args: line, 'add'/'subtract', 'to'/'from', readingTick'''
            try:
                # variable assignment literally backwards, because that's fun
                # square bracket weirdness removes the operator from the line
                start = len(operator)+1
                value, key = line[start:].split(' %s ' % preposition)
                value = value.strip()
                key = key.strip()
            except ValueError:
                raise FuntimesError(35, self.filename, self.name,
                    line, preposition, preposition)
            if type(Predicament.variables[key]) != int:
                raise FuntimesError(38, self.filename, self.name, line, key,
                    '%s %s' % (operator, preposition))
            # make sure variable exists
            if key not in Predicament.variables:
                raise FuntimesError(10, self.filename, self.name, line, key)

            if readingTick == -1:
                # we're doing this immediately - make it a number
                try:
                    value = int(value)
                except ValueError:
                    # is it not a goddamn number?
                    try:
                        value = int(replaceVariables(value))
                    except ValueError:
                        # yeah, it's not a goddamn number
                        raise FuntimesError(37, self.filename, self.name,
                            line, value)
                if operator == 'add':
                    Predicament.variables[key] += value
                elif operator == 'subtract':
                    Predicament.variables[key] -= value
                else:
                    raise FuntimesError(555555)
            elif readingTick > -1:
                self.addEvent(readingTick, '%s' % operator,
                                     '%s=%s' % (key, value))

        def skipIf(fp):
            while Parser.readingIfLevel < Parser.tempIfLevel:
                nextline = getNonBlankLine(fp)
                if nextline.startswith("/if"):
                    Parser.tempIfLevel -= 1
                elif nextline.startswith("if "):
                    Parser.tempIfLevel += 1
                elif nextline.find("/predicament") == 0 \
                    or nextline.find("/tick") == 0:
                    raise FuntimesError(13, self.name, predname)

        def doIf(fp, line):
            # mutated code from 2013
            # figures out whether to read conditional stuff in pred definitions

            # first, parse the line itself to get key and value
            # try splitting the if on 'is' or '='
            key, value = multiSplit(line, ' is ', PRIMARY_SPLITTER)

            try:
                value, followup = value.split(SECONDARY_SPLITTER)
                followup = followup.strip()
                if not followup:
                    followup = 'then'
            except ValueError:
                followup = None

            # while removing the 'if ' from the key...
            potentialKey = replaceVariables(key[3:].strip())
            if potentialKey in Predicament.variables:
                # try expanding % first
                key = potentialKey
            else:
                # if that won't work try stripping out %
                key = findVariables(key[3:].strip())

            negate = False
            if value.startswith('not '):
                value = value[4:] # remove the 'not ' part
                negate = True

            if len(key) == 1:
                # use local variables first, environment variables second
                globalDude = False
                if key not in self.dudeLocations:
                    if key in Predicament.variables:
                        globalDude = True
                    else:
                        # nonexistent dude
                        raise FuntimesError(48, self.filename, self.name, line, key)
                isDude = True
                try:
                    value = eval(value.strip())
                except SyntaxError:
                    if '~' not in value:
                        # non-numeric input
                        raise FuntimesError(294)
                    else:
                        if globalDude:
                            oldLocation = Predicament.variables[key]
                        else:
                            oldLocation = self.dudeLocations[key]
                        value0, value1 = value.split(',')
                        if value0.strip() == '~':
                            value = (oldLocation[0], int(value1))
                        else:
                            value = (int(value0), oldLocation[1])
            else:
                isDude = False
                value = replaceVariables(value)

            # why is this happening in here? global vars >:O
            Parser.tempIfLevel = Parser.readingIfLevel + 1

            # wtf
            if isDude:
                conditionIsTrue = ( oldLocation == value )

            # if the var doesn't exist, freak the hell out
            elif key not in Predicament.variables.keys():
                #raise FuntimesError(10, fp.name, name, line, key)
                conditionIsTrue = False

            # comparison cases > and <
            elif value.startswith('>') or value.startswith('<'):
                if type(Predicament.variables[key]) not in (int, float):
                    # the key isn't a comparable type
                    raise FuntimesError(24, fp.name, self.name, line, key)
                try:
                    comparee = eval(value[1:])
                except NameError:
                    # it's not a comparable value.
                    raise FuntimesError(25, fp.name, self.name, line,
                                              key, value[1:].strip())
                if value[1:].strip() in dir():
                    # uh oh. a consequence of using eval...
                    # try to stop file referring to variables in this module
                    raise FuntimesError(96)
                if type(comparee) not in (int, float):
                    # the value isn't a comparable type
                    raise FuntimesError(25, fp.name, self.name, value,
                                              Predicament.variables[key], comparee)
                if value.startswith('>'):
                    conditionIsTrue = ( Predicament.variables[key] > comparee )
                elif value.startswith('<'):
                    conditionIsTrue = ( Predicament.variables[key] < comparee )

            # regular ol' equality
            else:
                if type(Predicament.variables[key]) == int:
                    value = giveNumberIfPossible(value)
                conditionIsTrue = ( Predicament.variables[key] == value )

            if negate:
                conditionIsTrue = not conditionIsTrue
            # end of wtf

            if not followup:
                # get 'then', 'and', 'or' from next line
                followup = getNonBlankLine(fp).lower()

            if followup.startswith("then not"):
                # don't use this, it breaks if more than one statement is processed
                # for the simplest statements, it's okay.
                return not conditionIsTrue
            elif followup.startswith("then"):
                return conditionIsTrue
            line = getNonBlankLine(fp)
            if not line.startswith("if "):
                raise FuntimesError(11, fp.name, self.name, "'%s'" % followup)
            if followup.startswith("and not"):
                return ( not doIf(fp, line) and conditionIsTrue )
            elif followup.startswith("and"):
                return ( doIf(fp, line) and conditionIsTrue )
            elif followup.startswith("or not"):
                return ( not doIf(fp, line) or conditionIsTrue )
            elif followup.startswith("or"):
                return ( doIf(fp, line) or conditionIsTrue )
            #else:
                #return conditionIsTrue
            raise FuntimesError(11, fp.name, self.name, line)

        def computeIf(fp, line):
            if doIf(fp, line):
                # if the condition is true, read normally
                Parser.readingIfLevel += 1
            else:
                # if the condition isn't true,
                # discard lines until we reach end if
                skipIf(fp)

        line = line.strip()
        #=~=~=~=~ '/' BLOCK TERMINATORS
        if line.find("/if") == 0:
            if Parser.readingIfLevel > 0:
                Parser.readingIfLevel -= 1
                return True
            raise FuntimesError(12, self.filename, self.name)
        #=~=~=~=~ IF
        elif line.startswith("if "):
            computeIf(fp, line)
            return True
        #=~=~=~=~ SET
        elif line.startswith("set "):
            doSet(line, readingTick)
            return True
        elif line.startswith("add "):
            doMath(line, 'add', 'to', readingTick)
            return True
        elif line.startswith("subtract "):
            doMath(line, 'subtract', 'from', readingTick)
            return True
        # Turns out this isn't a weird line!
        return False

    @staticmethod
    def doEvent(eventType, event):
        '''
        Does stuff in this module to alter the persistent state of
        the predicaments and dudes. This method is run as state is
        being returned to Funplayer for display.
        '''
        #=~=~=~ SET AND MATH
        if eventType in ('set', 'add', 'subtract'):
            # not using global syntax because events are internal
            key, value = event.split('=')
            newvalue = value
            try:
                if type(Predicament.variables[key]) in (int, float):
                    newvalue = giveNumberIfPossible(value)
            except KeyError:
                # nonexisteaent variable
                newvalue = giveNumberIfPossible(value)
            if eventType == 'set':
                Predicament.variables[key] = newvalue
            elif eventType == 'add':
                Predicament.variables[key] += newvalue
            elif eventType == 'subtract':
                Predicament.variables[key] -= newvalue
        #=~=~=~ JUST REPLACE %VARIABLES%
        elif eventType in ('text', 'action'):
            event = replaceVariables(event)
        return eventType, event

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
        global predicaments
        # gotta have more comments than code
        Predicament.numPredicaments += 1

        self.isFunction = None
        with suppress(KeyError):
            self.isFunction = kwargs['isFunction']

        def init():
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
            # symbols that represent the parallel dude on a map
            self.dudeSymbols = []
            self.dudeLocations = {}
            # Funplayer may want to generate Dudes on-the-fly but
            # we need information about dudes so we must also pregen them
            self._pregenDudes = []
            # Fake dudes... don't have names, used for entrytext currently
            self.fakeDudes = []
            # direction dude is facing on each axis
            self.xdirection='+'  # right
            self.ydirection='+'  # down
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

            # now read the pred file to fill in these attributes
            self._parse_everything('pred', PREDDIR)

        init()

        # if this is a virtual pred, read it again...
        filename, lineNo, virtualLines = predicaments[self.name]
        if virtualLines:
            TempFile.writeLines(self, virtualLines)
            predicaments[self.name] = (filename, lineNo, [])
            init()

    '''
        Parsing methods for the initialization
    '''

    def _parse_function(self, value):
        # a predicament embedded within another predicament
        if value not in predicaments:
            raise FuntimesError(999)
        else:
            newfunction = Predicament(value,isFunction=self)
        for thing in newfunction.__dict__:
            forbidden = ('name', 'sound','inputtype','filename','result')
            if thing in forbidden:
                continue
            functhing = getattr(newfunction, thing)
            realthing = getattr(self, thing)
            if type(functhing) == list:
                if thing in ('arrowLabel','arrowGoto'):
                    for i, arrow in enumerate(functhing):
                        if arrow:
                            realthing[i] = arrow
                else:
                    for line in functhing:
                        realthing.append(line)
            elif type(functhing) == dict:
                for key, value in functhing.items():
                    realthing[key] = value
            elif type(functhing) == str and thing == 'mapname':
                # TODO: this doesn't work
                realthing = functhing

    def _parse_dudesymbol(self, key, value):
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

        x, y = Parser.parseCoords(self, key, value)
        #x, y = emptyCoordClosestTo(x, y, self.xdirection, self.ydirection,
        #    self.predmap, self.name)
        if key in str(self.predmap):
            moveMapTile(key, x, y)
        self.dudeLocations[key] = (x, y)
        Predicament.variables[key] = (x, y)

    def _parse_type(self,value,oldpredname):
        # TODO: type = textinput -> result
        self.inputtype = value
        if value.startswith('goto'):
            # this is a goto! reset the environment variable pronto
            Predicament.variables['predname'] = oldpredname
            try:
                keyw, dest = value.split(SECONDARY_SPLITTER)
                self.inputtype = keyw.strip()
                self.goto  = replaceVariables(dest.strip())
            except ValueError:
                raise FuntimesError(41, self.filename, self.name)
        if self.inputtype not in ('normal', 'inputtext', 'goto'):
            raise FuntimesError(6, self.filename, self.name, value)

    def _parse_dude(self,value):
        try:
            thisDudesSymbol, thisDudesName = value.split(SECONDARY_SPLITTER)
        except ValueError:
            raise FuntimesError(42, self.filename, self.name, value)
        if thisDudesSymbol.strip() not in self.dudeSymbols:
            self._pregenDudes.append(Dude(thisDudesName.strip()))
            self._dudes.append(thisDudesName.strip())
            self.dudeSymbols.append(thisDudesSymbol.strip())
        else:
            raise FuntimesError(44, self.filename, self.name, thisDudesSymbol.strip())

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
                    if i == 0:
                        hasUp = True
                    elif i == 1:
                        hasDown = True
                    elif i == 2:
                        hasLeft = True
                    elif i == 3:
                        hasRight = True
            maplist = []
            if hasUp:
                maplist.append('>>>   >>>')
            else:
                maplist.append(DEFAULT_MAP_WALL)
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
                maplist.append(DEFAULT_MAP_WALL)
            self.predmap = maplist

        # read lines until /map if there is no value after 'map='
        if not value:
            readMap(fp, line)
        elif value == 'auto':
            # put AutoMap function in this queue...
            doAutoMap()
            self._on_parser_finish.append(doAutoMap)
            # so it can use pred data parsed after this line
        else:
            raise FuntimesError(45, self.filename, self.name, line)

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
            if dudeSymbol == char:
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
            if tickNum == 'everytick':
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
        Dude.numDudes += 1

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
        self.sound = None
        self.isFunction = None

        if self.name:
            # read dude file
            self._parse_everything('dude', DUDEDIR)
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
        if tick == 'everytick':
            for eventType, event in self.everytick:
                yield Parser.doEvent(eventType, event)
            #(self.doEvent(eventType, event) for eventType, event in self.everytick)
        else:
            for eventNum, event in zip(self.eventNums, self._events):
                # if this event is for the given tick...
                if eventNum == tick:
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
# CLASSES OF FUNCTIONS FOR TEMP-FILE HANDLING
#
#=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~==~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=#

class VirtualPredicament:
    '''A predicament created by the engine.
    The virtualpreds global dict contains tuples of:
    new unique predname : (parent's predname, original non-virtual predname)
    thus virtual preds spawned by a real pred will have both values equal
    virtual preds spawned by other virtual preds will have different values
    '''
    @staticmethod
    def register(oldpredname, fp, ender):
        '''fp is file object seeked to the right position to read virtuallines
        used to read a block of lines from a file, with ender as the
        end-block phrase. ender would be something like '/up' or '/action' '''
        global predicaments; global virtualpreds
        line=True
        newlines=[]
        while line:
            line = getNonBlankLine(fp)
            if line.find(ender) == 0:
                # skip this line & end
                break
            newlines.append(line)
        newpredname = Predicament.uniqueName()
        filename, lineNo, extralines = predicaments[oldpredname]
        predicaments[newpredname] = (filename, lineNo, newlines)
        originalpredname = oldpredname
        # dig through each parent's entry until we get a non-virtual one
        while originalpredname in virtualpreds:
            originalpredname = virtualpreds[originalpredname][0]
        virtualpreds[newpredname] = (oldpredname, originalpredname)
        return newpredname

class TempFile:
    originPredDir = PREDDIR
    originDudeDir = DUDEDIR

    @staticmethod
    def init():
        global PREDDIR
        global DUDEDIR
        overwriteTree(PREDDIR, TMPDIR)
        if DUDEDIR != PREDDIR:
            overwriteTree(DUDEDIR, TMPDIR)
        PREDDIR = TMPDIR
        DUDEDIR = TMPDIR
        atexit.register(TempFile.deleteTmpFiles)

    @staticmethod
    def resetTempFiles():
        overwriteTree(TempFile.originPredDir, TMPDIR)
        if DUDEDIR != PREDDIR:
            overwriteTree(TempFile.originDudeDir, TMPDIR)
        makeGlobalDicts()

    @staticmethod
    def deleteTmpFiles():
        rmtree(TMPDIR)

    @staticmethod
    def compressLines(self, virtualLines):
        # only certain magical things go into the topLines...
        topLines = []
        processedLines = []
        for i, line in enumerate(virtualLines):
            try:
                key, value = line.split(PRIMARY_SPLITTER, 1)
                key = key.strip(); value = value.strip()
            except ValueError:
                if line.strip().startswith('set '):
                    key = 'set'
                else:
                    continue
            if key in self.dudeSymbols:
                # found a dude!
                x, y = Parser.parseCoords(self, key, value)
                line = '%s%s%s,%s' % (key, PRIMARY_SPLITTER, x, y)
            elif key == 'set':
                pass
            else:
                continue
            topLines.append(line)
            processedLines.append(i)

        # boringly construct bottomLines and return both
        bottomLines = [line for i, line in enumerate(virtualLines) \
            if i not in processedLines]
        return bottomLines, topLines

    @staticmethod
    def writeLines(self, newLines, deftype='predicament'):
        def removeFromFileLines(fileLines, line):
            newFileLines = []
            # line_ is what we iterate thru in this context,
            # line is the line we want to remove sometimes...
            finished_ = False
            for lineNo_, line_ in enumerate(fileLines):
                if lineNo_ < targetLineNo:
                    newFileLines.append(line_)
                else:
                    if line_.find(defEnder) == 0:
                        finished_ = True
                    if not finished_ and line_ != line:
                        newFileLines.append(line_)
                    if finished_:
                        newFileLines.append(line_)
            return newFileLines

        global predicaments; global dudes
        # parse args
        if deftype == 'predicament':
            globaldict = predicaments
        elif deftype == 'dude':
            globaldict = dudes
        filename, targetLineNo, _ = globaldict[self.name]
        defEnder = '/%s' % deftype

        # open file, get pre-existing lines
        with open(os.path.join(TMPDIR, filename), 'r') as f:
            fileLines = [line for line in f]
        # make list of lines to write for the new version
        bottomLines, topLines = TempFile.compressLines(self, newLines)

        # remove any dudeLocations defined in topLines from the fileLines
        # thus the topLines will provide the 1 canonical location for each dude
        dudeLocationsToWorryAbout = [l.strip()[:1] for l in topLines\
            if len(keyOfLine(l, PRIMARY_SPLITTER)) == 1]
        #print('dudes of', self.name,':', dudeLocationsToWorryAbout)
        finished = False
        readingBlock = False
        blockStarters = ['left','right','up','down','action']
        blockEnders = ['/%s' % starter for starter in blockStarters]
        for lineNo, line in enumerate(fileLines[:]):
            if lineNo < targetLineNo:
                continue
            if line.find(defEnder) == 0:
                finished = True
            if finished:
                continue
            try:
                thisKey, thisValue = line.split(PRIMARY_SPLITTER, 1)
                thisKey = thisKey.strip()
                if thisKey in blockStarters:
                    readingBlock = True
                    continue

                if thisKey in dudeLocationsToWorryAbout:
                    if not readingBlock:
                        fileLines = removeFromFileLines(fileLines, line)
                if thisKey == 'dude':
                    if keyOfLine(thisValue.strip(), SECONDARY_SPLITTER) \
                        in dudeLocationsToWorryAbout:
                            fileLines = removeFromFileLines(fileLines, line)
                            if line not in topLines:
                                topLines.insert(0, line.strip())
            except ValueError:
                for ender in blockEnders:
                    if line.find(ender) == 0:
                        readingBlock = False
                continue

        # now finally we start creating the new file
        with open(os.path.join(TMPDIR, filename), 'w') as f:
            lineNo = 0
            finishedWork = False
            finishedTopLines = False
            for line in fileLines:
                lineNo += 1
                f.seek(f.tell())

                if lineNo < targetLineNo or finishedWork:
                    f.write(line)
                    continue

                # second if, only reached when reading definition we care about
                if not finishedTopLines:
                    # start of the def we care about!
                    f.write(line)
                    for line in topLines:
                        f.write('%s\n' % line)
                    finishedTopLines = True
                elif line.find(defEnder) != 0:
                    # middle of the def we care about!
                    f.write(line)
                    continue
                elif line.find(defEnder) == 0:
                    # bottom of the def we care about!
                    finishedWork = True
                    for line in bottomLines:
                        f.write('%s\n' % line)
                    f.seek(f.tell())
                    f.write('%s\n' % defEnder)
        # update any definitions that occur in this file
        with open(os.path.join(TMPDIR, filename), 'r') as f:
            lineNo = 0
            for line in f:
                lineNo += 1
                try:
                    key, value = line.split(PRIMARY_SPLITTER, 1)
                except ValueError:
                    continue
                key = key.strip()
                if key == 'predicament':
                    value = value.strip()
                    oldEntry = predicaments[value]
                    predicaments[value] = (oldEntry[0], lineNo, oldEntry[2])


#=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~==~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=#
#
# FUNCTIONS
#
#=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~==~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=#

def replaceVariables(text):
    return replaceVariables_(text, Predicament.variables)

def makePredicament(predname):
    '''called by funplayer'''
    return Predicament(predname)

def findAllDefinitions(dir_, filetype):
    # populate a dict with locations of all known definitions of this filetype
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
                        name = line.split(PRIMARY_SPLITTER)[1]
                        # create entry in predicaments dictionary
                        # 'name' : (filename,lineNo,virtualLines)
                        name = name.strip()
                        predicaments[name] = (os.path.join(dirpath, filename),
                            lineNo,[])
    return predicaments

def makeGlobalDicts():
    global predicaments
    global dudes
    global virtualpreds
    predicaments = findAllDefinitions(PREDDIR, 'pred')
    dudes = findAllDefinitions(DUDEDIR, 'dude')
    virtualpreds = {}

def printGlobalDict(*args):
    def printDict(dictionary):
        if not quiet:
            print("{:<30}".format('TITLE') + "| LINE | FILE")
            for key, value in dictionary.items():
                print("{:<30}".format(key) + "|",
                    "{:<5}".format(str(value[1])) + "|",
                    value[0].replace(MYPATH,''))
                if value[2]:
                    for line in value[2]:
                        print("{:>28}".format(line)+'  |      |')
        else:
            shown = set()
            for value in dictionary.values():
                if value[0] not in shown:
                    print(value[0])
                    shown.add(value[0])


    quiet = False
    if len(args) > 1:
        quiet = args[1]

    try:
        input_ = args[0]
    except IndexError:
        global predicaments; global dudes
        input_ = [predicaments, dudes]

    if type(input_) is list:
        for dictionary in input_:
            printDict(dictionary)
            if not quiet:
                print('~=~=~=~')
    elif type(input_) is dict:
        printDict(args[0])

if __name__ == '__main__':
    def showHelp():
        print("usage: funtimes.py [--paths] [--show-all]\n")
        print("--show-all      list all data in the global dicts")
        print("--paths         list unique filenames to pred/dude definitions")
        print("--help          print this message and exit")
        quit()
    import sys
    makeGlobalDicts()
    cmdArgs = sys.argv[1:]
    if cmdArgs:
        if '--paths' in cmdArgs:
            quiet = True
        elif '--show-all' in cmdArgs:
            quiet = False
        else:
            showHelp()
    else:
        showHelp()
    if not quiet:
        print('~=~=~=~ PREDICAMENTS ~=~=~=~')
        print("number of predicaments:", len(predicaments))
        print("contents of PREDDIR (", PREDDIR, "): \n",
            [line.replace(MYPATH,'') for line in os.listdir(PREDDIR)])
        print('~=~=~=~   ~=~=~=~')
    printGlobalDict(predicaments, quiet)
    if not quiet:
        print('~=~=~=~ DUDES ~=~=~=~')
        print("number of dudes:", len(dudes))
        if DUDEDIR == PREDDIR:
            print('DUDEDIR has same contents as PREDDIR')
        else:
            print("contents of DUDEDIR (", DUDEDIR, "): \n",
                [line.replace(MYPATH,'') for line in os.listdir(DUDEDIR)])
        print('~=~=~=~   ~=~=~=~')
    printGlobalDict(dudes, quiet)
else:
    TempFile.init()
    makeGlobalDicts()
