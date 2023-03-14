from waifu import app
from waifu.config import cfg

if __name__ == "__main__":
	app.run(host="0.0.0.0", debug=True, port=cfg.get("website.port"))
