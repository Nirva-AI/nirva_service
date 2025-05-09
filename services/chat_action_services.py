from typing import List, Union
from fastapi import APIRouter
from services.game_server_instance import GameServerInstance
from models_v_0_0_1 import (
    ChatActionRequest,
    ChatActionResponse,
    # HomeGamePlayRequest,
    # HomeGamePlayResponse,
    # HomeTransDungeonRequest,
    # HomeTransDungeonResponse,
)
from loguru import logger
from llm_serves.chat_system import ChatSystem
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

# from game.web_tcg_game import WebTCGGame
from llm_serves.chat_request_handler import ChatRequestHandler

# from game.tcg_game import TCGGameState



###########################################################################################################################
# async def _test_gather() -> None:

#     server_url = "http://localhost:8100/v1/llm_serve/chat/"
#     chat_system = ChatSystem(
#         name="test_agent", user_name="yh", localhost_urls=[server_url]
#     )

#     test_prompt_data: Dict[str, str] = {
#         "agent1": "你好!你是谁",
#         "agent2": "德国的首都在哪里",
#         "agent3": "凯撒是哪国人？",
#     }

#     # 添加请求处理器
#     request_handlers: List[ChatRequestHandler] = []
#     for agent_name, prompt in test_prompt_data.items():
#         request_handlers.append(
#             ChatRequestHandler(name=agent_name, prompt=prompt, chat_history=[])
#         )

#     # 并发
#     await chat_system.gather(request_handlers=request_handlers)

#     for request_handler in request_handlers:
#         print(
#             f"Agent: {request_handler._name}, Response: {request_handler.response_content}"
#         )


###################################################################################################################################################################
chat_action_router = APIRouter()


###################################################################################################################################################################
###################################################################################################################################################################
###################################################################################################################################################################
# async def _execute_web_game(web_game: WebTCGGame) -> None:
#     assert web_game.player.name != ""
#     web_game.player.archive_and_clear_messages()
#     await web_game.a_execute()


###################################################################################################################################################################
###################################################################################################################################################################
###################################################################################################################################################################
@chat_action_router.post(path="/chat-action/v1/", response_model=ChatActionResponse)
async def handle_chat_action(
    request_data: ChatActionRequest,
    game_server: GameServerInstance,
) -> ChatActionResponse:

    logger.info(f"/chat-action/v1/: {request_data.model_dump_json()}")

    server_url = "http://localhost:8500/v1/llm_serve/chat/"
    chat_system = ChatSystem(
        name="nirva_agent",
        user_name=request_data.user_name,
        localhost_urls=[server_url],
    )

    chat_history: List[Union[SystemMessage, HumanMessage, AIMessage]] = []
    chat_history.append(
        SystemMessage(content="你需要扮演一个海盗与我对话，要用海盗的语气哦！")
    )

    try:
        chat_request_handler = ChatRequestHandler(
            name=request_data.user_name,
            prompt=request_data.content,
            chat_history=chat_history,
        )
        chat_system.handle(request_handlers=[chat_request_handler])
        chat_history.append(HumanMessage(content=request_data.content))
        chat_history.append(AIMessage(content=chat_request_handler.response_content))

        for msg in chat_history:
            logger.warning(msg.content)

        return ChatActionResponse(
            error=0,
            message=chat_request_handler.response_content,
        )

    except Exception as e:
        logger.error(f"Exception: {e}")
        # assert False, f"Error in processing user input = {e}"

    # 是否有房间？！！
    # room_manager = game_server.room_manager
    # if not room_manager.has_room(request_data.user_name):
    #     logger.error(
    #         f"home/gameplay/v1: {request_data.user_name} has no room, please login first."
    #     )
    #     return HomeGamePlayResponse(
    #         error=1001,
    #         message="没有登录，请先登录",
    #     )

    # # 是否有游戏？！！
    # current_room = room_manager.get_room(request_data.user_name)
    # assert current_room is not None
    # if current_room.game is None:
    #     logger.error(
    #         f"home/gameplay/v1: {request_data.user_name} has no game, please login first."
    #     )
    #     return HomeGamePlayResponse(
    #         error=1002,
    #         message="没有游戏，请先登录",
    #     )

    # web_game = current_room.game
    # assert web_game is not None
    # assert isinstance(web_game, WebTCGGame)

    # # 判断游戏状态，不是Home状态不可以推进。
    # if web_game.current_game_state != TCGGameState.HOME:
    #     logger.error(
    #         f"home/gameplay/v1: {request_data.user_name} game state error = {web_game.current_game_state}"
    #     )
    #     return HomeGamePlayResponse(
    #         error=1004,
    #         message=f"{request_data.user_input} 只能在营地中使用",
    #     )

    # # 根据标记处理。
    # match request_data.user_input.tag:

    #     case "/advancing":
    #         # 推进一次。
    #         await _execute_web_game(web_game)

    #         # 返回消息
    #         return HomeGamePlayResponse(
    #             client_messages=web_game.player.client_messages,
    #             error=0,
    #             message=request_data.model_dump_json(),
    #         )

    #     case "/speak":

    #         # player 添加说话的动作
    #         if web_game.activate_speak_action(
    #             target=request_data.user_input.data.get("target", ""),
    #             content=request_data.user_input.data.get("content", ""),
    #         ):

    #             # 清空消息。准备重新开始 + 测试推进一次游戏
    #             await _execute_web_game(web_game)

    #             # 返回消息
    #             return HomeGamePlayResponse(
    #                 client_messages=web_game.player.client_messages,
    #                 error=0,
    #                 message=request_data.model_dump_json(),
    #             )

    #     case _:
    #         logger.error(f"未知的请求类型 = {request_data.user_input.tag}, 不能处理！")

    return ChatActionResponse(
        error=1000,
        message="未知的请求类型, 不能处理！",
    )


