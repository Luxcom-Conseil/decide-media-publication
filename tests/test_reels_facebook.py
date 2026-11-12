from datetime import datetime, timedelta, timezone

import agent.scenario as scenario
from agent.publieurs import meta


class _R:
    def __init__(self, corps):
        self.status_code, self._corps, self.text = 200, corps, str(corps)

    def json(self):
        return self._corps


def test_le_short_part_en_reel_programme(tmp_path, monkeypatch):
    video = tmp_path / "s.mp4"
    video.write_bytes(b"0" * 1234)
    monkeypatch.setattr(scenario, "short_en_cache", lambda article, image: video)
    monkeypatch.setenv("META_PAGE_ID", "123")
    monkeypatch.setenv("META_PAGE_TOKEN", "jeton-essai")
    appels = []

    def post(url, data=None, files=None, headers=None, timeout=None):
        appels.append((url, data if isinstance(data, dict) else len(data), headers))
        if url.endswith("/video_reels") and data.get("upload_phase") == "start":
            return _R({"video_id": "987", "upload_url": "https://rupload.facebook.com/video-upload/v21.0/987"})
        return _R({"success": True})

    monkeypatch.setattr(meta.requests, "post", post)
    quand = datetime.now(timezone.utc) + timedelta(hours=3)
    r = meta.FacebookShorts({"meta": {"version_api": "v21.0"}}).programmer(
        "texte", tmp_path / "v.png", quand, {"title": "Coup de pouce", "body": "Une phrase.", "hashtags": ["cameroun"]})
    assert r.id == "987"
    debut, envoi, fin = appels
    assert debut[0].endswith("/123/video_reels") and debut[1]["upload_phase"] == "start"
    assert envoi[0] == "https://rupload.facebook.com/video-upload/v21.0/987" and envoi[1] == 1234
    assert envoi[2]["file_size"] == "1234" and envoi[2]["offset"] == "0"
    assert fin[1]["upload_phase"] == "finish" and fin[1]["video_state"] == "SCHEDULED"
    assert fin[1]["scheduled_publish_time"] == str(int(quand.timestamp())) and "#cameroun" in fin[1]["description"]
