from os.path import join, dirname

from ovos_plugin_common_play.ocp import MediaType, PlaybackType
from ovos_utils.parse import fuzzy_match
from ovos_workshop.skills.common_play import OVOSCommonPlaybackSkill, \
    ocp_search, ocp_play
from rarbgapi import RarbgAPI


class RARBGSkill(OVOSCommonPlaybackSkill):
    def __init__(self):
        super(RARBGSkill, self).__init__("RARBG")
        self.supported_media = [MediaType.GENERIC, MediaType.MOVIE,
                                MediaType.ADULT]
        self.rarbg = RarbgAPI()
        self.skill_icon = join(dirname(__file__), "ui", "logo.png")

    def calc_score(self, phrase, torrent, media_type, idx=0, base_score=0):
        if torrent.seeders < 1:
            return 0
        removes = ["WEBRip", "x265", "HDR", "DTS", "HD", "BluRay", "uhd",
                   "1080p", "720p", "BRRip", "XviD", "MP3", "2160p",
                   "h264", "AAC", "REMUX", "SDR", "hevc", "x264",
                   "REMASTERED", "RARBG", "SUBBED", "DVDRip"]
        removes = [r.lower() for r in removes]

        clean_name = torrent.filename.replace(".", " ").replace("-", " ")
        clean_name = " ".join([w for w in clean_name.split()
                               if w and w.lower() not in removes])
        score = base_score - idx
        score += fuzzy_match(phrase.lower(), clean_name) * 100
        if media_type == MediaType.MOVIE:
            score += 15
        return score

    @ocp_search()
    def search_torrents(self, phrase, media_type):
        categories = [RarbgAPI.CATEGORY_MOVIE_XVID,
                      RarbgAPI.CATEGORY_MOVIE_XVID_720P,
                      RarbgAPI.CATEGORY_MOVIE_H264,
                      RarbgAPI.CATEGORY_MOVIE_H264_1080P,
                      RarbgAPI.CATEGORY_MOVIE_H264_720P,
                      RarbgAPI.CATEGORY_MOVIE_H264_3D,
                      RarbgAPI.CATEGORY_MOVIE_H264_4K,
                      RarbgAPI.CATEGORY_MOVIE_H265_4K,
                      RarbgAPI.CATEGORY_MOVIE_H265_4K_HDR,
                      RarbgAPI.CATEGORY_MOVIE_FULL_BD,
                      RarbgAPI.CATEGORY_MOVIE_BD_REMUX
                      ]

        # no accidental porn results!
        if self.voc_match(phrase, "porn") or media_type == MediaType.ADULT:
            phrase = self.remove_voc(phrase, "porn")
            categories.append(RarbgAPI.CATEGORY_ADULT)

        base_score = 0
        if self.voc_match(phrase, "torrent"):
            phrase = self.remove_voc(phrase, "torrent")
            base_score = 40

        try:
            torrents = self.rarbg.search(search_string=phrase,
                                         categories=categories,
                                         extended_response=True)
        except:
            return  # probably rate limited
        torrents = sorted(torrents, key=lambda k: k.seeders, reverse=True)

        return [{
            "title": torrent.filename,
            "match_confidence": self.calc_score(phrase, torrent, media_type,
                                                idx, base_score),
            "media_type": MediaType.VIDEO,
            "uri": torrent.download,
            "playback": PlaybackType.SKILL,
            "skill_icon": self.skill_icon,
            "skill_id": self.skill_id
        } for idx, torrent in enumerate(torrents)]

    @ocp_play()
    def stream_torrent(self, message):
        self.bus.emit(message.forward("skill.peerflix.play", message.data))


def create_skill():
    return RARBGSkill()
