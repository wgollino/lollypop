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

from gi.repository import Gtk, GLib, Gdk

from lollypop.view import View
from lollypop.view_container import ViewContainer
from lollypop.widgets_album import AlbumSimpleWidget
from lollypop.widgets_album_context import AlbumContextWidget
from lollypop.widgets_album_context import AlbumPopoverWidget
from lollypop.define import Lp, ArtSize
from lollypop.objects import Album, Track


class AlbumContextView(View):
    """
        Album contextual view
    """

    def __init__(self, widget):
        """
            Init context
            @param main view widget
        """
        View.__init__(self)
        self._widget = widget
        self._viewport.add(widget)
        self._viewport.show()
        self._scrolled.set_min_content_height(ArtSize.BIG+35)
        self._scrolled.show()
        self.add(self._scrolled)

#######################
# PRIVATE             #
#######################
    def _get_children(self):
        """
            Return view children
            @return [AlbumWidget]
        """
        return [self._widget]


class AlbumsView(View):
    """
        Show albums in a box
    """

    def __init__(self, genre_id, is_compilation):
        """
            Init album view
            @param genre id as int
            @param is compilation as bool
        """
        View.__init__(self)
        self._signal = None
        self._context_album_id = None
        self._genre_id = genre_id
        self._is_compilation = is_compilation
        self._albumsongs = None
        self._context_widget = None
        self._press_rect = None
        self._lazy_queue = []  # Widgets not initialized
        self._scroll_value = 0
        self._timeout_id = None

        self._albumbox = Gtk.FlowBox()
        self._albumbox.set_selection_mode(Gtk.SelectionMode.NONE)
        self._albumbox.connect('child-activated', self._on_album_activated)
        self._albumbox.connect('button-press-event', self._on_button_press)
        self._albumbox.set_property('column-spacing', 5)
        self._albumbox.set_property('row-spacing', 5)
        self._albumbox.set_homogeneous(True)
        self._albumbox.set_max_children_per_line(1000)
        self._albumbox.show()

        self._viewport.set_property('valign', Gtk.Align.START)
        self._viewport.set_property('margin', 5)
        self._scrolled.set_property('expand', True)
        self._scrolled.get_vadjustment().connect('value-changed',
                                                 self._on_value_changed)
        self._context = ViewContainer(500)

        separator = Gtk.Separator()
        separator.show()

        self._paned = Gtk.Paned.new(Gtk.Orientation.VERTICAL)
        self._paned.pack1(self._scrolled, True, False)
        self._paned.pack2(self._context, False, False)
        height = Lp().settings.get_value('paned-context-height').get_int32()
        # We set a stupid max value, safe as self._context is shrinked
        if height == -1:
            height = Lp().window.get_allocated_height()
        self._paned.set_position(height)
        self._paned.connect('notify::position', self._on_position_notify)
        self._paned.show()
        self.add(self._paned)

    def populate(self, albums):
        """
            Populate albums
            @param is compilation as bool
        """
        # Add first album to get album size,
        # used to precalculate next albums size
        if albums:
            widget = AlbumSimpleWidget(albums.pop(0))
            widget.init_widget()
            widget.show_all()
            self._albumbox.insert(widget, -1)
            # Keep album requisition
            self._requisition = widget.get_preferred_size()[1]
            self._add_albums(albums)

