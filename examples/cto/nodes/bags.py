from clawgraph import ClawBag

clinical_reg_bag = ClawBag("clinical_regulatory")
cmc_reg_bag = ClawBag("cmc_regulatory")
clinical_ops_bag = ClawBag("clinical_ops")
reg_ops_bag = ClawBag("reg_ops")
strategy_labeling_bag = ClawBag("strategy_labeling")
marketing_bag = ClawBag("marketing")

all_bags = [
    clinical_reg_bag,
    cmc_reg_bag,
    clinical_ops_bag,
    reg_ops_bag,
    strategy_labeling_bag,
    marketing_bag
]
