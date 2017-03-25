#!/usr/bin/env python3
#=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~==~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=#
#
# funtimes.py
# last modified 2017/03/23
# resurrected by tassaron 2017/03/23
# from code by ninedotnine & tassaron 2013/05/24-2013/06/30
# inspired by a batch file game made in 2008
#
#=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~==~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=#
#
# FUNTIMES parser for Predicament files
# has a dictionary of predicament titles within Pred files
# creates Predicament objects playable by funplayer.py
#
#=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~==~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=#
#
# Licence would go here if anyone cared
#
#=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~==~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=#
import os
import random

class BadPredicamentError(Exception):
    def __init__(self, code=0, *args):
        print("predicament error code:", code)
        if code != 0 and code < len(prederrors):
            print(prederrors[code] % args)
        print("i can't work under these conditions. i quit.\n")
        quit()

class Predicament:
    """
    when creating a Predicament, pass in a string holding the name.
    the constructor will try to find this pred's data in the PREDDIR
    by checking the predicaments dictionary.
    to play this predicament, use play() in player.py
    """

    # pointless class variable: number of generated Predicaments
    numPredicaments = 0
    # dictionary of pred variables
    variables = { 'progress' : 0,
                  'girlname' : ''
                }

    def __init__(self, name):
        # gotta have more comments than code
        Predicament.numPredicaments += 1

        #=~=~=~ GUARANTEED ATTRIBUTES
        self.name = name
        # messages displayed in the description box
        self._text = []
        # inputtypes: normal, textinput
        self.inputtype = 'normal'
        #=~=~ Movement
        self.actionLabel = []
        self.actionGoto = []
        # arrow label and goto lists use this sequence:
        arrowListSequence = ('up', 'down', 'left', 'right')
        self.arrowLabel = []
        self.arrowGoto = []

        #=~=~=~ OPTIONAL ATTRIBUTES
        # parent which this Predicament inherits attributes from
        self.parent = None
        # variable outputed by 'textinput' inputtype
        self.result = None
        # sound played at Predicament creation
        self.sound = None
        # list or string variable that will output to 'funtimes.out'
        self.write = None
        # MAP DATA
        # name of file containing tilemap
        self.predmap = None
        # name displayed over tilemap
        self.mapname = None


        #=~=~=~ TRY TO OPEN THE PRED FILE CONTAINING OUR PREDICAMENT
        try:
            filename, lineNo = predicaments[self.name]
            open(os.path.join(PREDDIR, filename), 'r')
        except KeyError:
            # if the predicament isn't in our master dictionary...
            raise BadPredicamentError(3, self.name)
        except:
            # if the file can't be opened...
            raise BadPredicamentError(15, filename, self.name)


        busy = False # whether we are currently reading a predicament
        with open(os.path.join(PREDDIR, filename), 'r') as fp:
            # basically all of this is just to get to the right line and test
            for line in fp:
                # count down to the correct line
                if lineNo > 1:
                    lineNo -= 1
                    continue
                line = line.strip()
                # we know this is the right line
                # but don't trust the dictionary & check anyway!
                if line.find('predicament =') != 0:
                    raise BadPredicamentError(1, self.name)
                # if it's the wrong predicament, freak the hell out
                elif self.name != line.split('=')[1].strip():
                    raise BadPredicamentError(2, self.name)
                busy = True
                break
            if not busy:
                # we should be busy reading a predicament by this point...
                raise BadPredicamentError(5, filename, self.name)

            # finally, we start actually assigning the data
            global readingIfLevel, tempIfLevel
            readingIfLevel = 0
            tempIfLevel = 0
            # line should be true (it should still be the new pred line)
            while line:
                line = getNonBlankLine(fp)
                #=~  FIRST DO STUFF WITHOUT = IN IT
                #=~=~=~=~ '/' BLOCK TERMINATORS
                if line.find("/predicament") == 0:
                    busy = False
                    break
                elif line.find("/if") == 0:
                    if readingIfLevel > 0:
                        readingIfLevel -= 1
                        continue
                    raise BadPredicamentError(12, filename, self.name)
                #=~=~=~=~ IF
                elif line.strip().startswith("if "):
                    if doIf(fp, self.name, line):
                        # if the condition is true, read normally
                        readingIfLevel += 1
                        continue
                    # if the condition isn't true,
                    # discard lines until we reach end if
                    while readingIfLevel < tempIfLevel:
                        nextline = getNonBlankLine(fp)
                        if nextline.startswith("/if"):
                            tempIfLevel -= 1
                        elif nextline.startswith("if "):
                            tempIfLevel += 1
                        elif nextline.find("/predicament") == 0:
                            raise BadPredicamentError(13, self.name)
                    continue
                #=~=~=~=~ SET
                # TODO: needs much cleanup to handle strings/ints/bools more logically
                elif line.strip().startswith("set "):
                    try:
                        key, value = line.split('to')
                    except ValueError:
                        try:
                            key, value = line.split('=')
                        except ValueError:
                            raise BadPredicamentError(31, filename, self.name,
                                                      line)
                    # strip out the 'set ' part
                    key = key[4:].strip()
                    value = value.strip()
                    # store it in the Predicament class dictionary
                    try:
                        if value == 'random':
                            Predicament.variables[key.strip()] = random.randint(1,100)
                            continue
                        elif type(Predicament.variables[key]) in (int, float):
                            Predicament.variables[key.strip()] = int(value)
                            continue
                        else:
                            Predicament.variables[key.strip()] = value
                            continue
                    except KeyError:
                        # nonexistant variable
                        # TODO: create nonexistent variables?
                        raise BadPredicamentError(21, self.name, key.strip())
                elif line.strip().startswith("add "):
                    try:
                        # variable assignment literally backwards, because that's more fun
                        value, key = line[4:].split('to')
                        value = value.strip()
                        key = key.strip()
                    except ValueError:
                        raise BadPredicamentError(35, filename,
                                                  self.name, line)
                    # make sure variable exists
                    if key not in Predicament.variables.keys():
                        raise BadPredicamentError(10, filename, self.name,
                                                  line, key, 'profile')
                    # make sure it's a number
                    try:
                        value = int(value)
                    except ValueError:
                        raise BadPredicamentError(37, filename, self.name,
                                                  line, value)
                    if type(Predicament.variables[key]) == int:
                        Predicament.variables[key] += value
                    else:
                        raise BadPredicamentError(38, filename, self.name,
                                                  line, key, 'add to')
                    continue
                elif line.strip().startswith("subtract "):
                    try:
                        # also literally backwards, because that's more fun
                        value, key = line[9:].split('from')
                        value = value.strip()
                        key = key.strip()
                    except ValueError:
                        raise BadPredicamentError(36, filename, self.name,
                                                  line)
                    if key not in Predicament.variables.keys():
                        raise BadPredicamentError(10, filename, self.name,
                                                  line, key, 'profile')
                    if type(value) != int:
                        raise BadPredicamentError(37, filename, self.name,
                                                      line, value)
                    if type(Predicament.variables[key]) == int:
                        Predicament.variables[key] -= value
                    else:
                        raise BadPredicamentError(38, filename, self.name,
                                                  line, key, 'subtract from')
                    continue

                #=~=~=~=~ NORMAL STUFF THAT USES =
                try:
                    key, value = line.split('=')
                except ValueError:
                    raise BadPredicamentError(18, filename, self.name, line)
                key = key.rstrip().lower()
                if key == 'predicament':
                    # we're in a new predicament without closing the last one.
                    # the pred file must be invalid.
                    raise BadPredicamentError(4, filename, self.name)
                elif key == 'text':
                    # remove only the first space if any
                    if value and value[0] == ' ':
                        value = value[1:]
                    # add each line of text onto the prev line of text
                    self._text.append(value)
                    continue
                elif key == 'parent':
                    self.parent = value.strip()
                    continue
                elif key == 'action':
                    try:
                        action, goto = value.split('->')
                    except ValueError:
                        raise BadPredicamentError(23, self.name, line)
                    self.actionLabel.append(action.strip())
                    self.actionGoto.append(goto.strip())
                    continue
                elif key == 'sound':
                    self.sound.append(value.strip())
                    continue
                elif key == 'type':
                    if value.strip() not in ('normal', 'inputtext'):
                        raise BadPredicamentError(6, filename, self.name,
                                                  value.strip())
                    self.inputtype = value.strip()
                    continue
                elif key == 'result':
                    self.result = value.strip()
                    continue
                elif key == 'write':
                    self.write = value.strip()
                    continue
                elif key == 'map':
                    self.predmap = value.strip()
                    continue
                elif key == 'name':
                    self.mapname = value.strip()
                    continue
                elif key in ('up', 'down', 'left', 'right'):
                    try:
                        label, goto = value.split('->')
                    except ValueError:
                        raise BadPredicamentError(23, self.name, line)
                    for i, d in enumerate(arrowListSequence):
                        if key == d:
                            self.arrowLabel[i] = [label.strip()]
                            self.arrowGoto[i] = [goto.strip()]
                            continue
                else:
                    raise BadPredicamentError(14, filename, self.name,
                                              key.strip())

        if readingIfLevel:
            raise BadPredicamentError(13, filename, self.name)
        elif busy:
            # should always hit error 4 before this, so it may be redundant
            raise BadPredicamentError(7, filename, self.name)

    # this isn't used anywhere, but handy for debugging
    def __str__(self):
        return '< Predicament %s: %s >' % (self.name, self._text)

    @property
    def actions(self):
        # 2017/03/25 using properties to stop other modules breaking when this changes
        return [(label, goto) for label, goto in zip(self.actionLabel, self.actionGoto)]

    @property
    def arrows(self):
        return [(label, goto) for label, goto in zip(self.arrowLabel, self.arrowGoto)]

    @property
    def text(self):
        return [replaceVariables(line) for line in self._text]

    """
    def drawMap(self):
        with open(mapdir + self.predmap + '.map',
                  'r', encoding='utf-8') as currentMap:
            # find out the longest line so we can centre according to it
            longestLine = 0
            busy = True
            for line in currentMap:
                # don't count legend lines, which aren't relevant to map size
                if busy and line.strip()=="start legend":
                    busy = False
                if line.strip()=="end legend":
                    busy = True
                if busy:
                    if len(line) > longestLine:
                        longestLine = len(line)
        with open(mapdir + self.predmap + '.map',
                  'r', encoding='utf-8') as currentMap:
            # print the map's name over the map if it exists
            if self.mapname:
                self.mapname = replaceVariables(self.mapname).upper()
                # centre it over the map
                sys.stdout.write \
                (' ' * int((lineLength - len(self.mapname) - 1) / 2))
                print(self.mapname)
            busy = False
            for line in currentMap:
                # only read the tilemap
                if not busy and line.strip()=="start tilemap":
                    busy = True
                    continue
                elif line.strip()=="end tilemap":
                    busy = False
                    continue
                if busy:
                    sys.stdout.write(' ' * int((lineLength - longestLine) / 2))
                    try:
                        print(line, end='')
                    except UnicodeEncodeError:
                        if not os.path.isfile(mapdir +self.predmap + '-ascii.map'):
                            createAsciiMap(self.predmap)
                        line = createAsciiLine(line)
                        print(line, end='')
            print()

def createAsciiMap(predmap):
    # generates an ascii version of the map file, so it doesn't need to
    # do a million replace()s every time we come back to the same map
    try:
        with open(mapdir + predmap + '.map',
              'r', encoding='utf-8') as unicodeMap:
            with open(mapdir + predmap + '-ascii.map',
                      'w', encoding='utf-8') as asciiMap:
                for line in unicodeMap:
                    print(createAsciiLine(line), file=asciiMap, end='')
    except IOError:
        print("\nproblem creating or accessing:\n" + mapdir + predmap +
              "-ascii.map\nthis is a p. big deal, tbh")
        anykey()
        quit()

def createAsciiLine(line):
    unicodeWalls = ['\u2550', '\u2551', '\u2554',
                    '\u2557', '\u255A', '\u255D'] # '#'
    unicodeVertLines = ['\u2502'] # '|'
    unicodeHoriLines = ['\u2500'] # '_'
    unicodeDashes = ['\u254E', '\u254C'] # '.'
    unicodeCorners = ['\u250C', '\u2518', '\u2514', '\u2510'] # removed
    for character in unicodeWalls:
        line = line.replace(character, '#')
    for character in unicodeVertLines:
        line = line.replace(character, '|')
    for character in unicodeHoriLines:
        line = line.replace(character, '_')
    for character in unicodeDashes:
        line = line.replace(character, '.')
    for character in unicodeCorners:
        line = line.replace(character, ' ')
    return line
"""