#######################
# PRIVATE             #
#######################
    def _get_children(self):
        """
            Return view children
            @return [AlbumWidget]
        """
        children = []
        for child in self._albumbox.get_children():
            widget = child.get_child()
            children.append(widget)
        if self._context_widget is not None:
            children.append(self._context_widget)
        return children

    def _populate_context(self, album_id):
        """
            populate context view
            @param album id as int
        """
        size_group = Gtk.SizeGroup(mode=Gtk.SizeGroupMode.HORIZONTAL)
        self._context_widget = AlbumContextWidget(album_id,
                                                  self._genre_id,
                                                  False,
                                                  size_group)
        self._context_widget.populate()
        self._context_widget.show()
        view = AlbumContextView(self._context_widget)
        view.show()
        self._context.add(view)
        self._context.set_visible_child(view)
        self._context.clean_old_views(view)

    def _add_albums(self, albums):
        """
            Add albums to the view
            Start lazy loading
            @param [album ids as int]
        """
        if albums and not self._stop:
            widget = AlbumSimpleWidget(albums.pop(0),
                                       self._requisition.width,
                                       self._requisition.height)
            self._albumbox.insert(widget, -1)
            widget.show_all()
            self._lazy_queue.append(widget)
            GLib.idle_add(self._add_albums, albums)
        else:
            GLib.idle_add(self._lazy_loading)
            self._viewport.add(self._albumbox)

    def _lazy_loading(self, widgets=[], scroll_value=0):
        """
            Load the view in a lazy way:
                - widgets first
                - _waiting_init then
            @param widgets as [AlbumSimpleWidgets]
            @param scroll_value as float
        """
        widget = None
        if self._stop or self._scroll_value != scroll_value:
            return
        if widgets:
            widget = widgets.pop(0)
            self._lazy_queue.remove(widget)
        elif self._lazy_queue:
            widget = self._lazy_queue.pop(0)
        if widget is not None:
            widget.init_widget()
            GLib.idle_add(self._lazy_loading, widgets, scroll_value)

    def _is_visible(self, widget):
        """
            Is widget visible in scrolled
            @param widget as Gtk.Widget
        """
        widget_alloc = widget.get_allocation()
        scrolled_alloc = self._scrolled.get_allocation()
        try:
            (x, y) = widget.translate_coordinates(self._scrolled, 0, 0)
            return (y > -widget_alloc.height-ArtSize.BIG or y >= 0) and\
                y < scrolled_alloc.height+ArtSize.BIG
        except:
            return True

    def _lazy_or_not(self):
        """
            Add visible widgets to lazy queue
        """
        self._timeout_id = None
        widgets = []
        for child in self._lazy_queue:
            if self._is_visible(child):
                widgets.append(child)
        GLib.idle_add(self._lazy_loading, widgets, self._scroll_value)

    def _on_value_changed(self, adj):
        """
            Update scroll value and check for lazy queue
            @param adj as Gtk.Adjustment
        """
        if self._timeout_id is not None:
            GLib.source_remove(self._timeout_id)
            self._timeout_id = None
        self._scroll_value = adj.get_value()
        if not self._lazy_queue:
            return
        self._timeout_id = GLib.timeout_add(250, self._lazy_or_not)

    def _on_position_notify(self, paned, param):
        """
            Save paned position
            @param paned as Gtk.Paned
            @param param as Gtk.Param
        """
        Lp().settings.set_value('paned-context-height',
                                GLib.Variant('i', paned.get_position()))
        return False

    def _on_album_activated(self, flowbox, child):
        """
            Show Context view for activated album
            @param flowbox as Gtk.Flowbox
            @param child as Gtk.FlowboxChild
        """
        album_widget = child.get_child()
        if self._press_rect is None:
            if self._context_album_id == album_widget.get_id():
                self._context_album_id = None
                self._context.hide()
                self._context_widget.destroy()
                self._context_widget = None
            else:
                if Lp().settings.get_value('auto-play'):
                    album = Album(album_widget.get_id())
                    track = Track(album.tracks_ids[0])
                    Lp().player.load(track)
                    Lp().player.set_albums(track.id, None,
                                           self._genre_id)
                else:
                    self._context_album_id = album_widget.get_id()
                    self._populate_context(self._context_album_id)
                    self._context.show()
        else:
            if self._context_album_id is not None:
                self._context_album_id = None
                self._context.hide()
                self._context_widget.destroy()
                self._context_widget = None
            popover = AlbumPopoverWidget(album_widget.get_id(),
                                         self._genre_id)
            popover.set_relative_to(album_widget)
            popover.set_pointing_to(self._press_rect)
            popover.show()

    def _on_button_press(self, flowbox, event):
        """
            Store pressed button
            @param flowbox as Gtk.Flowbox
            @param event as Gdk.EventButton
        """
        if event.button == 1:
            self._press_rect = None
        else:
            self._press_rect = Gdk.Rectangle()
            self._press_rect.x = event.x
            self._press_rect.y = event.y
            self._press_rect.width = self._press_rect.height = 1
            event.button = 1
