#!/usr/bin/env python3
#=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~==~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=#
#
# funtimes.py
# last modified 2017/04/02
# resurrected by tassaron 2017/03/23
# from code by ninedotnine & tassaron 2013/05/24-2013/06/30
# inspired by a batch file game made in 2008
#
#=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~==~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=#
#
# FUNTIMES parser for Predicament files & associated stuff
# parses files in PREDDIR and DUDEDIR filepaths
# does nothing to /src, just references it in replaceTilde()
# defines objects used by funplayer.py to play a game
#
# TODO: different fatality levels for BadPredicamentError & option to ignore minor
# TODO: fix functions not applying their mapnames for some weird reason
# TODO: merge all dude-event-queue code together
# TODO: invalid variable deletes entire line, not just the variable
#
#=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~==~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=#
#
# Licence would go here if anyone cared
#
#=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~==~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=#
import os
import random
from itertools import chain

class BadPredicamentError(Exception):
    def __init__(self, code=0, *args):
        print("predicament error code:", code)
        if code != 0 and code < len(prederrors):
            print(prederrors[code] % args)
        print("i can't work under these conditions. i quit.\n")
        print('saw %s dudes in %s predicaments' % (Dude.numDudes, Predicament.numPredicaments))
        quit()

class Parser:
    def _parse_everything(self, filetype, mydir):
        '''
        Central hub from which all pred and dude file parsing is done.
        '''
        def init_trackers(isPredicament,isDude):
            if isPredicament:
                # reset if tracker variables
                Parser.readingIfLevel = 0
                Parser.tempIfLevel = 0
                readingTick = -1
                readingTickPassThru = None
            elif isDude:
                readingTick = 0
                readingTickPassThru = self
            return readingTick, readingTickPassThru

        def init_env_predname(isPredicament):
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
            if filetype=='pred':
                isDude=False
                isPredicament=True
                whatIAm='predicament'
            else:
                isDude=True
                isPredicament=False
                whatIAm='dude'
            return whatIAm, isPredicament, isDude
            
        def cleanUp(isPredicament, busy):
            if Parser.readingIfLevel and isPredicament:
                raise BadPredicamentError(13, self.filename, self.name)
            elif busy:
                # should always hit error 4 before this, so it may be redundant
                raise BadPredicamentError(7, self.filename, self.name)

        def tryToOpen(dir_, filetype, name):
            try:
                if filetype=='pred':
                    filename, lineNo = predicaments[name]
                elif filetype=='dude':
                    filename, lineNo = dudes[name]
                else:
                    raise KeyError
            except KeyError:
                # if the predicament isn't in our master dictionary...
                raise BadPredicamentError(3, filetype, name)
            try:
                open(os.path.join(dir_, filename), 'r')
            except:
                raise BadPredicamentError(15, filename, name)

            return filename, lineNo

        def findStartPoint(fp, lineNo, lookingFor, name):
            # cProfile says this causes barely any overhead even with 1000s of lines
            # we could do something like this: http://stackoverflow.com/a/620492
            # however it adds extra complexity w/o any gain, unless file is collosal
            busy = False # whether we are currently reading something
            # now get to the right line and test it
            for line in fp:
                # count down to the correct line
                if lineNo > 1:
                    lineNo -= 1
                    continue
                line = line.strip()
                # we know this is the right line
                # but don't trust the dictionary & check anyway!
                if line.find('%s =' % lookingFor) != 0:
                    raise BadPredicamentError(1, name)
                # if it's the wrong thing, freak the hell out
                elif name != line.split('=')[1].strip():
                    raise BadPredicamentError(2, name)
                busy = True
                break
            if not busy:
                raise BadPredicamentError(5, filename, name)
            return True

        whatIAm, isPredicament, isDude = whoAmI(filetype)
        
        #=~=~=~ TRY TO OPEN THE FILE CONTAINING THIS PREDICAMENT OR DUDE
        self.filename, lineNo = tryToOpen(mydir, filetype, self.name)

        with open(os.path.join(mydir, self.filename), 'r') as fp:
            # find line in file where this predicament begins...
            busy = findStartPoint(fp, lineNo, whatIAm, self.name)
            # initialize some tracking variables
            readingTick, readingTickPassThru = init_trackers(isPredicament,isDude)
            oldpredname = init_env_predname(isPredicament)
            
            # finally, we start actually assigning the data
            # line should be true (it should still be the new line)
            line=True
            while line:
                if isDude and readingTick != 0 and readingTick not in self.ticks:
                    # if reading a new tick, append to list of ticks this dude wants in on
                    self.ticks.append(readingTick)
                
                line = getNonBlankLine(fp)

                #=~  FIRST DO STUFF WITHOUT = IN IT
                if line.find("/%s" % whatIAm) == 0:
                    busy = False
                    break
                if line.strip() == 'quit':
                    self._parse_quit(readingTick)
                    continue
                if isDude and line.find("/tick") == 0:
                    readingTick=0
                    continue
                if doWeirdLines(fp, self.filename, self.name, line, readingTick, readingTickPassThru):
                    # if this returns True then it did the parsing work for us
                    continue

                #=~=~=~=~ NORMAL STUFF THAT USES =
                try:
                    key, value = line.split('=',1)
                except ValueError:
                    raise BadPredicamentError(18, self.filename, self.name, line)

                if isPredicament and key.strip() in self.dudesymbols:
                    # check for Dude symbols first because they're case sensitive
                    self._parse_dudesymbol(key.strip(), value)
                    continue
                    
                # everything else is case insensitive...
                key = key.rstrip().lower()
                if key == whatIAm:
                    # we're in a new predicament without closing the last one.
                    # the pred file must be invalid.
                    raise BadPredicamentError(4, self.filename, whatIAm, self.name, whatIAm)
                elif key == 'exit':
                    self._parse_exit(value.strip(), readingTick)
                    continue
                elif key == 'tick' and isDude:
                    try:
                        readingTick = int(value.strip())
                        continue
                    except TypeError:
                        raise BadPredicamentError(43, filename, self.name, value.strip())
                elif key == 'text':
                    self._parse_text(value.strip(),False,readingTick)
                    continue
                elif key == 'tile' and isDude:
                    self.tile = value.strip()
                    continue
                elif key == 'entry' and isPredicament:
                    self._parse_text(value.strip(),True,readingTick)
                    continue
                elif key == 'action':
                    self._parse_action(value,line,readingTick)
                    continue
                elif key == 'function' and isPredicament:
                    self._parse_function(value.strip())
                    continue
                elif key == 'sound':
                    self._parse_sound(value.strip())
                    continue
                elif key == 'type' and isPredicament:
                    self._parse_type(value.strip(),oldpredname)
                    continue
                elif key == 'map' and isPredicament:
                    self._parse_map(fp, line)
                    continue
                elif key == 'name':
                    self._parse_name(value.strip(), readingTick)
                    continue
                elif key == 'dude' and isPredicament:
                    self._parse_dude(value.strip())
                    continue
                elif key in ('up', 'down', 'left', 'right') and isPredicament:
                    self._parse_arrow(key, value.strip())
                    continue
                else:
                    raise BadPredicamentError(14, whatIAm, self.filename, self.name,
                                              key.strip())

        cleanUp(isPredicament, busy)

    def _parse_text(self,value,isEntry,readingTick):
        # remove only the first space if any
        if value and value[0] == ' ':
            value = value[1:]
        # add each line of text onto the prev line of text
        if readingTick==-1:
            value = replaceVariables(value)
        if readingTick==-1 and not isEntry:
            self._text.append(value)
        elif readingTick==-1 and isEntry:
            # make a fake dude to play this text on tick1
            self.fakeDudes.append(Dude.forEntrytext(value))
        elif readingTick>0:
            # this event is for specific tick
            self._events.append(('text',value))
            self.eventNums.append(readingTick)
        elif readingTick==0:
            # this event is for every tick
            self.everytick.append(('text',value))
            
    def _parse_action(self,value,line,readingTick=-1):
        try:
            action, goto = value.split('->')
        except ValueError:
            raise BadPredicamentError(23, self.name, line)
        if readingTick==-1:
            # predicament
            self.actionLabel.append(action)
            self.actionGoto.append(goto.strip())
        elif readingTick==0:
            # dude everytick
            self.everytick.append(('action','%s=%s' % (action, goto)))
        elif readingTick>0:
            self._events.append(('action','%s=%s' % (action, goto)))
            self.eventNums.append(readingTick)

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
            self.inputtype = 'quit'
        elif readingTick>0:
            # this event is for specific tick
            self._events.append(('quit',''))
            self.eventNums.append(readingTick)
        elif readingTick==0:
            # this event is for every tick
            self.everytick.append(('quit',''))

    def _parse_exit(self, value, readingTick):
        # tell funplayer to close the window
        if readingTick==-1:
            self.inputtype = 'exit%s' % value
        elif readingTick>0:
            # this event is for specific tick
            self._events.append(('exit',value))
            self.eventNums.append(readingTick)
        elif readingTick==0:
            # this event is for every tick
            self.everytick.append(('exit',value))

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

    def __init__(self, name, isFunction=False):
        # gotta have more comments than code
        Predicament.numPredicaments += 1

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
        self.dudesymbols = []
        self.dudeLocations = {}
        # Funplayer may want to generate Dudes on-the-fly but
        # we need information about dudes so we must also pregen them
        self._pregenDudes = []
        # Fake dudes... don't have names, used for entrytext currently
        self.fakeDudes = []
        # whether or not this is being loaded as a function
        self.isFunction=isFunction

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
        self._parse_everything('pred',PREDDIR)

    '''
        Parsing methods for the initialization
    '''

    def _parse_function(self, value):
        if value not in predicaments:
            raise BadPredicamentError(999)
        else:
            newfunction = Predicament(value,True)
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
                realthing = functhing

    def _parse_dudesymbol(self, key, value):
        try:
            x, y = value.split(',')
        except ValueError:
            raise BadPredicamentError(681)
        self.dudeLocations[key] = (int(x.strip()), int(y.strip()))

    def _parse_type(self,value,oldpredname):
        # TODO: type = textinput -> result
        self.inputtype = value
        if value.startswith('goto'):
            Predicament.variables['predname']=oldpredname
            try:
                keyw, dest = value.split('->')
                self.inputtype = keyw.strip()
                self.goto  = replaceVariables(dest.strip())
            except ValueError:
                raise BadPredicamentError(41, self.filename, self.name)
        if self.inputtype not in ('normal', 'inputtext', 'goto'):
            raise BadPredicamentError(6, self.filename, self.name, value)

    def _parse_arrow(self,key,value):
        try:
            label, goto = value.split('->')
        except ValueError:
            label, goto = None, value
        for i, d in enumerate(('up', 'down', 'left', 'right')):
            if key == d:
                if label:
                    # change label from default if one is set
                    self.arrowLabel[i] = label.strip()
                self.arrowGoto[i] = goto.strip()
                continue

    def _parse_dude(self,value):
        try:
            thisDudesSymbol, thisDudesName = value.split('->')
        except ValueError:
            raise BadPredicamentError(42, self.filename, self.name, value)
        if thisDudesSymbol.strip() not in self.dudesymbols:
            self._pregenDudes.append(Dude(thisDudesName.strip()))
            self._dudes.append(thisDudesName.strip())
            self.dudesymbols.append(thisDudesSymbol.strip())
        else:
            raise BadPredicamentError(44, self.filename, self.name)

    def _parse_map(self, fp, line):
        # fp and line are things we need to iterate through the pred file
        # name is something we only need to raise errors, to help debug
        maplist = []
        while line:
            # move down 1 line
            line = fp.readline()
            # stop reading if we encounter an end-block
            if line.find('/map') != -1:
                break
            elif line.find('/predicament') != -1:
                raise BadPredicamentError(40, self.filename, self.name, line.strip())
            else:
                # if the map isn't done yet, add this line onto the map
                # strip out the terminating newline character on the right
                maplist.append(line[:-1])

        # deduce how much indentation to remove from the left
        longest = max(maplist)
        indentSize = len(longest) - len(longest.lstrip())
        self.predmap = [line[indentSize:] for line in maplist]

    # this isn't used anywhere, but handy for debugging
    def __str__(self):
        return '< Predicament %s: %s >' % (self.name, self._text)
        
    @property
    def actions(self):
        return ((replaceVariables(label), replaceVariables(goto)) for label, goto in zip(self.actionLabel, self.actionGoto))

    @property
    def arrows(self):
        return ((replaceVariables(label), replaceVariables(goto)) for label, goto in zip(self.arrowLabel, self.arrowGoto))
    
    @property
    def text(self):
        return (line for line in self._text)

    @property
    def tilemap(self):
        predmap = self.predmap
        if len(predmap)<1:
            return predmap
        for symbol in self.dudesymbols:
            # add dudes to the map
            if symbol in str(predmap):
                # don't add dude if she's already on the map
                continue
            elif symbol in self.dudeLocations:
                x, y = self.dudeLocations[symbol]
                # find a free spot
                while True:
                    row = predmap[y]
                    try:
                        if row[x]==' ':
                            break
                        x+=1
                    except IndexError:
                        x=1
                        y+=1
                # found a suitable location for the dude!
                predmap[y] = '%s%s%s' % \
                            (row[:x], symbol, row[x+1:])
            else:
                while True:
                    # picks a random index of a string across a random row
                    randomRow = random.randint(1,len(predmap)-1)
                    randomRowLine = predmap[randomRow]
                    randomIndex = random.randint(1, len(randomRowLine)-1)
                    # make sure it's a free spot
                    if randomRowLine[randomIndex] != ' ':
                        continue
                    else:
                        predmap[randomRow] = '%s%s%s' % \
                            (randomRowLine[:randomIndex], symbol, randomRowLine[randomIndex+1:])
                        break
        return predmap

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
        for dudeSymbol, dudeObj in zip(self.dudesymbols, self._pregenDudes):
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
                if len(dudeObj.everytick)==0:
                    continue
            elif tickNum not in dudeObj.ticks:
                continue
            # return this dude if relevant to the requested tick
            yield dudeObj.name

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
        self.sound=None
        self.isFunction=False

        if self.name:
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
        '''returns events for the given tick number'''
        if tick=='everytick':
            for eventType, event in self.everytick:
                yield self.doEvent(eventType, event)
        else:
            for eventNum, event in zip(self.eventNums, self._events):
                # if this event is for the given tick...
                if eventNum==tick:
                    yield self.doEvent(event[0],event[1])

    def doEvent(self, eventType, event):
        # do events in this module as they're being returned to funplayer
        #=~=~ FIRST STUFF WE ACTUALL
        if eventType in ('set','add','subtract'):
            key, value = event.split('=')
            newvalue = value
            try:
                if type(Predicament.variables[key]) in (int, float):
                    newvalue=giveNumberIfPossible(value)
            except KeyError:
                # nonexisteant variable
                newvalue=giveNumberIfPossible(value)
            if eventType=='set':
                Predicament.variables[key]=newvalue
            elif eventType=='add':
                Predicament.variables[key]+=newvalue
            elif eventType=='subtract':
                Predicament.variables[key]-=newvalue
        elif eventType in ('text', 'action'):
            event = replaceVariables(event)

        # eventTypes we do work for still get passed through
        # in case funplayer wants to do something else with em too
        return eventType, event

