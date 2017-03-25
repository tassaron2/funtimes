#!/usr/bin/env python3
#=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~==~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=#
#
# funplayer.py
# last modified 2017/03/25
# created 2017/03/23
#
#=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~==~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=#
#
# Licence would go here if anyone cared
#
#=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~==~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=#
import funtimes

def init():
    global window
    window = Funwindow()

class Funplayer():
    # does computation of data returned from Funtimes (parser) module
    # uses GTK+ Funwindow object to draw what it computes
    # flexible so a non-gtk window could be used if it has the same interface
    def __init__(self, predname):
        # each instance only plays 1 predicament
        self.pred = funtimes.Predicament(predname)

    def play(self):
        # make some new boxes
        window.clear()
        # knock the boxes over!!

        # make the text area
        for line in self.pred.text:
            window.text.add(line)

        # make the action buttons
        for label, goto in self.pred.actions:
            window.actions.add(label, goto)

        # draw the window!
        window.draw()

    def tick(self):
        # a moment passes within the same Predicament
        pass

#=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~==~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=#
#
# GTK+ Funwindow for Funplayer
#
#=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~==~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=#
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

def play(predname='start'):
    predicament = Funplayer(predname)
    predicament.play()

# based on a batch file therefore needs goto ;)
def goto(*args):
    # the last argument is the new predname
    # anything else is a GTK object
    newpred = args[-1]
    play(newpred)

def main():
    Gtk.main()

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

    def clear(self):
        # empty the window contents
        self.remove(self.body)
        self.body = Body()
        self.add(self.body)

    def draw(self):
        self.show_all()

    #=~=~=~=~=~ PROPERTIES FUNPLAYER USES
    #=~=~ Each should be an object with properties genericizing its actions
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
        self.mapBox = Gtk.Box(); self.textBox = TextBox()
        topBox.pack_start(self.mapBox, False, False, 0)
        topBox.pack_start(self.textBox, False, False, 0)
        # make the low box
        self.arrowButtons = Gtk.Box()
        self.actionButtons = ActionButtons()
        lowBox.pack_start(self.arrowButtons, False, False, 0)
        lowBox.pack_start(self.actionButtons, False, False, 0)

class ActionButtons(Gtk.Box):
    # area of the window where buttons go for actions and arrows
    def add(self, label, gotoPred):
        button = Gtk.Button(label=label)
        button.connect('clicked', goto, gotoPred)
        self.pack_start(button, False, False, 0)

class TextBox(Gtk.Box):
    def __init__(self):
        super().__init__()
        self.set_orientation(Gtk.Orientation.VERTICAL)

    # text is printed here
    def add(self, item):
        self.pack_start(Gtk.Label(item), False, False, 0)

class OKWindow(Gtk.Dialog):
    # a window that returns nothing, just shows a message and goes away
    def __init__(self, text, title='Message'):
        Gtk.Dialog.__init__(self, title=title)
        self.set_border_width(8)
        self.bodyBox = self.get_content_area()
        self.bodyBox.pack_start(Gtk.Label(str(text)), False, False, 0)
        self.add_button(Gtk.STOCK_OK, Gtk.ResponseType.OK)
        self.show_all()

if __name__=='__main__':
    funplayer.init() # create window
    funplayer.play() # play 1st pred so window is not empty
    funplayer.main() # get input (loops forever)
