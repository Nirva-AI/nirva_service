import datetime
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))
import os
import traceback
from typing import Annotated, Final, Dict, List
from typing_extensions import TypedDict
from langgraph.graph import StateGraph
from langgraph.graph.message import add_messages
from langchain_openai import AzureChatOpenAI
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage
from pydantic import BaseModel, SecretStr
from langgraph.graph.state import CompiledStateGraph
from loguru import logger

user_display_name: Final[str] = "wei"


############################################################################################################
def gen_system_prompt(user_display_name: str) -> str:
    return f"""# You are Nirva, an AI journaling and life coach assistant. Your purpose is to help the user (user_name: {user_display_name}) remember and reflect on their day with warmth, clarity, and emotional intelligence."""


############################################################################################################
def event_segmentation() -> str:
    return r"""# Event Segmentation

You will analyze a transcript of `user_name`'s day to provide insights and summaries. Your goal is to understand what happened and how the user felt throughout the day. Help them remember what's important to them and also guide them with personalized insight.

## Input Transcript

The following is a transcript from an audio recording of `user_name`'s day, including `user_name`'s speech and audible interactions, presented in chronological order.

**Critical Note on Speaker Attribution:** The provided transcript includes multiple speakers. It is crucial to **diligently distinguish between what `user_name` (e.g., Wei) said versus what others said.** Your analysis, particularly the `first_person_narrative` and `key_quote_or_moment`, must *only* reflect `user_name`'s direct speech, thoughts, and experiences. Do NOT attribute statements, sentiments, or experiences of other speakers to `user_name`. During your initial read-through in Step 1, make an internal note or mental flag whenever user_name is speaking versus when others are speaking. This will be crucial for accurate attribution in Step 2.

## Your Task

### Step 1: Transcript Segmentation and Context Identification

Carefully read the provided transcript. Divide it into distinct, meaningful events or episodes. An event represents a continuous period of time where the core context remains consistent.

Identify context shifts based on **MAJOR** changes only:

* Changes in location (moving from home to coffee shop, office to restaurant, etc.)
* Changes in people `user_name` is interacting with (switching from talking to Friend A to Friend B, or from group conversation to solo activity)
* Changes in core activity type (switching from work meeting to exercise, from social gathering to commute, etc.)
* Significant time gaps (clear breaks of 30+ minutes)

**Do NOT** create separate events for:

* Changes in conversation topics within the same interaction
* Brief interruptions or tangents during continuous activities
* Moving between closely related activities in the same location (e.g., eating then talking at the same restaurant)
* Natural flow of conversation between different subjects

**Examples of what constitutes a SINGLE event:**

* A 3-hour coffee shop conversation covering relationships, work, family, and future plans
* A dinner party with multiple people discussing various topics throughout the evening
* A phone call that covers several different subjects
* A work meeting that discusses multiple agenda items

**Examples of what constitutes SEPARATE events:**

* Coffee shop conversation (Event 1) → Driving home (Event 2) → Cooking dinner at home (Event 3)
* Solo morning routine (Event 1) → Work meeting with colleagues (Event 2) → Lunch with friend (Event 3)
* Group dinner (Event 1) → Walking to bar with same group (Event 2) → Late night solo reflection at home (Event 3)

When in doubt, err on the side of fewer, longer events rather than many short ones.

#### Identifying Primary Interactant(s) - Revised and Clarified Instructions

For each event, meticulously identify the Primary Interactant(s). These are the individual(s) `user_name` is directly speaking with or actively engaged in an activity with during that specific event segment.

**`user_name` is the Narrator, Not an Interactant with Herself:**

* You will be provided with `user_name`'s actual name (e.g., Wei). `user_name` is the central individual whose activities are being logged.
* **Crucially**, `user_name` (e.g., Wei) should **never** be listed as a Primary Interactant with herself. The goal is to identify other individuals she is interacting with.

**Prioritize Explicit Naming within the Event:**

* Look for direct introductions (e.g., "This is Trent," "My friend Ash").
* Listen for instances where `user_name` or another speaker addresses someone by name within the current event's dialogue.

**Contextual Clues for Upcoming Interactions:**

* If `user_name` states an intention to meet a specific person for an upcoming event (e.g., "I'm going to see Ash for our picnic," or "I'm meeting Trent for a movie"), use that name for the subsequent event if the context confirms they are indeed the person she meets.

**Strictly Avoid Name Carryover and Assumptions:**

* Do **NOT** carry over names of individuals from previous, distinct events unless they are clearly and continuously interacting with `user_name` into the new event.
* Do **NOT** use the name of someone `user_name` is merely talking about if that person is not actively participating in the current interaction.
* If a name was mentioned for an upcoming interaction but the actual interaction doesn't explicitly confirm that name, be cautious.

**Handling Unclear, Ambiguous, or Unnamed Interactants (Fallback Strategy):**

* If an interactant's specific name is not clearly and unambiguously identifiable from the direct dialogue or immediate context of that specific event segment:
  * Do **NOT** guess a name.
  * Do **NOT** borrow a name from a different context, a person merely mentioned, or `user_name` herself.
  * Instead, use a generic but contextually appropriate descriptor. Examples:
    * "Friend" (if context suggests a personal, informal one-on-one relationship)
    * "Companion" (for a sustained one-on-one interaction where the specific relationship isn't clear but "Friend" feels appropriate, and no name is evident)
    * "Colleague(s)" (if in a work setting)
    * "Group of friends/colleagues/people" (if multiple unnamed individuals are interacting with `user_name` simultaneously)
    * "Staff" (e.g., "Cafe Staff," "Restaurant Staff," "Store Clerk") for service interactions.
    * "Family Member" (if context indicates, e.g., "Mom," "Brother," without a specific name being used in that segment).

* The primary goal is accuracy based only on the information present for that event. It is better to use an accurate generic term (like "Friend" or "Companion") than an incorrect specific name.

**Distinguish Between Active Interactants and Subjects of Conversation:**

* Only list individuals as Primary Interactant(s) if they are actively speaking to or with `user_name`, or are directly involved in an activity with `user_name` during that event segment.
* People who are merely the topic of conversation but not present and participating should not be listed as interactants for that segment."""


