# Section 1 Question 2: COE Quota and Price Elasticity

This folder contains the working materials for Section 1 Question 2.

## Files

- `../DS Case Study Prod - Section 1 Question 2.md`: Original prompt.
- `01_coe_quota_price_story.ipynb`: Reproducible notebook to download the COE datasets, prepare Category A/B data, model prices, estimate quota elasticity, and outline a public-facing data story.
- `data/coe_prices.csv`: COE bidding results and prices downloaded from data.gov.sg.
- `data/coe_quota.csv`: COE monthly quota dataset downloaded from data.gov.sg.
- `requirements.txt`: Python packages used by the notebook.

## Analytical Approach

The practical modeling unit is one COE bidding exercise for one vehicle category. For Category A and Category B, the price dataset already gives the needed exercise-level fields: month, bidding number, quota, successful bids, bids received, and premium.

The quota dataset is a supporting source. It contains a wider monthly history by data series, including quota, successful bids, bids received, and quota premium by bidding number. It is useful for validation and longer historical context, but the price dataset is the cleaner starting point for the 2010-2026 model.

The core hypothesis is that prices rise when quota is tight relative to demand. A quota-only model would be too thin because quota changes are partly policy-driven and demand is not directly controlled by LTA. The notebook therefore estimates:

1. descriptive trends in quota, bids, and premiums;
2. bid pressure as `bids_received / quota`;
3. lagged price and rolling demand-pressure features;
4. a log-price regression model for Category A and B;
5. quota elasticity from the fitted log-log relationship; and
6. scenario simulations showing the expected price impact of adding incremental certificates.

The public-facing story should lead with a simple narrative: COE prices are not just high because quotas are low; they are highest when quota supply is tight at the same time bidding pressure is elevated. The clearest charts are a dual trend chart, a bid-pressure scatterplot, a category comparison, and a small scenario table translating quota increases into estimated dollar impacts.
