#!/usr/bin/env python3

import sys
import gi
gi.require_version('Gst', '1.0')
gi.require_version('Gtk', '3.0')
gi.require_version('GdkX11', '3.0')
gi.require_version('GstVideo', '1.0')
from gi.repository import Gst, Gtk, GLib, GdkX11, GstVideo

class Player(object):
    def __init__(self):
        Gtk.init(sys.argv)
        Gst.init(sys.argv)

        self.state = Gst.State.NULL
        self.duration = Gst.CLOCK_TIME_NONE
        self.playbin = Gst.ElementFactory.make("playbin", "playbin")
        if not self.playbin:
            print("ERROR: Could not create playbin.")
            sys.exit(1)
        self.playbin.set_property(
            "uri", "http://video.webmfiles.org/big-buck-bunny_trailer.webm")

        # connect to playbin
        self.playbin.connect("video-tags-changed", self.on_tags_changed)
        self.playbin.connect("audio-tags-changed", self.on_tags_changed)
        self.playbin.connect("text-tags-changed", self.on_tags_changed)

        # GUI
        self.build_ui()

        # the signals
        bus = self.playbin.get_bus()
        bus.add_signal_watch()
        bus.connect("message::error", self.on_error)
        bus.connect("message::eos", self.on_eos)
        bus.connect("message::state-changed", self.on_state_changed)
        bus.connect("message::application", self.on_application_message)

    # set the playbin to PLAYING 
    def start(self):
        # start playing
        ret = self.playbin.set_state(Gst.State.PLAYING)
        if ret == Gst.StateChangeReturn.FAILURE:
            print("ERROR: Unable to set the pipeline to the playing state")
            sys.exit(1)

        GLib.timeout_add_seconds(1, self.refresh_ui)
        Gtk.main()
        self.cleanup()

    # set the playbin state to NULL and remove the reference to it
    def cleanup(self):
        if self.playbin:
            self.playbin.set_state(Gst.State.NULL)
            self.playbin = None

    def build_ui(self):
        main_window = Gtk.Window.new(Gtk.WindowType.TOPLEVEL)
        main_window.connect("delete-event", self.on_delete_event)

        video_window = Gtk.DrawingArea.new()
        video_window.set_double_buffered(False)
        video_window.connect("realize", self.on_realize)
        video_window.connect("draw", self.on_draw)

        play_button = Gtk.Button.new_from_stock(Gtk.STOCK_MEDIA_PLAY)
        play_button.connect("clicked", self.on_play)

        pause_button = Gtk.Button.new_from_stock(Gtk.STOCK_MEDIA_PAUSE)
        pause_button.connect("clicked", self.on_pause)

        stop_button = Gtk.Button.new_from_stock(Gtk.STOCK_MEDIA_STOP)
        stop_button.connect("clicked", self.on_stop)

        self.slider = Gtk.HScale.new_with_range(0, 100, 1)
        self.slider.set_draw_value(False)
        self.slider_update_signal_id = self.slider.connect(
            "value-changed", self.on_slider_changed)

        self.streams_list = Gtk.TextView.new()
        self.streams_list.set_editable(False)

        controls = Gtk.HBox.new(False, 0)
        controls.pack_start(play_button, False, False, 2)
        controls.pack_start(pause_button, False, False, 2)
        controls.pack_start(stop_button, False, False, 2)
        controls.pack_start(self.slider, True, True, 0)

        main_hbox = Gtk.HBox.new(False, 0)
        main_hbox.pack_start(video_window, True, True, 0)
        main_hbox.pack_start(self.streams_list, False, False, 2)

        main_box = Gtk.VBox.new(False, 0)
        main_box.pack_start(main_hbox, True, True, 0)
        main_box.pack_start(controls, False, False, 0)

        main_window.add(main_box)
        main_window.set_default_size(640, 480)
        main_window.show_all()

    def on_realize(self, widget):
        window = widget.get_window()
        window_handle = window.get_xid()

        self.playbin.set_window_handle(window_handle)
        # self.playbin.set_xwindow_id(window_handle)

    def on_play(self, button):
        self.playbin.set_state(Gst.State.PLAYING)
        pass

    def on_pause(self, button):
        self.playbin.set_state(Gst.State.PAUSED)
        pass

    def on_stop(self, button):
        self.playbin.set_state(Gst.State.READY)
        pass

    def on_delete_event(self, widget, event):
        self.on_stop(None)
        Gtk.main_quit()

    def on_draw(self, widget, cr):
        if self.state < Gst.State.PAUSED:
            allocation = widget.get_allocation()

            cr.set_source_rgb(0, 0, 0)
            cr.rectangle(0, 0, allocation.width, allocation.height)
            cr.fill()

        return False

    def on_slider_changed(self, range):
        value = self.slider.get_value()
        self.playbin.seek_simple(Gst.Format.TIME,
                                 Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT,
                                 value * Gst.SECOND)

    # refresh the GUI
    def refresh_ui(self):
        current = -1

        if self.state < Gst.State.PAUSED:
            return True

        if self.duration == Gst.CLOCK_TIME_NONE:
            ret, self.duration = self.playbin.query_duration(Gst.Format.TIME)
            if not ret:
                print("ERROR: Could not query current duration")
            else:
                self.slider.set_range(0, self.duration / Gst.SECOND)

        ret, current = self.playbin.query_position(Gst.Format.TIME)
        if ret:
            self.slider.handler_block(self.slider_update_signal_id)
            self.slider.set_value(current / Gst.SECOND)
            self.slider.handler_unblock(self.slider_update_signal_id)

        return True
    def on_tags_changed(self, playbin, stream):
        self.playbin.post_message(
            Gst.Message.new_application(
                self.playbin,
                Gst.Structure.new_empty("tags-changed")))

    def on_error(self, bus, msg):
        err, dbg = msg.parse_error()
        print("ERROR:", msg.src.get_name(), ":", err.message)
        if dbg:
            print("Debug info:", dbg)

    def on_eos(self, bus, msg):
        print("End-Of-Stream reached")
        self.playbin.set_state(Gst.State.READY)

    def on_state_changed(self, bus, msg):
        old, new, pending = msg.parse_state_changed()
        if not msg.src == self.playbin:
            return

        self.state = new
        print("State changed from {0} to {1}".format(
            Gst.Element.state_get_name(old), Gst.Element.state_get_name(new)))

        if old == Gst.State.READY and new == Gst.State.PAUSED:
            self.refresh_ui()

    # extract metadata 
    def analyze_streams(self):
        buffer = self.streams_list.get_buffer()
        buffer.set_text("")

        nr_video = self.playbin.get_property("n-video")
        nr_audio = self.playbin.get_property("n-audio")
        nr_text = self.playbin.get_property("n-text")

        for i in range(nr_video):
            tags = None
            tags = self.playbin.emit("get-video-tags", i)
            if tags:
                buffer.insert_at_cursor("video stream {0}\n".format(i))
                _, str = tags.get_string(Gst.TAG_VIDEO_CODEC)
                buffer.insert_at_cursor(
                    "  codec: {0}\n".format(
                        str or "unknown"))

        for i in range(nr_audio):
            tags = None
            tags = self.playbin.emit("get-audio-tags", i)
            if tags:
                buffer.insert_at_cursor("\naudio stream {0}\n".format(i))
                ret, str = tags.get_string(Gst.TAG_AUDIO_CODEC)
                if ret:
                    buffer.insert_at_cursor(
                        "  codec: {0}\n".format(
                            str or "unknown"))

                ret, str = tags.get_string(Gst.TAG_LANGUAGE_CODE)
                if ret:
                    buffer.insert_at_cursor(
                        "  language: {0}\n".format(
                            str or "unknown"))

                ret, str = tags.get_uint(Gst.TAG_BITRATE)
                if ret:
                    buffer.insert_at_cursor(
                        "  bitrate: {0}\n".format(
                            str or "unknown"))

        for i in range(nr_text):
            tags = None
            tags = self.playbin.emit("get-text-tags", i)
            if tags:
                buffer.insert_at_cursor("\nsubtitle stream {0}\n".format(i))
                ret, str = tags.get_string(Gst.TAG_LANGUAGE_CODE)
                if ret:
                    buffer.insert_at_cursor(
                        "  language: {0}\n".format(
                            str or "unknown"))

    def on_application_message(self, bus, msg):
        if msg.get_structure().get_name() == "tags-changed":
            # update the stream info in the GUI
            self.analyze_streams()

if __name__ == '__main__':
    p = Player()
    p.start()