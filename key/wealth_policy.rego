package acme.wealth

import rego.v1
import future.keywords.or

# ACME WM-DOA-001 v1.0 — candidate implementation, NOT approved for production.
# Input contract and unresolved interpretations are documented in README.md.
# All monetary values are normalized USD; percentages are percentage points.

truth(k) if { object.get(input, k, false) == true }
value(k, dflt) := object.get(input, k, dflt)
amount := value("aggregate_amount_usd", value("amount_usd", 0))
action := value("action", "")

# Distinct approvers must have valid, active, unexpired delegations; an upstream
# identity/authority service MUST supply the verified approval facts.
approved(role) if {
    some a in value("approvals", [])
    a.role == role
    a.valid == true
    a.actor_id != value("requester_id", "")
    not a.beneficiary
    not a.initiator
}

has_exception(kind) if {
    some e in value("exceptions", [])
    e.kind == kind
    e.valid == true
    e.policy_version == "1.0"
}

cooling_off_expedited if { approved("Operations"); approved("Fraud"); truth("expedite_cooling_off") }

# Each atomic finding: {rule_id, kind: deny|hold|approval|evidence, detail, role?}.
# A HOLD is non-executable, even if approvals are otherwise complete.
findings contains {"rule_id": "G-01", "kind": "hold", "detail": "Authenticated instruction or active discretionary mandate required"} if {
    action in {"listed_order", "rebalance", "complex_order", "internal_transfer", "external_transfer", "third_party_payment", "international_wire"}
    not truth("client_instruction_valid")
    not truth("discretionary_mandate_valid")
}
findings contains {"rule_id": "G-01", "kind": "hold", "detail": "Verbal instruction evidence missing"} if { truth("instruction_verbal"); not truth("verbal_evidence_recorded") }
findings contains {"rule_id": "G-02", "kind": "hold", "detail": "24-hour related-transaction aggregation not verified"} if { action in {"listed_order", "internal_transfer", "external_transfer", "third_party_payment", "international_wire"}; not truth("aggregation_24h_verified") }
findings contains {"rule_id": "G-02", "kind": "deny", "detail": "Intentional threshold evasion/splitting"} if { truth("circumvention_confirmed") }
findings contains {"rule_id": "G-03", "kind": "hold", "detail": "Approval expired or material change requires reapproval"} if { truth("approval_stale_or_material_change") }
findings contains {"rule_id": "G-04", "kind": "deny", "detail": "Legal freeze, product prohibition, or failed identity"} if { truth("legal_prohibition") or truth("account_frozen") or truth("product_prohibited") or truth("identity_failed") }
findings contains {"rule_id": "G-04", "kind": "hold", "detail": "Unresolved sanctions alert"} if { truth("sanctions_alert") }

# Approval requirements accumulate across all applicable rules.
required contains {"rule_id": "I-01", "role": "L1"} if { action == "listed_order"; amount > 100000; amount <= 500000 }
required contains {"rule_id": "I-01", "role": "L2"} if { action == "listed_order"; amount > 500000; amount <= 2000000 }
required contains {"rule_id": "I-01", "role": "L3"} if { action == "listed_order"; amount > 2000000 }
required contains {"rule_id": "I-01", "role": "Risk"} if { action == "listed_order"; amount > 2000000 }
findings contains {"rule_id": "I-01", "kind": "hold", "detail": "Listed order suitability/funds/restrictions not verified"} if { action == "listed_order"; not truth("suitability_passed") or not truth("funds_available") or not truth("trading_restrictions_cleared") }

required contains {"rule_id": "I-02", "role": "L1"} if { action == "rebalance"; value("rebalance_pct", 0) > 5; value("rebalance_pct", 0) <= 10 }
required contains {"rule_id": "I-02", "role": "L2"} if { action == "rebalance"; value("rebalance_pct", 0) > 10 }
required contains {"rule_id": "I-02", "role": "Compliance"} if { action == "rebalance"; value("rebalance_pct", 0) > 10 }
findings contains {"rule_id": "I-02", "kind": "deny", "detail": "Outside signed discretionary mandate"} if { action == "rebalance"; not truth("mandate_and_model_valid") }

