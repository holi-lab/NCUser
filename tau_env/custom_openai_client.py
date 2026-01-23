from openai import OpenAI

openai_client = OpenAI(
    api_key="<Your-API-Key>"
)

open_router_client = OpenAI(
    api_key = "<Your-API-Key>",
    base_url="https://openrouter.ai/api/v1"
)