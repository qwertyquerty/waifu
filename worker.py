import logging

class ColoredLogFormatter(logging.Formatter):
    grey = "\x1b[38;20m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    format = "[%(asctime)s] %(levelname)s: %(message)s"

    FORMATS = {
        logging.DEBUG: grey + format + reset,
        logging.INFO: grey + format + reset,
        logging.WARNING: yellow + format + reset,
        logging.ERROR: red + format + reset,
        logging.CRITICAL: bold_red + format + reset
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)

logger = logging.getLogger("waifu_worker")
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
ch.setFormatter(ColoredLogFormatter())
logger.addHandler(ch)

logger.info("Starting up...")

from diffusers import StableDiffusionPipeline
import torch
from datetime import datetime, timedelta
import sys
import time
from io import BytesIO

logger.info("Connecting...")

from waifu import app
from waifu.config import cfg
from waifu.db import *

if len(sys.argv) < 2:
    logger.error("Please specify Worker ID as first argument")
    exit()

WORKER_ID = sys.argv[1]

logger.info(f"Identifying as worker {WORKER_ID}")

pipes = {

}

logger.info("Loading models...")

with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    for model in cfg.get("models"):
        pipe = StableDiffusionPipeline.from_pretrained(model, torch_dtype=torch.float16)
        pipe = pipe.to("cuda")
        pipe.safety_checker = lambda images, clip_input: (images, False)
        pipes[model] = pipe

logger.info("Ready!")

def claim(prompt):
    prompt.claim_timestamp = datetime.utcnow()
    prompt.status = "GENERATING"
    prompt.worker = WORKER_ID
    db_ext.session.commit()

def generate(prompt):
    logger.info(f"Generating prompt [{prompt.id}] with model {prompt.model}")

    pipe = pipes[prompt.model]
    image = pipe(prompt.prompt, num_inference_steps=cfg.get("inference_steps"), negative_prompt=cfg.get("negative_prompt")).images[0]
    image_io = BytesIO()
    image.save(image_io, format="PNG")
    image_io.seek(0)
    data = image_io.read()

    logger.info(f"Finished generating prompt [{prompt.id}]")

    Image.submit(prompt, data)
    prompt.finish_timestamp = datetime.utcnow()
    prompt.status = "FINISHED"
    db_ext.session.commit()

    logger.info(f"Submitted [{prompt.id}]")

with app.app_context():
    while True:
        try:
            claimed = Prompt.query.filter(Prompt.worker == WORKER_ID, Prompt.status == "GENERATING", Prompt.model.in_(cfg.get("models"))).all()

            if len(claimed) > 0:
                generate(claimed[0])
            else:
                stale = Prompt.query.filter(Prompt.status == "GENERATING", Prompt.claim_timestamp >= (datetime.utcnow() + timedelta(seconds=60)), Prompt.model.in_(cfg.get("models"))).all()

                if len(stale):
                    logger.warn(f"Claiming stale job [{stale[0].id}] from worker {stale[0].worker}")
                    claim(stale[0])
                    continue

                queued = Prompt.query.filter(Prompt.status == "QUEUED").order_by(Prompt.request_timestamp.asc(), Prompt.model.in_(cfg.get("models"))).all()

                if len(queued):
                    claim(queued[0])
                    logger.info(f"Claiming queued job [{queued[0].id}]")
                    continue
            
            time.sleep(1)
            db_ext.session.commit()
            db_ext.session.begin()
        
        except Exception as e:
            logger.error(f"Error in job cycle: {e}")
            db_ext.session.rollback()
            db_ext.session.begin()
