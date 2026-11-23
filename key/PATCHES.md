# Patches applied to the answer key

`wealth_policy.original.rego` is the file as received. `wealth_policy.rego` is the copy the harness uses.
The original did not compile on OPA 1.22.4. Two mechanical fixes, no change of logic:

1. Line 10: `default` is a reserved word in Rego, so the helper parameter `default` was renamed to `dflt`.
2. Added `import future.keywords.or` because the file uses the `or` keyword (13 places).

To confirm with the key author: which OPA version the draft was written for.
