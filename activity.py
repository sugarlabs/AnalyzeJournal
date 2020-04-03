#!/usr/bin/env python
# -*- coding: utf-8 -*-

# activity.py by:
#    Agustin Zubiaga <aguz@sugarlabs.org>
#    Gonzalo Odiard <godiard@gmail.com>
#    Manuel Quiñones <manuq@laptop.org>
#    Walter Bender <walter@sugarlabs.org>

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GObject
from gi.repository import Pango
import os
import json
import locale
import logging
import utils

from io import StringIO
from gettext import gettext as _

from sugar3.activity import activity
from sugar3.activity.widgets import ActivityToolbarButton
from sugar3.activity.widgets import StopButton
from sugar3.activity.widgets import ToolbarButton
from sugar3.graphics.toolbarbox import ToolbarBox
from sugar3.graphics.toolbutton import ToolButton
from sugar3.graphics.radiotoolbutton import RadioToolButton
from sugar3.graphics.colorbutton import ColorToolButton
from sugar3.graphics.objectchooser import ObjectChooser
from sugar3.graphics.icon import Icon
from sugar3.graphics.alert import Alert
from sugar3.datastore import datastore

from charts import Chart
from readers import FreeSpaceReader
from readers import JournalReader
from readers import TurtleReader
import charthelp

# GUI Colors
_COLOR1 = utils.get_user_fill_color()
_COLOR2 = utils.get_user_stroke_color()
_WHITE = Gdk.color_parse("white")

# Paths
_ACTIVITY_DIR = os.path.join(activity.get_activity_root(), "data/")
_CHART_FILE = utils.get_chart_file(_ACTIVITY_DIR)

# Logging
_logger = logging.getLogger('analyze-journal-activity')
_logger.setLevel(logging.DEBUG)
logging.basicConfig()

#Dragging
DRAG_ACTION = Gdk.DragAction.COPY

class ChartArea(Gtk.DrawingArea):

    def __init__(self, parent):
        """A class for Draw the chart"""
        super(ChartArea, self).__init__()
        self._parent = parent
        self.add_events(Gdk.EventMask.EXPOSURE_MASK | Gdk.EventMask.VISIBILITY_NOTIFY_MASK)
        self.connect("draw", self._draw_cb)

        self.drag_dest_set(Gtk.DestDefaults.ALL, [], DRAG_ACTION)
        self.drag_dest_set_target_list(Gtk.TargetList.new([]))
        self.drag_dest_add_text_targets()
        self.connect('drag_data_received', self._drag_data_received)

    def _draw_cb(self, widget, context):
        alloc = self.get_allocation()

        # White Background:
        context.rectangle(0, 0, alloc.width, alloc.height)
        context.set_source_rgb(255, 255, 255)
        context.fill()

        # Paint the chart:
        chart_width = self._parent.current_chart.width
        chart_height = self._parent.current_chart.height

        cxpos = alloc.width / 2 - chart_width / 2
        cypos = alloc.height / 2 - chart_height / 2

        context.set_source_surface(self._parent.current_chart.surface,
                                   cxpos,
                                   cypos)
        context.paint()

    def _drag_data_received(self, w, context, x, y, data, info, time):
        if data and data.format == 8:
            io_file = StringIO(data.data)
            reader = ClipboardReader(io_file)
            self._parent._graph_from_reader(reader)
            context.finish(True, False, time)
        else:
            context.finish(False, False, time)


