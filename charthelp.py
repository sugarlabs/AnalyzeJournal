# Help for ChartActivity

from gettext import gettext as _

from helpbutton import HelpButton


def create_help(toolbar):
    helpitem = HelpButton()
    toolbar.insert(helpitem, -1)
    helpitem.show()
    helpitem.add_section(_('Basic usage'))
    helpitem.add_paragraph(_('First select data type:'))
    helpitem.add_paragraph(_('The free space in the Journal;'),
            'import-freespace')
    helpitem.add_paragraph(_('The types of Sugar Activities you have used;'),
            'import-journal')
    helpitem.add_paragraph(_('The types of blocks used in Turtle Art.'),
            'import-turtle')
    helpitem.add_paragraph(_('The graph title is the same as the Activity title'))

    helpitem.add_paragraph(_('You can change the type of graph:'))
    helpitem.add_paragraph(_('Vertical bars'), 'vbar')
    helpitem.add_paragraph(_('Horizontal bars'), 'hbar')
    helpitem.add_paragraph(_('Lines'), 'line')
    helpitem.add_paragraph(_('Pie'), 'pie')

    helpitem.add_section(_('Saving as an image'))
    helpitem.add_paragraph(_('In the activity toolbar you have button to save the graph as an image'),
            'save-as-image')
