from __future__ import annotations

from personal_brain import PersonalBrain


brain = PersonalBrain.from_config_file("config.json")


def on_wechat_text_message(text: str, sender: str = "me") -> str:
    """Pass text received by any WeChat adapter into Personal Brain."""
    return brain.handle_message(text, sender=sender, source="wechat")


if __name__ == "__main__":
    print(on_wechat_text_message("我希望 Personal Brain 的微信入口像好友一样轻。"))

