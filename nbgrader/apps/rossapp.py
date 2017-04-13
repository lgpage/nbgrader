import os
import re

from traitlets import List, default

from .baseapp import BaseNbConvertApp, nbconvert_aliases, nbconvert_flags
from ..api import Gradebook, MissingEntry
from ..ross import get_notebook_code
from ..ross import RossNode, RossNotebooks


aliases = {}
aliases.update(nbconvert_aliases)
aliases.update({
})

flags = {}
flags.update(nbconvert_flags)
flags.update({
})


class RossApp(BaseNbConvertApp):

    name = u'nbgrader-ross'
    description = u'Report On Submission Similarity (ROSS).'

    aliases = aliases
    flags = flags

    preprocessors = List([
    ])

    @property
    def _input_directory(self):
        return self.coursedir.autograded_directory

    @default("classes")
    def _classes_default(self):
        classes = super(RossApp, self)._classes_default()
        return classes

    def build_extra_config(self):
        extra_config = super(RossApp, self).build_extra_config()
        return extra_config

    def load_single_notebook_code(self, filename):
        regexp = re.escape(os.path.sep).join([
            self._format_source(
                "(?P<assignment_id>.*)", "(?P<student_id>.*)", escape=True),
            "(?P<notebook_id>.*).ipynb"
        ])

        m = re.match(regexp, filename)
        if m is None:
            self.fail(
                "Could not match '%s' with regexp '%s'", filename, regexp)
        gd = m.groupdict()
        node = RossNode(gd['student_id'], get_notebook_code(filename))
        return gd['notebook_id'], node

    def load_notebooks_code(self):
        regexp = self._format_source(
            "(?P<assignment_id>.*)", "(?P<student_id>.*)", escape=True)

        collection = dict()
        for assignment in sorted(self.assignments.keys()):
            m = re.match(regexp, assignment)
            if m is None:
                self.fail(
                    "Could not match '%s' with regexp '%s'", assignment, regexp)

            self.notebooks = sorted(self.assignments[assignment])
            for filename in self.notebooks:
                self.log.info("Loading notebook: {}".format(filename))
                notebook_id, node = self.load_single_notebook_code(filename)
                if notebook_id not in collection.keys():
                    collection[notebook_id] = RossNotebooks(notebook_id)
                collection[notebook_id].append(node)

        return collection

    def report_on_similarity(self, data):
        with Gradebook(self.coursedir.db_url) as gb:
            for notebook_id, collection in data.items():
                for comp in collection.comparisons:
                    nc = gb.update_or_create_notebook_comparison(
                        notebook_id,
                        self.assignment_id,
                        comp.student_ids,
                        **comp.metrics
                    )
                    self.log.info(
                        "Created/updated similarity metrics: {}".format(nc))

    def convert_notebooks(self):
        pass

    def start(self):
        data = self.load_notebooks_code()
        self.report_on_similarity(data)
        # super(RossApp, self).start()
