#!/usr/bin/env python3
#=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~==~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=#
#
# funplayer.py
# last modified 2017/04/02
# created 2017/03/23
#
#=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~==~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=#
#
# fundamental objects for computing Funtimes output is at the top
# under the next 'comment flag' is GTK stuff for the window
# but this is designed to be flexible so another window could be used later
#
# TODO: Make window properly resizeable, by keeping mapwindow/controls static
#       and scaling the textwindow to fill more space
# TODO: ctrl+up enlarges text
#
#=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~==~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=#
#
# Licence would go here if anyone cared
#
#=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~==~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=#
import funtimes
from textwrap import wrap
from html import escape

def play(predname='start'):
    global predicaments
    if predname not in predicaments:
        # make a Predicament for this predicament if there is none
        predicaments[predname] = Predicament(predname)
        thispred = predicaments[predname]
    else:
        # make a new Predicament but carry over some attributes
        thispred = Predicament(predname, predicaments[predname].pred)
    thispred.play()

def set_mode(value='MAP'):
    if value not in ['MENU','MAP']:
        print("Unknown mode %s" % value)
    else:
        Funwindow.mode = value
        Funwindow.modeVars = Funwindow.modeVarDicts[value]

def set_variables(dictionary):
    for key, value in dictionary.items():
        funtimes.Predicament.variables[key] = value

def delete_memory():
    global predicaments
    predicaments = {}

class Predicament:
    # does computation of Predicament objects created by funtimes module
    # flexible so a non-gtk window could be used if it has the same interface
    # e.g. easier to make it work in terminal or on a webpage
    
    def __init__(self, predname, oldpred=None):
        # each instance only plays 1 predicament
        while True:
            self.name = predname
            # make a wholly new predicament
            self.pred = funtimes.Predicament(predname)
            if not self.pred.goto:
                break
            else:
                predname = self.pred.goto
                if predname in predicaments:
                    oldpred=predicaments[predname]

        if predname not in predicaments:
            oldpred=None

        if oldpred:
            # take tick-number from the former predicament
            self._tick = predicaments[predname]._tick
            self.hasFakeDudes = predicaments[predname].hasFakeDudes
        else:
            self._tick=0

    def play(self):
        # make some new boxes
        window.clear()
        # knock the boxes over!!

        # make the map area
        window.tilemap.create(self.pred.tilemap, self.pred.tileForChar)
        # make the text area
        if self.pred.mapname:
            window.name.newName(self.pred.mapname)
        else:
            window.name.newName(Funwindow.modeVars['emptyMapName'])
        for line in self.pred.text:
            window.text.add(line)

        # tick to get any extra text or actions
        self.tick()

        if 'quit' in funtimes.predicaments\
        and 'quit' in Funwindow.modeVars:
            window.arrows.add(Funwindow.modeVars['quit'], 'quit')
        if Funwindow.modeVars['arrowsEnabled']:
            # make the arrow buttons
            for label, goto in self.pred.arrows:
                # disabled directions have None as goto
                window.arrows.add(label, goto)
        # make a link back to this predicament ('Wait')
        if 'wait' in Funwindow.modeVars:
            window.arrows.add(Funwindow.modeVars['wait'], self.pred.name)
        # make the action buttons
        for label, goto in self.pred.actions:
            window.actions.add(label, goto)

        # copy this newly modified pred into the global dict
        predicaments[self.name] = self
        # draw the window!
        window.draw()

    def tryToTick(self,dudename,tick):
        if dudename:
            # tick the dude! ...off
            Dude(dudename, self.name).tick(tick)
        else:
            # it's an imposter :|
            self.hasFakeDudes=True
            
    def tick(self):
        # our tick tracks time passage in this pred only
        # the window tick should measure total game ticks
        self._tick+=1

        # if we must tick the fake dudes, let's get it over with
        if self._tick==1 or self.hasFakeDudes==True:
            for dudeObj in self.pred.fakeDudes:
                for eventType, event in dudeObj.events(self._tick):
                    Dude.doEvent(eventType, event, None)
            # reset to false
            self.hasFakeDudes=False

        # tick dudes that need to be ticked every tick... tock
        for dudename in self.pred.dudesForTick('everytick'):
            self.tryToTick(dudename, 'everytick')

        # check if any other dudes need to be ticked
        for dudename in self.pred.dudesForTick(self._tick):
            self.tryToTick(dudename, self._tick)
        # anyone else has missed the train

        # close window if requested
        if self.pred.inputtype.startswith('exit'):
            getInput.closewin(self.pred.inputtype[4:])
        elif self.pred.inputtype=='quit':
            getInput.kill()
        # otherwise tick the window itself
        window.tick()

