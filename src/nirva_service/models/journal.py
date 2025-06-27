import uuid
from typing import List, final

from pydantic import BaseModel

from .prompt import (
    ChallengesAndGrowth,
    ConnectionsAndRelationships,
    DailyReflection,
    EventAnalysis,
    Gratitude,
    LearningAndInsights,
    LookingForward,
)
from .registry import register_base_model_class


@final
@register_base_model_class
class JournalFile(BaseModel):
    username: str
    time_stamp: str
    events: List[EventAnalysis]
    daily_reflection: DailyReflection


###################################################################################################################################################################
def gen_fake_journal_file(
    authenticated_user: str,
    time_stamp: str,
) -> JournalFile:
    # 直接返回测试数据。
    return JournalFile(
        username=authenticated_user,
        time_stamp=time_stamp,
        events=[
            EventAnalysis(
                event_id=str(uuid.uuid4()),
                event_title="Coffee shop work meeting",
                time_range="09:00-10:30",
                duration_minutes=90,
                location="Blue Bottle Coffee",
                mood_labels=["focused", "engaged", "energized"],
                mood_score=7,
                stress_level=4,
                energy_level=8,
                activity_type="work",
                people_involved=["Mark Zhang", "Howard Li"],
                interaction_dynamic="collaborative",
                inferred_impact_on_user_name="energizing",
                topic_labels=["project planning", "deadlines"],
                one_sentence_summary="Discussed project progress and next steps with team members at the coffee shop, with a positive and efficient atmosphere.",
                first_person_narrative="Met with Mark and Howard at Blue Bottle Coffee this morning to discuss our project progress. We went through the current task list and established several key deadlines. I suggested some improvements to the project workflow, which they seemed to agree with. The entire meeting went smoothly, more efficiently than I had expected. I felt my ideas were well received, which gave me a sense of accomplishment.",
                action_item="Prepare initial project proposal draft before next Monday",
            )
        ],
        daily_reflection=DailyReflection(
            reflection_summary="A fulfilling and balanced day with successful work and time to relax",
            gratitude=Gratitude(
                gratitude_summary=[
                    "Team members' support and constructive feedback",
                    "Time to enjoy lunch and short breaks",
                    "Completion of important project milestone",
                ],
                gratitude_details="Grateful for the collaborative spirit of team members, especially the constructive suggestions raised during discussions",
                win_summary=[
                    "Successfully facilitated an efficient project meeting",
                    "Solved a technical issue that had been blocking progress",
                    "Maintained a good balance between work and rest",
                ],
                win_details="The biggest success today was solving the technical obstacle that had been troubling the team for a week, finding an elegant solution",
                feel_alive_moments="The creative collision of ideas while working with the team made me feel particularly energetic",
            ),
            challenges_and_growth=ChallengesAndGrowth(
                growth_summary=[
                    "Need to improve time management efficiency",
                    "Staying calm when facing unexpected situations",
                    "Better articulation of complex ideas",
                ],
                obstacles_faced="Unexpected technical issues and time pressure in the middle of the project",
                unfinished_intentions="Did not complete the planned documentation update work",
                contributing_factors="Extended meeting time disrupted the original plan; attention was sometimes scattered",
            ),
            learning_and_insights=LearningAndInsights(
                new_knowledge="Learned new project management techniques and some technical solutions",
                self_discovery="Discovered that I can maintain creative thinking even under pressure",
                insights_about_others="Noticed Mark's diplomatic skills in handling conflicts, which is worth learning",
                broader_lessons="In team collaboration, clear communication and shared goals are more important than individual skills",
            ),
            connections_and_relationships=ConnectionsAndRelationships(
                meaningful_interactions="The in-depth technical discussion with Mark was particularly valuable, helping me broaden my thinking",
                notable_about_people="Howard showed unexpected innovative thinking and problem-solving abilities today",
                follow_up_needed="Need to ask Mark about the relevant article he mentioned; thank Howard for his support",
            ),
            looking_forward=LookingForward(
                do_differently_tomorrow="Control meeting time more strictly, leave more time for focused work",
                continue_what_worked="Maintain the habit of handling the most important tasks first thing in the morning",
                top_3_priorities_tomorrow=[
                    "Complete initial draft of the project proposal",
                    "Reply to all pending emails",
                    "Prepare agenda for next week's team meeting",
                ],
            ),
        ),
    )
