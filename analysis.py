from openai import OpenAI
import os

client = OpenAI(
    api_key=os.getenv("AIHUBMIX_API_KEY"),
    base_url="https://aihubmix.com/v1"
)

response = client.responses.create(
    model="gpt-5", # gpt-5, gpt-5-chat-latest, gpt-5-mini, gpt-5-nano
    input="Output format: Markdown",
    # reasoning={ "effort": "minimal" },
      # 推理深度 - Controls how many reasoning tokens the model generates before producing a response. value can be "minimal", "medium", "high", default is "medium"
      # minimal 仅在 gpt-5 系列支持
    text={"verbosity": "medium"},
      # 输出篇幅 - Verbosity determines how many output tokens are generated. value can be "low", "medium", "high", Models before GPT-5 have used medium verbosity by default. 
      # gpt-5-chat-latest 仅支持 medium
    #stream=True
)

#for event in response:
#  print(event)

print(response)