def doIf(fp, name, line):
    # figures out whether to read conditional stuff in pred definitions
    # first, parse the line itself to get key and value

    global tempIfLevel, readingIfLevel

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
    key = key[3:].strip()
    value = value.strip()

    # why is this happening in here? global vars >:O
    tempIfLevel = readingIfLevel + 1

    # make sure key exists
    if key not in Predicament.variables.keys():
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
            # maybe it's a variable!!
            if ( value[1:].strip() in Predicament.variables and
                type(profile[value[1:].strip()]) in (int, float) ):
                # aha! we're probably comparing profile stuff
                comparee = Predicament.variables[value[1:].strip()]
            else:
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
                if (value in Predicament.variables and
                    type(Predicament.variables[value]) in (int, float)):
                        conditionIsTrue = \
                                    ( Predicament.variables[key] == int(Predicament.variables[value]) )
                else:
                    raise BadPredicamentError(25, fp.name, name,
                                              line, key, value)
        else:
            # try to compare variable against another variable
            if value in Predicament.variables:
                conditionIsTrue = ( Predicament.variables[key] == Predicament.variables[value] )
            else:
                # otherwise compare it normally
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

def getNonBlankLine(fp):
    line = ''
    while line == '' or line.startswith("#"):
        line = fp.readline()
        if not line:
            # if eof is reached, that's bad.
            raise BadPredicamentError(17, fp.name)
        line = line.strip()
    return line

