# Why COE Prices Feel So Hot: A Data Story About Quota, Demand, and Bidding Pressure

![Cute cartoon cars waiting for limited COE certificates](assets/coe-cartoon-hero.png)

Singapore's COE system can feel like a very expensive game of musical chairs. Every bidding exercise, a fixed number of certificates is available. Buyers, dealers, and households decide how hard to bid. When the number of bidders rises faster than the number of certificates, prices can jump quickly.

This project looks at official COE bidding data from January 2010 to June 2026 and focuses on Category A and Category B. The goal is simple:

**Can we estimate how COE premiums move when quotas change, and can we translate that into plain examples?**

## The Short Answer

The data suggests that COE prices are not driven by quota alone. They are most strained when quota is tight and bidding pressure is high.

In the model, the most useful public-facing metric is:

```text
bid pressure = bids received / quota
```

If bid pressure is 1.40, that means 1.4 bids were received for every available certificate. More people are chasing each certificate, so the auction has more upward pressure.

For the latest bidding exercise in the dataset, June 2026 second bidding:

| Category | Quota | Bids received | Premium | Bid pressure |
|---|---:|---:|---:|---:|
| Category A | 1,251 | 1,768 | S$123,847 | 1.41 |
| Category B | 883 | 1,202 | S$123,502 | 1.36 |

## What the Model Does

The notebook builds a log-price regression model. In plain English, it predicts COE premium using:

- quota;
- bid pressure;
- previous bidding exercise premium;
- vehicle category;
- first or second bidding exercise in the month;
- post-COVID period indicator.

The target is the log of the COE premium. This is useful because coefficients can be interpreted as elasticities: percentage changes in inputs are linked to percentage changes in price.

The model was trained on bidding exercises before 2024 and tested on 2024 onward.

| Metric | Result |
|---|---:|
| Category A/B rows modelled | 780 |
| Training rows | 658 |
| Test rows | 120 |
| In-sample R-squared | 0.969 |
| Holdout MAE | S$3,955 |
| Holdout MAPE | 3.82% |

## The Key Idea: Quota Works Through Pressure

![Cute cartoon explainer showing quota elasticity](assets/coe-elasticity-cartoon.png)

There are two ways to talk about quota impact.

The first is a controlled model reading: if quota changes while bid pressure is held constant, the direct quota coefficient is small, about **-0.015**. That is a narrow statistical interpretation.

The more intuitive policy scenario is: what if the number of bids received stays similar, but more certificates are added? In that case, bid pressure falls because the same demand is spread across more certificates.

For this fixed-demand scenario, the estimated quota elasticity is about:

```text
-0.155
```

That means a 1% increase in quota is associated with an estimated 0.16% decrease in COE premium, assuming similar bidding demand.

This is not magic, and it is not a guarantee. It is a historical relationship from bidding data.

The important distinction is this:

| Interpretation | What it means | Why it matters |
|---|---|---|
| Direct quota effect | Quota changes while bid pressure is held constant | Useful for reading the regression coefficient, but less intuitive |
| Fixed-demand quota effect | Quota changes while bids received stay similar, so bid pressure changes | More useful for policy scenarios and public explanation |

For public communication, the second interpretation is clearer: if the same number of people are bidding but more certificates are available, the bidding room becomes less crowded.

## Scenario Walkthrough

Using June 2026 second bidding as the baseline, the model estimates the following impact if additional certificates were added and bids received stayed similar:

| Category | Extra certificates | Quota change | Estimated premium change | Estimated dollar change |
|---|---:|---:|---:|---:|
| Category A | 25 | +2.0% | -0.31% | -S$384 |
| Category A | 50 | +4.0% | -0.62% | -S$767 |
| Category A | 100 | +8.0% | -1.24% | -S$1,534 |
| Category A | 200 | +16.0% | -2.48% | -S$3,069 |
| Category B | 25 | +2.8% | -0.44% | -S$542 |
| Category B | 50 | +5.7% | -0.88% | -S$1,084 |
| Category B | 100 | +11.3% | -1.76% | -S$2,168 |
| Category B | 200 | +22.7% | -3.51% | -S$4,336 |

The pattern is important: the same number of extra certificates has a larger percentage effect in Category B because its baseline quota is smaller.

## Better Scenarios: What If Demand Also Changes?

Real markets do not sit still. If quota increases, some buyers may rush in because they think the next bidding round is a better opportunity. That can offset some of the price relief.

So a better management scenario varies both quota and demand. Using the same June 2026 baseline:

