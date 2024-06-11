# https://platform.openai.com/docs/assistants/overview

import json
import os
import openai
from dotenv import load_dotenv
import requests
from typing_extensions import override
from openai import AssistantEventHandler

load_dotenv()

client = openai.OpenAI()
model = "gpt-3.5-turbo"

news_api_key = os.environ.get("NEWS_API_KEY")

def get_news(topic):
  url = (
    f"https://newsapi.org/v2/everything?q={topic}&apiKey={news_api_key}&pageSize=5"
  )

  try:
    response = requests.get(url)
    if response.status_code == 200:
      news = json.dumps(response.json(), indent=4)
      news_json = json.loads(news)

      data = news_json

      final_news = []

      # Access the articles
      status = data["status"]
      total_results = data["totalResults"]
      articles = data["articles"]

      # Loop through the articles
      for article in articles:
        source_name = article["source"]["name"]
        title = article["title"]
        author = article["author"]
        description = article["description"]
        url = article["url"]
        content = article["content"]
        title_description = f"""
          Title: {title},
          Author: {author},
          Source: {source_name},
          Description: {description},
          URL: {url},
          Content: {content}
          """
        final_news.append(title_description)

      return final_news
    else:
      return  []

  except requests.exceptions.RequestException as e:
    print("Error occurred while fetching news", e)

# Create our Assistant

# assistant = client.beta.assistants.create(
#   name="Personal Trainer",
#   instructions="You are a highly knowledgable personal trainer and nutritionist.",
#   model=model,
# )

# assistant_id = assistant.id
# print(assistant_id)

# assistant_id = "asst_52gGnQcKtZjnF9Zs2oBp8QK4"

# Create a Thread

# thread = client.beta.threads.create()

# thread_id = thread.id
# print(thread_id)

# thread_id = "thread_z4PtZKiN2ueAFCBQX5D2qe7m"

# Create a Message

# message = client.beta.threads.messages.create(
#   thread_id=thread_id,
#   role="user",
#   content="How do I get started working out to lose fat and build muscles?"
# )

# Run the Assistant

# https://platform.openai.com/docs/assistants/overview#streaming-response
# First, we create a EventHandler class to define
# how we want to handle the events in the response stream.
 
class EventHandler(AssistantEventHandler):    
  @override
  def on_text_created(self, text) -> None:
    print(f"\nassistant > ", end="", flush=True)
      
  @override
  def on_text_delta(self, delta, snapshot):
    print(delta.value, end="", flush=True)
      
  def on_tool_call_created(self, tool_call):
    print(f"\nassistant > {tool_call.type}\n", flush=True)
  
  def on_tool_call_delta(self, delta, snapshot):
    if delta.type == 'code_interpreter':
      if delta.code_interpreter.input:
        print(delta.code_interpreter.input, end="", flush=True)
      if delta.code_interpreter.outputs:
        print(f"\n\noutput >", flush=True)
        for output in delta.code_interpreter.outputs:
          if output.type == "logs":
            print(f"\n{output.logs}", flush=True)
 
# Then, we use the `stream` SDK helper 
# with the `EventHandler` class to create the Run 
# and stream the response.
 
# with client.beta.threads.runs.stream(
#   thread_id=thread_id,
#   assistant_id=assistant_id,
#   instructions="Please address the user in a professional tone.",
#   event_handler=EventHandler(),
# ) as stream:
#   stream.until_done()

def main():
  news = get_news("bitcoin")
  print(news[0])


if __name__ == "__main__":
  main()