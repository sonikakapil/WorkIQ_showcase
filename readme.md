# WorkIQ Showcase
A Streamlit demo for showcasing **WorkIQ** through a clean, chat-first experience.

## Core flows
### Tomorrow Command Center
Turn tomorrow into one sharp operating brief.

### Continue From Earlier
Pick up from prior context instead of starting over.

### Draft What I Need
Turn work context into ready-to-send output.

### Productivity
Three focused productivity flows are built in:
- **Meeting Load Radar**
- **Channel Pulse**
- **Org Lens**

### Tomorrow Command Center
- Build my command center for tomorrow.
- What are the 3 meetings that matter most tomorrow?
- What is each key stakeholder likely to care about?
- What should I decide, delegate, or defer before tomorrow starts?
- If I only do three things tonight, what should they be?

### Continue From Earlier
- Continue from where we left off.
- What changed since the last discussion?
- What is now more urgent?
- What are the 5 highest-value follow-ups?
- What is the single fastest unblock?

### Draft What I Need
- Draft the 3 messages I most likely need next.
- Write me an executive follow-up note.
- Draft a stakeholder alignment message.
- Write an internal unblocker note I can send now.
- Give me concise drafts with a clear ask and next step.

### Meeting Load Radar
- Analyze my meeting load for this week.
- Which recurring meetings are costing me the most time?
- Where is my calendar overloaded?
- What should I shorten, delegate, or challenge?
- How much time could I win back?

### Channel Pulse
- What matters most across my Teams channels right now?
- What decisions were made recently?
- What action items need me?
- What mentions of me actually matter?
- What are the 3 things I should respond to today?

### Org Lens
- Show me my org context.
- Who around me really influences priorities?
- Who should I keep warm this week?
- Where are the alignment risks across the org?
- What is the smartest outreach move by stakeholder group?

## Best demo sequence

1. Build my command center for tomorrow.
2. Continue from where we left off.
3. Analyze my meeting load for this week.
4. What matters most across my Teams channels right now?
5. Draft the 3 messages I most likely need next.

## Optional Azure OpenAI polish

The app can optionally refine WorkIQ output using Azure OpenAI via **Microsoft Entra ID** for a sharper, more executive final answer.

## Quick start

```bash
pip install -r requirements.txt
streamlit run app.py