| Category | Quota change | Demand change | Estimated price change | Estimated premium |
|---|---:|---:|---:|---:|
| Category A | +5% | 0% | -0.75% | S$122,914 |
| Category A | +5% | +5% | -0.07% | S$123,756 |
| Category A | +10% | 0% | -1.47% | S$122,030 |
| Category A | +10% | +10% | -0.14% | S$123,669 |
| Category B | +5% | 0% | -0.75% | S$122,571 |
| Category B | +5% | +5% | -0.07% | S$123,411 |
| Category B | +10% | 0% | -1.47% | S$121,690 |
| Category B | +10% | +10% | -0.14% | S$123,325 |

This is the management insight: **quota increases help most when demand does not rise at the same time**.

## A Range Is More Honest Than One Number

The holdout model error is about **S$4,000 MAE**. That means the exact dollar estimate should not be read too literally.

For example, under a +10% quota and unchanged-demand scenario:

| Category | Central estimate | Approximate range using holdout MAE |
|---|---:|---:|
| Category A | S$122,030 | S$118,075 to S$125,985 |
| Category B | S$121,690 | S$117,735 to S$125,645 |

The range is not a formal statistical prediction interval. It is a practical reminder that the model supports scenario planning, not exact price promises.

## Category and Regime Differences

Category A and Category B should not always be treated as the same market.

Category A is closer to mass-market household demand. Category B includes larger and often more expensive vehicles, where buyers may be less price-sensitive. Category B also has a smaller baseline quota, so the same number of additional certificates can represent a larger percentage supply change.

Segment checks suggest this difference matters:

| Segment | Fixed-demand quota elasticity |
|---|---:|
| Category A only | -0.123 |
| Category B only | -0.200 |
| Pre-COVID regime | -0.150 |
| Post-COVID regime | -0.316 |

These segment estimates are directional, not definitive, because each segment has fewer observations. Still, they suggest that quota sensitivity may be stronger in Category B and in the post-COVID high-price regime.

## Why Prices Can Still Stay High

Even when quotas rise, premiums may not fall dramatically if demand rises at the same time. Buyers may rush in because they expect prices to climb later. Dealers may bid more aggressively. Economic conditions, loan rules, car prices, and substitution across COE categories can all affect the final premium.

That is why quota should not be treated as a single master switch. It is a pressure valve.

## Supplementary Demand Context

The model focuses on COE bidding data because quota, bids received, and premiums are the cleanest variables available at bidding-exercise level. Still, several external demand factors are useful when explaining why prices can remain high even when quota changes.

### China EVs, Tesla, and changing model mix

China-led EV price competition can affect COE demand by lowering the non-COE part of the car purchase. If the car itself becomes more affordable or attractive, more buyers may be willing to bid for the same fixed pool of certificates.

This is relevant in Singapore because EV adoption has become large enough to affect the market story. Business Times reported that EVs formed 57.6% of new car registrations in Q1 2026, with BYD accounting for 24.3% and Tesla 11.4% of all new car registrations. LTA has also adjusted the Category A EV power threshold to 110kW, which allows more mass-market EVs to compete in Category A.

For the model, this means recent residuals or post-2021 price pressure should not be read as quota-only effects. EV model mix, pricing, and brand competition are plausible demand-side explanations, especially for Category A.

Sources:

- [IEA Global EV Outlook 2025](https://www.iea.org/reports/global-ev-outlook-2025/trends-in-electric-car-markets-2)
- [LTA: Transitioning to Electric Vehicles](https://www.lta.gov.sg/content/ltagov/en/industry_innovations/technologies/electric_vehicles/transitioning_to_evs.html)
- [Business Times: EVs form about 60% of car registrations in Singapore](https://www.businesstimes.com.sg/singapore/evs-form-about-60-car-registrations-singapore-byd-accounts-nearly-1-4-new-cars)

### COVID changed the market regime

COVID is not just another year in the time series. LTA suspended COE bidding during the circuit breaker in April and May 2020, creating an operational break in the market.

There was also a behavioural channel. LTA ridership statistics show average daily public transport ridership fell sharply in 2020. That does not prove that households immediately switched to cars, but it supports treating 2020 and the post-COVID recovery as a distinct regime. IEA also noted that perceived infection risk could push people away from public transport and toward private modes after COVID.

For the model, this supports keeping 2020 and post-2020 indicators, and reviewing outliers around that period separately rather than treating them as normal volatility.

Sources:

- [LTA: ERP charging and COE bidding suspended during extended circuit breaker](https://www.lta.gov.sg/content/ltagov/en/newsroom/2020/4/news-releases/erp-charging-and-coe-bidding-continue-to-be-suspended-during-ext.html)
- [LTA: Public Transport Ridership statistics](https://www.lta.gov.sg/content/dam/ltagov/who_we_are/statistics_and_publications/statistics/pdf/PT_Ridership_Yearly_2015-2025.pdf)
- [IEA: Changes in transport behaviour during the COVID-19 crisis](https://www.iea.org/articles/changes-in-transport-behaviour-during-the-covid-19-crisis)

### Population growth is useful context, but not direct proof

Singapore's population reached 6.11 million in June 2025, up 1.2% from June 2024. This gives useful background for transport demand. However, the official population explanation says the increase was mainly due to non-resident growth, especially Work Permit holders and migrant domestic workers.

That matters for interpretation. Population growth may increase overall transport demand, but it should not be assumed to translate directly into higher private-car COE bidding. It is a supporting context variable, not a standalone explanation.

Source:

- [NPTD: Population Trends](https://www.population.gov.sg/our-population/population-trends/overall-population/)

### Wealth inflows and family offices may stiffen competition at the margin

Singapore's wealth-management ecosystem has grown quickly. MAS noted the rapid growth of single family offices, and Business Times reported that Singapore had more than 2,000 family offices by end-2024, nearly 10 times the level five years earlier.

This is relevant because wealthier buyers may be less price-sensitive, especially in Category B or luxury segments. However, this should be framed carefully. Family-office growth does not directly prove higher COE bidding unless it can be linked to vehicle registrations or bidding activity. It is best used as a plausible wealth-demand context, not as a quantified model driver.

Sources:

- [MAS: WMI Global-Asia Family Office Summit speech, 2025](https://www.mas.gov.sg/news/speeches/2025/speech-by-deputy-chairman-at-wmi-global-asia-family-office-summit-on-29-september-2025)
- [Business Times: Family-office foundations in Singapore](https://www.businesstimes.com.sg/companies-markets/whats-driving-surge-family-office-foundations-singapore-and-it-just-tax-perks)

### Fixed vehicle supply amplifies demand shifts

The reason these external demand factors matter is that Singapore's vehicle supply is tightly constrained. MOT states that since February 2018, the vehicle growth rate has been zero for all categories except Category C, and the zero-growth setting remains in place until 31 January 2028 for cars and motorcycles.

In a fixed-supply system, additional willingness to bid is more likely to appear in premiums than in vehicle counts. That is why demand-side context should sit beside quota analysis, even if the model itself remains focused on bidding data.

Source:

- [MOT: Vehicle Ownership](https://www.mot.gov.sg/what-we-do/motoring-road-network-and-infrastructure/vehicle-ownership/)

## How to Read the Result

The useful takeaway is not "add X certificates and price will definitely fall by Y dollars."

The better takeaway is:

**COE premiums respond to the balance between available certificates and bidding demand. Monitoring bid pressure gives a clearer early signal than quota alone.**

For policymakers, this model can support scenario planning. For the public, it gives a simpler way to understand why COE prices can feel volatile: every bidding exercise is a small market, and small changes in supply or demand can be amplified when pressure is already high.

## Caveats

This is an associative model, not a randomized policy experiment. It uses official historical bidding data and estimates relationships observed in the past. It does not fully capture buyer expectations, dealer strategies, macroeconomic shocks, vehicle technology shifts, Category E substitution, or future policy changes.

Still, it gives a practical starting point: explain COE movement through quota, demand, and pressure rather than quota alone.

## Future Improvements

There are three useful extensions, but they should not distract from the core bid-pressure story.

First, add external demand drivers such as interest rates, household income, car prices, fuel prices, loan rules, and private-hire or fleet demand. These could improve forecasting, but only if the data is reliable and aligned to bidding dates.

Second, use rolling time-series validation. Instead of one train/test split, the model could be tested year by year to see whether performance is stable across different market regimes.

Third, study residuals more deeply. The most useful question is not just whether the model is wrong, but when it is wrong. If it consistently underpredicts post-2021 spikes or performs worse for Category B, that would reveal a real market blind spot.

## Reproducibility

The analysis uses:

- `codes/data/coe_prices.csv`
- `codes/data/coe_quota.csv`
- `codes/01_coe_quota_price_story.ipynb`

Generated outputs, including generated cartoon images, are stored in `codes/outputs/`.
