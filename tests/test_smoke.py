import os
import unittest

from ca.llm import GlmModel


@unittest.skipUnless(os.environ.get("GLM_API_KEY") and os.environ.get("WRITER_MODEL"), "GLM smoke settings are not configured")
class GlmSmokeTest(unittest.TestCase):
    def test_one_call(self):
        model = GlmModel(
            os.environ["GLM_API_KEY"],
            os.environ.get("GLM_BASE_URL", "https://open.bigmodel.cn/api/paas/v4/chat/completions"),
            os.environ["WRITER_MODEL"],
        )
        self.assertTrue(model.complete("你只做连通测试。", "请只回复“好”。"))


if __name__ == "__main__":
    unittest.main()
