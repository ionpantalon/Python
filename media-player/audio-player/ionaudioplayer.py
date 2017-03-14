#!/usr/bin/env python3
import os
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gst', '1.0')


from gi.repository import GObject, Gst
from gi.repository import Gst, Gtk, GLib

from player import Main

class GenericException(Exception):
    pass

class SeekingExample(Gtk.Window):
    """Simple window with just 3 elements : play and pause buttons, and a slider"""
    
    def __init__(self):
        super(SeekingExample, self).__init__()
        self.set_size_request(600, 250)
        self.set_title("Ion audio player")
        self.connect("destroy", self.on_destroy)
        self.duration = Gst.CLOCK_TIME_NONE

        #GObject.threads_init()
        Gst.init(None)

        self.pl = Gst.ElementFactory.make("playbin", "player")
        self.pl.set_property('uri','file://'+os.path.abspath('Queen.webm'))
        
        #setting up a simple Horizontal box layout, with a window size of 500
        self.box = Gtk.Box(orientation = Gtk.Orientation.HORIZONTAL)
        self.add(self.box)
        
        #setting up controls with their signals and callbacks
        self.play_button = Gtk.Button.new_from_stock(Gtk.STOCK_MEDIA_PLAY)
        self.play_button.connect("clicked", self.testpl) #self.on_play
        self.pause_button = Gtk.Button.new_from_stock(Gtk.STOCK_MEDIA_PAUSE)
        self.pause_button.connect("clicked", self.on_pause)
        
        #creating a slider and calculating its range      
        self.slider = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 0.5)
        self.slider_handler_id = self.slider.connect("value-changed", self.on_slider_seek)
        
        # volume
        self.volume_handler = Gtk.Scale.new_with_range(Gtk.Orientation.VERTICAL, 0, 10, 0.5)
        # self.volume_handler_id = self.slider.connect("value-changed", self.on_slider_seek)
        

        #adding the controls to the layout
        self.box.pack_start(self.play_button, False, False, 2)
        self.box.pack_start(self.pause_button, False, False, 2)
        self.box.pack_start(self.slider, True, True, 2)
        
        self.show_all()

    def run(self):
        Gtk.main()
    
    def testpl(self, widget):
        self.is_playing = True

        self.pl.set_property('volume', 9)
        self.pl.set_state(Gst.State.PLAYING)
        GLib.timeout_add(1000, self.update_slider)

    def on_play(self, widget):
        self.is_playing = True
        self.pl.set_state(Gst.State.PLAYING)
        
        #starting up a timer to check on the current playback value
        GLib.timeout_add(1000, self.update_slider)
  
    def on_pause(self, widget): 
        self.is_playing = False
        self.pl.set_state(Gst.State.PAUSED)
        
    #called when the user moves the slider
    def on_slider_seek(self, widget):
        seek_time_secs = self.slider.get_value()
        self.pl.seek_simple(Gst.Format.TIME,  Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT, seek_time_secs * Gst.SECOND) 
    
    #called periodically by the Glib timer, returns false to stop the timer
    def update_slider(self):      
        if self.duration == Gst.CLOCK_TIME_NONE:
            success, self.duration = self.pl.query_duration(Gst.Format.TIME)
            if not success:
                print("ERROR: Could not query current duration")
            else:
                self.slider.set_range(0, self.duration / Gst.SECOND)             
            #fetching the position, in nanosecs
            success, position = self.pl.query_position(Gst.Format.TIME)
            if not success:
                raise GenericException("Couldn't fetch current song position to update slider")

            # block seek handler so we don't seek when we set_value()
            self.slider.handler_block(self.slider_handler_id)
            self.slider.set_value(float(position) / Gst.SECOND)
            self.slider.handler_unblock(self.slider_handler_id)
        return True # continue calling every x milliseconds
    
    def on_destroy(self, widget):
        Gtk.main_quit()
        
main = SeekingExample()
try:
    main.run()
except:
    Gtk.main_quit()
