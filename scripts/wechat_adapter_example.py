from __future__ import annotations

from personal_brain import PersonalBrain


brain = PersonalBrain.from_config_file("config.json")


def on_wechat_text_message(text: str, sender: str = "me") -> str:
    """把任意开源微信机器人收到的文本消息转进这里即可。"""
    return brain.handle_message(text, sender=sender, source="wechat")


if __name__ == "__main__":
    print(on_wechat_text_message("Personal Brain V0 先保存原文，再慢慢升级。"))
    print(on_wechat_text_message("我之前关于 Personal Brain 怎么想的？"))