def findVariables(text):
    '''
    finds text surrounded by % in a string and returns that text
    '''
    if '%' not in text or '%' not in text[text.index('%')+1:]:
        return text
    start = text.index('%')
    end = text[start+1:].index('%') + start + 1
    return text[start+1:end]
    

def replaceVariables(text):
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
    if text[start+1:end] not in Predicament.variables:
        # replace variable with nothing if it doesn't exist
        return replaceVariables(text[end+1:])
    else:
        return replaceVariables(text[:start] + str(Predicament.variables[text[start+1:end]])
                            + text[end+1:])
                            
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

def doWeirdLines(fp, filename, name, line, readingTick=-1,self=None):
    # returns True if it successfully parses a weird line
    # readingTick defaults to -1 for Predicaments
    # when readingTick is 0 or higher, it's for use by Dudes
    #=~=~=~=~ '/' BLOCK TERMINATORS
    if line.find("/if") == 0:
        if Parser.readingIfLevel > 0:
            Parser.readingIfLevel -= 1
            return True
        raise BadPredicamentError(12, filename, name)
    #=~=~=~=~ IF
    elif line.strip().startswith("if "):
        computeIf(fp, name, line, readingTick)
        return True
    #=~=~=~=~ SET
    elif line.strip().startswith("set "):
        doSet(filename, name, line, readingTick,self)
        return True
    elif line.strip().startswith("add "):
        doMath(filename, name, line, 'add', 'to', readingTick,self)
        return True
    elif line.strip().startswith("subtract "):
        doMath(filename, name, line, 'subtract', 'from', readingTick,self)
        return True
    return False