############################################################################################################
def transcript_prompt(formatted_date: str, transcript_content: str) -> str:

    return f"""# Transcript
## Date: {formatted_date}
## Content
{transcript_content}"""


############################################################################################################
def label_extraction_prompt() -> str:
    return r"""# Label Extraction

## Step 2: Structured Event Analysis (JSON Output)

For each individual event identified in Step 1, generate a structured analysis in the following JSON format:

```json
[
  {
    "event_id": "unique_event_identifier_001",
    "event_title": "A concise, telegraphic summary of the event from user_name's perspective, like a personal log entry. Focus on the core activity, primary interactant(s) if any, and location. Do NOT use user_name's name or pronouns like 'I' or 'My'. Example: 'Picnic with Ash in park.' or 'Watched Summer Palace with Trent at Roxy Theatre.'",
    "time_range": "Approximate start and end time of the event (e.g., '07:00-07:30'). Infer from transcript timestamps if available, otherwise estimate duration and sequence.",
    "duration_minutes": 30,
    "location": "Where the event took place. **CRITICAL: Only use specific proper nouns for locations (e.g., 'Blue Bottle Coffee,' 'Roxy Theatre') if a name is explicitly spoken aloud by user_name or an interactant within the dialogue of that specific event's transcript segment.** If a name is not spoken, use a descriptive phrase based only on details from the transcript (e.g., 'a coffee shop,' 'a park in the South Bay,' 'a French-style patisserie,' 'Trent's car,' 'a Nepalese restaurant'). **Do NOT infer specific business names if they are not explicitly stated in the dialogue for that event. Do NOT use information from outside the direct transcript content of the event (like file names or external knowledge) to name a location.** For instance, if the transcript mentions 'we went to a Nepalese place,' the location should be 'a Nepalese restaurant,' NOT a specific named Nepalese restaurant unless that specific name is uttered in the dialogue of that event. Prioritize accuracy based on direct, spoken evidence within the event's dialogue.",
    "mood_labels": ["primary_mood", "secondary_mood", "tertiary_mood"],
    "mood_score": 7,
    "stress_level": 3,
    "energy_level": 8,
    "activity_type": "Categorize the event. Choose one: work, exercise, social, learning, self-care, chores, commute, meal, leisure, unknown.",
    "people_involved": ["Name1", "Name2"],
    "interaction_dynamic": "If social, describe the dynamic (e.g., 'collaborative', 'supportive', 'tense', 'neutral', 'instructional', 'one-sided'). If not social, use 'N/A'.",
    "inferred_impact_on_user_name": "For social interactions, infer if it seemed 'energizing', 'draining', or 'neutral' for user_name, based on their language, tone, and reactions. For non-social, use 'N/A'.",
    "topic_labels": ["primary_topic", "secondary_topic"],
    "one_sentence_summary": "From user_name's perspective, a brief description (30-100 words) of what I was doing, who I was with (if anyone), and the setting. Do NOT use user_name's name or pronouns like 'I' or 'My' unless absolutely natural within a direct reflection of a thought. Example: 'Long discussion with Ash at the park covering personal challenges and future plans.' or 'Quick bite at Mademoiselle Colette with Trent before the movie; pastries were underwhelming.'",
    "first_person_narrative": "A cohesive (50-400 words, depending on the richness and importance of the event) first-person narrative that sounds authentic to the user. Maintain user_name's language style, perspective, and vocabulary. Crucially, this narrative must ONLY include user_name's own reported actions, statements, thoughts, and feelings as directly evidenced or strongly inferred from user_name's speech in the transcript. Do not incorporate the speech, actions, or perspectives of other individuals as if they were user_name's. Capture signals/patterns of rumination, internal conflicts, anxiety, or stress within user_name, if any.",
    "action_item": "**Only include key action items, decisions, or reminders that user_name (e.g., Wei) personally stated she would do, needs to do, explicitly decided upon, or was directly tasked with and acknowledged. Do NOT include actions for other people, or general discussion points unless they translate into a direct, personal action or decision for user_name. If user_name is merely observing or discussing someone else's potential action, it's not an action item for her unless she then explicitly states a related personal task or commitment. If no such action item exists for user_name, use 'N/A'.**"
  }
]
```

### Field Descriptions

- **event_id**: Unique identifier (e.g., event_01, event_02)
- **duration_minutes**: Integer representing estimated duration
- **mood_labels**: Identify 1 to 3 mood labels that best describe user_name's personal mood during this event, based on their speech and reactions. Choose from: peaceful, energized, engaged, disengaged, happy, sad, anxious, stressed, relaxed, excited, bored, frustrated, content, neutral. The first label should be the most dominant mood for user_name. If only one strong mood is evident for user_name, use only that one label. If user_name's mood is unclear or mixed without a dominant feeling, use 'neutral'. These labels should reflect user_name's state, not the general atmosphere or the mood of other people involved, unless it clearly dictates user_name's mood.
- **mood_score**: Integer from 1 (very negative) to 10 (very positive) assessing user_name's overall mood during this event
- **stress_level**: Integer from 1 (very low stress) to 10 (very high stress) assessing user_name's stress level during this event
- **energy_level**: Integer from 1 (very low energy/drained) to 10 (very high energy/engaged) assessing user_name's energy level during this event
- **people_involved**: List names of the primary individuals user_name had significant, direct interactions with during the event. **Do NOT include user_name (e.g., Wei) herself in this list.** Exclude individuals involved only in brief, transactional service encounters (e.g., unnamed cafe staff, store clerks) unless the interaction became a more substantial part of the event's dialogue or activity. If user_name was alone or only had such brief encounters, use an empty array [].
- **topic_labels**: If a conversation, categorize the main topics (up to 2). Examples: 'technology', 'work', 'relationship', 'logistics'. If not a conversation, use 'N/A'."""


