"""
Conversation Context Manager - Advanced Context Awareness System

This module provides sophisticated conversation memory, personality learning,
and multi-turn conversation handling for the Nirva chat system.
"""

import datetime
import json
from typing import Optional, Dict, Any, List, Set
from uuid import UUID
from dataclasses import dataclass, asdict
import re

from sqlalchemy.orm import Session
from loguru import logger

from ..db.pgsql_client import SessionLocal
from ..db.pgsql_conversation import (
    ConversationContextDB, ChatMessageDB, MessageRole, MessageType
)
from ..models.api import ChatMessage, MessageRole as APIMessageRole


@dataclass
class ConversationFact:
    """A fact or piece of information remembered about the user."""
    fact: str
    category: str  # personal, preference, goal, relationship, etc.
    confidence: float  # 0.0 to 1.0
    first_mentioned: datetime.datetime
    last_reinforced: datetime.datetime
    message_ids: List[str]  # Messages that support this fact


@dataclass
class PersonalityTrait:
    """A learned personality trait about the user."""
    trait_name: str
    trait_value: str  # e.g., "prefers direct communication", "enjoys humor"
    evidence_count: int
    strength: float  # 0.0 to 1.0
    last_observed: datetime.datetime


@dataclass
class ConversationTheme:
    """A recurring theme or topic in conversations."""
    theme: str
    frequency: int
    importance_score: float
    related_facts: List[str]
    last_discussed: datetime.datetime


