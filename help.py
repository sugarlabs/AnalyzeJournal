# Help for AnalizeJournal

from gettext import gettext as _

from helpbutton import HelpButton


def create_help(toolbar):
    helpitem = HelpButton()
    toolbar.insert(helpitem, -1)
    helpitem.add_section(_('Description'))
    helpitem.add_paragraph(_('This activity gives you the possibility to graphically, the journal usage'))
    helpitem.add_section(_('Usage'))
    helpitem.add_paragraph(_('In the area you can view the info'))
    helpitem.add_paragraph(_('You can update the data with this button'),
                                                                'gtk-refresh')
    helpitem.show()
