# Copyright (c) 2014-2016 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

from gi.repository import Gtk, GLib, Pango

from lollypop.define import Lp
from lollypop.tagreader import ScannerTagReader
from lollypop.utils import seconds_to_string


class ExternalsPopover(Gtk.Popover):
    """
        Popover for external tracks
    """

    def __init__(self):
        """
            Init popover
        """
        Gtk.Popover.__init__(self)
        self.set_position(Gtk.PositionType.BOTTOM)
        self.connect('unmap', self._on_self_unmap)
        builder = Gtk.Builder()
        builder.add_from_resource('/org/gnome/Lollypop/ExternalsPopover.ui')
        builder.connect_signals(self)

        self._signal_id = None
        self._view = builder.get_object('view')
        self._model = builder.get_object('model')
        self._tagreader = ScannerTagReader()

        renderer0 = Gtk.CellRendererPixbuf()
        renderer1 = Gtk.CellRendererText()
        renderer1.set_property('weight', 800)
        renderer1.set_property('weight-set', True)
        renderer1.set_property('ellipsize-set', True)
        renderer1.set_property('ellipsize', Pango.EllipsizeMode.END)
        renderer2 = Gtk.CellRendererText()
        renderer2.set_property('ellipsize-set', True)
        renderer2.set_property('ellipsize', Pango.EllipsizeMode.END)
        renderer3 = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn('')
        column.pack_start(renderer0, True)
        column.pack_start(renderer1, True)
        column.pack_start(renderer2, True)
        column.pack_end(renderer3, False)
        column.add_attribute(renderer0, 'icon-name', 1)
        column.add_attribute(renderer1, 'text', 2)
        column.add_attribute(renderer2, 'text', 3)
        column.add_attribute(renderer3, 'text', 4)
        column.set_expand(True)
        column.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
        self._view.append_column(column)
        self.add(self._view)
        self._signal_id = Lp().player.connect('current-changed',
                                              self._on_current_changed)
        size_setting = Lp().settings.get_value('window-size')
        if isinstance(size_setting[1], int):
            self.set_size_request(400, size_setting[1]*0.7)
        else:
            self.set_size_request(400, 600)

    def populate(self):
        """
            Populate popover
        """
        self._model.clear()
        self._populate(Lp().player.get_externals())

#######################
# PRIVATE             #
#######################
    def _populate(self, tracks):
        """
            Populate popover
            @param tracks as [Track]
            @thread safe
        """
        for track in tracks:
            if track.duration == 0.0:
                try:
                    infos = self._tagreader.get_infos(track.path)
                    if infos is not None:
                        tags = infos.get_tags()
                        track.duration = infos.get_duration()/1000000000
                        track.name = self._tagreader.get_title(tags,
                                                               track.path)
                        track.artist_names = self._tagreader.get_artists(tags)
                except Exception as e:
                    print("ExternalsPopover::_populate(): %s" % e)
                    track.name = track.uri
            GLib.idle_add(self._add_track, track)

    def _add_track(self, track):
        """
            Add track to model
            @param track as Track
            @param filepath as string
        """
        if track.uri == Lp().player.current_track.uri:
            self._model.append((track.uri, 'media-playback-start-symbolic',
                                track.artist, track.title,
                                seconds_to_string(track.duration)))
        else:
            self._model.append((track.uri, '', track.artist, track.title,
                                seconds_to_string(track.duration)))

    def _on_self_unmap(self, widget):
        """
            Disconnect signals and destroy
            @param widget as Gtk.Widget
        """
        if self._signal_id is not None:
            Lp().player.disconnect(self._signal_id)
        GLib.idle_add(self.destroy)

    def _on_current_changed(self, player):
        """
            Update play symbol
            @param player as Player
        """
        for item in self._model:
            if item[0] == player.current_track.uri:
                item[1] = 'media-playback-start-symbolic'
            else:
                item[1] = ''

    def _on_row_activated(self, view, path, column):
        """
            Play selected track
            @param view as Gtk.TreeView
            @param path as Gtk.TreePath
            @param column as Gtk.TreeViewColumn
        """
        if path is not None:
            iterator = self._model.get_iter(path)
            if iterator is not None:
                uri = self._model.get_value(iterator, 0)
                Lp().player.play_this_external(uri)