def doSet(filename, predname, line, readingTick=-1,self=None):
    # readingTick defaults to -1 for Predicaments
    # when readingTick is 0 or higher, it's for use by Dudes
    try:
        key, value = line.split('=')
    except ValueError:
        try:
            key, value = line.split(' to ')
        except ValueError:
            raise BadPredicamentError(31, filename, predname, line)
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
        # setting number variable to a string variable
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
        raise BadPredicamentError(35, filename, name, line,preposition,preposition)
    if type(Predicament.variables[key]) != int:
        raise BadPredicamentError(38, filename, name, line, key, '%s %s' % (operator, preposition))
    # make sure variable exists
    if key not in Predicament.variables:
        raise BadPredicamentError(10, filename, name, line, key)

    # if we're doing this immediately
    if readingTick==-1:
        # make it a number
        try:
            value = int(value)
        except TypeError:
            # it's not a goddamn number
            raise BadPredicamentError(37, filename, name, line, value)
        if operator=='add':
            Predicament.variables[key]+=value
        elif operator=='subtract':
            Predicament.variables[key]-=value
        else:
            raise BadPredicamentError()
    elif readingTick==0:
        #dude object has been passed to us
        self.everytick.append(('%s' % operator,
                               '%s=%s' % (key, value)))
    elif readingTick>0:
        self._events.append(('%s' % operator,
                             '%s=%s' % (key, value)))
        self.eventNums.append(readingTick)


