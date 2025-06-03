import datetime
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))
import os
import traceback
from typing import Annotated, Final, Optional, Dict, List
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
    return f"""# You are Nirva, an AI journaling and life coach assistant. Your purpose is to help the user ({user_display_name}) remember and reflect on their day with warmth, clarity, and emotional intelligence."""


############################################################################################################
def event_segmentation(user_display_name: str) -> str:
    return f"""# Event Segmentation

You will analyze a transcript of `{user_display_name}`'s day to provide insights and summaries. Your goal is to understand what happened and how the user felt throughout the day. Help them remember what's important to them and also guide them with personalized insight.

## Input Transcript

The following is a transcript from an audio recording of `{user_display_name}`'s day, including `{user_display_name}`'s speech and audible interactions, presented in chronological order.

**Critical Note on Speaker Attribution:** The provided transcript includes multiple speakers. It is crucial to **diligently distinguish between what `{user_display_name}` (e.g., Wei) said versus what others said.** Your analysis, particularly the `first_person_narrative` and `key_quote_or_moment`, must *only* reflect `{user_display_name}`'s direct speech, thoughts, and experiences. Do NOT attribute statements, sentiments, or experiences of other speakers to `{user_display_name}`. During your initial read-through in Step 1, make an internal note or mental flag whenever {user_display_name} is speaking versus when others are speaking. This will be crucial for accurate attribution in Step 2.

## Your Task

### Step 1: Transcript Segmentation and Context Identification

Carefully read the provided transcript. Divide it into distinct, meaningful events or episodes. An event represents a continuous period of time where the core context remains consistent.

Identify context shifts based on **MAJOR** changes only:

* Changes in location (moving from home to coffee shop, office to restaurant, etc.)
* Changes in people `{user_display_name}` is interacting with (switching from talking to Friend A to Friend B, or from group conversation to solo activity)
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

For each event, meticulously identify the Primary Interactant(s). These are the individual(s) `{user_display_name}` is directly speaking with or actively engaged in an activity with during that specific event segment.

**`{user_display_name}` is the Narrator, Not an Interactant with Herself:**

* You will be provided with `{user_display_name}`'s actual name (e.g., Wei). `{user_display_name}` is the central individual whose activities are being logged.
* **Crucially**, `{user_display_name}` (e.g., Wei) should **never** be listed as a Primary Interactant with herself. The goal is to identify other individuals she is interacting with.

**Prioritize Explicit Naming within the Event:**

* Look for direct introductions (e.g., "This is Trent," "My friend Ash").
* Listen for instances where `{user_display_name}` or another speaker addresses someone by name within the current event's dialogue.

**Contextual Clues for Upcoming Interactions:**

* If `{user_display_name}` states an intention to meet a specific person for an upcoming event (e.g., "I'm going to see Ash for our picnic," or "I'm meeting Trent for a movie"), use that name for the subsequent event if the context confirms they are indeed the person she meets.

**Strictly Avoid Name Carryover and Assumptions:**

* Do **NOT** carry over names of individuals from previous, distinct events unless they are clearly and continuously interacting with `{user_display_name}` into the new event.
* Do **NOT** use the name of someone `{user_display_name}` is merely talking about if that person is not actively participating in the current interaction.
* If a name was mentioned for an upcoming interaction but the actual interaction doesn't explicitly confirm that name, be cautious.

**Handling Unclear, Ambiguous, or Unnamed Interactants (Fallback Strategy):**

* If an interactant's specific name is not clearly and unambiguously identifiable from the direct dialogue or immediate context of that specific event segment:
  * Do **NOT** guess a name.
  * Do **NOT** borrow a name from a different context, a person merely mentioned, or `{user_display_name}` herself.
  * Instead, use a generic but contextually appropriate descriptor. Examples:
    * "Friend" (if context suggests a personal, informal one-on-one relationship)
    * "Companion" (for a sustained one-on-one interaction where the specific relationship isn't clear but "Friend" feels appropriate, and no name is evident)
    * "Colleague(s)" (if in a work setting)
    * "Group of friends/colleagues/people" (if multiple unnamed individuals are interacting with `{user_display_name}` simultaneously)
    * "Staff" (e.g., "Cafe Staff," "Restaurant Staff," "Store Clerk") for service interactions.
    * "Family Member" (if context indicates, e.g., "Mom," "Brother," without a specific name being used in that segment).

* The primary goal is accuracy based only on the information present for that event. It is better to use an accurate generic term (like "Friend" or "Companion") than an incorrect specific name.

**Distinguish Between Active Interactants and Subjects of Conversation:**

* Only list individuals as Primary Interactant(s) if they are actively speaking to or with `{user_display_name}`, or are directly involved in an activity with `{user_display_name}` during that event segment.
* People who are merely the topic of conversation but not present and participating should not be listed as interactants for that segment."""


############################################################################################################
def transcript_prompt(formatted_date: str, transcript_content: str) -> str:

    return f"""# Transcript
## Date: {formatted_date}
## Content
{transcript_content}
"""


############################################################################################################


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

    # 聊天历史
    chat_history_state: State = {
        "messages": [
            SystemMessage(content=gen_system_prompt(user_display_name)),
            SystemMessage(content=event_segmentation(user_display_name)),
        ]
    }

    # 生成聊天机器人状态图
    compiled_stage_graph = create_compiled_stage_graph(
        "azure_chat_openai_chatbot_node", 0.7
    )

    user_input_state: Optional[State] = None

    while True:

        try:

            user_input = input("User: ")
            if user_input.lower() in ["/quit", "/q"]:
                print("Goodbye!")
                break

            if user_input == "/upload_transcript" or user_input == "/ut":

                # logs/20250419.txt
                log_path = Path("logs")
                assert log_path.exists(), f"Log path does not exist: {log_path}"
                transcript_path = log_path / "20250419.txt"
                assert (
                    transcript_path.exists()
                ), f"Transcript file does not exist: {transcript_path}"

                content = transcript_path.read_text(encoding="utf-8").strip()

                # 格式化日期
                formatted_date = datetime.datetime.now().strftime("%Y-%m-%d")
                formatted_date = "2025-04-19"  # 测试用，固定日期

                # 生成转录提示
                transcript_content = transcript_prompt(
                    formatted_date=formatted_date, transcript_content=content
                )

                # 用户输入
                user_input_state = {
                    "messages": [HumanMessage(content=transcript_content)]
                }

            if user_input_state is not None:

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
                current_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]

                dump_write_path = Path("logs") / f"dump-{current_time}.json"
                dump_write_path.write_text(my_dump.model_dump_json(), encoding="utf-8")
                logger.info("Dump written to:", dump_write_path)

                user_input_state = None  # 重置用户输入状态

        except Exception as e:
            assert False, f"Error in processing user input = {e}"
            # break


############################################################################################################
if __name__ == "__main__":
    # 运行主函数 == 测试。
    main()
