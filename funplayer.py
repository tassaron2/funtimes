#!/usr/bin/env python3
#=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~==~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=#
#
# funplayer.py
# last modified 2017/03/26
# created 2017/03/23
#
#=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~==~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=#
#
# fundamental objects for computing Funtimes output is at the top
# under the next 'comment flag' is GTK stuff for the window
# but this is designed to be flexible so another window could be used later
#
#=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~==~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=#
#
# Licence would go here if anyone cared
#
#=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~==~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=#
import funtimes

def play(predname='start'):
    global predicaments
    if predname not in predicaments:
        # make a Predicament for this predicament if there is none
        predicaments[predname] = Predicament(predname)
    predicaments[predname].play()

class Predicament:
    # does computation of Predicament objects created by funtimes module
    # flexible so a non-gtk window could be used if it has the same interface
    # e.g. easier to make it work in terminal or on a webpage
    def __init__(self, predname):
        # each instance only plays 1 predicament
        while True:
            self.pred = funtimes.Predicament(predname)
            if not self.pred.goto:
                break
            else:
                predname = self.pred.goto
        self._tick=0

    def play(self):
        # make some new boxes
        window.clear()
        # knock the boxes over!!

        # make the map area
        window.tilemap.create(self.pred.tilemap, self.pred.tileForChar)
        # make the text area
        for line in self.pred.text:
            window.text.add(line)

        # tick to get any extra text or actions
        self.tick()

        # make the arrow buttons
        for label, goto in self.pred.arrows:
            # disabled directions have None as goto
            window.arrows.add(label, goto)
        # make a link back to this predicament ('Do nothing')
        window.arrows.add('Do nothing', self.pred.name)
        # make the action buttons
        for label, goto in self.pred.actions:
            window.actions.add(label, goto)

        # draw the window!
        window.draw()

    def tick(self):
        # our tick tracks time passage in this pred only
        # the window tick should measure total game ticks
        self._tick+=1

        # tick dudes that need to be ticked every tick... tock
        for dudename in self.pred.dudesForTick('everytick'):
            Dude(dudename).tick('everytick')

        # check if any other dudes need to be ticked
        for dudename in self.pred.dudesForTick(self._tick):
            Dude(dudename).tick(self._tick)
        # anyone else has missed the train

        window.tick()

class Dude:
    def __init__(self, dudename):
        self.dude = funtimes.Dude(dudename)

    def tick(self, tick):
        for eventType, event in self.dude.events(tick):
            if eventType=='text':
                window.text.add(event)

#=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~==~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=#
#
# GTK+ Funwindow for Funplayer
#
#=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~==~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=#
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

def main():
    Gtk.main()

def goto(*args):
    # based on a batch file therefore needs goto ;)
    # actually we need this to catch widgets passed from GTK
    # so they don't interfere with my nice pure play() function
    # the last argument is the new predname
    newpred = args[-1]
    play(newpred)

class Funwindow(Gtk.Window):
    def __init__(self):
        # call mom's initializer first :)
        Gtk.Window.__init__(self)
        # decorate the window
        self.set_size_request(400,400)
        self.set_border_width(6)
        # fill it with empty boxes!!
        self.body = Body()
        self.add(self.body)
        self.connect("delete-event", Gtk.main_quit)
        self._tick=0

    def clear(self):
        # empty the window contents
        self.remove(self.body)
        self.body = Body()
        self.add(self.body)

    def tick(self):
        self._tick+=1

    def draw(self):
        self.show_all()

    #=~=~=~=~=~ PROPERTIES FOR THE TOP PART OF THE CODE TO USE
    #=~=~ Each should be an object with properties genericizing its actions
    @property
    def tilemap(self):
        return self.body.mapBox
    @property
    def text(self):
        return self.body.textBox
    @property
    def actions(self):
        return self.body.actionButtons
    @property
    def arrows(self):
        return self.body.arrowButtons

class Body(Gtk.Box):
    # a vertical box to hold the window contents
    def __init__(self):
        Gtk.Box.__init__(self)
        self.set_orientation(Gtk.Orientation.VERTICAL)
        # split the screen into thirds
        topBox = Gtk.Box(); midBox = Gtk.Box(); lowBox = Gtk.Box()
        self.pack_start(topBox, False, False, 0)
        self.pack_start(midBox, False, False, 0)
        self.pack_start(lowBox, False, False, 0)
        # make the top box
        self.mapBox = MapBox(); self.textBox = TextBox()
        topBox.pack_start(self.mapBox, False, False, 0)
        topBox.pack_start(self.textBox, False, False, 0)
        # make the low box
        self.arrowButtons = ActionButtons()
        self.actionButtons = ActionButtons()
        lowBox.pack_start(self.arrowButtons, False, False, 0)
        lowBox.pack_start(self.actionButtons, False, False, 0)

class ActionButtons(Gtk.Box):
    # area of the window where buttons go for actions
    def add(self, label, gotoPred):
        button = Gtk.Button(label=label)
        if gotoPred:
            button.connect('clicked', goto, gotoPred)
        else:
            button.set_sensitive(False)
        self.pack_start(button, False, False, 0)

class TextBox(Gtk.Box):
    def __init__(self):
        super().__init__()
        self.set_orientation(Gtk.Orientation.VERTICAL)
        self.set_border_width(6)

    # text is printed here
    def add(self, item):
        self.pack_start(Gtk.Label(item), False, False, 0)

class MapBox(Gtk.Grid):
    def __init__(self):
        super().__init__()

    # makes a grid of tiles using a list of map rows
    def create(self, tilemap, tileForChar):
        if tilemap:
            for row, line in enumerate(tilemap):
                for col, char in enumerate(line):
                    self.attach(self.tile(tileForChar(char), char), col, row, 1, 1)

    def tile(self, pathtofile, char):
        if pathtofile==char:
            thisTile = Gtk.Label(char)
        else:
            thisTile = Gtk.Image()
            thisTile.set_from_file(pathtofile)
        return thisTile

class OKWindow(Gtk.Dialog):
    # a window that returns nothing, just shows a message and goes away
    def __init__(self, text, title='Message'):
        Gtk.Dialog.__init__(self, title=title)
        self.set_border_width(8)
        self.bodyBox = self.get_content_area()
        self.bodyBox.pack_start(Gtk.Label(str(text)), False, False, 0)
        self.add_button(Gtk.STOCK_OK, Gtk.ResponseType.OK)
        self.show_all()

# GLOBALS
window = Funwindow()
predicaments = {}

if __name__=='__main__':
    # EXAMPLE OF HOW TO USE THIS MODULE IN OTHER SCRIPT
    play() # play 1st pred so window is not empty
    main() # get input (loops forever)
