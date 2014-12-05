# -*- coding: UTF-8 -*-
# Copyright 2013-2014 by Luc Saffre.
# License: BSD, see file LICENSE for more details.

"""

.. management_command:: dump2py

To make a python dump of your database (be it for daily backup or
before a migration), go to your project directory and say::

  $ python manage.py dump2py mydump
  
This will create a python dump of your database to the directory
`mydump`.

The directory will contain a file :xfile:`restore.py` and a lot of
other `.py` files (currently one for every model) which are being
:func:`execfile`\ d from that :xfile:`restore.py`.

To restore such a dump to your database, simply run the `restore.py`
script using the :mod:`run <djangosite.management.commands.run>`
management command::

  $ python manage.py run mydump/restore.py

Or, if you don't use per-project :xfile:`manage.py` files::

  $ set DJANGO_SETTINGS_MODULE=myproject
  $ django-admin.py run mydump/restore.py


FILES
-----

.. xfile:: restore.py

The main script of a Python dump generated by the
:manage:`dump2py` command.

"""

from __future__ import unicode_literals

import logging
logger = logging.getLogger(__name__)

import os
from optparse import make_option
from decimal import Decimal

from django.db import models
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from django.contrib.contenttypes.models import ContentType
from django.contrib.sessions.models import Session

from djangosite.dbutils import sorted_models_list, full_model_name

from lino.utils.mldbc.fields import BabelCharField, BabelTextField


