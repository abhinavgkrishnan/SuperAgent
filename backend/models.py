from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.ext.declarative import declarative_base
from typing import Dict, Any, Optional

Base = declarative_base()

db = SQLAlchemy(model_class=Base)

class GeneratedContent(db.Model):
    """Model for storing generated content and responses"""
    __tablename__ = 'generated_content'

    id = db.Column(db.Integer, primary_key=True)
    prompt = db.Column(db.Text, nullable=False)
    content = db.Column(db.Text, nullable=False)
    content_type = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    meta_info = db.Column(db.JSON, nullable=True)

    def __init__(self, prompt: str, content: str, content_type: str, meta_info: Optional[Dict[str, Any]] = None):
        self.prompt = prompt
        self.content = content
        self.content_type = content_type
        self.meta_info = meta_info

    def to_dict(self):
        return {
            'id': self.id,
            'prompt': self.prompt,
            'content': self.content,
            'content_type': self.content_type,
            'created_at': self.created_at.isoformat(),
            'meta_info': self.meta_info
        }


class AgentMemory(db.Model):
    """Model for storing agent memory entries"""
    __tablename__ = 'agent_memory'

    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(50), nullable=False)  # analysis, plan, research, or decision
    content = db.Column(db.JSON, nullable=False)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    metrics_snapshot = db.Column(db.JSON, nullable=True)

    def __init__(self, type: str, content: Any, metrics_snapshot: Optional[Dict[str, Any]] = None):
        self.type = type
        self.content = content
        self.metrics_snapshot = metrics_snapshot

    def to_dict(self):
        return {
            'id': self.id,
            'type': self.type,
            'content': self.content,
            'timestamp': self.timestamp.isoformat(),
            'metrics_snapshot': self.metrics_snapshot
        }