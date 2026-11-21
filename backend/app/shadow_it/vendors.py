"""Catalog of known SaaS vendors, typical billing descriptors, categories, and risk ratings."""

from typing import Optional, Dict, Any

KNOWN_SAAS_VENDORS: Dict[str, Dict[str, Any]] = {
    "slack": {"name": "Slack Technologies", "category": "Communication", "risk": "LOW", "aliases": ["slack", "slack.com", "slack tech"]},
    "zoom": {"name": "Zoom Video Communications", "category": "Communication", "risk": "LOW", "aliases": ["zoom", "zoom.us", "zoom video"]},
    "notion": {"name": "Notion Labs", "category": "Productivity", "risk": "LOW", "aliases": ["notion", "notion.so", "notion labs"]},
    "figma": {"name": "Figma", "category": "Design", "risk": "LOW", "aliases": ["figma", "figma inc", "figma.com"]},
    "github": {"name": "GitHub", "category": "Developer Tools", "risk": "LOW", "aliases": ["github", "github.com", "github inc"]},
    "gitlab": {"name": "GitLab", "category": "Developer Tools", "risk": "LOW", "aliases": ["gitlab", "gitlab.com"]},
    "jira": {"name": "Atlassian / Jira", "category": "Productivity", "risk": "LOW", "aliases": ["atlassian", "jira", "confluence", "trello"]},
    "asana": {"name": "Asana", "category": "Productivity", "risk": "LOW", "aliases": ["asana", "asana.com"]},
    "hubspot": {"name": "HubSpot", "category": "CRM & Sales", "risk": "MEDIUM", "aliases": ["hubspot", "hubspot inc"]},
    "salesforce": {"name": "Salesforce", "category": "CRM & Sales", "risk": "MEDIUM", "aliases": ["salesforce", "sfdc", "salesforce.com"]},
    "dropbox": {"name": "Dropbox", "category": "Cloud Storage", "risk": "MEDIUM", "aliases": ["dropbox", "dropbox inc"]},
    "adobe": {"name": "Adobe Creative Cloud", "category": "Design & Media", "risk": "LOW", "aliases": ["adobe", "adobe systems", "photoshop", "creative cloud"]},
    "canva": {"name": "Canva", "category": "Design & Media", "risk": "LOW", "aliases": ["canva", "canva pty"]},
    "miro": {"name": "Miro", "category": "Collaboration", "risk": "LOW", "aliases": ["miro", "realtimeboard"]},
    "loom": {"name": "Loom Video", "category": "Communication", "risk": "LOW", "aliases": ["loom", "loom.com"]},
    "grammarly": {"name": "Grammarly", "category": "Productivity", "risk": "MEDIUM", "aliases": ["grammarly", "grammarly inc"]},
    "monday": {"name": "Monday.com", "category": "Project Management", "risk": "LOW", "aliases": ["monday.com", "monday com"]},
    "airtable": {"name": "Airtable", "category": "Data & Workflow", "risk": "LOW", "aliases": ["airtable", "formagrid"]},
    "stripe": {"name": "Stripe Payments", "category": "Payments & Billing", "risk": "HIGH", "aliases": ["stripe", "stripe.com"]},
    "razorpay": {"name": "Razorpay", "category": "Payments & Billing", "risk": "HIGH", "aliases": ["razorpay", "razorpay soft"]},
    "openai": {"name": "OpenAI / ChatGPT", "category": "AI & LLM", "risk": "MEDIUM", "aliases": ["openai", "chatgpt", "openai api"]},
    "anthropic": {"name": "Anthropic Claude", "category": "AI & LLM", "risk": "MEDIUM", "aliases": ["anthropic", "claude.ai", "anthropic api"]},
    "midjourney": {"name": "Midjourney", "category": "AI & Creative", "risk": "MEDIUM", "aliases": ["midjourney"]},
    "aws": {"name": "Amazon Web Services", "category": "Cloud Infrastructure", "risk": "HIGH", "aliases": ["aws", "amazon web services", "amazon aws"]},
    "azure": {"name": "Microsoft Azure", "category": "Cloud Infrastructure", "risk": "HIGH", "aliases": ["azure", "microsoft azure", "msft azure"]},
    "digitalocean": {"name": "DigitalOcean", "category": "Cloud Infrastructure", "risk": "HIGH", "aliases": ["digitalocean", "digital ocean"]},
    "vercel": {"name": "Vercel", "category": "Cloud & Hosting", "risk": "LOW", "aliases": ["vercel", "vercel inc", "zeit"]},
    "netlify": {"name": "Netlify", "category": "Cloud & Hosting", "risk": "LOW", "aliases": ["netlify", "netlify inc"]},
    "heroku": {"name": "Heroku", "category": "Cloud & Hosting", "risk": "LOW", "aliases": ["heroku"]},
    "datadog": {"name": "Datadog", "category": "Monitoring & Observability", "risk": "MEDIUM", "aliases": ["datadog", "datadog inc"]},
    "sentry": {"name": "Sentry", "category": "Monitoring & Observability", "risk": "LOW", "aliases": ["sentry", "functional software"]},
    "pagerduty": {"name": "PagerDuty", "category": "Monitoring & Incident", "risk": "MEDIUM", "aliases": ["pagerduty"]},
    "intercom": {"name": "Intercom", "category": "Customer Support", "risk": "MEDIUM", "aliases": ["intercom", "intercom inc"]},
    "zendesk": {"name": "Zendesk", "category": "Customer Support", "risk": "MEDIUM", "aliases": ["zendesk", "zendesk inc"]},
    "mailchimp": {"name": "Mailchimp", "category": "Marketing & Email", "risk": "LOW", "aliases": ["mailchimp", "the rocket science group"]},
    "sendgrid": {"name": "Twilio SendGrid", "category": "Marketing & Email", "risk": "LOW", "aliases": ["sendgrid", "twilio sendgrid"]},
    "twilio": {"name": "Twilio", "category": "Communication API", "risk": "MEDIUM", "aliases": ["twilio", "twilio inc"]},
    "linear": {"name": "Linear Orbit", "category": "Developer Tools", "risk": "LOW", "aliases": ["linear", "linear app"]},
    "clickup": {"name": "ClickUp", "category": "Productivity", "risk": "LOW", "aliases": ["clickup", "mango technologies"]},
    "cursor": {"name": "Cursor AI (Anysphere)", "category": "AI & Developer", "risk": "MEDIUM", "aliases": ["cursor", "anysphere"]},
    "v0": {"name": "v0 by Vercel", "category": "AI & Developer", "risk": "LOW", "aliases": ["v0.dev", "v0 dev"]},
}

def match_vendor_from_description(description: str) -> Optional[Dict[str, Any]]:
    if not description:
        return None
    d = description.lower()
    for key, info in KNOWN_SAAS_VENDORS.items():
        for alias in info["aliases"]:
            if alias in d:
                return {
                    "key": key,
                    "vendor_name": info["name"],
                    "category": info["category"],
                    "risk_level": info["risk"],
                }
    return None
