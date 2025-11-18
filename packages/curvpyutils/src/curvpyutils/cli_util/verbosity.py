import argparse
from typing import Optional, Literal

class VerbosityActionGroupFactory:
    """
    Factory for creating a verbosity action group with --quiet/-q, --verbose/-v, and --debug/-d flags.

    Use like this:

    ```python
    from curvpyutils.cli_util import VerbosityActionGroupFactory

    parser = argparse.ArgumentParser(...)
    VerbosityActionGroupFactory(
        parser, 
        quiet_flags=['--quiet', '-q'], 
        verbose_flags=['--verbose', '-v'], 
        debug_flags=['--debug', '-d'], 
        MAX_VERBOSITY=3
    ).add_verbosity_group("verbosity", "verbose")
    ```

    This will add a verbosity group to the parser with the following flags:
      --quiet/-q: suppress all output
      --verbose/-v: print verbose output (up to 3 times)
      --debug/-d: equivalent to -vvv

    The verbosity level is stored in the parser's namespace as the "verbosity" attribute.
    We also store a "verbose" boolean attribute that is True for any verbosity level greater than 0.
    The maximum verbosity level is 3.
    """
    def __init__(
            self, 
            parser: argparse.ArgumentParser,
            quiet_flags: Optional[list[str]] = ['--quiet', '-q'], 
            verbose_flags: Optional[list[str]] = ['--verbose', '-v'], 
            debug_flags: Optional[list[str]] = ['--debug', '-d'], 
            MAX_VERBOSITY: int = 3
        ):
        """
        Args:
            parser (argparse.ArgumentParser): the argument parser to add the verbosity action group to
            quiet_flags (list[str]): the flags for the quiet verbosity level; if None then there is no quiet option
            verbose_flags (list[str]): the flags for the verbose verbosity level; if None then there is no verbose option
            debug_flags (list[str]): the flags for the debug verbosity level; if None then there is no debug option    
            MAX_VERBOSITY (int): the maximum verbosity level
        """
        self.parser = parser
        self.saw_debug = False
        self.saw_verbose = False
        self.saw_quiet = False
        self.flags: dict[str, list[str]] = {
            'QUIET': quiet_flags,
            'VERBOSE': verbose_flags,
            'DEBUG': debug_flags,
        }
        self.MAX_VERBOSITY: int = MAX_VERBOSITY
    def _has_flag_type(self, flag_type: Literal['QUIET', 'VERBOSE', 'DEBUG']) -> bool:
        """
        Check if we have the given flag type defined.

        Args:
            flag_type: the type of flag to check ("QUIET", "VERBOSE" or "DEBUG")

        Returns:
            True if the given flag type is defined, False otherwise
        """
        return self.flags[flag_type] is not None and len(self.flags[flag_type]) > 0
    def make_verbosity_action(self, dest_name: str = "verbosity", bool_dest_name: str = "verbose") -> type[argparse.Action]:
        """
        Make a verbosity action.

        Args:
            dest_name (str): the name of the argument to store the verbosity level in
            bool_dest_name (str): the name of the argument to store the verbose boolean in;
                this will be set to True if the verbosity level is greater than 0
        """
        if bool_dest_name is None or len(bool_dest_name) == 0:
            bool_dest_name = "verbose"
        parent = self
        class VerbosityAction(argparse.Action):
            def __init__(self, option_strings, dest, nargs=None, **kwargs):
                super().__init__(option_strings, dest, nargs=0, **kwargs)
            def __call__(self, parser, namespace, values, option_string):
                if (parent._has_flag_type('DEBUG')) and (option_string in parent.flags['DEBUG']):
                    parent.saw_debug = True
                    if parent.saw_quiet:
                        raise argparse.ArgumentError(self, "cannot use with --quiet/-q")
                    setattr(namespace, self.dest, parent.MAX_VERBOSITY) # maximum verbosity
                    setattr(namespace, bool_dest_name, True)
                elif (parent._has_flag_type('VERBOSE')) and (option_string in parent.flags['VERBOSE']):
                    parent.saw_verbose = True
                    if parent.saw_quiet:
                        raise argparse.ArgumentError(self, "cannot use with --quiet/-q")
                    # increment the verbosity level
                    new_verbosity = min((getattr(namespace, self.dest, 0)+1), parent.MAX_VERBOSITY)
                    setattr(namespace, self.dest, new_verbosity)
                    setattr(namespace, bool_dest_name, True)
                elif (parent._has_flag_type('QUIET')) and (option_string in parent.flags['QUIET']):
                    parent.saw_quiet = True
                    if parent.saw_debug:
                        raise argparse.ArgumentError(self, "cannot use with --debug/-d")
                    if parent.saw_verbose:
                        raise argparse.ArgumentError(self, "cannot use with --verbose/-v")
                    # suppress all output
                    setattr(namespace, self.dest, -1)
                    setattr(namespace, bool_dest_name, False)
                else:
                    raise argparse.ArgumentError(self, f"Invalid verbosity option: {option_string}")
        return VerbosityAction
    def add_verbosity_group(self, dest_name: str = "verbosity", bool_dest_name: str = "verbose") -> None:
        """
        Add a verbosity action group to the parser.

        Args:
            dest_name (str): the name of the args attribute to store the verbosity level in
            bool_dest_name (str): the name of the args attribute to store the verbose boolean in;
                this will be set to True if the verbosity level is greater than 0
        """
        verbosity_action = self.make_verbosity_action(dest_name, bool_dest_name)
        verbosity_group = self.parser.add_argument_group("verbosity")
        if self._has_flag_type('VERBOSE'):
            verbosity_group.add_argument(*self.flags['VERBOSE'], dest=dest_name, action=verbosity_action, help="print verbose output (up to 3 times)")
        if self._has_flag_type('DEBUG'):
            verbosity_group.add_argument(*self.flags['DEBUG'], dest=dest_name, action=verbosity_action, help="equivalent to -vvv")
        if self._has_flag_type('QUIET'):
            verbosity_group.add_argument(*self.flags['QUIET'], dest=dest_name, action=verbosity_action, help="suppress all output")

        defaults_dict = {dest_name: 0}
        if bool_dest_name is not None and len(bool_dest_name) > 0:
            defaults_dict[bool_dest_name] = False
        self.parser.set_defaults(**defaults_dict)
