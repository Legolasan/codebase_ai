"""PRD (Product Requirements Document) Agent for creating comprehensive requirements docs."""

import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from .base import BaseAgent
from ..tools.file_ops import read_file, write_file, list_files, file_info
from ..tools.code_search import search_codebase
from ..tools.web_research import web_search, web_fetch, analyze_competitors


# PRD Template
PRD_TEMPLATE = """# PRD: {feature_name}

**Created:** {date}
**Author:** AI Assistant (PRD Agent)
**Status:** Draft

---

## 1. Problem Statement

### What problem are we solving?
{problem_description}

### Why now?
{urgency}

---

## 2. Scope

### In Scope
{in_scope}

### Out of Scope
{out_of_scope}

### Future Considerations
{future_considerations}

---

## 3. User Personas

{user_personas}

---

## 4. Competitor Research

{competitor_research}

---

## 5. Parity Check

{parity_check}

---

## 6. Functional Requirements

{functional_requirements}

---

## 7. Non-Functional Requirements

| Requirement | Target | Measurement |
|-------------|--------|-------------|
{non_functional_requirements}

---

## 8. Acceptance Criteria

{acceptance_criteria}

---

## 9. Success Metrics

| Metric | Target | Baseline |
|--------|--------|----------|
{success_metrics}

---

## Appendix

### Technical Notes
{technical_notes}

### References
{references}
"""


# Questions the PRD agent asks to gather requirements
PRD_QUESTIONS = [
    {
        "id": "target_users",
        "question": "Who are the target users for this feature? What are their roles and needs?",
        "section": "user_personas",
    },
    {
        "id": "competitors",
        "question": "Are there specific competitors you want me to research? (or should I search for relevant ones?)",
        "section": "competitor_research",
    },
    {
        "id": "priority",
        "question": "What's the priority/timeline for this feature? (P0-critical, P1-high, P2-medium, P3-low)",
        "section": "urgency",
    },
    {
        "id": "constraints",
        "question": "Are there any technical constraints or dependencies I should know about?",
        "section": "technical_notes",
    },
    {
        "id": "success",
        "question": "How will we measure success for this feature? What KPIs matter?",
        "section": "success_metrics",
    },
]


