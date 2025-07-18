import datetime
import json
import os

# import sys
import traceback
from pathlib import Path
from typing import Annotated, Dict, List, cast

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_openai import AzureChatOpenAI
from langgraph.graph import StateGraph
from langgraph.graph.message import add_messages
from langgraph.graph.state import CompiledStateGraph
from loguru import logger
from pydantic import BaseModel, SecretStr
from typing_extensions import TypedDict

import nirva_service.prompts.builtin as builtin
import nirva_service.utils.format_string as format_string
from nirva_service.config.account import FAKE_USER


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
            logger.error(f"invoke_azure_chat_openai_llm_action, An error occurred: {e}")

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
            SystemMessage(
                content=builtin.user_session_system_message(
                    FAKE_USER.username, FAKE_USER.display_name
                )
            ),
            HumanMessage(content=builtin.event_segmentation_message()),
            HumanMessage(
                content=builtin.transcript_message(
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
                    "messages": [
                        HumanMessage(content=builtin.label_extraction_message())
                    ]
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

                label_extraction_response_path = (
                    Path("logs") / f"dump1-2-{current_time_tag}.json"
                )
                label_extraction_response_path.write_text(
                    my_dump.model_dump_json(), encoding="utf-8"
                )
                logger.info("Dump written to:", label_extraction_response_path)

                step1_finished = True

                if len(update_messages):
                    # 提取 JSON 内容
                    json_content = format_string.extract_json_from_codeblock(
                        cast(str, update_messages[-1].content)
                    )
                    if json_content:
                        # 解析 JSON 内容
                        try:
                            label_extraction_response = (
                                builtin.LabelExtractionResponse.model_validate_json(
                                    json_content
                                )
                            )
                            logger.info(
                                "Label extraction response:", label_extraction_response
                            )
                            label_extraction_response_path = (
                                Path("logs")
                                / f"label_extraction_response-{current_time_tag}.json"
                            )
                            label_extraction_response_path.write_text(
                                label_extraction_response.model_dump_json(),
                                encoding="utf-8",
                            )
                        except json.JSONDecodeError as e:
                            logger.error(f"Failed to parse JSON: {e}")
                    else:
                        logger.warning("No JSON content found in the last message.")

            elif user_input == "step3" and step1_finished:
                user_input_state = {
                    "messages": [HumanMessage(content=builtin.reflection_message())]
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

                if len(update_messages):
                    # 提取 JSON 内容
                    json_content = format_string.extract_json_from_codeblock(
                        cast(str, update_messages[-1].content)
                    )
                    if json_content:
                        # 解析 JSON 内容
                        try:
                            reflection_response = (
                                builtin.ReflectionResponse.model_validate_json(
                                    json_content
                                )
                            )
                            logger.info("Reflection response:", reflection_response)
                            reflection_response_path = (
                                Path("logs")
                                / f"reflection_response-{current_time_tag}.json"
                            )
                            reflection_response_path.write_text(
                                reflection_response.model_dump_json(), encoding="utf-8"
                            )
                        except json.JSONDecodeError as e:
                            logger.error(f"Failed to parse JSON: {e}")
                    else:
                        logger.warning("No JSON content found in the last message.")

        except Exception as e:
            assert False, f"Error in processing user input = {e}"
            # break


############################################################################################################
if __name__ == "__main__":
    # 运行主函数 == 测试。
    main()
