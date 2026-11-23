# ACME Bank — candidate OPA/Rego policy engine

Source: `ACME_Bank_Wealth_Management_Policy.pdf`, WM-DOA-001 v1.0, effective 2026-11-01. Companion `ACME_Bank_Policy_Owner_Reference.pdf` used **only** to flag ambiguity and design tests; it is not an approved amendment.

**Status: draft, unadjudicated, fictional demonstration. Do not deploy for real banking decisions.**

## Invocation

OPA v1 Rego entry point: `data.acme.wealth.result`. Example:

```bash
opa eval -f pretty -d wealth_policy.rego -i example_input.json 'data.acme.wealth.result'
```

The engine returns `ALLOW`, `REQUIRE_APPROVAL`, `HOLD`, or `DENY`. Only `ALLOW` permits execution. `required_approvals` includes every applicable independent gate; `missing_approvals` lists those not verified. A `DENY` does not mean a user cannot submit a new request after an authorized policy exception; it means the current request is not executable.

## Input contract

The input is a JSON object. Required core fields: `policy_version`, `action`, `requester_id`, `amount_usd`, `aggregate_amount_usd`, `approvals`, `required_data_fresh_and_complete`, `audit_evidence_ready`. Money is USD and percentages use percentage points. All relevant facts must be computed by trusted services, **not supplied by the requesting AI agent**. For transfers, trusted services supply `daily_external_total_usd` including the proposed payment and `aggregation_24h_verified`. For fee concessions, supply `concession_90d_aggregation_verified`. For transactions, `client_instruction_valid`, `sanctions_screening_clear`, and other action-specific flags must be supplied. See source code for all predicates.

Approvals: `[{"role":"L2","actor_id":"manager-12","valid":true,"beneficiary":false,"initiator":false}]`. `valid` must be computed after verifying role/delegation, employee status, signature, scope, expiry, change fingerprint, and segregation of duties. `Operations` in the approval array represents a verified independent operations gate. `operations_release_verified` is a distinct *final release* fact; neither can be self-asserted.

Exceptions: `[{"kind":"daily_external_cap","valid":true,"policy_version":"1.0"}]`. This is a trusted verification of a fully signed, scoped, time-bound committee exception, not an override boolean supplied by a requester.

**Production-hardening gap:** This demonstration evaluates preverified facts and is not a full identity, evidence, authority, aggregation, calendar, exception or payment-execution system. In particular, `required_data_fresh_and_complete=true` must only be issued after a schema-based completeness and freshness check; otherwise the optional-default fields in the example implementation could under-enforce. Use strict JSON-schema validation and typed evidence before calling OPA.

## Interpretation decisions required before production

1. **AMB-01 / G-02:** Define exact relatedness, aggregation keys and 24-hour window; use `aggregate_amount_usd` only from approved aggregation service.
2. **AMB-02 / G-03:** Define material changes, business-day calendar and approval validity fingerprint.
3. **AMB-03 / I-05:** Define tax-sensitive classification and specialist-routing criteria.
4. **AMB-04 / M-05:** Define versioned jurisdiction-risk lists and sanctions-screening lifecycle.
5. **AMB-05 / M-04:** Define documented business-purpose taxonomy and minimum evidence.
6. **AMB-06 / O-05:** Define inactivity measurement and account events.
7. **AMB-07 / E-01:** Enumerate waivable rules and control owners.
8. **CON-01 / M-02 + M-06:** Apply per-payment and daily limits cumulatively (not a true contradiction).
9. **CON-02 / M-03 + E-02:** Urgent new destinations conservatively require both expedited cooling-off (Operations+Fraud) and emergency (L2+Operations) controls.
10. **CON-03 / I-04 + E-01:** Committee identity and exception signatures must be clarified; draft assumes trusted `issuer_concentration` exception.
11. **CON-04 / F-01 + F-03:** Define how to convert repeated discounts into 90-day delegated-authority tiers. Current draft **holds** when aggregation unverified but does not automatically tier on aggregate discounts.

## Important limits / further work

- Management escalation is modeled as **the named level** (e.g., L2), not cumulative L1+L2. Independent gates always accumulate. Confirm with policy owner.
- `M-05` international wires are a distinct action. Real international third-party wires or first-time destinations must be **multi-classified** so M-03/M-04/M-05/M-06 all apply; current demo supports shared flags for M-03 and M-06 but does not automatically apply M-04 to international wires. Extend the input to `transaction_tags` and evaluate all matching rules before deployment.
- `I-04` concentration checks apply to all modeled investment actions, but the upstream service must provide post-trade concentration; absent facts must fail the upstream schema check.
- `O-03` Legal approval is a conservative stand-in for 'Legal or approved specialist verification'; approved specialist equivalence requires adjudication.
- `C-01` active risk flags remain HOLD until a **separate authenticated investigation-resolution event** clears them; Fraud approval alone never lifts an active hold.
- `A-02` is a periodic monitoring obligation, not a per-request gate.
- `E-01` cannot be implemented safely as a generic blanket override. Only the two explicitly scoped hard-cap exceptions are recognized here, and an independent exception-governance workflow is required.
- `C-02` Operations release is modeled as a gate plus separate final-release fact, which may require a two-phase decision: authorization to release, then confirmation of release. Do not create a circular execution dependency.
- External money movement ownership, verification and sanctions requirements must be validated in a dedicated orchestration layer for every payment subtype.

## Source mapping

All 34 labeled source rules are represented in `wealth_policy.rego` as a gate, prohibition, hold, evidence obligation or a combination. The mapping is detailed in `rule_inventory.csv`.