required contains {"rule_id": "I-03", "role": "Compliance"} if { action in {"complex_order", "listed_order"}; truth("complex_or_restricted_product") }
findings contains {"rule_id": "I-03", "kind": "hold", "detail": "Product eligibility not documented"} if { truth("complex_or_restricted_product"); not truth("product_eligible") }
findings contains {"rule_id": "I-03", "kind": "deny", "detail": "Restricted security not released"} if { truth("restricted_security"); not truth("restriction_lifted_by_compliance") }

required contains {"rule_id": "I-04", "role": "Risk"} if { action in {"listed_order", "complex_order", "rebalance"}; value("issuer_concentration_after_pct", 0) > 15 or value("illiquid_after_pct", 0) > 20 }
required contains {"rule_id": "I-04", "role": "L2"} if { action in {"listed_order", "complex_order", "rebalance"}; value("issuer_concentration_after_pct", 0) > 15 or value("illiquid_after_pct", 0) > 20 }
findings contains {"rule_id": "I-04", "kind": "deny", "detail": "Issuer concentration >25%; committee exception required"} if { action in {"listed_order", "complex_order", "rebalance"}; value("issuer_concentration_after_pct", 0) > 25; not has_exception("issuer_concentration") }
required contains {"rule_id": "I-05", "role": "L1"} if { truth("tax_sensitive_sale"); value("estimated_realized_loss_usd", 0) > 50000 }
findings contains {"rule_id": "I-05", "kind": "hold", "detail": "Client loss acknowledgement missing"} if { truth("tax_sensitive_sale"); value("estimated_realized_loss_usd", 0) > 50000; not truth("client_loss_acknowledged") }
required contains {"rule_id": "I-05", "role": "TaxSpecialist"} if { truth("material_tax_uncertainty") }

required contains {"rule_id": "M-01", "role": "Operations"} if { action == "internal_transfer" }
required contains {"rule_id": "M-01", "role": "L1"} if { action == "internal_transfer"; amount > 50000; amount <= 250000 }
required contains {"rule_id": "M-01", "role": "L2"} if { action == "internal_transfer"; amount > 250000 }
findings contains {"rule_id": "M-01", "kind": "deny", "detail": "Not same beneficial owner"} if { action == "internal_transfer"; value("same_beneficial_owner", null) == false }
findings contains {"rule_id": "M-01", "kind": "hold", "detail": "Ownership/identity validation missing"} if { action == "internal_transfer"; not truth("ownership_and_identity_verified") }

required contains {"rule_id": "M-02", "role": "Operations"} if { action == "external_transfer" }
required contains {"rule_id": "M-02", "role": "L1"} if { action == "external_transfer"; amount > 25000; amount <= 100000 }
required contains {"rule_id": "M-02", "role": "L2"} if { action == "external_transfer"; amount > 100000; amount <= 500000 }
required contains {"rule_id": "M-02", "role": "L3"} if { action == "external_transfer"; amount > 500000 }
required contains {"rule_id": "M-02", "role": "AML"} if { action == "external_transfer"; amount > 500000 }
findings contains {"rule_id": "M-02", "kind": "hold", "detail": "External destination ownership not verified"} if { action == "external_transfer"; not truth("destination_client_owned_verified") }

required contains {"rule_id": "M-03", "role": "Operations"} if { truth("new_or_changed_destination") }
required contains {"rule_id": "M-03", "role": "Fraud"} if { truth("new_or_changed_destination"); truth("expedite_cooling_off") }
findings contains {"rule_id": "M-03", "kind": "hold", "detail": "Independent callback to previously verified channel missing"} if { truth("new_or_changed_destination"); not truth("independent_callback_passed") }
findings contains {"rule_id": "M-03", "kind": "hold", "detail": "24-hour destination cooling-off not elapsed or expedited approval pending"} if { truth("new_or_changed_destination"); not truth("cooling_off_elapsed"); not cooling_off_expedited }

required contains {"rule_id": "M-04", "role": "L2"} if { action == "third_party_payment" }
required contains {"rule_id": "M-04", "role": "Operations"} if { action == "third_party_payment" }
required contains {"rule_id": "M-04", "role": "AML"} if { action == "third_party_payment" }
required contains {"rule_id": "M-04", "role": "L3"} if { action == "third_party_payment"; amount > 100000 }
findings contains {"rule_id": "M-04", "kind": "deny", "detail": "Third-party business purpose not documented"} if { action == "third_party_payment"; not truth("business_purpose_documented") }

