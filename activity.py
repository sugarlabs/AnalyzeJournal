#!/usr/bin/env python
# -*- coding: utf-8 -*-

# activity.py by:
#    Agustin Zubiaga <aguz@sugarlabs.com>

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

import gtk
import sys
import os
import statvfs
import logging
import pango

from gettext import gettext as _

from sugar import env

from sugar.activity import activity
from sugar.activity.widgets import ActivityToolbarButton
from sugar.activity.widgets import StopButton
from sugar.graphics.toolbarbox import ToolbarBox
from sugar.graphics.toolbutton import ToolButton

path = os.path.join(os.getenv('HOME'), 'Activities', 'SimpleGraph.activity')
sys.path.insert(0, path)

from charts import Chart

logger = logging.getLogger('AnalizeJournal-activity')
logger.setLevel(logging.DEBUG)
logging.basicConfig()


class AnalizeJournal(activity.Activity):

    def __init__(self, handle):
        activity.Activity.__init__(self, handle, False)

        self.max_participants = 1

        # TOOLBARS
        toolbarbox = ToolbarBox()

        activity_button = ActivityToolbarButton(self)
        toolbarbox.toolbar.insert(activity_button, 0)

        update_btn = ToolButton('gtk-refresh')
        update_btn.connect('clicked', self._analize)
        toolbarbox.toolbar.insert(update_btn, -1)

        separator = gtk.SeparatorToolItem()
        separator.set_draw(False)
        separator.set_expand(True)
        toolbarbox.toolbar.insert(separator, -1)

        stopbtn = StopButton(self)
        toolbarbox.toolbar.insert(stopbtn, -1)

        toolbarbox.show_all()

        self.set_toolbar_box(toolbarbox)

        # CHART
        self.chart = None
        self.chart_data = []

        # CANVAS
        self.area = Area(self)
        self.set_canvas(self.area)

        self.area.show_all()

        # ANALIZE
        self.show_all()
        self._analize(None)

    def  _analize(self, widget):
        self.chart_data = []

        free_space, used_space, total_space = self._get_space()

        # Graph
        self.chart_data.append((_('Free'), free_space))
        self.chart_data.append((_('Used'), used_space))

        self.chart = Chart()
        self.chart.data_set(self.chart_data)
        self.chart.set_type('pie')
        self._resize_chart()
        self.chart.render(self)

        # Set info
        f_type, t_type, u_type = 'MBs', 'MBs', 'MBs'

        if free_space >= 1024:
            free_space = self._get_GBs(free_space)
            f_type = 'GBs'

        if total_space >= 1024:
            total_space = self._get_GBs(total_space)
            t_type = 'GBs'

        if used_space >= 1024:
            used_space = self._get_GBs(used_space)
            u_type = 'GBs'

        a = _('Total space: %s %s') % (total_space, t_type)
        b = _('Used space: %s %s') % (used_space, u_type)
        c = _('Free space: %s %s') % (free_space, f_type)

        info = a + '\n' + b + '\n' + c

        self.area.text = info

        self.area.queue_draw()

    def _resize_chart(self):
        sx, sy, width, height = self.area.get_allocation()

        new_width = width - 200
        new_height = height - 200

        self.chart.width = new_width
        self.chart.height = new_height

    def _get_space(self):
        stat = os.statvfs(env.get_profile_path())
        free_space = stat[statvfs.F_BSIZE] * stat[statvfs.F_BAVAIL]
        total_space = stat[statvfs.F_BSIZE] * stat[statvfs.F_BLOCKS]

        free_space = self._get_MBs(free_space)
        total_space = self._get_MBs(total_space)
        used_space = total_space - free_space

        logger.info('Free space: %s/%s MBs' % (free_space, total_space))

        return free_space, used_space, total_space

    def _get_MBs(self, space):
        space = space / (1024 * 1024)

        return space

    def _get_GBs(self, space):
        space = space / 1024

        return space


class Area(gtk.DrawingArea):

    def __init__(self, parent):
        super(Area, self).__init__()
        self._parent = parent
        self.add_events(gtk.gdk.EXPOSURE_MASK | gtk.gdk.VISIBILITY_NOTIFY_MASK)
        self.connect('expose-event', self._expose_cb)

        self.text = ''

        pango_context = self.get_pango_context()
        self.layout = pango.Layout(pango_context)
        self.layout.set_font_description(pango.FontDescription('13'))

    def _expose_cb(self, widget, event):
        context = self.window.cairo_create()
        gc = self.window.new_gc()

        x, y, w, h = self.get_allocation()

        # White Background:
        context.rectangle(0, 0, w, h)
        context.set_source_rgb(255, 255, 255)
        context.fill()

        # Paint the chart:
        cw, ch = self._parent.chart.width, self._parent.chart.height
        x, y, w, h = self.get_allocation()

        cy = y + h / 2 - ch / 2

        context.set_source_surface(self._parent.chart.surface, x, cy)
        context.paint()

        # Write the info
        self.layout.set_markup(self.text)
        lx = x + cw

        self.window.draw_layout(gc, lx, cy, self.layout)
