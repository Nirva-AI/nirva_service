import json
import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime

from loguru import logger

from ...models.journal import JournalFile
from ...models.prompt import EventAnalysis
from ...models.api import IncrementalAnalyzeResponse
from ...db.pgsql_journal_file import get_journal_file, save_or_update_journal_file
from ..langgraph_services.langgraph_request_task import LanggraphRequestTask
from ..langgraph_services.langgraph_service import LanggraphService


###############################################################################################################################################
class IncrementalAnalyzer:
    """增量分析处理器"""
    
    def __init__(self, langgraph_service: LanggraphService):
        self.langgraph_service = langgraph_service
    
    
    async def process_incremental_transcript(
        self, 
        username: str,
        time_stamp: str,
        new_transcript: str
    ) -> IncrementalAnalyzeResponse:
        """
        处理增量转录内容
        
        Args:
            username: 用户名
            time_stamp: 日期时间戳
            new_transcript: 新的转录内容
            
        Returns:
            IncrementalAnalyzeResponse: 处理结果
        """
        
        logger.info(f"开始处理用户 {username} 在 {time_stamp} 的增量转录")
        
        # 1. 获取现有的JournalFile
        existing_journal = await self._get_existing_journal(username, time_stamp)
        
        # 2. 如果没有现有日记，创建新的
        if not existing_journal:
            return await self._create_initial_journal(username, time_stamp, new_transcript)
        
        # 3. 分析新转录内容与现有事件的关系
        analysis_result = await self._analyze_incremental_content(
            existing_journal.events, new_transcript
        )
        
        # 4. 根据分析结果更新事件列表
        updated_events = await self._update_events_based_on_analysis(
            existing_journal.events, analysis_result, new_transcript
        )
        
        # 5. 更新JournalFile并保存到数据库
        updated_journal = JournalFile(
            username=username,
            time_stamp=time_stamp,
            events=updated_events,
            daily_reflection=existing_journal.daily_reflection  # 保持原有的反思
        )
        
        save_or_update_journal_file(username, updated_journal)
        
        # 6. 统计更新结果
        original_count = len(existing_journal.events)
        new_count = len(updated_events)
        updated_count = 0
        new_events_count = max(0, new_count - original_count)
        
        if new_events_count == 0:
            updated_count = 1  # 如果没有新事件，说明是更新了现有事件
        
        logger.info(f"增量分析完成 - 原有事件: {original_count}, 新增事件: {new_events_count}, 更新事件: {updated_count}")
        
        return IncrementalAnalyzeResponse(
            updated_events_count=updated_count,
            new_events_count=new_events_count,
            total_events_count=new_count,
            message=f"成功处理增量转录，新增 {new_events_count} 个事件，更新 {updated_count} 个事件"
        )
    
    
    async def _get_existing_journal(self, username: str, time_stamp: str) -> Optional[JournalFile]:
        """获取现有的日记文件"""
        try:
            journal_db = get_journal_file(username, time_stamp)
            if journal_db:
                journal_data = json.loads(journal_db.content_json)
                return JournalFile.model_validate(journal_data)
            return None
        except Exception as e:
            logger.error(f"获取现有日记失败: {e}")
            return None
    
    
    async def _create_initial_journal(
        self, 
        username: str, 
        time_stamp: str, 
        new_transcript: str
    ) -> IncrementalAnalyzeResponse:
        """创建初始日记文件"""
        
        logger.info(f"为用户 {username} 创建 {time_stamp} 的初始日记")
        
        # 使用现有的事件分析逻辑进行完整分析
        # 这里可以调用原有的analyze_actions中的逻辑
        # 为了简化，我们先创建一个基本的事件
        
        initial_event = EventAnalysis(
            event_id=str(uuid.uuid4()),
            event_title="初始活动记录",
            time_range="待分析",
            duration_minutes=30,
            location="待确定",
            mood_labels=["neutral"],
            mood_score=7,
            stress_level=5,
            energy_level=7,
            activity_type="unknown",
            people_involved=[],
            interaction_dynamic="N/A",
            inferred_impact_on_user_name="N/A",
            topic_labels=["initial"],
            one_sentence_summary=new_transcript[:100] + "..." if len(new_transcript) > 100 else new_transcript,
            first_person_narrative=new_transcript,
            action_item="N/A"
        )
        
        # 创建基本的每日反思结构（待后续完善）
        from ...models.prompt import (
            DailyReflection, Gratitude, ChallengesAndGrowth, 
            LearningAndInsights, ConnectionsAndRelationships, LookingForward
        )
        
        initial_reflection = DailyReflection(
            reflection_summary="初始记录，待完善",
            gratitude=Gratitude(
                gratitude_summary=["开始记录生活"],
                gratitude_details="感谢开始记录的这一刻",
                win_summary=["建立记录习惯"],
                win_details="成功开始记录生活",
                feel_alive_moments="每一个被记录的时刻"
            ),
            challenges_and_growth=ChallengesAndGrowth(
                growth_summary=["建立更好的记录习惯"],
                obstacles_faced="记录的初始阶段",
                unfinished_intentions="完善记录内容",
                contributing_factors="新习惯的建立需要时间"
            ),
            learning_and_insights=LearningAndInsights(
                new_knowledge="开始系统性记录生活",
                self_discovery="发现记录的价值",
                insights_about_others="期待与他人互动的记录",
                broader_lessons="记录让生活更有意义"
            ),
            connections_and_relationships=ConnectionsAndRelationships(
                meaningful_interactions="待记录更多互动",
                notable_about_people="期待记录与他人的连接",
                follow_up_needed="继续完善人际关系记录"
            ),
            looking_forward=LookingForward(
                do_differently_tomorrow="更详细地记录活动",
                continue_what_worked="保持记录的习惯",
                top_3_priorities_tomorrow=["完善记录", "增加细节", "保持习惯"]
            )
        )
        
        initial_journal = JournalFile(
            username=username,
            time_stamp=time_stamp,
            events=[initial_event],
            daily_reflection=initial_reflection
        )
        
        save_or_update_journal_file(username, initial_journal)
        
        return IncrementalAnalyzeResponse(
            updated_events_count=0,
            new_events_count=1,
            total_events_count=1,
            message="创建了初始日记记录"
        )
    
    
    async def _analyze_incremental_content(
        self, 
        existing_events: List[EventAnalysis], 
        new_transcript: str
    ) -> Dict[str, Any]:
        """分析增量内容与现有事件的关系"""
        
        # 构建现有事件的摘要
        events_summary = self._build_events_summary(existing_events)
        
        # 构建分析提示词
        prompt = self._build_incremental_analysis_prompt(events_summary, new_transcript)
        
        # 调用AI分析
        request_task = LanggraphRequestTask(
            username="system",
            prompt=prompt,
            chat_history=[],
            timeout=60 * 2
        )
        
        try:
            await self.langgraph_service.analyze(request_handlers=[request_task])
            
            if len(request_task._response.messages) == 0:
                raise Exception("AI分析未返回任何内容")
            
            response_content = request_task.last_response_message_content
            return self._parse_analysis_response(response_content)
            
        except Exception as e:
            logger.error(f"增量分析失败: {e}")
            # 返回默认的新增事件分析
            return {
                "analysis": {
                    "first_event_relationship": "NEW",
                    "target_event_id": None,
                    "detected_events": [
                        {
                            "event_title": "新活动",
                            "estimated_time_range": "待确定",
                            "location": "待确定",
                            "activity_type": "unknown",
                            "people_involved": [],
                            "content_summary": new_transcript[:200],
                            "reasoning": "AI分析失败，默认为新事件"
                        }
                    ]
                },
                "reasoning": "AI分析失败，使用默认处理"
            }
    
    
    def _build_events_summary(self, events: List[EventAnalysis]) -> str:
        """构建现有事件的摘要"""
        if not events:
            return "当前没有已记录的事件。"
        
        summary = ""
        for event in events:
            people_str = ", ".join(event.people_involved) if event.people_involved else "独自"
            summary += f"""
事件ID: {event.event_id}
标题: {event.event_title}
时间: {event.time_range}
地点: {event.location}
活动类型: {event.activity_type}
参与人员: {people_str}
概要: {event.one_sentence_summary}

"""
        return summary
    
    
    def _build_incremental_analysis_prompt(self, events_summary: str, new_transcript: str) -> str:
        """构建增量分析的AI提示词"""
        
        # 读取提示词模板
        try:
            with open("src/nirva_service/prompts/incremental_analysis.md", "r", encoding="utf-8") as f:
                template = f.read()
            
            return template.format(
                existing_events=events_summary,
                new_transcript=new_transcript
            )
        except Exception as e:
            logger.error(f"读取提示词模板失败: {e}")
            
            # 返回简化的提示词
            return f"""
请分析以下新转录内容，判断其中的事件与现有事件的关系。

现有事件：
{events_summary}

新转录内容：
{new_transcript}

请返回JSON格式的分析结果：
{{
  "analysis": {{
    "first_event_relationship": "CONTINUE" 或 "NEW",
    "target_event_id": "如果是延续，提供事件ID",
    "detected_events": [{{
      "event_title": "事件标题",
      "estimated_time_range": "时间范围",
      "location": "地点",
      "activity_type": "活动类型",
      "people_involved": ["人员列表"],
      "content_summary": "内容摘要",
      "reasoning": "判断理由"
    }}]
  }},
  "reasoning": "分析过程"
}}
"""
    
    
    def _parse_analysis_response(self, response_content: str) -> Dict[str, Any]:
        """解析AI分析响应"""
        try:
            # 提取JSON内容
            json_start = response_content.find('{')
            json_end = response_content.rfind('}') + 1
            
            if json_start == -1 or json_end == 0:
                raise ValueError("响应中未找到有效的JSON内容")
            
            json_content = response_content[json_start:json_end]
            return json.loads(json_content)
            
        except Exception as e:
            logger.error(f"解析AI响应失败: {e}")
            logger.error(f"原始响应: {response_content}")
            
            # 返回默认结果
            return {
                "analysis": {
                    "first_event_relationship": "NEW",
                    "target_event_id": None,
                    "detected_events": []
                },
                "reasoning": "解析失败，使用默认设置"
            }
    
    
    async def _update_events_based_on_analysis(
        self,
        existing_events: List[EventAnalysis],
        analysis_result: Dict[str, Any],
        new_transcript: str
    ) -> List[EventAnalysis]:
        """根据分析结果更新事件列表"""
        
        analysis = analysis_result.get("analysis", {})
        relationship = analysis.get("first_event_relationship", "NEW")
        target_event_id = analysis.get("target_event_id")
        detected_events = analysis.get("detected_events", [])
        
        updated_events = existing_events.copy()
        
        if relationship == "CONTINUE" and target_event_id:
            # 延续现有事件
            updated_events = self._merge_content_to_existing_event(
                updated_events, target_event_id, new_transcript, detected_events
            )
        else:
            # 新增事件
            updated_events.extend(
                self._create_new_events_from_analysis(detected_events, new_transcript)
            )
        
        return updated_events
    
    
    def _merge_content_to_existing_event(
        self,
        events: List[EventAnalysis],
        target_event_id: str,
        new_transcript: str,
        detected_events: List[Dict[str, Any]]
    ) -> List[EventAnalysis]:
        """将新内容合并到现有事件"""
        
        for event in events:
            if event.event_id == target_event_id:
                # 更新事件内容
                event.first_person_narrative += "\n\n" + new_transcript
                event.one_sentence_summary = self._update_summary(
                    event.one_sentence_summary, detected_events
                )
                
                # 更新其他可能的字段
                if detected_events:
                    first_detected = detected_events[0]
                    if first_detected.get("people_involved"):
                        # 合并参与人员，去重
                        new_people = first_detected["people_involved"]
                        existing_people = set(event.people_involved)
                        for person in new_people:
                            if person not in existing_people:
                                event.people_involved.append(person)
                
                logger.info(f"已将新内容合并到事件 {target_event_id}")
                break
        
        return events
    
    
    def _create_new_events_from_analysis(
        self,
        detected_events: List[Dict[str, Any]],
        new_transcript: str
    ) -> List[EventAnalysis]:
        """根据分析结果创建新事件"""
        
        new_events = []
        
        for detected in detected_events:
            new_event = EventAnalysis(
                event_id=str(uuid.uuid4()),
                event_title=detected.get("event_title", "新活动"),
                time_range=detected.get("estimated_time_range", "待确定"),
                duration_minutes=30,  # 默认值
                location=detected.get("location", "待确定"),
                mood_labels=["neutral"],  # 默认值
                mood_score=7,
                stress_level=5,
                energy_level=7,
                activity_type=detected.get("activity_type", "unknown"),
                people_involved=detected.get("people_involved", []),
                interaction_dynamic="N/A",
                inferred_impact_on_user_name="N/A",
                topic_labels=["incremental"],
                one_sentence_summary=detected.get("content_summary", new_transcript[:100]),
                first_person_narrative=new_transcript,
                action_item="N/A"
            )
            new_events.append(new_event)
            
            logger.info(f"创建新事件: {new_event.event_title}")
        
        # 如果没有检测到具体事件，创建一个默认事件
        if not new_events:
            default_event = EventAnalysis(
                event_id=str(uuid.uuid4()),
                event_title="新活动记录",
                time_range="待确定",
                duration_minutes=30,
                location="待确定",
                mood_labels=["neutral"],
                mood_score=7,
                stress_level=5,
                energy_level=7,
                activity_type="unknown",
                people_involved=[],
                interaction_dynamic="N/A",
                inferred_impact_on_user_name="N/A",
                topic_labels=["incremental"],
                one_sentence_summary=new_transcript[:100] + "..." if len(new_transcript) > 100 else new_transcript,
                first_person_narrative=new_transcript,
                action_item="N/A"
            )
            new_events.append(default_event)
        
        return new_events
    
    
    def _update_summary(self, original_summary: str, detected_events: List[Dict[str, Any]]) -> str:
        """更新事件摘要"""
        if detected_events and detected_events[0].get("content_summary"):
            return original_summary + " " + detected_events[0]["content_summary"]
        return original_summary


############################################################################################################################################### 