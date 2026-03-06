"""
ClawGraph Expert Example: Clinical Trial Operations (CTO) Nodes package
Modules are split by domain for maintainability.
"""

from .bags import (
    clinical_reg_bag,
    cmc_reg_bag,
    clinical_ops_bag,
    reg_ops_bag,
    strategy_labeling_bag,
    marketing_bag,
    all_bags
)

from .clinical_reg import *
from .cmc_reg import *
from .clinical_ops import *
from .reg_ops import *
from .strategy import *
from .marketing import *

__all__ = [
    "clinical_reg_bag",
    "cmc_reg_bag",
    "clinical_ops_bag",
    "reg_ops_bag",
    "strategy_labeling_bag",
    "marketing_bag",
    "all_bags"
]
