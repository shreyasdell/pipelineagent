from typing import Optional, Dict, Any
from sqlalchemy import create_engine, Column, String, JSON, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime
from loguru import logger
from core.config.settings import settings

Base = declarative_base()


class AgentStatePersistence(Base):
    """SQLAlchemy model for persisting agent states"""
    
    __tablename__ = "agent_states"
    
    deployment_conversation_id = Column(String, primary_key=True)
    state_data = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    current_agent = Column(String, nullable=True)


class StateManager:
    """Manages state persistence with PostgreSQL"""
    
    def __init__(self):
        if settings.database_url:
            self.engine = create_engine(settings.database_url)
            Base.metadata.create_all(self.engine)
            self.SessionLocal = sessionmaker(bind=self.engine)
            self.enabled = True
        else:
            self.enabled = False
            logger.warning("Database URL not configured, state persistence disabled")
    
    def save_state(self, deployment_conversation_id: str, state_data: Dict[str, Any], current_agent: Optional[str] = None) -> bool:
        """Save or update agent state to PostgreSQL"""
        if not self.enabled:
            logger.debug(f"State persistence disabled, skipping save for {deployment_conversation_id}")
            return False
            
        session = self.SessionLocal()
        try:
            existing_state = session.query(AgentStatePersistence).filter(
                AgentStatePersistence.deployment_conversation_id == deployment_conversation_id
            ).first()
            
            if existing_state:
                existing_state.state_data = state_data
                existing_state.updated_at = datetime.utcnow()
                existing_state.current_agent = current_agent
            else:
                new_state = AgentStatePersistence(
                    deployment_conversation_id=deployment_conversation_id,
                    state_data=state_data,
                    current_agent=current_agent
                )
                session.add(new_state)
            
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            print(f"Error saving state: {e}")
            return False
        finally:
            session.close()
    
    def load_state(self, deployment_conversation_id: str) -> Optional[Dict[str, Any]]:
        """Load agent state from PostgreSQL"""
        if not self.enabled:
            logger.debug(f"State persistence disabled, skipping load for {deployment_conversation_id}")
            return None
            
        session = self.SessionLocal()
        try:
            state = session.query(AgentStatePersistence).filter(
                AgentStatePersistence.deployment_conversation_id == deployment_conversation_id
            ).first()
            
            if state:
                return state.state_data
            return None
        except Exception as e:
            print(f"Error loading state: {e}")
            return None
        finally:
            session.close()
    
    def delete_state(self, deployment_conversation_id: str) -> bool:
        """Delete agent state from PostgreSQL"""
        if not self.enabled:
            logger.debug(f"State persistence disabled, skipping delete for {deployment_conversation_id}")
            return False
            
        session = self.SessionLocal()
        try:
            state = session.query(AgentStatePersistence).filter(
                AgentStatePersistence.deployment_conversation_id == deployment_conversation_id
            ).first()
            
            if state:
                session.delete(state)
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            print(f"Error deleting state: {e}")
            return False
        finally:
            session.close()


# Global state manager instance
state_manager = StateManager()