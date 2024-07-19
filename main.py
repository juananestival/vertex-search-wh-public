from flask import Flask, jsonify, request
import logging
from flask_cors import CORS
import os
import json
from google.cloud import discoveryengine_v1alpha as discoveryengine
from typing import List
import re
import google.protobuf.json_format
from google.api_core.client_options import ClientOptions
import asyncio
from vertexai.generative_models import (
    GenerativeModel,
    GenerationConfig,
    HarmCategory,
    HarmBlockThreshold,
)
import vertexai


app = Flask(__name__)
CORS(app)

datastore_id = os.environ.get("DATASTORE_ID")
project_id = os.environ.get("PROJECT_ID")
location = os.environ.get("LOCATION")
collection_id = os.environ.get("COLLECTION_ID")
serving_config_id = os.environ.get("SERVING_CONFIG_ID")
engine_id = os.environ.get("ENGINE_ID")
base_url = "https://discoveryengine.googleapis.com/v1beta"
serving_config = f"projects/{project_id}/locations/{location}/collections/{collection_id}/dataStores/{datastore_id}/servingConfigs/{serving_config_id}"
endpoint = f"{base_url}/{serving_config}:search"
vertexai.init(project=project_id)
search_query = ""
search_serving_config = f"projects/{project_id}/locations/{location}/collections/default_collection/engines/{engine_id}/servingConfigs/default_config"


def get_client():
  client = discoveryengine.SearchServiceClient(
    client_options=(
        ClientOptions(
            api_endpoint=f"{location}-discoveryengine.googleapis.com"
        )
        if location != "global"
        else None
    )
  )
  return client
def get_content_search_spec():
  content_search_spec = discoveryengine.SearchRequest.ContentSearchSpec(
    snippet_spec=discoveryengine.SearchRequest.ContentSearchSpec.SnippetSpec(
        return_snippet=True
    ),
    summary_spec=discoveryengine.SearchRequest.ContentSearchSpec.SummarySpec(
        summary_result_count=5,
        include_citations=True,
        ignore_adversarial_query=True,
        ignore_non_summary_seeking_query=True,
    ),
  )

  return content_search_spec

def get_snippets(response):
  for index, result in enumerate(response.results):
    print(index)
    data = result.document.derived_struct_data
    for snippet_item in data.get("snippets", []):
      title = data.get("title", "Unknown Title")
      print(f"Title: {title}")
      print(f"Snippet: {snippet_item.get('snippet')}")
      #display(IPython.display.HTML(snippet_item.get("snippet")))
      link = data.get("link", "Unknown Link")
      print(f"Link: {link}\n")
  return ""


@app.post("/demo")
def demo():
  data = request.get_json()
  print(f"data {data}")
  print(f"query {data['text']}")
  search_query = data['text']
  client = get_client()
  content_search_spec = get_content_search_spec()
  response = client.search(
    discoveryengine.SearchRequest(
        serving_config=search_serving_config,
        query=search_query,
        page_size=10,
        content_search_spec = content_search_spec
    )
  )
  get_snippets(response)

  #
  output = {
    'sessionInfo': {
      'parameters': {
        'userAuthenticated': 'y',
        }
      },
    "fulfillment_response": {
      "messages": [
        {
          "text": {
            #"text": ["test"]
            "text": [response.summary.summary_text]
            }
        },
        {
          "payload": {
            "richContent": [
                        [
                            {
                                "type": "chips",
                                "options": [
                                    { "text": "Option 1" },
                                    { "text": "Option 2" },
                                    { "text": "Option 3" }
                                ]
                            }
                        ]
                    ]

          }

        }
      ]
    }
  }
  response_json = json.dumps(output)

  #return jsonify({'response': response.summary.summary_text})
  return response_json

@app.post("/search")
def search():
  data = request.get_json()
  print(data)
  query = data.get("query")
  num_results = data.get("num_results")

  client = discoveryengine_v1beta.SearchServiceClient()

  req = discoveryengine_v1beta.SearchRequest(
      serving_config=serving_config,
      query=query,
      page_size=num_results,
  )

  res = client.search(req)
  results = []
  for result in res.results:
    doc = result.document
    doc_dict = {}
    doc_dict['name'] = doc.name
    doc_dict['title'] = doc.derived_struct_data['title']
    doc_dict['link'] = doc.derived_struct_data['link']
    doc_dict['snippet'] = doc.derived_struct_data['snippets'][0]['snippet']
    results.append(doc_dict)

  data = {"results": results}

  return jsonify(data)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
