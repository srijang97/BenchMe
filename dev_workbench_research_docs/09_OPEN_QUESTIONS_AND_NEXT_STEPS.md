# Open Questions and Next Steps

## 1. What remains unresolved

### Customer-side unknowns
- How many teams would actually pay for benchmarking vs just reading vendor docs?
- Which buyer feels the pain most strongly: CTO, Eng manager, DevEx, agency owner, security lead?
- Is repo-specific benchmark the wedge, or is procurement audit easier to sell first?
- Is PR evidence a standalone product or just a feature?

### Product-side unknowns
- How automated can benchmark generation really become?
- How benchmarkable are realistic private repos?
- How much human curation is needed for useful benchmark tasks?
- Can we benchmark closed products fairly enough?
- Does routing need to come much later?

### GTM unknowns
- Which entry point closes fastest?
- Service first or software first?
- Open-source CLI or private benchmark SaaS first?
- Can agencies become early lighthouse customers?

## 2. Strongest next research to run

### A. Customer interviews
Even though this handoff focused on internet research, the next highest-value work is direct interviews:
- AI-native startup CTOs
- agency owners / leads
- platform / DevEx leaders
- engineers using Cursor / Claude / Codex heavily
- security/compliance stakeholders

### B. Benchmarkability audit on public repos
Build a tiny PoC that:
- ingests benchmark-friendly public repos
- scores benchmarkability
- runs a few workflow classes
- compares 2–4 tools/models
- outputs a report

### C. Procurement prototype
Create a mock deliverable:
- “Which AI dev tools should this team buy?”
- benchmark summary
- spend map
- workflow map
- verification risks
- tool recommendation

### D. PR evidence mock
Mock the evidence pack:
- what AI changed
- what it read
- what tests ran
- risk level
- review checklist
- model/tool provenance
- cost

Then test whether buyers find it compelling.

## 3. Recommended immediate sequence

### Step 1
Use these documents to continue research in another chat if needed.

### Step 2
Build a public-repo PoC:
- repo intelligence benchmark
- PR review benchmark
- verified code-edit benchmark
- cost + latency + success dashboard

### Step 3
Create a procurement-audit style output from the PoC.

### Step 4
Only after that, decide whether the first product is:
- benchmarkability audit
- benchmark SaaS
- procurement audit
- PR evidence
- observability dashboard
- routing later

## 4. Current likely best sequence

1. Benchmarkability audit
2. Repo benchmark
3. Procurement recommendation
4. Observability
5. PR evidence
6. Routing
7. Governance / enterprise layer

## 5. Strongest reasons to pursue

- Real public pain exists.
- Serious teams already use multiple AI tools.
- Pricing is getting more metered and complex.
- Verification debt is strong.
- Repo-specific evaluation is increasingly recognized as necessary.
- The full bundle is not clearly owned.

## 6. Strongest reasons to be careful

- Some adjacent players are already close.
- Enterprise trust and code access may slow adoption.
- Benchmark generation may be operationally hard.
- Buyers may prefer consulting-style audits before buying software.
- Routing alone may be too abstract to sell first.

## 7. What success would look like

A good next milestone would be:
- a public benchmarkability and bakeoff demo,
- a mock procurement report,
- and at least a few credible buyer conversations saying:
  “Can you run this on our repo?”