###################################################################################################################################################################
###################################################################################################################################################################
###################################################################################################################################################################
# @chat_action_router.post(
#     path="/home/trans_dungeon/v1/", response_model=HomeTransDungeonResponse
# )
# async def home_trans_dungeon(
#     request_data: HomeTransDungeonRequest,
#     game_server: GameServerInstance,
# ) -> HomeTransDungeonResponse:

#     logger.info(f"/home/trans_dungeon/v1/: {request_data.model_dump_json()}")

#     # 是否有房间？！！
#     room_manager = game_server.room_manager
#     if not room_manager.has_room(request_data.user_name):
#         logger.error(
#             f"home_trans_dungeon: {request_data.user_name} has no room, please login first."
#         )
#         return HomeTransDungeonResponse(
#             error=1001,
#             message="没有登录，请先登录",
#         )

#     # 是否有游戏？！！
#     current_room = room_manager.get_room(request_data.user_name)
#     assert current_room is not None
#     if current_room.game is None:
#         logger.error(
#             f"home_trans_dungeon: {request_data.user_name} has no game, please login first."
#         )
#         return HomeTransDungeonResponse(
#             error=1002,
#             message="没有游戏，请先登录",
#         )

#     web_game = current_room.game
#     assert web_game is not None
#     assert isinstance(web_game, WebTCGGame)

#     # 判断游戏状态，不是Home状态不可以推进。
#     if web_game.current_game_state != TCGGameState.HOME:
#         logger.error(
#             f"home_trans_dungeon: {request_data.user_name} game state error = {web_game.current_game_state}"
#         )
#         return HomeTransDungeonResponse(
#             error=1004,
#             message="trans_dungeon只能在营地中使用",
#         )

#     # 判断地下城是否存在
#     if len(web_game.current_dungeon.levels) == 0:
#         logger.warning(
#             "没有地下城可以传送, 全部地下城已经结束。！！！！已经全部被清空！！！！或者不存在！！！！"
#         )
#         return HomeTransDungeonResponse(
#             error=1005,
#             message="没有地下城可以传送, 全部地下城已经结束。！！！！已经全部被清空！！！！或者不存在！！！！",
#         )

#     # 传送地下城执行。
#     if not web_game.launch_dungeon():
#         logger.error("第一次地下城传送失败!!!!")
#         return HomeTransDungeonResponse(
#             error=1006,
#             message="第一次地下城传送失败!!!!",
#         )
#     #
#     return HomeTransDungeonResponse(
#         error=0,
#         message=request_data.model_dump_json(),
#     )


###################################################################################################################################################################
###################################################################################################################################################################
###################################################################################################################################################################