class Command(BaseCommand):
    tmpl_dir = ''
    args = "output_dir"

    option_list = BaseCommand.option_list + (
        make_option('--noinput', action='store_false',
                    dest='interactive', default=True,
                    help='Do not prompt for input of any kind.'),
        #~ make_option('--quick', action='store_true',
        #~ dest='quick', default=False,
        #~ help='Do not call full_clean() method on restored instances.'),
        #~ make_option('--overwrite', action='store_true',
        #~ dest='overwrite', default=False,
        #~ help='Overwrite existing files.'),
    )

    def write_files(self):
        logger.info("Writing %s...", self.main_file)
        self.stream = open(self.main_file, 'wt')
        current_version = settings.SITE.version

        self.stream.write("""\
#!/usr/bin/env python
# -*- coding: UTF-8 -*-
""")

        self.stream.write('''\
"""
This is a Python dump created using %s.
''' % settings.SITE.using_text())

        #~ self.stream.write(settings.SITE.welcome_text())
        self.stream.write('''
"""
from __future__ import unicode_literals

import logging
logger = logging.getLogger('%s')
import os

''' % __name__)
        if False:
            self.stream.write("""
os.environ['DJANGO_SETTINGS_MODULE'] = '%s'
""" % settings.SETTINGS_MODULE)

        self.stream.write('SOURCE_VERSION = %r\n' % str(current_version))
        self.stream.write('''
from decimal import Decimal
from datetime import datetime as dt
from datetime import time,date
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from lino.utils.dpy import create_mti_child
from lino.utils.dpy import DpyLoader
from lino.core.dbutils import resolve_model
        
def new_content_type_id(m):
    if m is None: return m
    ct = ContentType.objects.get_for_model(m)
    if ct is None: return None
    return ct.pk
    
''')
        s = ','.join([
            '%s=values[%d]' % (lng.name, lng.index)
            for lng in settings.SITE.languages])
        self.stream.write('''
def bv2kw(fieldname, values):
    """
    Needed if `Site.languages` changed between dumpdata and loaddata
    """
    return settings.SITE.babelkw(fieldname, %s)
    
''' % s)
        self.models = [m for m in sorted_models_list()
                       if not issubclass(m, (ContentType, Session))]
        for model in self.models:
            self.stream.write('%s = resolve_model("%s")\n' % (
                full_model_name(model, '_'), full_model_name(model)))
        self.stream.write('\n')
        self.models = self.sort_models(self.models)
        self.stream.write('\n')
        for model in self.models:
            fields = [f for f,
                      m in model._meta.get_fields_with_model() if m is None]
            for f in fields:
                if getattr(f, 'auto_now_add', False):
                    raise Exception("%s.%s.auto_now_add is True : values will be lost!" % (
                        full_model_name(model), f.name))
            #~ fields = model._meta.local_fields
            #~ fields = [f for f in model._meta.fields if f.serialize]
            #~ fields = [f for f in model._meta.local_fields if f.serialize]
            self.stream.write('def create_%s(%s):\n' % (
                model._meta.db_table, ', '.join([
                    f.attname for f in fields
                    if not getattr(f, '_lino_babel_field', False)])))
            if model._meta.parents:
                if len(model._meta.parents) != 1:
                    msg = "%s : model._meta.parents is %r" % (
                        model, model._meta.parents)
                    raise Exception(msg)
                pm, pf = model._meta.parents.items()[0]
                child_fields = [f for f in fields if f != pf]
                if child_fields:
                    attrs = ',' + ','.join([
                        '%s=%s' % (f.attname, f.attname)
                        for f in child_fields])
                else:
                    attrs = ''
                #~ self.stream.write('    return insert_child(%s.objects.get(pk=%s),%s%s)\n' % (
                    #~ full_model_name(pm,'_'),pf.attname,full_model_name(model,'_'),attrs))
                self.stream.write('    return create_mti_child(%s,%s,%s%s)\n' % (
                    full_model_name(pm, '_'), pf.attname, full_model_name(model, '_'), attrs))
            else:
                self.stream.write("    kw = dict()\n")
                for f in fields:
                    if getattr(f, '_lino_babel_field', False):
                        continue
                    elif isinstance(f, (BabelCharField, BabelTextField)):
                        self.stream.write(
                            '    if %s is not None: kw.update(bv2kw(%r,%s))\n' % (
                                f.attname, f.attname, f.attname))
                    else:
                        if isinstance(f, models.DecimalField):
                            self.stream.write(
                                '    if %s is not None: %s = Decimal(%s)\n' % (
                                    f.attname, f.attname, f.attname))
                        elif isinstance(f, models.ForeignKey) and f.rel.to is ContentType:
                            #~ self.stream.write(
                                #~ '    %s = ContentType.objects.get_for_model(%s).pk\n' % (
                                #~ f.attname,f.attname))
                            self.stream.write(
                                '    %s = new_content_type_id(%s)\n' % (
                                    f.attname, f.attname))
                        self.stream.write(
                            '    kw.update(%s=%s)\n' % (f.attname, f.attname))

                self.stream.write('    return %s(**kw)\n\n' %
                                  full_model_name(model, '_'))
        self.stream.write('\n')
        #~ used_models = set()

        self.stream.write("""

def main():
    loader = DpyLoader(globals())
    from django.core.management import call_command
    # call_command('initdb', interactive=False)
    call_command('initdb')
    os.chdir(os.path.dirname(__file__))
    loader.initialize()

""")

        for model in self.models:
            filename = '%s.py' % model._meta.db_table
            filename = os.path.join(self.output_dir, filename)
            logger.info("Writing %s...", filename)
            stream = file(filename, 'wt')
            stream.write('# -*- coding: UTF-8 -*-\n')
            qs = model.objects.all()
            stream.write(
                'logger.info("Loading %d objects to table %s...")\n' % (
                    qs.count(), model._meta.db_table))
            fields = [
                f for f, m in model._meta.get_fields_with_model()
                if m is None]
            fields = [
                f for f in fields
                if not getattr(f, '_lino_babel_field', False)]
            stream.write(
                "# fields: %s\n" % ', '.join(
                    [f.name for f in fields]))
            for obj in qs:
                self.count_objects += 1
                #~ used_models.add(model)
                stream.write('loader.save(create_%s(%s))\n' % (
                    obj._meta.db_table,
                    ','.join([self.value2string(obj, f) for f in fields])))
            stream.write('\n')
            stream.write('loader.flush_deferred_objects()\n')
            stream.close()

            #~ self.stream.write('\nfilename = os.path.join(os.path.dirname(__file__),"%s.py")\n' % )
            self.stream.write('    execfile("%s.py")\n' % model._meta.db_table)

        self.stream.write(
            '    loader.finalize()\n')
        # self.stream.write(
        #     '    logger.info("Loaded %d objects",loader.count_objects)\n')
        self.stream.write("""
if __name__ == '__main__':
    main()
""")
        #~ self.stream.write('\nsettings.SITE.load_from_file(globals())\n')
        self.stream.close()

    def sort_models(self, unsorted):
        sorted = []
        hope = True
        """
        20121120 if we convert the list to a set, we gain some performance 
        for the ``in`` tests, but we obtain a random sorting order for all 
        independent models, making the double dump test less evident.
        """
        #~ 20121120 unsorted = set(unsorted)
        while len(unsorted) and hope:
            hope = False
            guilty = dict()
            #~ print "hope for", [m.__name__ for m in unsorted]
            for model in unsorted:
                deps = set([f.rel.to
                            for f in model._meta.fields
                            if f.rel is not None and f.rel.to is not model and f.rel.to in unsorted])
                #~ deps += [m for m in model._meta.parents.keys()]
                for m in sorted:
                    if m in deps:
                        deps.remove(m)
                if len(deps):
                    guilty[model] = deps
                else:
                    sorted.append(model)
                    unsorted.remove(model)
                    hope = True
                    break

                #~ ok = True
                #~ for d in deps:
                    #~ if d in unsorted:
                        #~ ok = False
                #~ if ok:
                    #~ sorted.append(model)
                    #~ unsorted.remove(model)
                    #~ hope = True
                    #~ break
                #~ else:
                    #~ guilty[model] = deps
                #~ print model.__name__, "depends on", [m.__name__ for m in deps]
        if unsorted:
            assert len(unsorted) == len(guilty)
            msg = "There are %d models with circular dependencies :\n" % len(
                unsorted)
            msg += "- " + '\n- '.join([
                full_model_name(m) + ' (depends on %s)' % ", ".join([
                    full_model_name(d) for d in deps])
                for m, deps in guilty.items()])
            if False:
                # we don't write them to the .py file because they are
                # in random order which would cause false ddt to fail
                for ln in msg.splitlines():
                    self.stream.write('\n# %s' % ln)
            logger.info(msg)
            sorted.extend(unsorted)
        return sorted

    def value2string(self, obj, field):
        if isinstance(field, (BabelCharField, BabelTextField)):
            #~ return repr([repr(x) for x in dbutils.field2args(obj,field.name)])
            return repr(settings.SITE.field2args(obj, field.name))
        value = field._get_val_from_obj(obj)
        # Protected types (i.e., primitives like None, numbers, dates,
        # and Decimals) are passed through as is. All other values are
        # converted to string first.
        if value is None:
        #~ if value is None or value is NOT_PROVIDED:
            return 'None'
        if isinstance(field, models.DateTimeField):
            d = value
            return 'dt(%d,%d,%d,%d,%d,%d)' % (
                d.year, d.month, d.day, d.hour, d.minute, d.second)
        if isinstance(field, models.TimeField):
            d = value
            return 'time(%d,%d,%d)' % (d.hour, d.minute, d.second)
        if isinstance(field, models.ForeignKey) and field.rel.to is ContentType:
            ct = ContentType.objects.get(pk=value)
            return full_model_name(ct.model_class(), '_')
            #~ return "'"+full_model_name(ct.model_class())+"'"
            #~ return repr(tuple(value.app_label,value.model))
        if isinstance(field, models.DateField):
            d = value
            return 'date(%d,%d,%d)' % (d.year, d.month, d.day)
            #~ return 'i2d(%4d%02d%02d)' % (d.year,d.month,d.day)
        if isinstance(value, (float, Decimal)):
            return repr(str(value))
        if isinstance(value, (int, long)):
            return str(value)
        return repr(field.value_to_string(obj))

    def handle(self, *args, **options):
        if len(args) != 1:
            raise CommandError("No output_dir specified.")

        self.output_dir = os.path.abspath(args[0])
        self.main_file = os.path.join(self.output_dir, 'restore.py')
        self.count_objects = 0
        if os.path.exists(self.output_dir):
            raise CommandError(
                "Specified output_dir %s already exists. "
                "Delete it yourself if you dare!" % self.output_dir)

        os.makedirs(self.output_dir)

        self.options = options

        #~ logger.info("Running %s to %s.", self, self.output_dir)
        self.write_files()
        logger.info("Wrote %s objects to %s and siblings.",
                    self.count_objects, self.main_file)
