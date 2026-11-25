Audit this network device config against the {{ baseline }} hardening baseline used at {{ site }}.

Config:
{{ config }}

Give a compliance score from 0 to 100 with a label saying how many baseline rules fail.
List each failing rule with the exact config line and the exact fix.
Then give the remediation commands in a safe order; say when a step could lock the operator out.