required contains {"rule_id": "M-05", "role": "Operations"} if { action == "international_wire" }
required contains {"rule_id": "M-05", "role": "L1"} if { action == "international_wire"; amount > 50000; amount <= 250000 }
required contains {"rule_id": "M-05", "role": "L2"} if { action == "international_wire"; amount > 250000 }
required contains {"rule_id": "M-05", "role": "AML"} if { action == "international_wire"; amount > 250000 or truth("high_risk_jurisdiction") }
findings contains {"rule_id": "M-05", "kind": "hold", "detail": "Sanctions screening incomplete"} if { action == "international_wire"; not truth("sanctions_screening_clear") }

required contains {"rule_id": "M-06", "role": "L3"} if { action in {"external_transfer", "third_party_payment", "international_wire"}; value("daily_external_total_usd", 0) > 750000 }
required contains {"rule_id": "M-06", "role": "Risk"} if { action in {"external_transfer", "third_party_payment", "international_wire"}; value("daily_external_total_usd", 0) > 750000 }
findings contains {"rule_id": "M-06", "kind": "deny", "detail": "Daily external total >$1.5m requires Enterprise Risk Committee exception"} if { action in {"external_transfer", "third_party_payment", "international_wire"}; value("daily_external_total_usd", 0) > 1500000; not has_exception("daily_external_cap") }
findings contains {"rule_id": "M-07", "kind": "hold", "detail": "Urgency does not waive mandatory controls"} if { truth("urgent"); truth("attempted_control_bypass") }

required contains {"rule_id": "O-01", "role": "Operations"} if { action == "open_account" }
findings contains {"rule_id": "O-01", "kind": "hold", "detail": "Onboarding documentation/KYC/suitability incomplete"} if { action == "open_account"; not truth("onboarding_complete") }
required contains {"rule_id": "O-02", "role": "AML"} if { action == "open_account"; truth("high_risk_pep_or_complex") }
required contains {"rule_id": "O-02", "role": "L2"} if { action == "open_account"; truth("high_risk_pep_or_complex") }
findings contains {"rule_id": "O-02", "kind": "hold", "detail": "Enhanced due diligence incomplete"} if { action == "open_account"; truth("high_risk_pep_or_complex"); not truth("edd_complete") }
required contains {"rule_id": "O-03", "role": "Legal"} if { truth("trust_entity_or_poa"); action in {"open_account", "internal_transfer", "external_transfer", "third_party_payment", "international_wire"} }
findings contains {"rule_id": "O-03", "kind": "hold", "detail": "Signing authority unverified"} if { truth("trust_entity_or_poa"); not truth("signing_authority_verified") }
findings contains {"rule_id": "O-04", "kind": "hold", "detail": "Reauthentication or suitability refresh incomplete"} if { action == "change_profile"; not truth("client_reauthenticated") or not truth("suitability_refreshed") }
required contains {"rule_id": "O-04", "role": "AML"} if { action == "change_profile"; truth("beneficial_owner_changed") }
required contains {"rule_id": "O-05", "role": "Operations"} if { action == "reactivate_account"; value("inactive_months", 0) >= 18 }
required contains {"rule_id": "O-05", "role": "L1"} if { action == "reactivate_account"; value("inactive_months", 0) >= 18 }

required contains {"rule_id": "F-01", "role": "L1"} if { action == "fee_discount"; value("discount_pct", 0) > 10; value("discount_pct", 0) <= 20 }
required contains {"rule_id": "F-01", "role": "L2"} if { action == "fee_discount"; value("discount_pct", 0) > 20; value("discount_pct", 0) <= 35 }
required contains {"rule_id": "F-01", "role": "L3"} if { action == "fee_discount"; value("discount_pct", 0) > 35 }
required contains {"rule_id": "F-01", "role": "Finance"} if { action == "fee_discount"; value("discount_pct", 0) > 35 }
findings contains {"rule_id": "F-01", "kind": "hold", "detail": "Approved pricing band not verified"} if { action == "fee_discount"; not truth("pricing_band_valid") }

required contains {"rule_id": "F-02", "role": "L1"} if { action == "fee_refund"; amount > 250; amount <= 2500 }
required contains {"rule_id": "F-02", "role": "L2"} if { action == "fee_refund"; amount > 2500; amount <= 10000 }
required contains {"rule_id": "F-02", "role": "Finance"} if { action == "fee_refund"; amount > 2500 }
required contains {"rule_id": "F-02", "role": "L3"} if { action == "fee_refund"; amount > 10000 }
required contains {"rule_id": "F-02", "role": "Compliance"} if { action == "fee_refund"; amount > 10000 }
findings contains {"rule_id": "F-02", "kind": "hold", "detail": "Error/service justification missing"} if { action == "fee_refund"; not truth("refund_justification_documented") }

