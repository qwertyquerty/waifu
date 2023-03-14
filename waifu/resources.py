from waifu.config import cfg
from waifu.db import Prompt, Image, db_ext

from flask_apispec import MethodResource, use_kwargs

import marshmallow
from marshmallow import Schema, fields

from flask import abort, send_file, request, jsonify

from io import BytesIO

class PromptRequestSchema(Schema):
    prompt = fields.String(validate=marshmallow.validate.Length(max=80), required=True)
    model = fields.String(validate=marshmallow.validate.Length(min=3, max=32), required=True)

class QueueResource(MethodResource):
    def get(self, id):
        prompt = Prompt.query.get(id)

        if not prompt:
            return abort(404)
        
        queue_pos = prompt.queue_rank()

        if prompt:
            return jsonify({"id": prompt.id, "status": prompt.status, "position": queue_pos})

class ImageResource(MethodResource):
    def get(self, id):
        image = Image.query.get(id)

        if not image:
            return abort(404)
        
        image_io = BytesIO(image.image)
        image_io.seek(0)

        return send_file(image_io, mimetype="image/png")

class RequestResource(MethodResource):
    @use_kwargs(PromptRequestSchema)
    def get(self, **kwargs):
        if kwargs["model"] not in cfg.get("models"):
            return jsonify({"status": "ERROR", "message": f"Unknown model {kwargs['model']}!"})

        ip = request.headers.get('CF-Connecting-IP', request.remote_addr)
        current_ip_queues = Prompt.query.filter(Prompt.status != "FINISHED", Prompt.ip == ip).count()

        if current_ip_queues >= cfg.get("queue_per_ip"):
            return jsonify({"status": "ERROR", "message": f"Your IP address already has {cfg.get('queue_per_ip')} images queued!"})
        
        prompt = Prompt.add_to_queue(kwargs["prompt"], kwargs["model"], ip)
        queue_pos = prompt.queue_rank()

        db_ext.session.commit()

        return jsonify({"id": prompt.id, "status": prompt.status, "position": queue_pos})
