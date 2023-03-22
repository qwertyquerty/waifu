from waifu import db_ext, ma_ext

from datetime import datetime

import sqlalchemy
from sqlalchemy import Column, DateTime, String, Enum, LargeBinary, Integer

from hashlib import md5
import time

import warnings


class Prompt(db_ext.Model):
    __tablename__ = "prompt_queue"

    id = Column("id", String(32), primary_key=True)
    ip = Column("ip", String(40))
    status = Column("status", Enum("QUEUED", "GENERATING", "FINISHED"))
    worker = Column("worker", String(16))
    request_timestamp = Column("request_timestamp", DateTime())
    claim_timestamp = Column("claim_timestamp", DateTime())
    finish_timestamp = Column("finish_timestamp", DateTime())
    prompt = Column("prompt", String(80))
    model = Column("model", String(32))
    progress = Column("progress", Integer())

    @classmethod
    def add_to_queue(cls, prompt, model, ip):
        prompt = cls(
            id = md5((prompt+str(time.time())).encode()).hexdigest(),
            ip = ip,
            status = "QUEUED",
            prompt = prompt,
            model = model,
            request_timestamp = datetime.utcnow(),
            progress = 0
        )

        db_ext.session.add(prompt)

        return prompt
    
    def queue_rank(self):
        if self.status == "FINISHED":
            return -1
        
        if self.status == "GENERATING":
            return 0
        
        queue = Prompt.query.filter(Prompt.status == "QUEUED").order_by(Prompt.request_timestamp.asc()).all()

        for i in range(len(queue)):
            if queue[i].id == self.id:
                return i + 1
        
        return None

class Image(db_ext.Model):
    __tablename__ = "image_cache"

    id = Column("id", String(32), primary_key=True)
    timestamp = Column("timestamp", DateTime())
    image = Column("image", LargeBinary(2**20))

    @classmethod
    def submit(cls, prompt, data):
        image = cls(
            id = prompt.id,
            timestamp = datetime.utcnow(),
            image = data
        )

        db_ext.session.add(image)


class PromptSchema(ma_ext.SQLAlchemyAutoSchema):
    class Meta:
        model = Prompt

class ImageSchema(ma_ext.SQLAlchemyAutoSchema):
    class Meta:
        model = Image