findings contains {"rule_id": "F-03", "kind": "hold", "detail": "90-day related concession aggregation unresolved"} if { action in {"fee_discount", "fee_refund"}; not truth("concession_90d_aggregation_verified") }
required contains {"rule_id": "F-03", "role": "Finance"} if { action in {"fee_discount", "fee_refund"}; truth("retroactive_concession") }
required contains {"rule_id": "F-04", "role": "Compliance"} if { action in {"fee_discount", "fee_refund"}; truth("employee_related_or_conflict") }

findings contains {"rule_id": "C-01", "kind": "hold", "detail": "Fraud/AML investigation hold"} if { truth("risk_flag_active") }
required contains {"rule_id": "C-01", "role": "Fraud"} if { truth("risk_flag_active") }
findings contains {"rule_id": "C-02", "kind": "hold", "detail": "Operations final release not verified"} if { action in {"internal_transfer", "external_transfer", "third_party_payment", "international_wire", "open_account"}; not truth("operations_release_verified") }
findings contains {"rule_id": "C-03", "kind": "deny", "detail": "Separation of duties violation"} if { truth("self_approval_attempt") or truth("self_callback_attempt") or truth("self_release_attempt") }
findings contains {"rule_id": "C-04", "kind": "hold", "detail": "Required input missing or stale"} if { not truth("required_data_fresh_and_complete") }
findings contains {"rule_id": "A-01", "kind": "hold", "detail": "Immutable audit envelope unavailable"} if { not truth("audit_evidence_ready") }
findings contains {"rule_id": "A-02", "kind": "evidence", "detail": "Monthly Compliance/Risk exception monitoring and circumvention escalation"} if { truth("exception_or_control_failure") }
findings contains {"rule_id": "E-01", "kind": "hold", "detail": "Exception justification, owner, duration or controls missing"} if { truth("exception_requested"); not truth("exception_package_complete") }
required contains {"rule_id": "E-01", "role": "L3"} if { truth("exception_requested") }
findings contains {"rule_id": "E-01", "kind": "deny", "detail": "Exception cannot waive legal/sanctions/identity prohibitions"} if { truth("exception_requested"); truth("nonwaivable_exception_attempt") }
required contains {"rule_id": "E-02", "role": "L2"} if { truth("emergency_hardship") }
required contains {"rule_id": "E-02", "role": "Operations"} if { truth("emergency_hardship") }
findings contains {"rule_id": "E-02", "kind": "hold", "detail": "Emergency independent verification missing"} if { truth("emergency_hardship"); not truth("emergency_independently_verified") }
findings contains {"rule_id": "E-03", "kind": "hold", "detail": "Acting authority not formally registered"} if { truth("acting_approver_used"); not truth("acting_appointment_verified") }

# Fail closed: unknown actions, malformed amount, unsupported policy version.
findings contains {"rule_id": "SYSTEM", "kind": "hold", "detail": "Unsupported action"} if { not action in {"listed_order", "complex_order", "rebalance", "internal_transfer", "external_transfer", "third_party_payment", "international_wire", "open_account", "change_profile", "reactivate_account", "fee_discount", "fee_refund"} }
findings contains {"rule_id": "SYSTEM", "kind": "hold", "detail": "Invalid or negative amount"} if { not is_number(amount) or amount < 0 }
findings contains {"rule_id": "SYSTEM", "kind": "hold", "detail": "Policy version mismatch"} if { value("policy_version", "") != "1.0" }

missing_approvals contains r if { some r in required; not approved(r.role) }

# Status precedence DENY > HOLD > REQUIRE_APPROVAL > ALLOW.
decision := "DENY" if { some f in findings; f.kind == "deny" }
else := "HOLD" if { some f in findings; f.kind == "hold" }
else := "REQUIRE_APPROVAL" if { count(missing_approvals) > 0 }
else := "ALLOW"

result := {
    "decision": decision,
    "policy_id": "WM-DOA-001",
    "policy_version": "1.0",
    "required_approvals": sort([r | some r in required]),
    "missing_approvals": sort([r | some r in missing_approvals]),
    "findings": sort([f | some f in findings]),
    "executable": decision == "ALLOW",
}