class Dude:
    def __init__(self, dudename, predname):
        self.dude = funtimes.Dude(dudename)
        self.predname = predname

    def tick(self, tick):
        for eventType, event in self.dude.events(tick):
            Dude.doEvent(eventType, event, self.dude.nick)

    def doEvent(eventType, event, nick):
        if eventType=='text':
            if nick:
                window.text.add(event, nick)
            else:
                window.text.add(event)
        elif eventType=='action':
            label, goto = event.split('=')
            window.actions.addToEnd(label.strip(), goto.strip())
        elif eventType=='quit':
            getInput.kill()
        elif eventType=='exit':
            getInput.closewin(event)
            

#=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~==~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=#
#
# GTK+ Funwindow for Funplayer
#
#=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~==~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=#
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GdkPixbuf

class getInput:
    exitcode = 9
    
    @staticmethod
    def kill(*args):
        getInput.exitcode = 9
        getInput.main_quit()
        
    @staticmethod
    def closewin(*args):
        getInput.exitcode = args[-1]
        getInput.main_quit()
        
    @staticmethod
    def main_quit():
        Gtk.main_quit()
        
def main():
    #gtkStyle()    
    Gtk.main()
    return getInput.exitcode

def goto(*args):
    '''based on a batch file therefore needs goto ;)
    actually we need this to catch widgets passed from GTK
    so they don't interfere with my nice pure play() function
    the last argument is the new predname'''
    newpred = args[-1]
    play(newpred)

def gtkStyle():
        css = """
GtkWindow {
    color: %s;
    background-color: %s;
}
GtkButton GtkLabel {
    color: %s;
}
GtkButton:active GtkLabel {
    color: %s;
}
GtkButton:active:hover GtkLabel {
    color: %s;
}
GtkButton {
    border-width: 0 0 0 0;
    border-image: none;
    border-radius: 0;
    background-image:none;
    background-color: %s;
}
GtkButton:active {
    border-width: 0 0 0 0;
    border-image: none;
    border-radius: 0;
    background-image:none;
    background-color: %s;
}
        """ % (Funwindow.color['text'],\
               Funwindow.color['bg'],\
               Funwindow.color['inactive'],\
               Funwindow.color['lighttext'],\
               Funwindow.color['lighttext'],\
               Funwindow.color['bg'],\
               Funwindow.color['lightbg'])
        css = str.encode(css)
        style_provider = Gtk.CssProvider()
        style_provider.load_from_data(css)

        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            style_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

class Funwindow(Gtk.Window):
    mode = 'MAP'
    modeVarDicts = {
        'MAP'  : { 'quit'          : 'Disconnect',
                   'wait'          : 'Wait',
                   'arrowsEnabled' : True,
                   'emptyMapName'  : '                ',
                   'textPrefix'    : '• ',
                 },
        'MENU' : { 'quit'          : 'Quit',
                   'arrowsEnabled' : False,
                   'emptyMapName'  : '',
                   'textPrefix'    : '    ',
                 },
    }
    modeVars = modeVarDicts['MAP']

    colorChoice = {
        'generic' : {
                'inactive' : '#696969',
                'lighttext' : '#151515',
                },
        'idk' : {
                'inactive' : '#b58900',
                'text' : '#8C9440',
                'lighttext' : '#B5BD68',
                'bg' : '#1D1F21',
                'lightbg' : '#373B41',
                }
    }
    color = colorChoice['generic']
    height = 320
    width = 648
    
    def __init__(self):
        # call mom's initializer first :)
        super().__init__()
        # decorate the window
        self.set_size_request(Funwindow.width, Funwindow.height)
        self.set_border_width(2)
        # fill it with empty boxes!!
        self.body = Body()
        self.add(self.body)
        self.connect("delete-event", getInput.closewin, 8)
        self._tick=0

    def clear(self):
        # empty the window contents
        self.body.clear()

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
    def name(self):
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
        # THINGS THAT ARE CREATED JUST ONCE
        # split the screen into thirds
        self.topBox = Gtk.Box(); self.lowBox = Gtk.Box()#; self.midBox = Gtk.Box()
        self.pack_start(self.topBox, False, False, 0)
        #self.pack_start(self.midBox, False, False, 0)
        self.pack_start(self.lowBox, False, False, 0)
        # make the top box
        self.makeTopBox()
        # make a scrolling window for the text
        self.textBox = TextBox()
        textWindow = Gtk.ScrolledWindow()
        # connect window-size-change event to function which scrolls down
        textWindow.connect('size-allocate', self.scrollTextBox)
        textWindow.add_with_viewport(self.textBox)
        textWindow.set_size_request(Funwindow.width-256, Funwindow.height-64)
        self.topBox.pack_start(textWindow, False, False, 0)
        # make the low box
        self.makeLowBox()

    def scrollTextBox(self, widget, event):
        '''keeps scrolledWindow scrolled to the bottom'''
        scroll = widget.get_vadjustment()
        scroll.set_value(scroll.get_upper() - scroll.get_page_size())

    def clear(self):
        for box in self.boxes():
            if box != 'textBox':
                # TODO: make less crap
                if box=='mapBox':
                    self.topBox.remove(eval('self.%s' % box))
                else:
                    self.lowBox.remove(eval('self.%s' % box))
            elif box=='textBox':
                colour = getColor('inactive')
                for label in self.textBox.newRows:
                    label.set_markup("<span %s>%s</span>"\
                        % (colour, label.get_text()))
        self.makeTopBox()
        self.makeLowBox()

    def boxes(self):
        # returns only the lowest-level boxes
        highLevelBoxes = ['topBox','midBox','lowBox']
        return (child for child in self.__dict__ if child not in highLevelBoxes)

    def makeTopBox(self):
        if Funwindow.mode=='MAP':
            self.mapBox = MapGrid()
        elif Funwindow.mode=='MENU':
            self.mapBox = MapBox()
        self.topBox.pack_start(self.mapBox, False, False, 0)

    def makeLowBox(self):
        self.arrowButtons = ActionButtons()
        self.actionButtons = ActionButtons()
        self.lowBox.pack_start(self.arrowButtons, False, False, 0)
        self.lowBox.pack_start(self.actionButtons, False, False, 0)
        

