from typing import Union, Tuple

################################################################################
#
# Types
#
################################################################################

# The result type returned by the individual workers
ResultType = Union[Tuple[str, float], Exception]

# The result type returned by the GhDualWorker's get_results() method
#  - first str is the run JSON
#  - second str is the jobs JSON
#  - the floag is the offset in seconds since the later of the two fetches completed
# If either worker returns an exception, then that is the entire return value of get_results().
# If both raise exceptions, it is arbitrary which exception is returned.
CombinedResultType = Union[Tuple[str, str, float], Exception]
