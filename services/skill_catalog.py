from dataclasses import dataclass
from typing import Dict, List


@dataclass
class SkillDefinition:
    skill_id: str
    title: str
    category: str
    description: str
    example: str


class SkillCatalog:
    def __init__(self):
        self.skills = [
            SkillDefinition(
                skill_id="workiq_chat",
                title="WorkIQ Ask",
                category="Core",
                description="Freeform query across Microsoft 365 work context.",
                example="What meetings do I have tomorrow?",
            ),
            SkillDefinition(
                skill_id="daily_outlook_triage",
                title="Daily Outlook Triage",
                category="Productivity",
                description="Quick summary of inbox and calendar for the day.",
                example="Give me my inbox and calendar triage for today.",
            ),
            SkillDefinition(
                skill_id="email_analytics",
                title="Email Analytics",
                category="Productivity",
                description="Analyze email patterns for a period.",
                example="Analyze my email patterns this month.",
            ),
            SkillDefinition(
                skill_id="meeting_cost_calculator",
                title="Meeting Cost Calculator",
                category="Productivity",
                description="Estimate time and cost spent in meetings.",
                example="Estimate the cost of my meetings this week using an hourly rate.",
            ),
            SkillDefinition(
                skill_id="org_chart",
                title="Org Chart",
                category="Productivity",
                description="Show org structure for a person.",
                example="Show me the org chart for John Doe.",
            ),
            SkillDefinition(
                skill_id="channel_digest",
                title="Channel Digest",
                category="Productivity",
                description="Digest activity across Teams channels.",
                example="Give me a digest of Engineering and Product channels for the last 3 days.",
            ),
            SkillDefinition(
                skill_id="multi_plan_search",
                title="Multi-Plan Search",
                category="Productivity",
                description="Search Planner tasks across all plans.",
                example="Find overdue tasks across all my Planner plans.",
            ),
        ]

    def all(self) -> List[SkillDefinition]:
        return self.skills

    def by_category(self, category: str) -> List[SkillDefinition]:
        return [s for s in self.skills if s.category == category]

    def get(self, skill_id: str) -> SkillDefinition:
        for skill in self.skills:
            if skill.skill_id == skill_id:
                return skill
        raise KeyError(f"Unknown skill_id: {skill_id}")

    def build_prompt(self, skill_id: str, inputs: Dict[str, str]) -> str:
        if skill_id == "workiq_chat":
            return (inputs.get("question") or "").strip()

        if skill_id == "daily_outlook_triage":
            day = (inputs.get("day") or "today").strip()
            return (
                f"Give me a concise but useful Outlook triage for {day}. "
                f"Summarize my most important emails, meetings, likely conflicts, action items, and anything requiring my attention first."
            )

        if skill_id == "email_analytics":
            period = (inputs.get("period") or "last 30 days").strip()
            return (
                f"Analyze my email patterns for {period}. "
                f"Include total received and sent, top senders, unread backlog, high-priority emails, busiest days, and clear productivity takeaways."
            )

        if skill_id == "meeting_cost_calculator":
            period = (inputs.get("period") or "this week").strip()
            hourly_rate = (inputs.get("hourly_rate") or "100").strip()
            currency = (inputs.get("currency") or "USD").strip()
            return (
                f"Calculate the time and estimated cost of my meetings for {period}. "
                f"Assume an hourly rate of {hourly_rate} {currency} for me unless attendee-specific cost data is unavailable. "
                f"Show total meeting hours, major time blocks, and an estimated cost summary."
            )

        if skill_id == "org_chart":
            person = (inputs.get("person") or "me").strip()
            return (
                f"Show the org chart for {person}. "
                f"Include their manager, peers if relevant, and direct reports. "
                f"Present it clearly and call out role titles."
            )

        if skill_id == "channel_digest":
            scope = (inputs.get("scope") or "all my relevant Teams channels").strip()
            lookback = (inputs.get("lookback") or "last 3 days").strip()
            focus = (inputs.get("focus") or "key discussions, decisions, mentions, and action items").strip()
            return (
                f"Give me a channel digest for {scope} over the {lookback}. "
                f"Focus on {focus}. "
                f"Organize the answer by channel and highlight anything that needs my attention."
            )

        if skill_id == "multi_plan_search":
            query = (inputs.get("query") or "overdue tasks").strip()
            return (
                f"Search across all my Planner plans for {query}. "
                f"Group results by plan and call out overdue items, owners, and due dates."
            )

        raise KeyError(f"Unknown skill_id: {skill_id}")