class ActionButtons(Gtk.Box):
    # area of the window where buttons go for actions
    def __init__(self):
        super().__init__()
        self.set_border_width(4)
        self.set_spacing(4)
    
    def makeButton(self, label, gotoPred):
        button = Gtk.Button()
        buttonlabel = Gtk.Label()
        if '<' in label or '>' in label:
            label = escape(label)
        buttonlabel.set_markup("<b>%s</b>" % label)
        button.add(buttonlabel)
        button.set_size_request(64, 64)
        if gotoPred:
            button.connect('clicked', goto, gotoPred)
        else:
            button.set_sensitive(False)
        return button
    
    def add(self, label, gotoPred):
        button = self.makeButton(label, gotoPred)
        self.pack_start(button, False, False, 0)

    def addToEnd(self, label, gotoPred):
        button = self.makeButton(label, gotoPred)
        self.pack_end(button, False, False, 0)

class TextBox(Gtk.Box):
    def __init__(self):
        super().__init__()
        self.set_orientation(Gtk.Orientation.VERTICAL)
        self.set_border_width(8)
        self._newRows=[]

    # text is printed here
    def add(self, item, dudename=None):
        if dudename:
            item = '<b>%s</b>: %s' % (dudename, item)
        lines = wrap(item,38)
        for i, line in enumerate(lines):
            colour = getColor('text')
            if i==0:
                line = "<span %s font_desc='unifont' size='large'>%s%s</span>"\
                        % (colour, Funwindow.modeVars['textPrefix'], line)
            else:
                line = "<span %s font_desc='unifont' size='large'>%s</span>"\
                       % (colour, line)
            widget = Gtk.Label()
            widget.set_markup(line)
            widget.set_halign(Gtk.Align.START)
            self._newRows.append(widget)
            self.pack_start(widget, False, False, 1)


    def newName(self, name):
        widget = Gtk.Label()
        colour = getColor('lighttext')
        widget.set_markup(\
        '<span %s font_desc="sans" size="x-large" underline="low"><b>%s</b></span>'\
         % (colour, name))
        widget.set_halign(Gtk.Align.START)
        self._newRows.append(widget)
        self.pack_start(widget, False, False, 1)

    @property
    def newRows(self):
        for child in self.get_children():
            if child in self._newRows:
                # this is no longer a new row!
                self._newRows.remove(child)
                if child.get_text().strip()=='':
                    # omit from history if it's an empty string
                    self.remove(child)
                    continue
                yield child

class MapBox(Gtk.Box):
    '''MapBox for Funwindow's MENU mode.
    Uses map as bold text.'''
    def __init__(self):
        super().__init__()
        self.set_orientation(Gtk.Orientation.VERTICAL)
        self.set_border_width(4)
        
    def create(self, tilemap, tileForChar):
        for line in tilemap:
            line = funtimes.replaceVariables(line)
            widget = Gtk.Label()
            widget.set_markup('<span font_desc="mono" size="x-large"><b>%s</b></span>' % line)
            widget.set_halign(Gtk.Align.START)
            self.pack_start(widget,False,False,0)

class MapGrid(Gtk.Grid):
    '''MapBox for Funwindow's MAP mode.
    Replaces characters on map with tiles.'''
    def __init__(self):
        super().__init__()
        self.set_border_width(4)

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
            if pathtofile=='':
                thisTile.set_size_request(32,32)
            else:
                pixbuf = GdkPixbuf.Pixbuf().new_from_file_at_scale(pathtofile,32, 32, True)
                thisTile.set_from_pixbuf(pixbuf)
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
delete_memory()

def getColor(key):
    if key in Funwindow.color:
        return "color='%s'" % Funwindow.color[key]
    else:
        return ''

if __name__=='__main__':
    # EXAMPLE OF HOW TO USE THIS MODULE IN OTHER SCRIPT
    play() # play 1st pred so window is not empty
    main() # get input (loops forever)
