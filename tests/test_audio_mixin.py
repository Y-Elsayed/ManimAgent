import unittest

from nodes.audio_mixin import AudioMixin


class AudioMixinTests(unittest.TestCase):
    def test_audio_methods_exist(self):
        self.assertTrue(hasattr(AudioMixin, "play_with_audio"))
        self.assertTrue(hasattr(AudioMixin, "_tts"))
        self.assertTrue(hasattr(AudioMixin, "_get_audio_duration"))


if __name__ == "__main__":
    unittest.main()