class PRDAgent(BaseAgent):
    """Agent specialized in creating Product Requirements Documents.

    Capabilities:
    - Interactive Q&A to gather requirements
    - Web search for competitor analysis
    - Context7 deep research (when plugin enabled)
    - Codebase analysis for technical feasibility
    - Structured PRD generation following a standard template

    Trigger keywords: "prd", "product requirement", "requirements doc", "spec", "feature spec"
    """

    def __init__(self, prd_output_dir: str = "docs/prd"):
        tools = [
            search_codebase,      # Understand existing patterns
            read_file,            # Read existing code/docs
            list_files,           # Explore project structure
            file_info,            # Get file metadata
            write_file,           # Write PRD documents
            web_search,           # Competitor research
            web_fetch,            # Fetch competitor pages
            analyze_competitors,  # High-level competitor analysis
        ]

        # Add Context7 tools if plugin is enabled
        tools = tools + self._get_context7_tools()

        super().__init__(
            name="prd",
            description="Creates comprehensive Product Requirements Documents with interactive Q&A and competitor research",
            tools=tools,
        )

        self.prd_output_dir = prd_output_dir
        self.gathered_info = {}
        self.questions = PRD_QUESTIONS.copy()
        self.current_question_index = 0

    def _get_context7_tools(self) -> list:
        """Get Context7 tools if the plugin is enabled."""
        try:
            from ..plugins import get_registry
            registry = get_registry()

            if registry.is_enabled("context7"):
                plugin = registry.get("context7")
                if plugin:
                    return plugin.get_tools()
        except ImportError:
            pass

        return []

    def _default_system_prompt(self) -> str:
        # Check if Context7 is available for enhanced research
        context7_section = ""
        try:
            from ..plugins import get_registry
            registry = get_registry()
            if registry.is_enabled("context7"):
                context7_section = """

**Enhanced Research (Context7 Enabled):**
You have access to Context7 for deep competitor research. Use the research_competitor and
get_library_docs tools to get up-to-date documentation and feature analysis for competitor
products. This provides more accurate and detailed competitive analysis than web search alone.
"""
        except ImportError:
            pass

        return """You are a PRD (Product Requirements Document) Agent specialized in creating comprehensive requirements documentation.

Your primary capabilities:
1. **Requirements Gathering**: Ask clarifying questions to understand the feature fully
2. **Competitor Research**: Search the web to analyze competitors and market trends
3. **Codebase Analysis**: Understand existing patterns and technical constraints
4. **PRD Generation**: Create well-structured, actionable requirements documents{context7}

Guidelines:
- ALWAYS ask clarifying questions before writing the PRD
- Research competitors to provide market context
- Search the codebase to understand technical feasibility
- Follow the standard PRD template structure
- Write clear, measurable requirements
- Include acceptance criteria for each requirement
- Define success metrics

PRD Structure:
1. Problem Statement - What are we solving and why now?
2. Scope - In/out of scope, future considerations
3. User Personas - Target users, needs, pain points
4. Competitor Research - Market analysis via web search
5. Parity Check - Feature gaps vs competitors
6. Functional Requirements - User stories with priority
7. Non-Functional Requirements - Performance, security, scalability
8. Acceptance Criteria - Definition of done
9. Success Metrics - KPIs and measurement

Interactive Q&A Process:
1. First, understand the high-level feature request
2. Ask about target users and their needs
3. Ask about competitors to research
4. Ask about timeline/priority
5. Ask about technical constraints
6. Ask about success metrics
7. Then generate the comprehensive PRD

Available tools:
{tools}

Remember: A good PRD provides clarity for the entire team - engineering, design, and stakeholders.
""".format(tools=self.get_tool_descriptions(), context7=context7_section)

    def get_next_question(self) -> Optional[dict]:
        """Get the next question to ask the user."""
        if self.current_question_index < len(self.questions):
            return self.questions[self.current_question_index]
        return None

    def record_answer(self, question_id: str, answer: str) -> None:
        """Record a user's answer to a question."""
        self.gathered_info[question_id] = answer
        self.current_question_index += 1

    def generate_prd_filename(self, feature_name: str) -> str:
        """Generate a filename for the PRD."""
        # Sanitize feature name for filename
        slug = feature_name.lower()
        slug = "".join(c if c.isalnum() or c in " -_" else "" for c in slug)
        slug = slug.replace(" ", "-")
        slug = slug[:50]  # Limit length

        date_str = datetime.now().strftime("%Y-%m-%d")
        return f"{slug}-{date_str}.md"

    def save_prd(self, prd_content: str, feature_name: str) -> str:
        """Save the PRD to a file.

        Args:
            prd_content: The PRD content to save
            feature_name: Name of the feature for filename

        Returns:
            Path to the saved PRD file
        """
        # Ensure output directory exists
        output_path = Path(self.prd_output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        filename = self.generate_prd_filename(feature_name)
        file_path = output_path / filename

        # Write the PRD
        result = write_file.invoke({
            "file_path": str(file_path),
            "content": prd_content,
        })

        if "Error" in result:
            return f"Error saving PRD: {result}"

        return str(file_path)

    def create_prd(self, feature_description: str, answers: dict = None) -> dict:
        """Create a PRD for a feature.

        Args:
            feature_description: Description of the feature
            answers: Optional pre-gathered answers to skip Q&A

        Returns:
            Dict with PRD content and file path
        """
        if answers:
            self.gathered_info = answers

        messages = [
            {
                "role": "user",
                "content": f"""Create a comprehensive Product Requirements Document for the following feature:

**Feature:** {feature_description}

**Gathered Information:**
{self._format_gathered_info()}

**Instructions:**
1. First, search the web for competitor information related to this feature
2. Search the codebase to understand existing patterns and technical context
3. Generate a complete PRD following the standard template

Please create the PRD now.""",
            }
        ]

        return self.invoke(messages)

    def _format_gathered_info(self) -> str:
        """Format gathered information for the prompt."""
        if not self.gathered_info:
            return "No additional information gathered yet."

        formatted = []
        for key, value in self.gathered_info.items():
            formatted.append(f"- **{key.replace('_', ' ').title()}**: {value}")

        return "\n".join(formatted)

    def analyze_feature(self, feature_description: str) -> dict:
        """Analyze a feature request before creating the PRD.

        Args:
            feature_description: Initial feature description

        Returns:
            Analysis including suggested questions and initial research
        """
        messages = [
            {
                "role": "user",
                "content": f"""Analyze this feature request and provide initial research:

**Feature:** {feature_description}

Tasks:
1. Search the codebase for any existing related functionality
2. Identify the key areas that need clarification
3. Suggest specific questions to ask the stakeholder
4. Do initial web search for similar features in other products

Provide your analysis.""",
            }
        ]

        return self.invoke(messages)

    def review_prd(self, prd_path: str) -> dict:
        """Review an existing PRD for completeness and quality.

        Args:
            prd_path: Path to the PRD file

        Returns:
            Review with suggestions for improvement
        """
        messages = [
            {
                "role": "user",
                "content": f"""Review the PRD at '{prd_path}' for completeness and quality.

Steps:
1. Read the PRD file
2. Check if all required sections are present
3. Verify requirements are specific and measurable
4. Check if acceptance criteria are testable
5. Suggest improvements

Provide your review with specific recommendations.""",
            }
        ]

        return self.invoke(messages)