class AnalyzeJournal(activity.Activity):

    def __init__(self, handle):

        activity.Activity.__init__(self, handle, True)

        self.max_participants = 1

        # CHART_OPTIONS

        self.x_label = ""
        self.y_label = ""
        self.chart_color = utils.get_user_fill_color('str')
        self.chart_line_color = utils.get_user_stroke_color('str')
        self.current_chart = None
        self.charts_area = None
        self.chart_data = []

        # TOOLBARS
        toolbarbox = ToolbarBox()

        activity_button = ActivityToolbarButton(self)
        activity_btn_toolbar = activity_button.page

        activity_btn_toolbar.title.connect('changed', self._set_chart_title)

        save_as_image = ToolButton("save-as-image")
        save_as_image.connect("clicked", self._save_as_image)
        save_as_image.set_tooltip(_("Save as image"))
        activity_btn_toolbar.insert(save_as_image, -1)

        save_as_image.show()

        toolbarbox.toolbar.insert(activity_button, 0)

        import_freespace = ToolButton("import-freespace")
        import_freespace.connect("clicked", self.__import_freespace_cb)
        import_freespace.set_tooltip(_("Read Freespace data"))
        toolbarbox.toolbar.insert(import_freespace, -1)
        import_freespace.show()

        import_journal = ToolButton('import-journal')
        import_journal.connect('clicked', self.__import_journal_cb)
        import_journal.set_tooltip(_('Read Journal data'))
        toolbarbox.toolbar.insert(import_journal, -1)
        import_journal.show()

        import_turtle = ToolButton('import-turtle')
        import_turtle.connect('clicked', self.__import_turtle_cb)
        import_turtle.set_tooltip(_('Read Turtle data'))
        toolbarbox.toolbar.insert(import_turtle, -1)
        import_turtle.show()

        separator = Gtk.SeparatorToolItem()
        separator.set_draw(True)
        separator.set_expand(False)
        toolbarbox.toolbar.insert(separator, -1)

        add_vbar_chart = RadioToolButton()
        add_vbar_chart.connect("clicked", self._add_chart_cb, "vbar")
        add_vbar_chart.set_tooltip(_("Vertical Bar Chart"))
        add_vbar_chart.props.icon_name = "vbar"
        charts_group = add_vbar_chart
        toolbarbox.toolbar.insert(add_vbar_chart, -1)

        add_hbar_chart = RadioToolButton()
        add_hbar_chart.connect("clicked", self._add_chart_cb, "hbar")
        add_hbar_chart.set_tooltip(_("Horizontal Bar Chart"))
        add_hbar_chart.props.icon_name = "hbar"
        add_hbar_chart.props.group = charts_group
        toolbarbox.toolbar.insert(add_hbar_chart, -1)

        add_pie_chart = RadioToolButton()
        add_pie_chart.connect("clicked", self._add_chart_cb, "pie")
        add_pie_chart.set_tooltip(_("Pie Chart"))
        add_pie_chart.props.icon_name = "pie"
        add_pie_chart.props.group = charts_group
        add_pie_chart.set_active(True)
        toolbarbox.toolbar.insert(add_pie_chart, -1)

        self.chart_type_buttons = [add_vbar_chart,
                                   add_hbar_chart,
                                   add_pie_chart]

        separator = Gtk.SeparatorToolItem()
        separator.set_draw(True)
        separator.set_expand(False)
        toolbarbox.toolbar.insert(separator, -1)

        fullscreen_btn = ToolButton('view-fullscreen')
        fullscreen_btn.set_tooltip(_('Fullscreen'))
        fullscreen_btn.connect("clicked", self.__fullscreen_cb)

        toolbarbox.toolbar.insert(fullscreen_btn, -1)

        charthelp.create_help(toolbarbox.toolbar)

        separator = Gtk.SeparatorToolItem()
        separator.set_draw(False)
        separator.set_expand(True)
        toolbarbox.toolbar.insert(separator, -1)

        stopbtn = StopButton(self)
        toolbarbox.toolbar.insert(stopbtn, -1)

        self.set_toolbar_box(toolbarbox)

        # CANVAS
        paned = Gtk.HPaned()
        box = Gtk.VBox()
        self.box = box

        # Set the info box width to 1/3 of the screen:
        def size_allocate_cb(widget, allocation):
            paned.disconnect(self._setup_handle)
            box_width = allocation.width / 3
            box.set_size_request(box_width, -1)

        self._setup_handle = paned.connect('size_allocate',
                    size_allocate_cb)

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self.labels_and_values = ChartData(self)
        scroll.add(self.labels_and_values)

        self.labels_and_values.connect("label-changed", self._label_changed)
        self.labels_and_values.connect("value-changed", self._value_changed)

        box.pack_start(scroll, True, True, 0)

        paned.add1(box)

        # CHARTS AREA

        eventbox = Gtk.EventBox()
        self.charts_area = ChartArea(self)
        self.charts_area.connect('size_allocate', self._chart_size_allocate)

        eventbox.modify_bg(Gtk.StateType.NORMAL, _WHITE)

        eventbox.add(self.charts_area)
        paned.add2(eventbox)

        self.set_canvas(paned)

        self.show_all()

    def _add_chart_cb(self, widget, type="vbar"):
        self.current_chart = Chart(type)

        self.update_chart()

    def _chart_size_allocate(self, widget, allocation):
        self._render_chart()

    def unfullscreen(self):
        self.box.show()
        activity.Activity.unfullscreen(self)

    def __fullscreen_cb(self, button):
        self.box.hide()
        self._render_chart(fullscreen=True)
        activity.Activity.fullscreen(self)

    def _render_chart(self, fullscreen=False):
        if self.current_chart is None or self.charts_area is None:
            return

        try:
            # Resize the chart for all the screen sizes
            alloc = self.get_allocation()

            if fullscreen:
                new_width = alloc.width
                new_height = alloc.height

            if not fullscreen:
                alloc = self.charts_area.get_allocation()

                new_width = alloc.width - 40
                new_height = alloc.height - 40

            self.current_chart.width = new_width
            self.current_chart.height = new_height

            # Set options
            self.current_chart.set_color_scheme(color=self.chart_color)
            self.current_chart.set_line_color(self.chart_line_color)

            if self.current_chart.type == "pie":
                self.current_chart.render(self)
            else:
                self.current_chart.render()
            self.charts_area.queue_draw()

        except (ZeroDivisionError, ValueError):
            pass

        return False

    def _update_chart_data(self):
        if self.current_chart is None:
            return
        self.current_chart.data_set(self.chart_data)
        self._update_chart_labels()

    def _set_chart_title(self, widget):
        self._update_chart_labels(title=widget.get_text())

    def _update_chart_labels(self, title=""):
        if self.current_chart is None:
            return

        if not title and self.metadata["title"]:
            title = self.metadata["title"]

        self.current_chart.set_title(title)
        self.current_chart.set_x_label(self.x_label)
        self.current_chart.set_y_label(self.y_label)
        self._render_chart()

    def update_chart(self):
        if self.current_chart:
            self.current_chart.data_set(self.chart_data)
            self.current_chart.set_title(self.metadata["title"])
            self.current_chart.set_x_label(self.x_label)
            self.current_chart.set_y_label(self.y_label)
            self._render_chart()

    def _label_changed(self, treeview, path, new_label):
        path = int(path)
        self.chart_data[path] = (new_label, self.chart_data[path][1])
        self._update_chart_data()

    def _value_changed(self, treeview, path, new_value):
        path = int(path)
        self.chart_data[path] = (self.chart_data[path][0], float(new_value))
        self._update_chart_data()

    def _set_h_label(self, widget):
        new_text = widget.get_text()

        if new_text != self.h_label._text:
            self.x_label = new_text
            self._update_chart_labels()

    def _set_v_label(self, widget):
        new_text = widget.get_text()

        if new_text != self.v_label._text:
            self.y_label = new_text
            self._update_chart_labels()

    def _set_chart_color(self, widget, pspec):
        self.chart_color = utils.rgb2html(widget.get_color())
        self._render_chart()

    def _set_chart_line_color(self, widget, pspec):
        self.chart_line_color = utils.rgb2html(widget.get_color())
        self._render_chart()

    def _object_chooser(self, mime_type, type_name):
        chooser = ObjectChooser()
        matches_mime_type = False

        response = chooser.run()
        if response == Gtk.ResponseType.ACCEPT:
            jobject = chooser.get_selected_object()
            metadata = jobject.metadata
            file_path = jobject.file_path

            if metadata['mime_type'] == mime_type:
                matches_mime_type = True

            else:
                alert = Alert()

                alert.props.title = _('Invalid object')
                alert.props.msg = \
                       _('The selected object must be a %s file' % (type_name))

                ok_icon = Icon(icon_name='dialog-ok')
                alert.add_button(Gtk.ResponseType.OK, _('Ok'), ok_icon)
                ok_icon.show()

                alert.connect('response', lambda a, r: self.remove_alert(a))

                self.add_alert(alert)

                alert.show()

        return matches_mime_type, file_path, metadata['title']

    def _graph_from_reader(self, reader):
        self.labels_and_values.model.clear()
        self.chart_data = []

        chart_data = reader.get_chart_data()
        horizontal, vertical = reader.get_labels_name()

        # Load the data
        for row  in chart_data:
            self._add_value(None,
                            label=row[0], value=float(row[1]))

            self.update_chart()

    def _add_value(self, widget, label="", value="0.0"):
        data = (label, float(value))
        if not data in self.chart_data:
            pos = self.labels_and_values.add_value(label, value)
            self.chart_data.insert(pos, data)
            self._update_chart_data()


    def _remove_value(self, widget):
        value = self.labels_and_values.remove_selected_value()
        self.chart_data.remove(value)
        self._update_chart_data()

    def __import_freespace_cb(self, widget):
            reader = FreeSpaceReader()
            self._graph_from_reader(reader)

    def __import_journal_cb(self, widget):
        reader = JournalReader()
        self._graph_from_reader(reader)

    def __import_turtle_cb(self, widget):
        matches_mime_type, file_path, title = self._object_chooser(
            'application/x-turtle-art', _('Turtle'))
        if matches_mime_type:
            reader = TurtleReader(file_path)
            self._graph_from_reader(reader)

    def _save_as_image(self, widget):
        if self.current_chart:
            jobject = datastore.create()

            jobject.metadata['title'] = self.metadata["title"]
            jobject.metadata['mime_type'] = "image/png"

            self.current_chart.as_png(_CHART_FILE)
            jobject.set_file_path(_CHART_FILE)

            datastore.write(jobject)

    def load_from_file(self, f):
        try:
            data = json.load(f)
        finally:
            f.close()

        self.metadata["title"] = data['title']
        self.x_label = data['x_label']
        self.y_label = data['y_label']
        self.chart_color = data['chart_color']
        self.chart_line_color = data['chart_line_color']
        self.current_chart.type = data['current_chart.type']
        chart_data = data['chart_data']

        # Update charts buttons
        _type = data["current_chart.type"]
        if _type == "vbar":
            self.chart_type_buttons[0].set_active(True)

        elif _type == "hbar":
            self.chart_type_buttons[1].set_active(True)

        elif _type == "line":
            self.chart_type_buttons[2].set_active(True)

        elif _type == "pie":
            self.chart_type_buttons[3].set_active(True)

        #load the data
        for row  in chart_data:
            self._add_value(None, label=row[0], value=float(row[1]))


        self.update_chart()

    def write_file(self, file_path):
        self.metadata['mime_type'] = "application/x-chart-activity"
        if self.current_chart:

            data = {}
            data['title'] = self.metadata["title"]
            data['x_label'] = self.x_label
            data['y_label'] = self.y_label
            data['chart_color'] = self.chart_color
            data['chart_line_color'] = self.chart_line_color
            data['current_chart.type'] = self.current_chart.type
            data['chart_data'] = self.chart_data

            f = open(file_path, 'w')
            try:
                json.dump(data, f)
            finally:
                f.close()

    def read_file(self, file_path):
        f = open(file_path, 'r')
        self.load_from_file(f)


