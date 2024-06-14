# https://platform.openai.com/docs/assistants/overview

import json
import os
import openai
import time
import streamlit as st
from dotenv import load_dotenv
import requests

load_dotenv()

client = openai.OpenAI()
model = "gpt-3.5-turbo"

news_api_key = os.environ.get("NEWS_API_KEY")

def get_news(topic: str):
  url = (
    f"https://newsapi.org/v2/everything?q={topic}&sortBy=publishedAt&apiKey={news_api_key}&pageSize=5"
  )

  try:
    response = requests.get(url)
    if response.status_code == 200:
      news = json.dumps(response.json(), indent=4)
      news_json = json.loads(news)

      data = news_json

      final_news = []

      # Access the articles
      articles = data["articles"]

      # Loop through the articles
      for article in articles:
        source_name = article["source"]["name"]
        published_at = article["publishedAt"]
        title = article["title"]
        author = article["author"]
        description = article["description"]
        url = article["url"]
        content = article["content"]
        title_description = f"""
          Title: {title},
          Published At: {published_at},
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


class AssistantManager:
  # If we already have an assistant and thread ID, we can use them
  thread_id = None
  assistant_id = None

  def __init__(self, model: str = model):
    self.client = client
    self.model = model
    self.assistant = None
    self.thread = None
    self.run = None
    self.summary = None
  
    # Retrieve existing assistant and thread IDs
    if AssistantManager.assistant_id:
      self.assistant = client.beta.assistants.retrieve(
        assistant_id=AssistantManager.assistant_id)
    
    if AssistantManager.thread_id:
      self.thread = client.beta.threads.retrieve(
        thread_id=AssistantManager.thread_id)
  
  def create_assistant(self, name: str, instructions: str, tools: list):
    if not self.assistant:
      assistant_obj = client.beta.assistants.create(
        name=name,
        instructions=instructions,
        model=self.model,
        tools=tools
      )
      AssistantManager.assistant_id = assistant_obj.id
      self.assistant = assistant_obj
      print("Assistant ID: ", self.assistant.id)
  
  def create_thread(self):
    if not self.thread:
      thread_obj = client.beta.threads.create()
      AssistantManager.thread_id = thread_obj.id
      self.thread = thread_obj
      print("Thread ID: ", self.thread.id)
  
  def add_message_to_thread(self, role: str, content: str):
    if self.thread:
      message = client.beta.threads.messages.create(
        self.thread.id,
        role=role,
        content=content
      )
      print("Message ID: ", message.id)
  

  def run_assistant(self, instructions: str):
    if self.thread and self.assistant:
      run = client.beta.threads.runs.create(
        thread_id=self.thread.id,
        assistant_id=self.assistant.id,
        instructions=instructions
      )
      self.run = run
      print("Run ID: ", self.run.id)
  
  
  def process_message(self):
    if self.thread:
      messages = self.client.beta.threads.messages.list(
        thread_id=self.thread.id
      )
      summary = []

      last_message = messages.data[0]
      role = last_message.role
      response = last_message.content[0].text.value
      summary.append(response)

      self.summary = "\n".join(summary)
      print(f"SUMMARY: {role}: {response}")

  def call_required_functions(self, required_actions):
    if not self.run:
      return
    tool_outputs = []

    for action in required_actions["tool_calls"]:
      func_name = action["function"]["name"]
      arguments = json.loads(action["function"]["arguments"])

      if func_name == "get_news":
        output = get_news(arguments["topic"])
        print("Output: ", output)

        final_str = ""
        for item in output:
          final_str += "".join(item)

        tool_outputs.append({
            "tool_call_id": action["id"],
            "output": final_str
          })
      
      else:
        raise ValueError(f"Function {func_name} not found")

    print("Submitting tool outputs back to the Assistant...")  
    self.client.beta.threads.runs.submit_tool_outputs(
      thread_id=self.thread.id,
      run_id=self.run.id,
      tool_outputs=tool_outputs
    )
        

  def wait_for_completion(self):
    if self.thread and self.run:
      while True:
        time.sleep(5)
        run_status = self.client.beta.threads.runs.retrieve(
          thread_id=self.thread.id,
          run_id=self.run.id
        )
        print("Run status: ", run_status.model_dump_json(indent=4))

        if run_status.status == "completed":
          self.process_message()
          break
        elif run_status.status == "requires_action":
          print("Run requires action")
          self.call_required_functions(
            required_actions=run_status.required_action.submit_tool_outputs.model_dump()
          )
  
  # For streamlit
  def get_summary(self):
    return self.summary

  # Retrieve and print steps for debugging
  def run_steps(self):
    run_steps = self.client.beta.threads.runs.steps.list(
      thread_id=self.thread.id,
      run_id=self.run.id
    )
    return run_steps.data
  
  print("Run steps: ", {run_steps})
 

# Main function to run the assistant

def main():

  manager = AssistantManager()
  
  # Streamlit interface
  st.title("News Summarizer")

  with st.form(key="user_input_form"):
    instructions = st.text_input("Enter topic:")
    submit_button = st.form_submit_button(label="Get News Summary")

    if submit_button:
      manager.create_assistant(
        name="News Summarizer", 
        instructions="You are a news article summariser. You will be given a topic and you need to provide a summary of the news articles related to that topic.",
        tools=[
          {
            "type": "function",
            "function": {
              "name": "get_news",
              "description": "Get news articles related to a topic.",
              "parameters": {
                "type": "object",
                "properties": {
                  "topic": {
                    "type": "string",
                    "description": "The topic to get news articles for."
                  }
                },
                "required": ["topic"]
            
              }
            }
          }
        ])      
      manager.create_thread()

      # Add message to the thread and run the assistant
      manager.add_message_to_thread(
        role="user", 
        content=f"Summarize the news on this topic {instructions}")
      
      manager.run_assistant(instructions="Summarize the news")

      # Wait for the completion of the assistant
      manager.wait_for_completion()

      summary = manager.get_summary() 

      print("Summary: ", summary)

      st.write(summary)

      st.text("Run steps:")
      st.code(manager.run_steps(), line_numbers=True)


if __name__ == "__main__":
  main()