class ConversationContextManager:
    """
    Advanced conversation context management for intelligent, personalized AI responses.
    """
    
    def __init__(self):
        # Simple in-memory cache for context data
        self._context_cache = {}
        self._cache_ttl = 300  # 5 minutes cache TTL
    
    def get_or_create_context(self, user_id: UUID) -> ConversationContextDB:
        """Get or create conversation context for a user."""
        with SessionLocal() as db:
            context = db.query(ConversationContextDB).filter(
                ConversationContextDB.user_id == user_id
            ).first()
            
            if not context:
                context = ConversationContextDB(
                    user_id=user_id,
                    conversation_memory={
                        "facts": [],
                        "themes": [],
                        "conversation_patterns": {}
                    },
                    personality_state={
                        "traits": [],
                        "preferences": {},
                        "communication_style": "balanced"
                    },
                    mental_state_summary={},
                    recent_events_summary={}
                )
                db.add(context)
                db.commit()
                db.refresh(context)
                
                logger.info(f"Created new conversation context for user {user_id}")
            
            return context
    
    def _invalidate_cache(self, user_id: UUID) -> None:
        """Invalidate cache for a user."""
        if user_id in self._context_cache:
            del self._context_cache[user_id]
    
    def update_conversation_memory(
        self, 
        user_id: UUID, 
        new_messages: List[ChatMessage],
        ai_response: Optional[str] = None
    ) -> None:
        """
        Update conversation memory based on new messages and AI response.
        Extracts facts, updates themes, and learns personality traits.
        Invalidates cache after update.
        """
        with SessionLocal() as db:
            context = self.get_or_create_context(user_id)
            
            # Extract facts from messages
            extracted_facts = self._extract_facts_from_messages(new_messages)
            
            # Update conversation memory
            memory = context.conversation_memory or {}
            facts = [ConversationFact(**f) for f in memory.get("facts", [])]
            themes = [ConversationTheme(**t) for t in memory.get("themes", [])]
            
            # Add new facts
            for fact in extracted_facts:
                existing_fact = self._find_similar_fact(facts, fact.fact)
                if existing_fact:
                    # Reinforce existing fact
                    existing_fact.last_reinforced = datetime.datetime.now(datetime.timezone.utc)
                    existing_fact.confidence = min(1.0, existing_fact.confidence + 0.1)
                    if fact.fact not in [m for f in new_messages for m in [f.id]]:
                        existing_fact.message_ids.extend([m.id for m in new_messages])
                else:
                    facts.append(fact)
            
            # Update themes
            message_content = " ".join([msg.content for msg in new_messages if msg.role == APIMessageRole.HUMAN])  # Human messages
            themes = self._update_conversation_themes(themes, message_content)
            
            # Save updated memory
            memory["facts"] = [asdict(f) for f in facts]
            memory["themes"] = [asdict(t) for t in themes]
            memory["last_updated"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
            
            context.conversation_memory = memory
            
            # Update personality state
            personality = self._analyze_personality_from_messages(new_messages, context.personality_state or {})
            context.personality_state = personality
            
            context.last_updated = datetime.datetime.now(datetime.timezone.utc)
            
            db.commit()
            
            # Invalidate cache since context was updated
            self._invalidate_cache(user_id)
            
            logger.debug(f"Updated conversation context for user {user_id}: {len(facts)} facts, {len(themes)} themes")
    
    def _extract_facts_from_messages(self, messages: List[ChatMessage]) -> List[ConversationFact]:
        """Extract factual information from user messages."""
        facts = []
        current_time = datetime.datetime.now(datetime.timezone.utc)
        
        for message in messages:
            if message.role != APIMessageRole.HUMAN:  # Only process human messages
                continue
                
            content = message.content.lower()
            message_id = message.id
            
            # Pattern matching for common facts
            fact_patterns = [
                # Personal information
                (r"my name is (\w+)", "personal", "name"),
                (r"i work (?:at|for) ([^,.!?]+)", "work", "employer"),
                (r"i'm (\d+) years old", "personal", "age"),
                (r"i live in ([^,.!?]+)", "personal", "location"),
                (r"i have a (\w+) named (\w+)", "personal", "pet"),
                
                # Preferences
                (r"i (love|like|enjoy|prefer) ([^,.!?]+)", "preference", "likes"),
                (r"i (hate|dislike|don't like) ([^,.!?]+)", "preference", "dislikes"),
                (r"my favorite ([^,.!?]+) is ([^,.!?]+)", "preference", "favorite"),
                
                # Goals and aspirations
                (r"i want to ([^,.!?]+)", "goal", "aspiration"),
                (r"my goal is to ([^,.!?]+)", "goal", "objective"),
                (r"i'm trying to ([^,.!?]+)", "goal", "current_effort"),
                
                # Relationships
                (r"my (\w+) is ([^,.!?]+)", "relationship", "family"),
                (r"i'm (\w+) to ([^,.!?]+)", "relationship", "marital_status"),
                
                # Health and habits
                (r"i (?:have|suffer from) ([^,.!?]+)", "health", "condition"),
                (r"i usually ([^,.!?]+) in the morning", "habit", "morning_routine"),
                (r"i always ([^,.!?]+)", "habit", "routine"),
            ]
            
            for pattern, category, subcategory in fact_patterns:
                matches = re.finditer(pattern, content)
                for match in matches:
                    fact_text = match.group(0)
                    
                    fact = ConversationFact(
                        fact=fact_text,
                        category=category,
                        confidence=0.8,
                        first_mentioned=current_time,
                        last_reinforced=current_time,
                        message_ids=[message_id]
                    )
                    facts.append(fact)
        
        return facts
    
    def _find_similar_fact(self, facts: List[ConversationFact], new_fact: str) -> Optional[ConversationFact]:
        """Find if a similar fact already exists."""
        new_fact_lower = new_fact.lower()
        
        for fact in facts:
            # Simple similarity check - could be enhanced with NLP
            if (
                fact.fact.lower() in new_fact_lower or 
                new_fact_lower in fact.fact.lower() or
                self._calculate_similarity(fact.fact.lower(), new_fact_lower) > 0.7
            ):
                return fact
        
        return None
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Simple text similarity calculation."""
        words1 = set(text1.split())
        words2 = set(text2.split())
        
        if not words1 or not words2:
            return 0.0
            
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union)
    
    def _update_conversation_themes(self, themes: List[ConversationTheme], content: str) -> List[ConversationTheme]:
        """Update conversation themes based on new content."""
        content_lower = content.lower()
        current_time = datetime.datetime.now(datetime.timezone.utc)
        
        # Theme keywords mapping
        theme_keywords = {
            "work_career": ["work", "job", "career", "office", "meeting", "project", "boss", "colleague"],
            "health_fitness": ["exercise", "gym", "health", "doctor", "medication", "workout", "diet"],
            "family_relationships": ["family", "mother", "father", "sister", "brother", "spouse", "children", "relationship"],
            "hobbies_interests": ["hobby", "music", "movie", "book", "game", "sport", "art", "cooking"],
            "travel": ["travel", "trip", "vacation", "flight", "hotel", "visit", "country", "city"],
            "technology": ["computer", "phone", "app", "software", "internet", "website", "tech"],
            "education": ["school", "university", "study", "learn", "course", "degree", "student", "teacher"],
            "finance": ["money", "budget", "investment", "savings", "expensive", "cheap", "cost", "price"],
            "mental_health": ["stress", "anxiety", "depression", "therapy", "counseling", "mental", "mood"],
            "goals_planning": ["goal", "plan", "future", "dream", "aspiration", "want", "hope", "achieve"]
        }
        
        # Count theme relevance
        theme_scores = {}
        for theme, keywords in theme_keywords.items():
            score = sum(1 for keyword in keywords if keyword in content_lower)
            if score > 0:
                theme_scores[theme] = score
        
        # Update existing themes or create new ones
        for theme_name, score in theme_scores.items():
            existing_theme = next((t for t in themes if t.theme == theme_name), None)
            
            if existing_theme:
                existing_theme.frequency += 1
                existing_theme.importance_score = (existing_theme.importance_score + score) / 2
                existing_theme.last_discussed = current_time
            else:
                new_theme = ConversationTheme(
                    theme=theme_name,
                    frequency=1,
                    importance_score=float(score),
                    related_facts=[],
                    last_discussed=current_time
                )
                themes.append(new_theme)
        
        # Sort themes by importance and frequency
        themes.sort(key=lambda t: (t.importance_score * t.frequency), reverse=True)
        
        # Keep only top 20 themes
        return themes[:20]
    
    def _analyze_personality_from_messages(
        self, 
        messages: List[ChatMessage], 
        current_personality: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze and update personality traits from messages."""
        traits = [PersonalityTrait(**t) for t in current_personality.get("traits", [])]
        preferences = current_personality.get("preferences", {})
        
        # Analyze communication style
        human_messages = [msg.content for msg in messages if msg.role == APIMessageRole.HUMAN]
        combined_content = " ".join(human_messages).lower()
        
        # Communication patterns
        patterns = {
            "direct_communication": len(re.findall(r'\b(directly|straight|honestly|simply)\b', combined_content)),
            "emotional_expression": len(re.findall(r'\b(feel|feeling|emotion|excited|sad|happy|angry)\b', combined_content)),
            "detail_oriented": len(re.findall(r'\b(specifically|exactly|precisely|detail|particular)\b', combined_content)),
            "casual_tone": len(re.findall(r'\b(yeah|yep|gonna|wanna|kinda|sorta)\b', combined_content)),
            "questioning_nature": combined_content.count('?'),
            "uses_humor": len(re.findall(r'\b(lol|haha|funny|joke|humor)\b', combined_content)),
        }
        
        current_time = datetime.datetime.now(datetime.timezone.utc)
        
        # Update or create traits
        for trait_name, evidence in patterns.items():
            if evidence > 0:
                existing_trait = next((t for t in traits if t.trait_name == trait_name), None)
                
                if existing_trait:
                    existing_trait.evidence_count += evidence
                    existing_trait.strength = min(1.0, existing_trait.strength + evidence * 0.1)
                    existing_trait.last_observed = current_time
                else:
                    new_trait = PersonalityTrait(
                        trait_name=trait_name,
                        trait_value=f"shows {trait_name.replace('_', ' ')}",
                        evidence_count=evidence,
                        strength=min(1.0, evidence * 0.1),
                        last_observed=current_time
                    )
                    traits.append(new_trait)
        
        # Determine communication style
        style_scores = {
            "formal": patterns["detail_oriented"] + (10 - patterns["casual_tone"]),
            "casual": patterns["casual_tone"] + patterns["uses_humor"],
            "direct": patterns["direct_communication"],
            "emotional": patterns["emotional_expression"],
        }
        
        communication_style = max(style_scores, key=style_scores.get) if any(style_scores.values()) else "balanced"
        
        return {
            "traits": [asdict(t) for t in traits],
            "preferences": preferences,
            "communication_style": communication_style,
            "last_analyzed": current_time.isoformat()
        }
    
    def _is_cache_valid(self, user_id: UUID) -> bool:
        """Check if cached context is still valid."""
        if user_id not in self._context_cache:
            return False
        
        cache_entry = self._context_cache[user_id]
        cache_time = cache_entry.get("timestamp", datetime.datetime.min)
        
        # Check if cache is within TTL
        return (datetime.datetime.now(datetime.timezone.utc) - cache_time).total_seconds() < self._cache_ttl
    
    def get_enhanced_context_for_ai(self, user_id: UUID) -> Dict[str, Any]:
        """
        Get comprehensive context for AI to generate personalized responses.
        Uses caching to reduce database load.
        """
        # Check cache first
        if self._is_cache_valid(user_id):
            return self._context_cache[user_id]["data"]
        
        context = self.get_or_create_context(user_id)
        
        # Extract key information for AI context
        memory = context.conversation_memory or {}
        personality = context.personality_state or {}
        
        facts = [ConversationFact(**f) for f in memory.get("facts", [])]
        themes = [ConversationTheme(**t) for t in memory.get("themes", [])]
        traits = [PersonalityTrait(**t) for t in personality.get("traits", [])]
        
        # Get most important facts (high confidence, recently mentioned)
        important_facts = sorted(
            facts, 
            key=lambda f: f.confidence * (1.0 if (datetime.datetime.now(datetime.timezone.utc) - f.last_reinforced).days < 7 else 0.5),
            reverse=True
        )[:10]
        
        # Get most relevant themes
        relevant_themes = sorted(themes, key=lambda t: t.importance_score * t.frequency, reverse=True)[:5]
        
        # Get strongest personality traits
        strong_traits = [t for t in traits if t.strength > 0.3][:5]
        
        enhanced_context = {
            "conversation_memory": {
                "key_facts": [
                    {
                        "fact": f.fact,
                        "category": f.category,
                        "confidence": f.confidence
                    }
                    for f in important_facts
                ],
                "main_themes": [
                    {
                        "theme": t.theme.replace("_", " "),
                        "importance": t.importance_score,
                        "frequency": t.frequency
                    }
                    for t in relevant_themes
                ]
            },
            "personality_insights": {
                "communication_style": personality.get("communication_style", "balanced"),
                "key_traits": [
                    {
                        "trait": t.trait_name.replace("_", " "),
                        "strength": t.strength,
                        "description": t.trait_value
                    }
                    for t in strong_traits
                ]
            },
            "context_available": {
                "has_conversation_memory": len(important_facts) > 0,
                "has_personality_insights": len(strong_traits) > 0,
                "total_facts": len(facts),
                "total_themes": len(themes)
            }
        }
        
        # Cache the result
        self._context_cache[user_id] = {
            "data": enhanced_context,
            "timestamp": datetime.datetime.now(datetime.timezone.utc)
        }
        
        return enhanced_context
    
    def get_conversation_suggestions(self, user_id: UUID) -> List[str]:
        """Generate intelligent conversation starters based on user context."""
        context = self.get_or_create_context(user_id)
        memory = context.conversation_memory or {}
        personality = context.personality_state or {}
        
        themes = [ConversationTheme(**t) for t in memory.get("themes", [])]
        communication_style = personality.get("communication_style", "balanced")
        
        suggestions = []
        
        # Theme-based suggestions
        for theme in themes[:3]:
            if theme.theme == "work_career":
                suggestions.append("How has your work been going lately?")
            elif theme.theme == "health_fitness":
                suggestions.append("Have you been keeping up with your fitness goals?")
            elif theme.theme == "family_relationships":
                suggestions.append("How are things with your family?")
            elif theme.theme == "goals_planning":
                suggestions.append("Any progress on your recent goals?")
        
        # Style-based suggestions
        if communication_style == "emotional":
            suggestions.append("How are you feeling today?")
        elif communication_style == "direct":
            suggestions.append("What's the main thing on your mind?")
        elif communication_style == "casual":
            suggestions.append("What's new with you?")
        
        # Default suggestions
        if not suggestions:
            suggestions = [
                "What's been on your mind lately?",
                "How has your day been?",
                "Is there anything you'd like to talk about?"
            ]
        
        return suggestions[:3]


# Singleton instance
conversation_context_manager = ConversationContextManager()