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
        
        # 使用LLM分析转录内容
        try:
            # 构建事件分析提示词
            prompt = self._build_initial_analysis_prompt(new_transcript, time_stamp)
            
            # 调用LLM进行分析
            request_task = LanggraphRequestTask(
                username="system",
                prompt=prompt,
                chat_history=[],
                timeout=60 * 3
            )
            
            await self.langgraph_service.analyze(request_handlers=[request_task])
            
            if len(request_task._response.messages) == 0:
                raise Exception("LLM分析未返回内容")
            
            # 解析LLM响应
            response_content = request_task.last_response_message_content
            events = self._parse_llm_events_response(response_content, new_transcript)
            
            if not events:
                raise Exception("未能从LLM响应中提取事件")
                
        except Exception as e:
            logger.error(f"LLM分析失败，使用简单分析: {e}")
            # 分析转录内容以提取事件（备用方案）
            events = await self._analyze_transcript_for_events(new_transcript)
            
            if not events:
                # 如果分析失败，创建一个基本事件
                initial_event = EventAnalysis(
                    event_id=str(uuid.uuid4()),
                    event_title="Daily Activity",
                    time_range="Full Day",
                    duration_minutes=30,
                    location="Various",
                    mood_labels=["neutral"],
                    mood_score=7,
                    stress_level=5,
                    energy_level=7,
                    activity_type="leisure",
                    people_involved=[],
                    interaction_dynamic="N/A",
                    inferred_impact_on_user_name="N/A",
                    topic_labels=["daily"],
                    one_sentence_summary=self._generate_summary_from_transcript(new_transcript),
                    first_person_narrative=self._generate_narrative_from_transcript(new_transcript),
                    action_item="N/A"
                )
                events = [initial_event]
        
        # 创建基本的每日反思结构（待后续完善）
        from ...models.prompt import (
            DailyReflection, Gratitude, ChallengesAndGrowth, 
            LearningAndInsights, ConnectionsAndRelationships, LookingForward
        )
        
        initial_reflection = DailyReflection(
            reflection_summary="Daily activities and experiences",
            gratitude=Gratitude(
                gratitude_summary=["Daily experiences"],
                gratitude_details="Grateful for the day's experiences",
                win_summary=["Completed activities"],
                win_details="Successfully navigated the day",
                feel_alive_moments="Moments of connection and activity"
            ),
            challenges_and_growth=ChallengesAndGrowth(
                growth_summary=["Personal development"],
                obstacles_faced="Daily challenges",
                unfinished_intentions="Tasks to complete",
                contributing_factors="Time and circumstances"
            ),
            learning_and_insights=LearningAndInsights(
                new_knowledge="Daily learnings",
                self_discovery="Personal insights",
                insights_about_others="Social observations",
                broader_lessons="Life lessons"
            ),
            connections_and_relationships=ConnectionsAndRelationships(
                meaningful_interactions="Social interactions",
                notable_about_people="People in my life",
                follow_up_needed="Future connections"
            ),
            looking_forward=LookingForward(
                do_differently_tomorrow="Areas for improvement",
                continue_what_worked="Successful practices",
                top_3_priorities_tomorrow=["Priority 1", "Priority 2", "Priority 3"]
            )
        )
        
        initial_journal = JournalFile(
            username=username,
            time_stamp=time_stamp,
            events=events,
            daily_reflection=initial_reflection
        )
        
        save_or_update_journal_file(username, initial_journal)
        
        return IncrementalAnalyzeResponse(
            updated_events_count=0,
            new_events_count=len(events),
            total_events_count=len(events),
            message=f"创建了初始日记，包含 {len(events)} 个事件"
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
    
    
    async def _analyze_transcript_for_events(self, transcript: str) -> List[EventAnalysis]:
        """分析转录内容并提取事件"""
        try:
            # 解析转录内容以提取时间和内容
            parsed_segments = self._parse_transcript_segments(transcript)
            
            if not parsed_segments:
                return []
            
            events = []
            for segment in parsed_segments:
                event = EventAnalysis(
                    event_id=str(uuid.uuid4()),
                    event_title=self._generate_event_title(segment['content']),
                    time_range=segment['time_range'],
                    duration_minutes=segment['duration_minutes'],
                    location=self._extract_location(segment['content']),
                    mood_labels=["neutral"],
                    mood_score=7,
                    stress_level=5,
                    energy_level=7,
                    activity_type=self._determine_activity_type(segment['content']),
                    people_involved=self._extract_people(segment['content']),
                    interaction_dynamic="Conversational",
                    inferred_impact_on_user_name="Neutral",
                    topic_labels=self._extract_topics(segment['content']),
                    one_sentence_summary=self._generate_summary_from_transcript(segment['content']),
                    first_person_narrative=self._generate_narrative_from_transcript(segment['content']),
                    action_item="None identified"
                )
                events.append(event)
            
            return events
            
        except Exception as e:
            logger.error(f"分析转录内容失败: {e}")
            return []
    
    
    def _parse_transcript_segments(self, transcript: str) -> List[Dict[str, Any]]:
        """解析转录内容，提取时间段和内容"""
        segments = []
        
        try:
            import re
            # 匹配时间戳格式 [HH:MM] 或 [MM:SS]
            time_pattern = r'\[(\d{1,2}:\d{2})\]'
            
            # 分割转录文本按时间戳
            parts = re.split(time_pattern, transcript)
            
            times = []
            contents = []
            
            for i, part in enumerate(parts):
                if i % 2 == 1:  # 奇数索引是时间戳
                    times.append(part)
                elif i % 2 == 0 and part.strip():  # 偶数索引是内容
                    contents.append(part.strip())
            
            # 组合时间和内容
            for i in range(min(len(times), len(contents))):
                if i < len(times) - 1:
                    time_range = f"{times[i]}-{times[i+1]}"
                    # 计算持续时间
                    duration = self._calculate_duration(times[i], times[i+1])
                else:
                    time_range = f"{times[i]}-{times[i]}"
                    duration = 5  # 默认5分钟
                
                segments.append({
                    'time_range': time_range,
                    'duration_minutes': duration,
                    'content': contents[i] if i < len(contents) else ""
                })
            
            # 如果没有找到时间戳，将整个内容作为一个段落
            if not segments:
                segments.append({
                    'time_range': "00:00-23:59",
                    'duration_minutes': 60,
                    'content': transcript
                })
            
            return segments
            
        except Exception as e:
            logger.error(f"解析转录段落失败: {e}")
            return [{
                'time_range': "00:00-23:59",
                'duration_minutes': 60,
                'content': transcript
            }]
    
    
    def _calculate_duration(self, start_time: str, end_time: str) -> int:
        """计算两个时间之间的分钟数"""
        try:
            # 解析时间格式 HH:MM 或 MM:SS
            start_parts = start_time.split(':')
            end_parts = end_time.split(':')
            
            # 判断是小时:分钟还是分钟:秒
            if int(start_parts[0]) > 23:  # 如果第一个数字大于23，应该是分钟:秒
                start_minutes = int(start_parts[0])
                end_minutes = int(end_parts[0])
            else:  # 否则是小时:分钟
                start_minutes = int(start_parts[0]) * 60 + int(start_parts[1])
                end_minutes = int(end_parts[0]) * 60 + int(end_parts[1])
            
            duration = end_minutes - start_minutes
            return max(1, duration)  # 至少1分钟
            
        except Exception:
            return 30  # 默认30分钟
    
    
    def _generate_event_title(self, content: str) -> str:
        """生成事件标题"""
        # 基于内容生成简短标题
        words = content.split()[:5]
        title = " ".join(words)
        if len(title) > 50:
            title = title[:47] + "..."
        return title if title else "Activity"
    
    
    def _extract_location(self, content: str) -> str:
        """从内容中提取位置信息"""
        # 简单的位置提取逻辑
        location_keywords = ['home', 'office', 'cafe', 'restaurant', 'store', 'shop', 
                           '家', '办公室', '咖啡', '餐厅', '商店', '超市']
        
        content_lower = content.lower()
        for keyword in location_keywords:
            if keyword in content_lower:
                return keyword.capitalize()
        
        return "Unknown Location"
    
    
    def _determine_activity_type(self, content: str) -> str:
        """确定活动类型"""
        content_lower = content.lower()
        
        if any(word in content_lower for word in ['work', 'meeting', 'project', '工作', '会议', '项目']):
            return "work"
        elif any(word in content_lower for word in ['eat', 'food', 'lunch', 'dinner', '吃', '饭', '午餐', '晚餐']):
            return "meal"
        elif any(word in content_lower for word in ['shop', 'buy', 'store', '购物', '买', '商店']):
            return "shopping"
        elif any(word in content_lower for word in ['game', 'play', '游戏', '玩']):
            return "entertainment"
        else:
            return "leisure"
    
    
    def _extract_people(self, content: str) -> List[str]:
        """从内容中提取人物"""
        # 简单的人名提取（实际应该用NER）
        people = []
        
        # 查找Speaker标记
        import re
        speaker_pattern = r'Speaker \d+:'
        speakers = re.findall(speaker_pattern, content)
        
        if len(set(speakers)) > 1:
            people.append("Others")
        
        return people
    
    
    def _extract_topics(self, content: str) -> List[str]:
        """提取话题标签"""
        topics = []
        
        content_lower = content.lower()
        
        topic_keywords = {
            'technology': ['computer', 'software', 'app', '电脑', '软件'],
            'finance': ['money', 'pay', 'price', '钱', '支付', '价格'],
            'social': ['friend', 'talk', 'chat', '朋友', '聊天'],
            'shopping': ['buy', 'shop', 'store', '买', '购物', '商店'],
            'food': ['eat', 'food', 'meal', '吃', '食物', '饭']
        }
        
        for topic, keywords in topic_keywords.items():
            if any(keyword in content_lower for keyword in keywords):
                topics.append(topic)
        
        if not topics:
            topics.append('general')
        
        return topics
    
    
    def _generate_summary_from_transcript(self, content: str) -> str:
        """从转录内容生成摘要"""
        # 清理内容并生成摘要
        cleaned = ' '.join(content.split()[:30])  # 取前30个词
        
        if len(cleaned) > 150:
            cleaned = cleaned[:147] + "..."
        
        return cleaned if cleaned else "Activity recorded"
    
    
    def _generate_narrative_from_transcript(self, content: str) -> str:
        """从转录内容生成第一人称叙述"""
        # 转换为第一人称叙述
        narrative = content
        
        # 移除Speaker标记
        import re
        narrative = re.sub(r'\[\d{2}:\d{2}\]', '', narrative)
        narrative = re.sub(r'Speaker \d+:', 'I', narrative)
        
        # 清理多余空格
        narrative = ' '.join(narrative.split())
        
        # 限制长度
        if len(narrative) > 500:
            narrative = narrative[:497] + "..."
        
        return narrative if narrative else "I engaged in various activities throughout the day."
    
    
    def _build_initial_analysis_prompt(self, transcript: str, date: str) -> str:
        """构建初始事件分析的提示词"""
        return f"""
Analyze the following transcript and extract meaningful events from it.

Date: {date}
Transcript:
{transcript}

Please analyze this transcript and provide a JSON response with the following structure:
{{
  "events": [
    {{
      "event_title": "Brief descriptive title",
      "time_range": "HH:MM-HH:MM format from transcript",
      "duration_minutes": estimated duration,
      "location": "inferred location or 'Unknown'",
      "activity_type": "work|meal|social|shopping|leisure|unknown",
      "people_involved": ["list of people mentioned"],
      "mood_labels": ["positive", "neutral", or "negative"],
      "mood_score": 1-10,
      "topic_labels": ["topics discussed"],
      "one_sentence_summary": "A concise one-sentence summary of what happened",
      "first_person_narrative": "A 2-3 sentence first-person narrative describing the experience and feelings",
      "action_item": "Any follow-up actions needed or 'None'"
    }}
  ]
}}

IMPORTANT:
1. Extract actual time ranges from the [HH:MM] timestamps in the transcript
2. Create DIFFERENT summary and narrative - summary should be objective, narrative should be subjective first-person
3. If the transcript contains Chinese, respond with Chinese summaries/narratives
4. **CRITICAL**: Group related segments into larger events - aim for 3-5 major events per day maximum
5. Focus on meaningful activities, not technical audio capture messages
6. Merge activities that:
   - Occur within 60 minutes of each other
   - Happen in the same general location
   - Involve similar types of activities
7. Examples of what should be ONE event:
   - Working on computer + checking emails + attending online meeting = "Work session"
   - Making breakfast + eating + cleaning dishes = "Morning routine"
   - Multiple conversations with the same people = "Social gathering"
"""
    
    
    def _parse_llm_events_response(self, response_content: str, original_transcript: str) -> List[EventAnalysis]:
        """解析LLM响应并创建事件列表"""
        try:
            import json
            import re
            
            # 提取JSON内容
            json_match = re.search(r'\{.*\}', response_content, re.DOTALL)
            if not json_match:
                raise ValueError("未找到JSON内容")
            
            data = json.loads(json_match.group())
            events = []
            
            for event_data in data.get('events', []):
                try:
                    event = EventAnalysis(
                        event_id=str(uuid.uuid4()),
                        event_title=event_data.get('event_title', 'Activity'),
                        time_range=event_data.get('time_range', '00:00-23:59'),
                        duration_minutes=event_data.get('duration_minutes', 30),
                        location=event_data.get('location', 'Unknown'),
                        mood_labels=event_data.get('mood_labels', ['neutral']),
                        mood_score=event_data.get('mood_score', 7),
                        stress_level=5,  # Default
                        energy_level=7,  # Default
                        activity_type=self._validate_activity_type(event_data.get('activity_type', 'unknown')),
                        people_involved=event_data.get('people_involved', []),
                        interaction_dynamic="Conversational" if event_data.get('people_involved') else "Solo",
                        inferred_impact_on_user_name="Neutral",
                        topic_labels=event_data.get('topic_labels', ['general']),
                        one_sentence_summary=event_data.get('one_sentence_summary', '')[:200],
                        first_person_narrative=event_data.get('first_person_narrative', '')[:500],
                        action_item=event_data.get('action_item', 'None')
                    )
                    
                    # 确保summary和narrative不同
                    if event.one_sentence_summary == event.first_person_narrative:
                        event.first_person_narrative = f"I {event.one_sentence_summary.lower()} It was an interesting experience."
                    
                    events.append(event)
                    logger.info(f"LLM创建事件: {event.event_title} ({event.time_range})")
                    
                except Exception as e:
                    logger.error(f"解析单个事件失败: {e}")
                    continue
            
            return events
            
        except Exception as e:
            logger.error(f"解析LLM事件响应失败: {e}")
            return []
    
    
    def _validate_activity_type(self, activity_type: str) -> str:
        """验证并规范化活动类型"""
        valid_types = ['work', 'exercise', 'social', 'learning', 'self-care', 
                      'chores', 'commute', 'meal', 'leisure', 'unknown']
        
        activity_type = activity_type.lower()
        if activity_type in valid_types:
            return activity_type
        
        # 尝试映射常见的类型
        mappings = {
            'eating': 'meal',
            'food': 'meal',
            'shopping': 'leisure',
            'daily_life': 'leisure',
            'entertainment': 'leisure',
            'meeting': 'work',
            'study': 'learning'
        }
        
        return mappings.get(activity_type, 'unknown')


############################################################################################################################################### 