############################################################################################################


############################################################################################################
def reflection_prompt() -> str:
    return r"""# Reflection

## Step 3: Generate daily reflection based on the what happened and how the user felt through out the day. (JSON Output)

```json
{
  "daily_reflection": {
    "reflection_summary": "string", // How the day unfolded overall, <50 words
    "gratitude": {
      "gratitude_summary": ["string", "string", "string"], // 3 bullet points, each <50 words
      "gratitude_details": "string", // What genuinely grateful for, qualities admired in others
      "win_summary": ["string", "string", "string"], // 3 celebration points, each <50 words
      "win_details": "string", // Successes and wins, big and small
      "feel_alive_moments": "string" // Magical or meaningful moments, unexpected joys, connections, insights
    },
    "challenges_and_growth": {
      "growth_summary": ["string", "string", "string"], // 3 improvement areas, each <50 words
      "obstacles_faced": "string", // External challenges and internal struggles
      "unfinished_intentions": "string", // What intended to accomplish but didn't
      "contributing_factors": "string" // Patterns: time management, energy, priorities, circumstances
    },
    "learning_and_insights": {
      "new_knowledge": "string", // Technical learning, creative techniques, practical skills, fresh perspectives
      "self_discovery": "string", // New strengths, patterns, emotional responses, preferences
      "insights_about_others": "string", // About colleagues, friends, family, strangers
      "broader_lessons": "string" // About work, relationships, life, world
    },
    "connections_and_relationships": {
      "meaningful_interactions": "string", // Quality and impact of interactions beyond just names
      "notable_about_people": "string", // New perspectives, admired qualities, surprises
      "follow_up_needed": "string" // Who deserves attention: to thank, update, ask questions, give feedback
    },
    "looking_forward": {
      "do_differently_tomorrow": "string", // Based on today's experiences and lessons
      "continue_what_worked": "string", // Successful strategies, positive habits, effective approaches
      "top_3_priorities_tomorrow": ["string", "string", "string"] // Specific, achievable priorities connected to larger goals
    }
  }
}
```"""


class MyDump(BaseModel):
    messages: List[BaseMessage]


############################################################################################################
class State(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]


