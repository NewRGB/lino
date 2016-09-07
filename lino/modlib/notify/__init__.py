# Copyright 2008-2016 Luc Saffre
# License: BSD (see file COPYING for details)

"""Adds functionality for managing notifications.

.. autosummary::
   :toctree:

    models
    actions
    mixins
    utils

Templates used by this plugin
=============================

.. xfile:: notify/body.eml

    A Jinja template used for generating the body of the email when
    sending a notification per email to its recipient.

    Available context variables:

    - ``obj`` -- The :class:`Notification
      <lino.modlib.notify.models.Notification>` instance being sent.

    - ``E`` -- The html namespace :mod:`lino.utils.xmlgen.html`

    - ``rt`` -- The runtime API :mod:`lino.api.rt`

    - ``ar`` -- The action request which caused the notification. a
      :class:`BaseRequest <lino.core.requests.BaseRequest>` instance.

"""

from lino.api import ad, _


class Plugin(ad.Plugin):
    "See :class:`lino.core.plugin.Plugin`."

    verbose_name = _("Notifications")

    needs_plugins = ['lino.modlib.users', 'lino.modlib.gfks']

    # email_subject_template = "Notification about {obj.owner}"
    # """The template used to build the subject lino of notification emails.

    # :obj: is the :class:`Notification
    #       <lino.modlib.notify.models.Notification>` object.

    # """

    def setup_main_menu(self, site, profile, m):
        p = site.plugins.office
        m = m.add_menu(p.app_label, p.verbose_name)
        m.add_action('notify.MyNotifications')

    def setup_explorer_menu(self, site, profile, m):
        p = site.plugins.system
        m = m.add_menu(p.app_label, p.verbose_name)
        m.add_action('notify.AllNotifications')

