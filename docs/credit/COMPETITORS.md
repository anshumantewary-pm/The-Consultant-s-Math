# CreditDecision: competitor feature map

Research date: 21 November 2026. Sources are listed at the end. Most capability statements come from vendor marketing pages and press releases, so they are **claims, not verified product tests**. A blank cell means the research did not find evidence of the capability, not that the vendor lacks it.

## Who we looked at

| Vendor | Product | Type | Where it plays |
|---|---|---|---|
| nCino | Credit Analysis Suite, Automated Spreading, Banking Advisor (GenAI) | Loan origination platform (Salesforce-based) | Origination → underwriting → portfolio monitoring |
| Moody's | Lending Suite (incl. CreditLens), Early Warning | Credit risk platform + data | Spreading, scoring (PD/LGD), monitoring, early warning |
| S&P Global Market Intelligence | Credit Memo Builder (launched 4 Jun 2026), RiskGauge, Credit Analytics | Data + agentic AI memo tool | Memo drafting on S&P data; PD/LGD models on 400M+ entities |
| TD Bank U.S. | TD Credit Assist (in-house) | Bank-built AI tool | Memo prep from 3 days to under 30 minutes; 10,000+ reviews a year |
| Finastra | Loan IQ (+ VeriLoan origination, Loan IQ Nexus/Build) | Corporate and syndicated loan servicing | Servicing, billing and collections; origination via VeriLoan |
| Baker Hill | NextGen | Origination + portfolio risk | Commercial and small-business lending |
| Aloan | AI-native underwriting | Startup | Documents → policy-configured memo with figures traced to source; covenant monitoring |
| CarbonAI | AI agents for CRE lending | Startup ($12M, Cowboy Ventures) | Underwriting, due diligence, investment memo, loan monitoring |
| Accend, EnFi | AI underwriting agents | Startups | Commercial credit workflow automation |
| Taktile | Decisioning platform | Decision engine | Agentic AI across commercial credit, including memo drafting |
| Newgen | Loan Collections Management | Collections | AI risk prioritisation for commercial collections |
| Botminds | Watchlist and Early Warning Intelligence | Monitoring | Deterioration signals into governed watchlist workflows |
| Biz2X | Loan Portfolio Monitoring | Monitoring | Real-time early warning signs |
| Linedata | Monitoring module | Monitoring | Risk triggers by portfolio subset, ranked by severity |

## Feature matrix

● = vendor claims it, from the sources below. ◐ = partial or adjacent. CreditDecision column: ✅ built in this repo, 🟡 partial, 🔲 planned.

| Capability | nCino | Moody's | S&P | Finastra | Aloan | CarbonAI | Taktile | Newgen / Botminds / Biz2X / Linedata | **CreditDecision** |
|---|---|---|---|---|---|---|---|---|---|
| Statement spreading (OCR) | ● | ● | | | ● | ● | | | 🔲 |
| Ratio and trend analysis | ● | ● | ● | | ● | ● | | | ✅ |
| Pro forma for the new facility | | | | | | | | | ✅ |
| Debt capacity (leverage / DSCR headroom) | | | | | | | | | ✅ |
| PD / internal rating | | ● | ● | | | | | | ✅ |
| LGD and collateral haircuts | | ● | ● | | | | | | ✅ |
| Regulatory capital (IRB RWA) | | | | | | | | | ✅ |
| RAROC and hurdle-margin solve | | | | | | | | | ✅ |
| Policy checks and exception register | | | | | ● (policy-configured) | | ◐ | | ✅ |
| Automated decision recommendation | | | | | | | ◐ | | ✅ |
| Approval authority routing | | | | | | | | | ✅ |
| Covenant design with headroom | | | | | | | | | ✅ |
| Credit memo generation | ● | ● | ● | | ● | ● | ● | | ✅ (deterministic) |
| Figures traced to source | | | ● (inline citations) | | ● | | | | 🟡 (traced to formulas; source documents planned) |
| GenAI narrative / Q&A on documents | ● | ● | ● | | ● | ● | ● | | 🔲 |
| Configurable memo template | ● | | ● | | ● | | | | 🟡 (fixed 12 sections) |
| Covenant monitoring | ● | ● | | | ● | ● | | ◐ | ✅ |
| Early-warning signals | ● | ● | | | | ● | | ● | ✅ |
| Watchlist workflow | | | | | | | | ● | ✅ (strategy + playbook) |
| Re-rating and migration | | ● | | | | | | | ✅ |
| IFRS 9 staging and ECL | | | | | | | | | ✅ |
| US classification (Pass → Loss) | | | | | | | | | ✅ |
| RBI SMA / NPA buckets | | | | | | | | | ✅ |
| Collections and workout playbook | ● (integrated collections) | | | ● (billing and collections) | | | | ● | ✅ |
| Recovery estimate | | | | | | | | | ✅ |
| Loan servicing and billing | | | | ● | | | | | 🔲 (out of scope; integrate) |
| Syndicated loans | | | | ● | | | | | 🔲 |
| External data (ratings, market) | | ● | ● | | | | | | 🔲 |
| Open API | | ● (REST) | | ● (open APIs) | | | | | ✅ (JSON CLI / library) |

## What the map says