def computeIf(fp, name, line, readingTick=None):
    # here's where I jumped through a flaming hoop
    # to avoid changing ninedotnine's doIf() code :P
    if doIf(fp, name, line, readingTick):
        # if the condition is true, read normally
        Parser.readingIfLevel += 1
    else:
        # if the condition isn't true,
        # discard lines until we reach end if
        skipIf(fp, name)

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
        raise BadPredicamentError(26, fp.name, name, line)
    # remove the 'if ' from the key
    key = findVariables(key[3:].strip())
    value = replaceVariables(value)

    # why is this happening in here? global vars >:O
    Parser.tempIfLevel = Parser.readingIfLevel + 1

    # make sure key exists
    if key not in Predicament.variables.keys():
        if readingTick!=-1:
            # Dudes have to read all the If statements
            # every tick, so this variable might be created
            # in the future for another if statement
            return False
        else:
            # freak the hell out if this is a Predicament
            raise BadPredicamentError(10, fp.name, name, line, key)

    # wtf
    if value.startswith('>') or value.startswith('<'):
        if type(Predicament.variables[key]) not in (int, float):
            # the key isn't a comparable type
            raise BadPredicamentError(24, fp.name, name, line, key)
        try:
            comparee = eval(value[1:])
        except NameError:
            # it's not a comparable value.
                raise BadPredicamentError(25, fp.name, name, line,
                                          key, value[1:].strip())
        if value[1:].strip() in dir():
        #if value[1:].strip() in dir(__name__):
            # uh oh. a consequence of using eval...
            # the pred file can refer to variables in this code
            # this doesn't even catch all of these cases
            # it might, if we hadn't called something else predicaments
            raise BadPredicamentError(96)
        if type(comparee) not in (int, float):
            # the value isn't a comparable type
            raise BadPredicamentError(25, fp.name, name, value,
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
            raise BadPredicamentError(29, fp.name, name, line)
        if type(Predicament.variables[key]) == int:
            try:
                conditionIsTrue = ( Predicament.variables[key] == int(value) )
            except ValueError:
                conditionIsTrue = False
                #raise BadPredicamentError(25, fp.name, name, line, key, value)
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
        raise BadPredicamentError(11, fp.name, name, "'%s'" % followup)
    if followup.startswith("and not"):
        return ( not doIf(fp, name, line) and conditionIsTrue )
    elif followup.startswith("and"):
        return ( doIf(fp, name, line) and conditionIsTrue )
    elif followup.startswith("or not"):
        return ( not doIf(fp, name, line) or conditionIsTrue )
    elif followup.startswith("or"):
        return ( doIf(fp, name, line) or conditionIsTrue )
    raise BadPredicamentError(11, fp.name, name, line)

def skipIf(fp, predname):
    while Parser.readingIfLevel < Parser.tempIfLevel:
        nextline = getNonBlankLine(fp)
        if nextline.startswith("/if"):
            Parser.tempIfLevel -= 1
        elif nextline.startswith("if "):
            Parser.tempIfLevel += 1
        elif nextline.find("/predicament") == 0\
        or nextline.find("/tick") == 0\
        or nextline.find("/dude") == 0:
            raise BadPredicamentError(13, 'idk', predname)

def getNonBlankLine(fp):
    line = ''
    while line == '' or line.startswith("#"):
        line = fp.readline()
        if not line:
            # if eof is reached, that's bad.
            raise BadPredicamentError(17, fp.name)
        line = line.strip()
    return line

def findAllDefinitions(preddir, filetype):
    # populate a dictionary with locations of all known definitions of this filetype
    if not os.path.isdir(preddir):
        raise BadPredicamentError(8, preddir)
    predicaments = {}
    for filename in os.listdir(preddir):
        basename, ext = os.path.splitext(filename)
        if ext != '.%s' % filetype:
            #print("WARNING: skipping %s/%s%s..." % (preddir, basename, ext))
            continue
        pointless = True # whether this boolean is pointless
        lineNo = 0
        with open(os.path.join(preddir, filename), 'r') as fp:
            for line in fp:
                lineNo += 1
                line = line.strip()
                if line.find("predicament =") == 0 and filetype=='pred'\
                or line.find("dude =") == 0 and filetype=='dude':
                    name = line.split('=')[1]
                    # create entry in predicaments dictionary
                    # 'title of predicament' : ('which pred file it is in',
                    #                         lineNo)
                    name = name.strip()
                    predicaments[name] = (filename, lineNo)
    return predicaments

prederrors = (
    '',
    "what the hell? i can't find predicament %s\ndid you modify it while the game was running?", # 1
    "wrong predicament found: %s",
    "what?? %s %s doesn't exist, \nor didn't exist when the game was started! >:(",
    "in %s, %s %s was not ended before another %s started.",
    "reached end of %s\nbefore finding %s\ndid you modify it while the game was running?", # 5
    "in %s, %s has a type of '%s'.\ni don't know what the hell that means.",
    "%s doesn't have an /predicament for %s",
    "data directory %s\nis nonexistent or unreadable. wtf",
    "%s has the type '%s', which is insane.",
    "in %s:\npredicament %s has the following line:\n%s\nbut the variable '%s' doesn't exist\nmaybe you made a typo somewhere", # 10
    "in %s:\n%s has %s after if.\nyou forgot to use a keyword, used an invalid keyword,\nor didn't include a condition after 'or' or 'and'.\nkeywords other than 'then' must precede an if.\nonly use 'then' after the final if condition.",
    "in %s, there is an unexpected '/if' in predicament %s",
    "in %s, reached end of %s before '/if'.\nconditionals must remain within originating predicament.",
    "in %s, %s %s has a '%s' directive.\ni don't know what the hell that means.",
    "%s could not be found while searching for %s\ndid you rename or delete it while the game was running?", # 15
    "", # 16
    "reached end of %s while looking for '/if'.\nthis is literally the end of the world.",
    "in %s, %s has no '=' on this line:\n%s\nmaybe you made a typo?",
    "%s refers to a '%s.wav'. there was an error accessing\nor playing this file. did you mistype the name?",
    "predicament %s tries to set %s to '%s'\nbut %s is supposed to be a number!", # 20
    "predicament %s tries to set '%s' to a value\nbut that variable could not be created!",
    "[THIS SPACE FOR RENT] doesn't exist in %s! >:(\nwhat kind of game are you playing at?",
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
)

MYPATH = os.path.dirname(os.path.realpath(__file__))
PREDDIR = os.path.join(MYPATH, 'pred')
DUDEDIR = PREDDIR
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
