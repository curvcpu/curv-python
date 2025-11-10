from collections import Counter

class StrListWithMostCommon(list[str]):
    """
    A list of strings that, when asked to render itself as a string, will return the most common string in the list.

    Examples:
        strs = StrListWithMostCommon(["abc", " ", "\t", " "], default_str="xxx")
        print(strs) # prints " " because that's the most common string in the list
        
        strs = StrListWithMostCommon([], default_str="xxx")
        print(indent_strs) # prints "xxx" because the list is empty
    """
    def __init__(self, strs:list[str] = None, default_str:str = ""):
        """
        Initialize the list with the given strings, which can be None or an empty list.

        Args:
            strs: a list of strings to initialize the list with (ok if None or an empty list)
            default_str: the string to render as if the list is empty (default: "").

        Returns:
            None
        """
        super().__init__(strs if strs is not None else [])
        self.default_str = default_str
    def _get_most_common_str(self) -> str:
        # .most_common(1) returns a list like [(" ", 3)]; [0[0] returns the string itself
        return Counter(self).most_common(1)[0][0] if len(self) > 0 else self.default_str
    def __str__(self) -> str:
        return self._get_most_common_str()
