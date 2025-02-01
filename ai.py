from nonebot import on_command, on_message, get_driver
from nonebot.adapters.onebot.v11 import Bot, Event, Message, MessageSegment
from nonebot.params import CommandArg
from nonebot.rule import to_me
from openai import OpenAI
from typing import Dict, List, Set
from nonebot import init
import asyncio

# 存储正在对话的用户ID
chatting_users: Set[str] = set()

# 定义消息和命令触发器
init(command_start=[" ", "/"])
start_chat = on_command("那我问你", aliases={"对话"}, priority=5)
chat_handler = on_message(rule=to_me(), priority=5)
end_chat = on_command("结束对话", aliases={"停止对话"}, priority=5)

# DeepSeek API 配置从环境变量获取
config = get_driver().config
API_KEY = getattr(config, "deepseek_api_key", "")  # 从环境变量获取API Key
BASE_URL = getattr(config, "deepseek_base_url", "https://api.deepseek.com")  # 从环境变量获取base URL
MODEL = getattr(config, "deepseek_model", "deepseek-chat")  # 从环境变量获取模型名称

# 初始化 OpenAI 客户端（同步客户端）
client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

# 存储用户的对话历史
user_history: Dict[str, List[Dict[str, str]]] = {}

async def call_deepseek_api(messages: List[Dict[str, str]]) -> str:
    """
    异步调用 DeepSeek API 进行对话
    """
    try:
        # 将同步调用放到线程池执行
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,  # 使用默认的executor
            lambda: client.chat.completions.create(
                model=MODEL,
                messages=messages,
                stream=False,
            )
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"请求发生错误：{str(e)}"

@start_chat.handle()
async def handle_start_chat(bot: Bot, event: Event, args: Message = CommandArg()):
    """
    开始对话（异步）
    """
    user_id = event.get_user_id()
    message = args.extract_plain_text().strip()
    
    if user_id in chatting_users:
        await start_chat.finish('你已经在对话中了，可以直接说话。')
        return
        
    chatting_users.add(user_id)
    if user_id not in user_history:
        user_history[user_id] = [{"role": "system", "content": "我是七海nana7mi,一个喜欢鲨鱼的女高中生."}]
                               
    if message:
        user_history[user_id].append({"role": "user", "content": message})
        response = await call_deepseek_api(user_history[user_id])
        user_history[user_id].append({"role": "assistant", "content": response})
        
        await start_chat.finish(response)
    else:
        await start_chat.finish('已开始对话！你可以直接和我聊天，说"结束对话"结束对话。')

@chat_handler.handle()
async def handle_chat(bot: Bot, event: Event):
    """
    处理用户消息（异步）
    """
    user_id = event.get_user_id()
    message = event.get_plaintext().strip()
    
    if user_id not in chatting_users:
        await chat_handler.finish('那你问我')
        return

    user_history[user_id].append({"role": "user", "content": message})

    await chat_handler.send("正在思考，请稍等...")
    response = await call_deepseek_api(user_history[user_id])

    user_history[user_id].append({"role": "assistant", "content": response})
    
    await chat_handler.finish(response)

@end_chat.handle()
async def handle_end_chat(bot: Bot, event: Event):
    """
    结束对话（异步）
    """
    user_id = event.get_user_id()
    if user_id in chatting_users:
        chatting_users.remove(user_id)
        await end_chat.finish("对话已结束！")
    else:
        await end_chat.finish("你当前没有进行中的对话。")

# 清除对话历史命令
clear_history = on_command("clear_history", aliases={"清除历史"}, priority=5)

@clear_history.handle()
async def handle_clear_history(bot: Bot, event: Event):
    """
    异步清除用户的对话历史
    """
    user_id = event.get_user_id()
    if user_id in user_history:
        del user_history[user_id]
        await clear_history.finish("对话历史已清除！")
    else:
        await clear_history.finish("你没有对话历史可清除。")