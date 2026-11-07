"""OS-independent conversion engine. Must not import Windows-specific modules."""

from clickmorph.core.context import RunContext
from clickmorph.core.joblog import JobLog, default_log_path
from clickmorph.core.jobs import Failure, JobResult, NotApplicableError, OutputError, run_job
from clickmorph.core.naming import atomic_write, output_name, reserve_output
from clickmorph.core.natsort import natural_key, natural_sorted
from clickmorph.core.operation import (
    Operation,
    Option,
    OptionError,
    OptionValue,
    RunFn,
    SelectionMode,
)
from clickmorph.core.registry import Registry, register, registry

__all__ = [
    "Failure",
    "JobLog",
    "JobResult",
    "NotApplicableError",
    "Operation",
    "Option",
    "OptionError",
    "OptionValue",
    "OutputError",
    "Registry",
    "RunContext",
    "RunFn",
    "SelectionMode",
    "atomic_write",
    "default_log_path",
    "natural_key",
    "natural_sorted",
    "output_name",
    "register",
    "registry",
    "reserve_output",
    "run_job",
]
