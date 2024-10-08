import json
from json.decoder import JSONDecodeError
import toml
from collections import OrderedDict
from pathlib import Path
from typing import Union

from .error import SpecificationError


class SlurmPipelineBase(object):
    """
    Read a pipeline execution specification or status.

    @param specification: Either a C{str} or C{Path} giving the name of a file
        containing a JSON or TOML execution specification, or a C{dict} holding a
        correctly formatted execution specification. A passed specification C{dict}
        is not modified. See ../README.md for the expected contents of the
        specification.
    """

    def __init__(self, specification: Union[str, Path, dict]) -> None:
        if isinstance(specification, (str, Path)):
            specification = self._loadSpecification(specification)
        self.checkSpecification(specification)
        self.specification = specification.copy()
        # Change the 'steps' key in the specification into an ordered dict.
        # keyed by specification step name, with values that are the passed
        # specification step dicts. This gives more convenient direct
        # access to steps by name. The original JSON specification file has
        # the steps in a list because order is important.
        self.specification["steps"] = OrderedDict(
            (step["name"], step) for step in self.specification["steps"]
        )

    @staticmethod
    def checkSpecification(specification: dict) -> None:
        """
        Check an execution specification is as expected.

        @param specification: A C{dict} containing an execution specification.
        @raise SpecificationError: if there is anything wrong with the
            specification.
        """
        stepNames = set()

        if not isinstance(specification, dict):
            raise SpecificationError("The specification must be a dict")

        if "steps" not in specification:
            raise SpecificationError(
                "The specification must have a top-level 'steps' key"
            )

        if not isinstance(specification["steps"], list):
            raise SpecificationError("The 'steps' key must be a list")

        for count, step in enumerate(specification["steps"], start=1):
            if not isinstance(step, dict):
                raise SpecificationError("Step %d is not a dictionary" % count)

            try:
                stepName = step["name"]
            except KeyError:
                raise SpecificationError("Step %d does not have a 'name' key" % count)

            if not isinstance(stepName, str):
                raise SpecificationError(
                    "The 'name' key in step %d is not a string" % count
                )

            if "script" not in step:
                raise SpecificationError(
                    "Step %d (%r) does not have a 'script' key" % (count, stepName)
                )

            if not isinstance(step["script"], str):
                raise SpecificationError(
                    "The 'script' key in step %d (%r) is not a string"
                    % (count, stepName)
                )

            if step["name"] in stepNames:
                raise SpecificationError(
                    "The name %r of step %d was already used in "
                    "an earlier step" % (stepName, count)
                )

            if "collect" in step and not step.get("dependencies"):
                raise SpecificationError(
                    "Step %d (%r) is a 'collect' step but does not have any "
                    "dependencies" % (count, stepName)
                )

            stepNames.add(stepName)

            if "dependencies" in step:
                dependencies = step["dependencies"]
                if not isinstance(dependencies, list):
                    raise SpecificationError(
                        "Step %d (%r) has a non-list 'dependencies' key"
                        % (count, stepName)
                    )

                # A step cannot depend on itself.
                if step["name"] in dependencies:
                    raise SpecificationError(
                        "Step %d (%r) depends itself" % (count, stepName)
                    )

                # All named dependencies must already have been specified.
                for dependency in dependencies:
                    if dependency not in stepNames:
                        raise SpecificationError(
                            "Step %d (%r) depends on a non-existent (or "
                            "not-yet-defined) step: %r" % (count, stepName, dependency)
                        )

        if "skip" in specification:
            if not isinstance(specification["skip"], list):
                raise SpecificationError("The 'skip' key must be a list")
            for stepName in specification["skip"]:
                if stepName not in stepNames:
                    raise SpecificationError(
                        "The 'skip' key mentions a non-existent step, '%s'" % stepName
                    )

    @staticmethod
    def _loadSpecification(specificationFile: Union[str, Path]) -> dict:
        """
        Load a JSON or TOML execution specification.

        @param specificationFile: A C{str} file name containing a JSON or TOML
            execution specification.
        @raise ValueError: If C{specificationFile} does not contain valid JSON or TOML.
        @return: The parsed specification as a C{dict}.
        """
        with open(specificationFile) as fp:
            try:
                return json.load(fp)
            except JSONDecodeError as e:
                jsonError = e

        with open(specificationFile) as fp:
            try:
                specification = toml.load(fp)
            except toml.decoder.TomlDecodeError as tomlError:
                raise ValueError(
                    f"Specification file {specificationFile!r} could not be "
                    f"parsed as JSON ({jsonError}) or TOML ({tomlError})."
                )
            else:
                # Allow the TOML specification to optionally use 'step' for each step
                # section, instead of 'steps'.
                if "step" in specification and "steps" not in specification:
                    specification["steps"] = specification["step"]
                    del specification["step"]

                return specification

    @staticmethod
    def specificationToJSON(specification: dict) -> str:
        """
        Produce a JSON string for a specification.

        @param specification: A specification C{dict}.
        @return: A C{str} giving C{specification} in JSON form.
        """
        specification = specification.copy()

        # Convert sets to lists and the steps ordered dictionary into a list.
        specification["skip"] = list(specification["skip"])
        steps = []
        for step in specification["steps"].values():
            tasks = step["tasks"]
            for taskName, jobIds in tasks.items():
                tasks[taskName] = list(sorted(jobIds))
            taskDependencies = step["taskDependencies"]
            for taskName, jobIds in taskDependencies.items():
                taskDependencies[taskName] = list(sorted(jobIds))
            steps.append(step)
        specification["steps"] = steps
        return json.dumps(
            specification, sort_keys=True, indent=2, separators=(",", ": ")
        )

    def finalSteps(self) -> set[str]:
        """
        Find the specification steps on which nothing depends. These are the
        the steps that must all finish before a specification has fully
        finished running.

        @return: A C{set} of C{str} step names.
        """
        # This implementation is slightly inefficient, but is easy to
        # understand. It would be faster to just gather all step names that
        # appear in any step dependency and then return the set of all step
        # names minus that set.
        steps = self.specification["steps"]
        result = set()
        for stepName in steps:
            for step in steps.values():
                try:
                    if stepName in step["dependencies"]:
                        break
                except KeyError:
                    pass
            else:
                result.add(stepName)

        return result
