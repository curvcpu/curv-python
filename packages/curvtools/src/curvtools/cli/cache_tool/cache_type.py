from enum import Enum

class CacheType(Enum):
    DCACHE = 0
    ICACHE = 1
    
    def __str__(self):
        return self.name.lower()
    def __repr__(self):
        return self.name.lower()