1. **Memo drafting is now table stakes.** nCino, Moody's, S&P, Aloan, CarbonAI, Taktile and TD's in-house tool all draft memos. Competing on "we also write the memo" is not a position.
2. **Trust is the open problem.** BCG warns against treating agentic credit as a drafting tool; nCino says fragmented data moves manual work around instead of removing it. The products that stand out (S&P, Aloan) lead with **citations and traceability**. CreditDecision goes further: the numbers are computed by documented formulas and the memo is rendered from them, so there is nothing to hallucinate.
3. **Decision economics are missing from the memo tools.** None of the memo products in the research claim RAROC, IRB capital, a hurdle-margin solve or approval routing. These decide whether a bank *should* lend at the price offered, and they sit in separate pricing tools today.
4. **Origination and collections are separate products.** Monitoring and collections vendors (Newgen, Botminds, Biz2X, Linedata) do not originate; origination suites bolt monitoring on. CreditDecision uses one scorecard, one LGD model and one set of covenants from approval to recovery, and adds IFRS 9, US classification and RBI SMA staging in the same output.

## Positioning

> **CreditDecision: borrower in, decision and memo out, and the same engine all the way to recovery.** Every number is computed, every threshold is policy config, and the credit memo cannot disagree with the decision.

Gaps to close to be credible against the suites: document spreading, an LLM narrative layer with citations, configurable templates, workflow and audit, external data. See [feature-tracker.csv](feature-tracker.csv).

## Sources

- Moody's, [Future of credit assessment](https://www.moodys.com/web/en/us/insights/banking/future-of-credit-assessment-turning-information-into-better-lending-decisions.html); [Credit memo white paper, Sep 2026](https://www.moodys.com/web/en/us/site-assets/moodys-credit-memo-white-paper-8Sep2026.pdf); [Spreading and scoring](https://www.moodys.com/web/en/us/solutions/lending/loan-origination/spreading-scoring.html); [Lending Suite](https://www.moodys.com/web/en/us/campaigns/lending-suite.html); [Early warning in action](https://www.moodys.com/web/en/us/insights/credit-risk/moodys-early-warning-in-action-knm.html); [Redefining loan monitoring](https://www.moodys.com/web/en/us/insights/lending/redefining-loan-monitoring.html)
- RFP.wiki, [Moody's Lending Suite review](https://www.rfp.wiki/financial-services-banking-fintech/commercial-loan-origination-solutions/moodys-lending-suite)
- nCino, [Credit Analysis Suite](https://www.ncino.com/solutions/credit-analysis); [Banking Advisor](https://www.ncino.com/en-US/banking-advisor); [Banking Advisor launch](https://www.ncino.com/news/ncino-deploying-banking-advisor-gen-ai-solution-drive-efficiency-financial-institutions); [Automated spreading](https://www.ncino.com/ja-JP/solutions/automated-spreading); [Relationship reviews and agentic AI](https://www.ncino.com/blog/commercial-relationship-reviews-two-days-agentic-ai); FinTech Global, [Commercial banking is now running two jobs](https://fintech.global/2026/07/03/ncino-commercial-banking-is-now-running-two-jobs/)
- S&P Global, [Credit Memo Builder launch, 4 Jun 2026](https://press.spglobal.com/2026-06-04-S-P-Global-Launches-Agentic-AI-Powered-Credit-Memo-Builder-TM-to-Streamline-Credit-Analysis); [Credit Memo Builder](https://www.spglobal.com/market-intelligence/en/solutions/products/credit-memo-builder); [Bank case study](https://www.spglobal.com/market-intelligence/en/news-insights/case-studies/a-bank-uses-ai-backed-by-trusted-data-to-quickly-and-reliably-produce-credit-memos); [RiskGauge and Credit Analytics coverage to 400M entities](https://press.spglobal.com/2025-03-03-S-P-Global-Market-Intelligence-expands-RiskGauge-and-Credit-Analytics-solutions-coverage-to-400-million-corporate-entities-including-U-S-private-entities?asPDF=1)
- FF News, [TD launches Credit Assist](https://ffnews.com/news/td-launches-credit-assist-turning-days-of-commercial-credit-work-into-minutesc-223d31f6)
- BCG, [Agentic AI in wholesale credit decisions](https://www.bcg.com/publications/2026/agentic-ai-wholesale-credit-decisions)
- Backbase, [AI in commercial banking](https://www.backbase.com/blog/ai-in-commercial-banking)
- Finastra, [Loan IQ](https://finastra.com/solutions/loan-iq); [Loan IQ solution overview](https://www.finastra.com/sites/default/files/file/2026-06/resource-loan-iq-solution-overview.pdf); [Corporate lending origination](https://finastra.com/solutions/lending/loan-origination)
- Addy, [Commercial lending software](https://addy.com/blog/commercial-lending-software); GetApp, [Commercial loan monitoring](https://www.getapp.com/finance-accounting-software/commercial-loan/f/monitoring/)
- Aloan, [FinovateFall 2026](https://finovate.com/videos/finovatefall-2026-aloan/); The Next Web, [CarbonAI raises $12M](https://thenextweb.com/news/carbonai-12m-cre-lending-agents); Y Combinator, [Accend](https://ycombinator.com/companies/accend); Finovate, [EnFi](https://finovate.com/?p=91609); Taktile, [AI agents in commercial credit underwriting](https://www.taktile.com/articles/ai-agents-commercial-credit-underwriting)
- Newgen, [Loan collections management](https://newgensoft.com/gb/solutions/industries/financial-institutions/commercial-banking/loan-collections-management); Botminds, [Watchlist early warning](https://botminds.ai/solutions/watchlist-early-warning-intelligence); Biz2X, [Loan portfolio monitoring](https://www.biz2x.com/loan-portfolio-monitoring); Linedata, [When annual portfolio reviews aren't enough](https://www.linedata.com/newsroom/thought-leadership/when-annual-portfolio-reviews-arent-enough); Abrigo, [early warning signs](https://abrigo.com/?p=59395)
