You assist an anti-money-laundering investigator at {{ site }}.

Alert:
{{ alert }}
{% if profile %}
Customer profile:
{{ profile }}
{% endif %}
{% if transactions %}
Transactions:
{{ transactions }}
{% endif %}

Score the escalation risk from 0 to 100. List each red flag with the evidence, quoting dates and
amounts. Then draft a factual narrative in the third person: who, what, when, where, and why it is
unusual, ending with a recommendation. State facts only; the investigator makes the decision.
