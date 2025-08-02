import openai
import os
import json
from openai import AzureOpenAI
import time
from dotenv import load_dotenv
from pprint import pprint
from itertools import chain
import pandas as pd
from tqdm import tqdm
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from typing import Dict, Union

endpoint = "https://eitamazureopenai.openai.azure.com/openai/deployments/o1/chat/completions?api-version=2025-01-01-preview"
api_version = "2024-12-01-preview"
tqdm.pandas()




class GptCall:
    def __init__(self, gpt_version='gpt4', evaluation_criteria=None):
        self.gpt_version = gpt_version

    
    def init_gpt(self):

        if self.gpt_version == 'gpt4':
            token_provider = get_bearer_token_provider(
                DefaultAzureCredential(),
                "https://cognitiveservices.azure.com/.default")

            # endpoint = os.getenv("GPT4_OPENAI_ENDPOINT")

            client = AzureOpenAI(
                azure_ad_token_provider=token_provider,
                azure_endpoint=endpoint,
                api_version=api_version #  os.getenv("GPT4_DEPLOYMENT_VERSION")
            )
            # model = os.getenv("GPT4_DEPLOYMENT_NAME")
            
        else:
            raise ValueError(f'Invalid gpt_version: {self.gpt_version}')
        
        return client



    def call_gpt(self, messages):

        client = self.init_gpt()

        gpt_response = self.get_gpt_response(client, messages)
        return gpt_response
    
    

    @staticmethod
    def get_gpt_response(client, messages, ):
        seed = 42
        attempts = 0
        while attempts < 3:
            try:
                response = client.chat.completions.create(
                    model="o1",
                    messages=messages,
                    seed=seed + attempts)
                return response.choices[0].message.content
            except Exception as e:
                print(e)
                time.sleep(2)
                attempts += 1
        return []


