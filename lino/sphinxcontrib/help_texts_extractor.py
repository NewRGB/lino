# -*- coding: UTF-8 -*-
# Copyright 2016-2019 Rumma & Ko Ltd
# License: BSD (see file COPYING for details)

'''
Causes one or several :xfile:`help_texts.py` files to be generated
after each complete build of the doctree.

See :doc:`/dev/help_texts` for a topic overview.

Usage
=====

In your :xfile:`conf.py` file, add
:mod:`lino.sphinxcontrib.help_texts_extractor` to your ``extensions``
and define a ``help_texts_builder_targets`` setting::

    extensions += ['lino.sphinxcontrib.help_texts_extractor']
    help_texts_builder_targets = {
        'lino_algus.': 'lino_algus.lib.algus'
    }
    

Internals
=========

This builder traverses the doctree in order to find `object
descriptions
<http://www.sphinx-doc.org/en/stable/extdev/nodes.html>`_, i.e.  text
nodes defined by Sphinx and inserted e.g. by the :rst:dir:`class` and
:rst:dir:`attribute` directives (which potentially have been inserted
by autodoc and autosummary).

Example of a class description::

    <desc desctype="class" domain="py" noindex="False" objtype="class">
        <desc_signature class="" first="False" fullname="Plan" ids="..." module="..." names="...">
        <desc_annotation>class </desc_annotation>
            <desc_addname>lino_xl.lib.invoicing.models.</desc_addname>
            <desc_name>Plan</desc_name>
            <desc_parameterlist>
                <desc_parameter>*args</desc_parameter>
                <desc_parameter>**kwargs</desc_parameter>
            </desc_parameterlist>
        </desc_signature>
        <desc_content>
            <paragraph>Bases: <reference internal="False" reftitle="(in Lino v1.7)" refuri="http://www.lino-framework.org/api/lino.modlib.users.mixins.html#lino.modlib.users.mixins.UserAuthored"><literal classes="xref py py-class">lino.modlib.users.mixins.UserAuthored</literal></reference>
            </paragraph>
            <paragraph>An <strong>invoicing plan</strong> is a rather temporary database object which represents the plan of a given user to have Lino generate a series of invoices.
            </paragraph>
            <index entries="..."/>
        <desc desctype="attribute" objtype="attribute">
            <desc_signature class="Plan" first="False" fullname="Plan.user" ids="..." module="..." names="...">
                <desc_name>user</desc_name>
            </desc_signature>
      <desc_content/>
    </desc>
    <desc desctype="attribute" ... objtype="attribute">
        <desc_signature class="Plan" first="False" fullname="Plan.journal" ids="..." module="..." names="...">
            <desc_name>journal</desc_name>
        </desc_signature>
        <desc_content>
            <paragraph>The journal where to create invoices.  When this field is
            empty, you can fill the plan with suggestions but cannot
            execute the plan.</paragraph>
        </desc_content>
    </desc>
    ...

Example of a field description::

    <desc desctype="attribute" domain="py" noindex="False" objtype="attribute">
      <desc_signature class="Plan" first="False" fullname="Plan.journal" 
            ids="lino_xl.lib.invoicing.models.Plan.journal" 
            module="lino_xl.lib.invoicing.models" 
            names="lino_xl.lib.invoicing.models.Plan.journal">
        <desc_name>journal</desc_name>
      </desc_signature>
      <desc_content>
        <paragraph>
          The journal where to create invoices.  When this field is
          empty, you can fill the plan with suggestions but cannot
          execute the plan.
        </paragraph>
      </desc_content>
    </desc>
'''

from __future__ import print_function
from __future__ import unicode_literals

from collections import OrderedDict

import six

from docutils import nodes
from docutils import core
from sphinx import addnodes
from sphinx.util import logging ; logger = logging.getLogger(__name__)

from importlib import import_module

from unipath import Path
from lino.core.utils import simplify_name

useless_starts = set(['lino.core'])
useless_endings = set(['.My', '.ByUser'])
# useless_endings = set(['.VentilatingTable', '.My', '.ByUser',
#                        '.Table', '.AbstractTable', '.VirtualTable',
#                        '.Actor'])

HEADER = """# -*- coding: UTF-8 -*-
# generated by lino.sphinxcontrib.help_text_builder
from __future__ import unicode_literals
from django.utils.translation import ugettext_lazy as _
"""


def node2html(node):
    parts = core.publish_from_doctree(node, writer_name="html")
    return parts['body']


