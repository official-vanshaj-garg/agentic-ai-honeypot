# OVERVIEW

**Project:** NIRIKSHA.ai — Agentic Honeypot for Scam Detection, Engagement, and Intelligence Extraction
**Built for:** India AI Impact Buildathon 2026 (HCL GUVI)
**Classification:** Research prototype

---

## What the Project Does

NIRIKSHA.ai is a backend API that acts as an AI-powered honeypot. When a scammer sends a message, instead of blocking or ignoring them, the system:

1. Replies as a confused but cooperative person using an LLM (Llama 3.3 70B via Groq)
2. Keeps the conversation going across multiple turns
3. Silently extracts identifying information the scammer reveals (phone number, UPI ID, bank account, phishing link, email, reference IDs)
4. Produces a structured intelligence report after ~10 turns

The system never reveals that it is an AI. The scammer believes they are talking to a potential victim.

---

## The Problem It Solves

Most anti-scam tools block or filter suspicious messages immediately. This stops one scam attempt but gives investigators nothing useful — no identity, no infrastructure, no patterns. The scammer simply moves on.

NIRIKSHA.ai trades one interaction for many. By keeping the scammer engaged, it collects the kind of information that is normally only gathered after a scam has already succeeded and been reported.

---

## Who This Is For

| Audience | Use |
|---|---|
| Researchers | Studying LLM-based social engineering defence, conversational AI for security, or scam intelligence gathering |
| Academics / students | Demonstrable working prototype for a mini-project or final year project submission |
| Hackathon evaluators | REST API that can be hit directly to demonstrate the full conversation + report pipeline |
| Future product developers | Foundation for a SaaS tool targeting banks, telecoms, or cybercrime units |

---

## What Makes It Novel (Research Angle)

The combination of three things is what makes this interesting as a research idea:

1. **Agentic persona maintenance** — The LLM holds a consistent character across multiple turns without breaking.
2. **Silent intelligence elicitation** — The agent strategically steers conversation to extract specific missing data types without the scammer realising they are being profiled.
3. **Structured output** — The session ends with a machine-readable report, not just a conversation log.

Using an LLM for the engagement side while using regex for the extraction side is a practical design choice that keeps the extraction reliable and the conversation natural.

---

## Current Scope

The project is a backend API only. It has:
- One REST endpoint (`POST /api/detect`)
- In-memory session state (no database)
- No frontend, no dashboard, no deployment infrastructure
- A local integration test harness

It is not production-ready and is not hardened for public deployment. It is a working demonstration of the core idea.

---

## Positioning

| Track | Assessment |
|---|---|
| Hackathon submission | Complete and working. Scored 96.65/100 on the built-in evaluation harness. |
| College mini-project | Suitable. The pipeline is complete, the idea is clear, and the code is clean. |
| Research paper | The core idea is novel and publishable. Missing: real conversation dataset, baseline comparison, independent evaluation, ethics review. |
| Production system | Not ready. Missing: database, frontend, rate limiting, auth hardening, monitoring. |
