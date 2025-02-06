# Imports
from openai import *
from pathlib import Path
from typing import Tuple
import google.generativeai as genai
import signal
import sys
import tiktoken
import time
import os

import json
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
import boto3

class LLM:
    """
    An online inference model using different LLMs, including gemini, gpt-3.5, and gpt-4
    """

    def __init__(
        self, 
        online_model_name: str,
        temperature: float, 
        system_role="You are a experienced programmer and good at understanding programs written in mainstream programming languages."
    ) -> None:
        self.online_model_name = online_model_name
        self.encoding = tiktoken.encoding_for_model("gpt-3.5-turbo-0125") # We only use gpt-3.5 to measure token cost
        self.temperature = temperature
        self.systemRole = system_role
        return

    def infer(
        self, message: str, is_measure_cost: bool = False
    ) -> Tuple[str, int, int]:
        print(self.online_model_name, "is running")
        output = ""
        if "gemini" in self.online_model_name:
            output = self.infer_with_gemini(message)
        elif "gpt" in self.online_model_name:
            output = self.infer_with_openai_model(message)
        elif "claude" in self.online_model_name:
            output = self.infer_with_claude(message)
        elif "deepseek" in self.online_model_name:
            output = self.infer_with_deepseek_model(message)
        else:
            raise ValueError("Unsupported model name")
        input_token_cost = (
            0
            if not is_measure_cost
            else len(self.encoding.encode(self.systemRole))
            + len(self.encoding.encode(message))
        )
        output_token_cost = (
            0 if not is_measure_cost else len(self.encoding.encode(output))
        )
        return output, input_token_cost, output_token_cost

    def infer_with_gemini(self, message: str) -> str:
        """
        Infer using the Gemini model from Google Generative AI
        """
        def timeout_handler(signum, frame):
            raise TimeoutError("ChatCompletion timeout")

        def simulate_ctrl_c(signal, frame):
            raise KeyboardInterrupt("Simulating Ctrl+C")

        gemini_model = genai.GenerativeModel("gemini-pro")
        signal.signal(signal.SIGALRM, timeout_handler)

        received = False
        tryCnt = 0
        while not received:
            tryCnt += 1
            time.sleep(2)
            try:
                signal.alarm(50)  # Set a timeout of 50 seconds
                message = self.systemRole + "\n" + message

                safety_settings = [
                    {
                        "category": "HARM_CATEGORY_DANGEROUS",
                        "threshold": "BLOCK_NONE",
                    },
                    {
                        "category": "HARM_CATEGORY_HARASSMENT",
                        "threshold": "BLOCK_NONE",
                    },
                    {
                        "category": "HARM_CATEGORY_HATE_SPEECH",
                        "threshold": "BLOCK_NONE",
                    },
                    {
                        "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                        "threshold": "BLOCK_NONE",
                    },
                    {
                        "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                        "threshold": "BLOCK_NONE",
                    },
                ]

                response = gemini_model.generate_content(
                    message,
                    safety_settings=safety_settings,
                    generation_config=genai.types.GenerationConfig(
                        temperature=self.temperature
                    ),
                )
                time.sleep(2)
                signal.alarm(0)  # Cancel the timeout
                output = response.text
                print("Inference succeeded...")
                return output
            except TimeoutError:
                print("ChatCompletion call timed out")
                received = False
                simulate_ctrl_c(None, None)  # Simulate Ctrl+C effect
            except KeyboardInterrupt:
                print("ChatCompletion cancelled by user")
                received = False
                continue
            except Exception:
                print("API error:", sys.exc_info())
                return ""
            if tryCnt > 5:
                return ""

    def infer_with_openai_model(self, message):
        """
        Infer using the OpenAI model
        """
        def timeout_handler(signum, frame):
            raise TimeoutError("ChatCompletion timeout")

        def simulate_ctrl_c(signal, frame):
            raise KeyboardInterrupt("Simulating Ctrl+C")

        api_key = os.environ.get("OPENAI_API_KEY").split(":")[0]

        model_input = [
            {
                "role": "system",
                "content": self.systemRole,
            },
            {"role": "user", "content": message},
        ]

        received = False
        tryCnt = 0
        output = ""

        signal.signal(signal.SIGALRM, timeout_handler)
        while not received:
            tryCnt += 1
            time.sleep(2)
            try:
                signal.alarm(100)  # Set a timeout of 100 seconds
                client = OpenAI(api_key=api_key)
                response = client.chat.completions.create(
                    model=self.online_model_name,
                    messages=model_input,
                    temperature=self.temperature,
                )

                signal.alarm(0)  # Cancel the timeout
                output = response.choices[0].message.content
                break
            except TimeoutError:
                print("ChatCompletion call timed out")
                received = False
                simulate_ctrl_c(None, None)  # Simulate Ctrl+C effect
            except KeyboardInterrupt:
                print("ChatCompletion cancelled by user")
                output = ""
                break
            except Exception:
                print("API error:", sys.exc_info())
                received = False
            if tryCnt > 5:
                output = ""
        return output
    
    def infer_with_deepseek_model(self, message):
        """
        Infer using the DeepSeek model
        """
        def timeout_handler(signum, frame):
            raise TimeoutError("ChatCompletion timeout")

        def simulate_ctrl_c(signal, frame):
            raise KeyboardInterrupt("Simulating Ctrl+C")

        api_key = os.environ.get("DEEPSEEK_API_KEY")

        model_input = [
            {
                "role": "system",
                "content": self.systemRole,
            },
            {"role": "user", "content": message},
        ]

        received = False
        tryCnt = 0
        output = ""

        signal.signal(signal.SIGALRM, timeout_handler)
        while not received:
            tryCnt += 1
            time.sleep(2)
            try:
                signal.alarm(100)  # Set a timeout of 100 seconds
                client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
                response = client.chat.completions.create(
                    model=self.online_model_name,
                    messages=model_input,
                    temperature=self.temperature,
                )

                signal.alarm(0)  # Cancel the timeout
                output = response.choices[0].message.content
                break
            except TimeoutError:
                print("ChatCompletion call timed out")
                received = False
                simulate_ctrl_c(None, None)  # Simulate Ctrl+C effect
            except KeyboardInterrupt:
                print("ChatCompletion cancelled by user")
                output = ""
                break
            except Exception:
                print("API error:", sys.exc_info())
                received = False
            if tryCnt > 5:
                output = ""
        return output

    def infer_with_claude(self, message):
        """
        Infer using the OpenAI model
        """
        def timeout_handler(signum, frame):
            raise TimeoutError("ChatCompletion timeout")

        def simulate_ctrl_c(signal, frame):
            raise KeyboardInterrupt("Simulating Ctrl+C")

        model_id = "anthropic.claude-3-5-sonnet-20241022-v2:0"

        model_input = [
            {
                "role": "assistant",
                "content": self.systemRole,
            },
            {"role": "user", "content": message},
        ]
        
        body = json.dumps(
        {
            "messages": model_input,
            "max_tokens": 4000,
            "anthropic_version": "bedrock-2023-05-31",
            "temperature": self.temperature,
            "top_k": 50,
        }
        )

        received = False
        tryCnt = 0
        output = ""

        signal.signal(signal.SIGALRM, timeout_handler)
        while not received:
            tryCnt += 1
            time.sleep(2)
            try:
                signal.alarm(100)  # Set a timeout of 100 seconds
                client = boto3.client("bedrock-runtime", region_name="us-west-2", config=Config(read_timeout=100))
                
                response = client.invoke_model(
                    modelId=model_id,
                    contentType="application/json",
                    body = body
                )["body"].read().decode("utf-8")

                signal.alarm(0)  # Cancel the timeout
                response = json.loads(response)
                output = response["content"][0]["text"]
                break
            except TimeoutError:
                print("ChatCompletion call timed out")
                received = False
                simulate_ctrl_c(None, None)  # Simulate Ctrl+C effect
            except KeyboardInterrupt:
                print("ChatCompletion cancelled by user")
                output = ""
                break
            except Exception:
                print("API error:", sys.exc_info())
                received = False
            if tryCnt > 5:
                output = ""
        return output
