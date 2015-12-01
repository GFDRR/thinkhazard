from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    Unicode,
    DateTime,
    String,
    )


from sqlalchemy.orm import (
    relationship,
    )
import datetime

from thinkhazard_common.models import (
    Base,
    )


class FeedbackStatus(Base):
    __tablename__ = 'enum_feedbackstatus'

    id = Column(Integer, primary_key=True)
    mnemonic = Column(Unicode)
    title = Column(Unicode, nullable=False)


class UserFeedback(Base):
    __tablename__ = 'userfeedback'

    id = Column(Integer, primary_key=True)
    description = Column(Unicode, nullable=False)
    submissiondate = Column(DateTime, nullable=False,
                            default=datetime.datetime.utcnow)
    useremailaddress = Column(String(254))
    url = Column(Unicode, nullable=False)
    feedbackstatus_id = Column(Integer, ForeignKey(FeedbackStatus.id),
                               nullable=False)

    feedbackstatus = relationship(FeedbackStatus)