# method what replaces variables' plaintext representations
# with the actual variable when getting text from predfile
def replaceVariables(text):
    if '%' not in text or '%' not in text[text.index('%')+1:]:
        # '%' doesn't appear or doesn't appear again after appearing
        return text
    start = text.index('%')
    end = text[start+1:].index('%') + start + 1
    if text[start+1:end] not in Predicament.variables:
        print("can't find %s in Predicament variables" % text[start+1:end])
        quit()
    return replaceVariables(text[:start] + str(Predicament.variables[text[start+1:end]])
                            + text[end+1:])

def findPredicaments(preddir):
    # populate predicaments dictionary with locations of all known predicaments
    if not os.path.isdir(preddir):
        raise BadPredicamentError(8)
    predicaments = {}
    for filename in os.listdir(preddir):
        basename, ext = os.path.splitext(filename)
        if ext != '.pred':
            #print("WARNING: skipping %s/%s%s..." % (preddir, basename, ext))
            continue
        pointless = True # whether this boolean is pointless
        lineNo = 0
        with open(os.path.join(preddir, filename), 'r') as fp:
            for line in fp:
                lineNo += 1
                line = line.strip()
                if line.find("predicament =") == 0:
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
    "what?? predicament %s doesn't exist, \nor didn't exist when the game was started! >:(",
    "in %s, %s was not ended correctly.",
    "reached the end of %s before finding %s\ndid you modify it while the game was running?", # 5
    "in %s, %s has a type of '%s'.\ni don't know what the hell that means.",
    "%s doesn't have an end of predicament for %s",
    "no data directory",
    "%s has the type '%s', which is insane.",
    "in %s:\npredicament %s has the following line:\n%s\n'%s' is not a valid entry in %s.", # 10
    "in %s:\n%s has %s after if.\nyou forgot to use a keyword, used an invalid keyword,\nor didn't include a condition after 'or' or 'and'.\nkeywords other than 'then' must precede an if.\nonly use 'then' after the final if condition.",
    "in %s, there is an unexpected 'end if' in predicament %s",
    "reached end of predicament %s before 'end if'.\nconditionals must remain within originating predicament.",
    "in %s, %s has a '%s' directive.\ni don't know what the hell that means.",
    "%s could not be found while searching for %s\ndid you rename or delete it while the game was running?", # 15
    "in %s, %s has no type.",
    "reached end of %s while looking for 'end if'.\nthis is literally the end of the world.",
    "in %s, %s has no '=' on this line:\n%s\nmaybe you made a typo?",
    "%s refers to a '%s.wav'. there was an error accessing\nor playing this file. did you mistype the name?",
    "predicament %s tries to set %s to '%s'\nbut %s is supposed to be a number!", # 20
    "predicament %s tries to set '%s' to a value\nbut that variable does not exist!",
    "predicament %s refers to %s.map,\nwhich doesn't exist in %s! >:(\nwhat kind of game are you playing at?",
    "a movement or action directive in predicament %s contains this line:\n %s\nwhich does not have a -> in it.\nmovement and action must declare the label, then ->,\nthen the name of the predicament which the labelled movement\nor action leads to. for example:\n Leave the house. -> outside",
    "in %s\npredicament %s has the following condition:\n%s\nbut %s is not of a comparable type\nif it was intended to contain a word, it will always contain a word\nsetting it to a number will not allow you to perform comparisons",
    "in %s\npredicament %s has the following condition:\n%s\nthis is trying to perform a comparison on %s,\nbut %s is neither a number nor a variable containing a number.\nyou are comparing apples and oranges, and i'm allergic.",
    # ^-- 25
    "in %s:\npredicament %s has this line:\n%s\nan if statement must contain 'is' or 'has'.",
    "in %s:\npredicament %s has this line:\n%s\nchecking the status of a quest can only be done with keywords:\ninitial, known, started, done, failed\nor 'progress' followed by a number",
    "in %s:\npredicament %s has this line:\n%s\nit appears to refer to a dictionary called '%s'\nbut i don't know what that is... :/",
    "in %s:\npredicament %s has this line:\n%s\nnegating a comparison is pointless. just use the opposite.",
    "in %s, predicament %s has this line:\n%s\nit appears to refer to a dictionary called %s\nbut that's not a valid dictionary.", #30
    "in %s, predicament %s has this line:\n%s\nsetting must be done using 'to' or '='.",
    "in %s, predicament %s has this line:\n%s\n%s is not sensible.\nquest entries must be set to keywords:\ninitial, known, started, done, failed\nor 'progress' followed by a number",
    "in %s, predicament %s\ntries to %s %s from player.\nthis item does not exist.",
    "in %s, predicament %s\ntries to take a pack of ketchup from player.\nthe player is saving that for a rainy day.\nthey refuse to let go of it.",
    "in %s, predicament %s\ndoes not have a 'to' on this line:\n%s\nyou must add TO a variable, using the word TO.", #35
    "in %s, predicament %s\ndoes not have a 'from' on this line:\n%s\nyou must subtract FROM a variable, using the word FROM.",
    "in %s, predicament %s\nhas this invalid line:\n%s\n'%s' is not an integer. you must use a whole number\nor a profile entry that contains a whole number.",
    "in %s, predicament %s\nhas this invalid line:\n%s\n'%s' does not refer to a number. you can't %s it.",
)

PREDDIR = '%s/pred' % os.path.dirname(os.path.realpath(__file__))
predicaments = findPredicaments(PREDDIR)

if __name__ == '__main__':
    print("content of", PREDDIR, ": ", os.listdir(PREDDIR))
    print()
    print("number of predicaments:", len(predicaments))
    for key in predicaments:
        print(key + ":", predicaments[key])