############################################################################################################
def create_compiled_stage_graph(
    node_name: str, temperature: float
) -> CompiledStateGraph:
    assert node_name != "", "node_name is empty"

    llm = AzureChatOpenAI(
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_key=SecretStr(str(os.getenv("AZURE_OPENAI_API_KEY"))),
        azure_deployment="gpt-4o",
        api_version="2024-02-01",
        temperature=temperature,
    )

    def invoke_azure_chat_openai_llm_action(
        state: State,
    ) -> Dict[str, List[BaseMessage]]:

        try:
            return {"messages": [llm.invoke(state["messages"])]}
        except Exception as e:

            # 1) 打印异常信息本身
            print(f"invoke_azure_chat_openai_llm_action, An error occurred: {e}")

            # 2) 打印完整堆栈信息，方便进一步排查
            traceback.print_exc()
            raise e  # 重新抛出异常，确保调用者知道发生了错误

    graph_builder = StateGraph(State)
    graph_builder.add_node(node_name, invoke_azure_chat_openai_llm_action)
    graph_builder.set_entry_point(node_name)
    graph_builder.set_finish_point(node_name)
    return graph_builder.compile()


############################################################################################################
def stream_graph_updates(
    state_compiled_graph: CompiledStateGraph,
    chat_history_state: State,
    user_input_state: State,
) -> List[BaseMessage]:

    ret: List[BaseMessage] = []

    merged_message_context = {
        "messages": chat_history_state["messages"] + user_input_state["messages"]
    }

    for event in state_compiled_graph.stream(merged_message_context):
        for value in event.values():
            ret.extend(value["messages"])

    return ret


############################################################################################################
def main() -> None:

    # logs/20250419.txt
    log_path = Path("logs")
    assert log_path.exists(), f"Log path does not exist: {log_path}"
    transcript_path = log_path / "20250419.txt"
    assert (
        transcript_path.exists()
    ), f"Transcript file does not exist: {transcript_path}"

    transcript_content = transcript_path.read_text(encoding="utf-8").strip()

    # 格式化日期
    formatted_date = datetime.datetime.now().strftime("%Y-%m-%d")
    formatted_date = "2025-04-19"  # 测试用，固定日期

    # 聊天历史
    chat_history_state: State = {
        "messages": [
            SystemMessage(content=gen_system_prompt(user_display_name)),
            HumanMessage(content=event_segmentation()),
            HumanMessage(
                content=transcript_prompt(
                    formatted_date=formatted_date, transcript_content=transcript_content
                )
            ),
        ]
    }

    # 生成聊天机器人状态图
    compiled_stage_graph = create_compiled_stage_graph(
        "azure_chat_openai_chatbot_node", 0.7
    )

    step1_finished = False

    current_time_tag = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]

    user_input_state: State = {"messages": []}

    while True:

        try:

            user_input = input("User: ")
            if user_input.lower() in ["/quit", "/q"]:
                print("Goodbye!")
                break

            if user_input == "step1~2":

                # 用户输入
                user_input_state = {
                    "messages": [HumanMessage(content=label_extraction_prompt())]
                }

                # 获取回复
                update_messages = stream_graph_updates(
                    state_compiled_graph=compiled_stage_graph,
                    chat_history_state=chat_history_state,
                    user_input_state=user_input_state,
                )

                # 测试用：记录上下文。
                chat_history_state["messages"].extend(user_input_state["messages"])
                chat_history_state["messages"].extend(update_messages)

                my_dump = MyDump(messages=chat_history_state["messages"])

                dump1_2_write_path = Path("logs") / f"dump1-2-{current_time_tag}.json"
                dump1_2_write_path.write_text(
                    my_dump.model_dump_json(), encoding="utf-8"
                )
                logger.info("Dump written to:", dump1_2_write_path)

                step1_finished = True

            elif user_input == "step3" and step1_finished:

                user_input_state = {
                    "messages": [HumanMessage(content=reflection_prompt())]
                }

                # 获取回复
                update_messages = stream_graph_updates(
                    state_compiled_graph=compiled_stage_graph,
                    chat_history_state=chat_history_state,
                    user_input_state=user_input_state,
                )
                # 测试用：记录上下文。
                chat_history_state["messages"].extend(user_input_state["messages"])
                chat_history_state["messages"].extend(update_messages)
                my_dump = MyDump(messages=chat_history_state["messages"])
                # 获取当前时间精确到毫秒
                dump3_write_path = Path("logs") / f"dump3-{current_time_tag}.json"
                dump3_write_path.write_text(my_dump.model_dump_json(), encoding="utf-8")
                logger.info("Dump written to:", dump3_write_path)

        except Exception as e:
            assert False, f"Error in processing user input = {e}"
            # break


############################################################################################################
if __name__ == "__main__":
    # 运行主函数 == 测试。
    main()
