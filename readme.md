# WorkIQ Showcase

A polished Streamlit demo for showcasing **WorkIQ** through a clean, chat-first experience.

This app is designed for demos, workshops, and executive storytelling. It highlights high-value work intelligence across meetings, Teams, stakeholders, continuity, and draft generation.

## Core flows

- **Tomorrow Command Center** - Turn tomorrow into one sharp operating brief
- **Continue From Earlier** - Pick up from prior context instead of starting over
- **Draft What I Need** - Turn work context into ready-to-send output
- **Productivity** - Focused views for meeting load, Teams signal, and org visibility

## 🎯 What You Can Query

| Type | Example questions |
|---|---|
| 📅 **Tomorrow Command Center** | "Build my command center for tomorrow" |
| 📅 **Tomorrow Command Center** | "What are the 3 meetings that matter most tomorrow?" |
| 📅 **Tomorrow Command Center** | "What should I decide, delegate, or defer before tomorrow starts?" |
| 🧠 **Continue From Earlier** | "Continue from where we left off" |
| 🧠 **Continue From Earlier** | "What changed since the last discussion?" |
| 🧠 **Continue From Earlier** | "What is the single fastest unblock?" |
| ✍️ **Draft What I Need** | "Draft the 3 messages I most likely need next" |
| ✍️ **Draft What I Need** | "Write me an executive follow-up note" |
| ✍️ **Draft What I Need** | "Draft a stakeholder alignment message" |
| 📊 **Meeting Load Radar** | "Analyze my meeting load for this week" |
| 📊 **Meeting Load Radar** | "Which recurring meetings are costing me the most time?" |
| 📊 **Meeting Load Radar** | "How much time could I win back?" |
| 💬 **Channel Pulse** | "What matters most across my Teams channels right now?" |
| 💬 **Channel Pulse** | "What decisions were made recently?" |
| 💬 **Channel Pulse** | "What are the 3 things I should respond to today?" |
| 🏢 **Org Lens** | "Show me my org context" |
| 🏢 **Org Lens** | "Who around me really influences priorities?" |
| 🏢 **Org Lens** | "What is the smartest outreach move by stakeholder group?" |

## Best demo sequence

1. **Build my command center for tomorrow**
2. **Continue from where we left off**
3. **Analyze my meeting load for this week**
4. **What matters most across my Teams channels right now?**
5. **Draft the 3 messages I most likely need next**

That sequence moves from awareness to prioritization to action.

## Optional Azure OpenAI polish

The app can optionally refine WorkIQ output using Azure OpenAI via **Microsoft Entra ID** for a sharper, more executive final answer.

## Quick start

```bash
pip install -r requirements.txt
streamlit run app.py