class HelpTextExtractor(object):

    def initialize(self, app):
        self.name2dict = dict()
        self.name2file = dict()
        # we must write our files only when all documents have been
        # processed (i.e. usually after a "clean")
        self.docs_processed = 0
        
        targets = app.env.config.help_texts_builder_targets
        # print(20160725, targets)
        for root, modname in targets.items():
            mod = import_module(modname)
            htf = Path(mod.__file__).parent.child('help_texts.py')
            # if not htf.exists():
            #     raise Exception("No such file: {}".format(htf))
            self.name2file[root] = htf
            self.name2dict[root] = OrderedDict()
            
        print("Collecting help texts for {}".format(
            ' '.join(self.name2file.values())))

    def extract_help_texts(self, app, doctree):
        # if docname != 'api/lino_xl.lib.invoicing.models':
        #     return
        # print(doctree)
        # return

        # for node in doctree.traverse():
        #     self.node_classes.add(node.__class__)
        for node in doctree.traverse(addnodes.desc):
            if node['domain'] == 'py':
                if node['objtype'] == 'class':
                    self.store_content(node)
                elif node['objtype'] == 'attribute':
                    self.store_content(node)
                elif node['objtype'] == 'method':
                    self.store_content(node)
        # for node in doctree.traverse(nodes.field):
        #     self.fields.add(node.__class__)
        self.docs_processed += 1

    def write_help_texts_files(self, app, exception):
        if exception:
            return
        # found_docs also contains excluded files
        # print('20181004 found={}, all={}, processed={}'.format(
        #     len(app.env.found_docs), len(app.env.all_docs),
        #     self.docs_processed))
        if self.docs_processed < len(app.env.found_docs):
        # if self.docs_processed < len(app.env.all_docs):
            logger.info(
                "Don't write help_texts.py files because "
                "only {0} of {1} docs have been processed".format(
                    self.docs_processed,
                    len(app.env.found_docs)))
            return
        for k, fn in self.name2file.items():
            texts = self.name2dict.get(k, None)
            if not texts:
                logger.info("No help texts for {}".format(k))
                continue
            # fn = os.path.join(self.outdir, 'help_texts.py')
            print("Writing {} help texts for {} to {}".format(
                len(texts), k, fn))

            fd = open(fn, "w")

            def writeln(s):
                if six.PY2:
                    s = s.encode('utf-8')
                fd.write(s)
                fd.write("\n")

            writeln(HEADER)
            writeln("help_texts = {")
            for k, v in texts.items():
                writeln('''    '{}' : _("""{}"""),'''.format(k, v))
            writeln("}")
            fd.close()

    def store_content(self, node):
        sig = []
        content = []
        for c in node.children:
            if isinstance(c, addnodes.desc_content):
                for cc in c.children:
                    if isinstance(cc, nodes.paragraph):
                        p = cc.astext()
                        if not p.startswith("Bases:"):
                            if len(content) == 0:
                                content.append(p)
            elif isinstance(c, addnodes.desc_signature):
                sig.append(c)
        # if len(sig) != 1:
        #     raise Exception("sig is {}!".format(sig))
        sig = sig[0]
        # sig = list(node.traverse(addnodes.desc_signature))[0]
        # content = [
        #     p.astext() for p in node.traverse(addnodes.desc_content)]
        # content = [p for p in content if not p.startswith("Bases:")]
        if not content:
            return
        content = '\n'.join(content)
        if '"""' in content:
            msg = '{} : First paragraph of content may not contain \'"""\'. '
            raise Exception(msg.format(sig['names'][0]))
        if content.startswith('"'):
            content = " " + content
        if content.endswith('"'):
            content += " "
            # msg = '{} : First paragraph of content may not end with \'"\'.'
            # self.warn(msg.format(sig['names'][0]))
        for name in sig['names']:
            self.sig2dict(name, content)

    def sig2dict(self, name, value):
        for e in useless_starts:
            if name.startswith(e):
                return
        for e in useless_endings:
            if name.endswith(e):
                return
        name = simplify_name(name)
        for root, d in self.name2dict.items():
            if name.startswith(root):
                d[name] = value


def setup(app):
    hte = HelpTextExtractor()
    app.add_config_value('help_texts_builder_targets', {}, 'env')
    app.connect('builder-inited', hte.initialize)
    app.connect('doctree-read', hte.extract_help_texts)
    app.connect('build-finished', hte.write_help_texts_files)


