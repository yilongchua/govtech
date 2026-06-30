# Section 1 Question 1: Analysis Approach

## Problem Framing

The question asks whether the HDB Resale Portal, launched in January 2018, reduced the business opportunity for property agents in registered HDB resale transactions.

The strongest public-facing framing is not "Did agents disappear?" but:

> After self-service resale transactions became easier, what share of HDB resale buyer/seller sides continued to use agents?

## Data Sources

- `data/cea_salespersons_property_transaction_records_residential.csv`
  - Official CEA salesperson residential transaction records.
  - Counts CEA salesperson-side records.
  - For this question, filter to `property_type == HDB`, `transaction_type == RESALE`, and `represented` in `BUYER` or `SELLER`.

- `data/resale_flat_prices_2017_onwards.csv`
  - Official HDB resale flat transactions from January 2017 onwards.
  - Counts registered HDB resale transactions.

## Key Measurement Issue

The two datasets do not count the same unit.

HDB resale data counts one registered resale transaction. CEA data counts salesperson-side records. A single registered HDB resale transaction can have:

- zero CEA rows if no agent was used,
- one CEA row if only buyer or seller used an agent,
- two CEA rows if both buyer and seller used agents.

Because there is no shared transaction ID, the defensible headline metric is:

```text
agent-side record rate = CEA HDB resale buyer/seller salesperson-side records / (2 * registered HDB resale transactions)
```

This measures the share of possible buyer/seller sides represented by agents.

## Recommended Storyline

1. Establish the pre-portal baseline using 2017.
2. Plot monthly agent-side penetration from 2017 onward and annotate January 2018.
3. Compare annual resale-market volume against annual agent-side volume.
4. Estimate business impact as the gap between observed agent sides and expected agent sides if the 2017 penetration rate had continued.
5. Split buyer-side and seller-side penetration to see where self-service may have changed behaviour.
6. Add town-level comparisons to make the story concrete for general readers.

## Caveats

- This estimates transaction opportunities, not exact commission revenue.
- The CEA dataset contains salesperson-side records, not unique deals.
- Commission impact would require assumptions about commission rates and resale prices.
- Broader housing-market changes after 2018 may also affect agent volume, so the portal should be interpreted as a key event, not the only causal factor.

The notebook in `section_1_question_1_hdb_agent_impact.ipynb` implements the download and first-pass analysis workflow.
