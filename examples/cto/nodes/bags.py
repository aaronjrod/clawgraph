import os

from clawgraph import ClawBag

# Resolve skills directory relative to this file
SKILLS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "skills"))

clinical_reg_bag = ClawBag("clinical_regulatory", skills_dir=SKILLS_DIR)
cmc_reg_bag = ClawBag("cmc_regulatory", skills_dir=SKILLS_DIR)
clinical_ops_bag = ClawBag("clinical_ops", skills_dir=SKILLS_DIR)
reg_ops_bag = ClawBag("reg_ops", skills_dir=SKILLS_DIR)
strategy_labeling_bag = ClawBag("strategy_labeling", skills_dir=SKILLS_DIR)
marketing_bag = ClawBag("marketing", skills_dir=SKILLS_DIR)

all_bags = [
    clinical_reg_bag,
    cmc_reg_bag,
    clinical_ops_bag,
    reg_ops_bag,
    strategy_labeling_bag,
    marketing_bag,
]
