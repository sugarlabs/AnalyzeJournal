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

from gettext import gettext as _

from sugar import env

from sugar.activity import activity
from sugar.activity.widgets import ActivityToolbarButton
from sugar.activity.widgets import StopButton
from sugar.graphics.toolbarbox import ToolbarBox

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
        toolbarbox.toolbar.insert(activity_button, -1)

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
        self.chart_area = ChartArea(self)
        self.set_canvas(self.chart_area)

        self.chart_area.show_all()

        # ANALIZE
        self._analize()

    def  _analize(self):
        self.chart_data = []

        free_space, used_space, total_space = self._get_space()

        self.chart_data.append((_('Free'), free_space))
        self.chart_data.append((_('Used'), used_space))

        self.chart = Chart()
        self.chart.data_set(self.chart_data)
        self.chart.set_type('pie')
        self.chart.render(self)

        self.chart_area.queue_draw()

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


class ChartArea(gtk.DrawingArea):

    def __init__(self, parent):
        super(ChartArea, self).__init__()
        self._parent = parent
        self.add_events(gtk.gdk.EXPOSURE_MASK | gtk.gdk.VISIBILITY_NOTIFY_MASK)
        self.connect("expose-event", self._expose_cb)

    def _expose_cb(self, widget, event):
        context = self.window.cairo_create()

        x, y, w, h = self.get_allocation()

        # White Background:
        context.rectangle(0, 0, w, h)
        context.set_source_rgb(255, 255, 255)
        context.fill()

        # Paint the chart:
        context.set_source_surface(self._parent.chart.surface)
        context.paint()
