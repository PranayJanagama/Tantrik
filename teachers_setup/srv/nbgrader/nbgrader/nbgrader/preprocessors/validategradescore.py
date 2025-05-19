# /srv/nbgrader/nbgrader/nbgrader/preprocessors/validategradescore.py
"""
Note:- Total code updates are in /srv/nbgrader/nbgrader/nbgrader folder
1. import the ValidateTotalScore in preprocessors/__init__.py file and add in the list of preprocessors
2. import ValidateTotalScore in converters/generate_assignment.py
3. add ValidateTotalScore preprocessor after SaveCells in preprocessors list

"""
from . import NbGraderPreprocessor
from traitlets import Integer
from nbconvert.exporters.exporter import ResourcesDict
from nbformat.notebooknode import NotebookNode
from typing import Tuple

class ValidateTotalScore(NbGraderPreprocessor):
    expected_total = Integer(100, help="The expected total score for the notebook.").tag(config=True)

    def preprocess(self, nb: NotebookNode, resources: ResourcesDict) -> Tuple[NotebookNode, ResourcesDict]:
        assignment_name = resources['nbgrader']['assignment']

        # Skip validation for 'demo' or 'practice' assignments
        if any(word in assignment_name.lower() for word in ['demo', 'practice', 'ps1']):
            self.log.debug(f"⚠️ Skipping validation for assignment '{assignment_name}' because it is in skip list.")
            print(f"⚠️ Skipping validation for assignment '{assignment_name}'.")
            return nb, resources

        total_score = 0
        autograded_cells = 0

        for cell in nb.cells:
            metadata = cell.get('metadata', {})
            nbgrader_meta = metadata.get('nbgrader', {})

            if nbgrader_meta.get('grade', False):
                points = nbgrader_meta.get('points', 0)
                total_score += points
                autograded_cells += 1

        # Validate total score
        if total_score != self.expected_total:
            raise ValueError(
                f"❌ Validation Failed: Total autograde score is {total_score}, expected {self.expected_total}. "
                f"Detected {autograded_cells} autograded cells."
            )
        
        return nb, resources