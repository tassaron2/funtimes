#!/usr/bin/env python3
#=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~==~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=#
#
# funquests.py
# last modified 2017/05/06
# created by tassaron 2017/04/05
#
#=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~==~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=#
#
# Generates a pred file containing random connected rooms.
#
#=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~==~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=#
import os
import argparse
import random

PREDDIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'pred','funquests')
NamesInUse = []

class Predicament:
    def __init__(self, predname, backArrow, keepGoing):
        self.predname = predname
        self.backGoto=''
        self.backDirection=''

        def directions():
            '''choose 1-4 unique directions'''
            arrows = ['up', 'down', 'left', 'right']
            if backArrow[1]:
                arrows.remove(reverseDirection(backArrow[1]))
            choices = [random.choice(arrows)]
            gotos = []
            for i in range(3):
                nextchoice = random.choice(arrows)
                if nextchoice not in choices:
                    choices.append(nextchoice)
                    gotos.append(unique(predname))

            return choices, gotos

        if keepGoing:
            self.directions, self.directionGoto = directions()
        else:
            self.directions = []
            self.directionGoto = []
        if backArrow[0] is not None:
            self.backGoto = backArrow[0]
            self.backDirection = reverseDirection(backArrow[1])

class QuestMap:
    def __init__(self, predname):
        # a dictionary of created predicaments for createPredFile()
        self.predicaments = {}
        # preds that still neeed to be created before this map can be done
        # { 'predname' : (pred that points to it, direction that pred is) }
        self.predsToCreate = {}
        # now create the first pred: an entrypoint
        self.newPredicament('%sentry' % predname,\
                            backArrow=(None, None), keepGoing=True)

        # now generate preds until we reach totalPreds!
        totalPreds = random.randint(8, 15)
        generatedPreds = 1
        while True:
            iterator = dict(self.predsToCreate)
            for predname, backArrow in iterator.items():
                self.predsToCreate.pop(predname)
                generatedPreds+=1
                keepGoing = (generatedPreds < totalPreds)
                self.newPredicament(predname, backArrow, keepGoing)
            if not iterator:
                break


    def newPredicament(self, predname, backArrow, keepGoing):
        print('making %s' % predname)
        if predname in self.predicaments:
            print('WTF'); quit()
        # make a new Predicament object
        newpred = Predicament(predname, backArrow,keepGoing)
        self.predicaments[predname] = newpred
        # add its directions to the predsToCreate
        backDirection = reverseDirection(backArrow[1])
        for goto, direction in zip(newpred.directionGoto, newpred.directions):
            if direction != backDirection:
                self.predsToCreate[goto] = (predname, direction)

def reverseDirection(string):
    if string is not None:
        if string=='up':
            return 'down'
        elif string=='down':
            return 'up'
        elif string=='left':
            return 'right'
        elif string=='right':
            return 'left'
        else:
            print('Not a direction')

def unique(string):
    global NamesInUse
    if string[-5:] == 'entry':
        string = string[:-5]
    else:
        string = string[:-3]
    while True:
        rndNum = random.randint(100,999)
        predname = '%s%s' % (string, rndNum)
        if predname not in NamesInUse:
            NamesInUse.append(predname)
            break
    return predname

def write(text):
    fp.write('%s\n' % text)

def writePredicament(predobj):
    leftExpr = '    if Y is 1,~ ->'
    noLeftExpr = '    if Y is not 1,~ ->'
    rightExpr = '    if Y is 7,~ ->'
    noRightExpr = '    if Y is not 7,~ ->'
    upExpr = '    if Y is ~,1 ->'
    noUpExpr = '    if Y is not ~,1 ->'
    downExpr = '    if Y is ~,7 ->'
    noDownExpr = '    if Y is not ~,7 ->'

    def writeExpression(direction, goto):
        if goto:
            if direction == 'left':
                write(leftExpr)
            elif direction == 'right':
                write(rightExpr)
            elif direction == 'up':
                write(upExpr)
            elif direction == 'down':
                write(downExpr)
            write('        %s = %s' % (direction, goto))
            write('    /if')
            blockStarter = '        %s =' % direction
        else:
            blockStarter = '        %s = disable map' % direction
        if direction == 'left':
            write(noLeftExpr)
            write(blockStarter)
            write('            Y = -1,~')
        elif direction == 'right':
            write(noRightExpr)
            write('        %s =' % direction)
            write('            Y = +1,~')
        elif direction == 'up':
            write(noUpExpr)
            write('        %s =' % direction)
            write('            Y = ~,-1')
        elif direction == 'down':
            write(noDownExpr)
            write('        %s =' % direction)
            write('            Y = ~,+1')
        write('        /%s' % direction)
        write('    /if')


    print('writing %s to file' % predobj.predname)
    write('')
    write('predicament = %s' % predobj.predname)
    write('    map = auto')
    write('    dude = Y -> you')
    if predobj.backDirection == 'left':
        write('    Y = 1,3')
    elif predobj.backDirection == 'right':
        write('    Y = 7,3')
    elif predobj.backDirection == 'up':
        write('    Y = 3,1')
    elif predobj.backDirection == 'down':
        write('    Y = 3,7')
    else:
        write('    Y = 3,3')

    write('    text = %predname%')
    write('    function = supereasyProbe')

    noMapDoors = [ 'left', 'right', 'up', 'down']
    if predobj.backDirection:
        noMapDoors.remove(predobj.backDirection)
        writeExpression(predobj.backDirection, predobj.backGoto)

    for direction, goto in zip(predobj.directions, predobj.directionGoto):
        noMapDoors.remove(direction)
        writeExpression(direction, goto)

    for direction in noMapDoors:
        writeExpression(direction, None)
    write('/predicament')

def createPredFile(predname):
    global fp
    with open(os.path.join(PREDDIR, '%s.pred' % predname), 'w') as fp:
        write('# generated by funquests.py')
        write('version = 1')
        questMap = QuestMap(predname)
        for predobj in questMap.predicaments.values():
            writePredicament(predobj)
        print('done :D')

def main():
    # first parse command line arguments
    parser = argparse.ArgumentParser(description='creates a pred file containing a funtimes quest')
    parser.add_argument('predname', help='name of pred file')
    arg = vars(parser.parse_args()) # return arguments as a dictionary
    createPredFile(arg['predname'])

if __name__ == '__main__':
    main()
