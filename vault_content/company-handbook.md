---
title: "Company Handbook"
created: "{{CREATED_TIMESTAMP}}"
tier: bronze
status: active
---

# Company Handbook

This handbook defines action classification rules for the AI Employee. The agent uses these rules to determine which actions can be auto-executed and which require human approval.

## Routine Actions

Actions the agent can auto-execute without human approval. These are low-risk, reversible operations.

- **File organization**: Moving, renaming, or categorizing files within the vault
- **Report generation**: Creating summary reports from existing vault data
- **Note creation**: Writing new markdown notes based on processed events
- **Data summarization**: Condensing information from multiple sources into a summary

## Sensitive Actions

Actions that require human review and approval before execution. These involve external communication or data modifications with broader impact.

- **Send email**: Composing and sending email messages on behalf of the user
- **Post to social media**: Publishing content to social media platforms
- **Modify financial records**: Updating invoices, expense reports, or financial data
- **External API calls**: Making requests to third-party services

## Critical Actions

Actions that require explicit human approval and confirmation. These are high-risk, potentially irreversible operations.

- **Execute payment**: Processing financial transactions or transfers
- **Delete files**: Permanently removing files or data from any system
- **Modify credentials**: Changing passwords, API keys, or access tokens
- **Legal document actions**: Signing, submitting, or modifying legal documents