class ChartData(Gtk.TreeView):

    __gsignals__ = {
             'label-changed': (GObject.SignalFlags.RUN_FIRST, None, [str, str], ),
             'value-changed': (GObject.SignalFlags.RUN_FIRST, None, [str, str], ), }

    def __init__(self, activity):

        GObject.GObject.__init__(self)


        self.model = Gtk.ListStore(str, str)
        self.set_model(self.model)

        self._selection = self.get_selection()
        self._selection.set_mode(Gtk.SelectionMode.SINGLE)

        # Label column

        column = Gtk.TreeViewColumn(_("Label"))
        label = Gtk.CellRendererText()
        label.set_property('editable', True)
        label.connect("edited", self._label_changed, self.model)

        column.pack_start(label, True)
        column.add_attribute(label, 'text', 0)
        self.append_column(column)

        # Value column

        column = Gtk.TreeViewColumn(_("Value"))
        value = Gtk.CellRendererText()
        value.set_property('editable', True)
        value.connect("edited", self._value_changed, self.model, activity)

        column.pack_start(value, True)
        column.add_attribute(value, 'text', 1)

        self.append_column(column)
        self.set_enable_search(False)

        self.show_all()

    def add_value(self, label, value):
        treestore, selected = self._selection.get_selected()
        if not selected:
            path = 0

        elif selected:
            path = int(str(self.model.get_path(selected))) + 1
        try:
            _iter = self.model.insert(path, [label, value])
        except ValueError:
            _iter = self.model.append([label, str(value)])


        self.set_cursor(self.model.get_path(_iter),
                        self.get_column(1),
                        True)

        return path

    def remove_selected_value(self):
        model, iter = self._selection.get_selected()
        value = (self.model.get(iter, 0)[0], float(self.model.get(iter, 1)[0]))
        self.model.remove(iter)

        return value

    def _label_changed(self, cell, path, new_text, model):
        model[path][0] = new_text

        self.emit("label-changed", str(path), new_text)

    def _value_changed(self, cell, path, new_text, model, activity):
        is_number = True
        number = new_text.replace(",", ".")
        try:
            float(number)
        except ValueError:
            is_number = False

        if is_number:
            decimals = utils.get_decimals(str(float(number)))
            new_text = locale.format('%.' + decimals + 'f', float(number))
            model[path][1] = str(new_text)

            self.emit("value-changed", str(path), number)

        elif not is_number:
            alert = Alert()

            alert.props.title = _('Invalid Value')
            alert.props.msg = \
                           _('The value must be a number (integer or decimal)')

            ok_icon = Icon(icon_name='dialog-ok')
            alert.add_button(Gtk.ResponseType.OK, _('Ok'), ok_icon)
            ok_icon.show()

            alert.connect('response', lambda a, r: activity.remove_alert(a))

            activity.add_alert(alert)

            alert.show()


class Entry(Gtk.ToolItem):

    def __init__(self, text):
        GObject.GObject.__init__(self)

        self.entry = Gtk.Entry()
        self.entry.set_text(text)
        self.entry.connect("focus-in-event", self._focus_in)
        self.entry.connect("focus-out-event", self._focus_out)
        self.entry.modify_font(Pango.FontDescription("italic"))

        self._text = text

        self.add(self.entry)

        self.show_all()

    def _focus_in(self, widget, event):
        if widget.get_text() == self._text:
            widget.set_text("")
            widget.modify_font(Pango.FontDescription(""))

    def _focus_out(self, widget, event):
        if widget.get_text() == "":
            widget.set_text(self.text)
            widget.modify_font(Pango.FontDescription("italic"))
