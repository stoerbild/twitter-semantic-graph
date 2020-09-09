from typing import Optional, List
from fastapi import FastAPI
from pydantic import BaseModel

from connectors.twitter import TwitterClient
from connectors.redis import RedisClient
from logic.network import NetworkBuilder
from fastapi.middleware.cors import CORSMiddleware

redis_client = RedisClient()

app = FastAPI()

origins = [
    "http://localhost",
    "http://localhost:3000",
    "http://localhost:3001",
    "http://0.0.0.0:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class GraphRequest(BaseModel):
    hashtags: List[str]
    languages: Optional[List[str]] = None
    filter_retweets: Optional[bool] = True
    filter_node_frequency: Optional[int] = 0
    filter_link_frequency: Optional[int] = 0


@redis_client.cache
def get_tweets_text(hashtags, filter_retweets, languages):
    twitter_client = TwitterClient()
    tweets, full_text = twitter_client.search_tweets_by_hashtags(
        hashtags, filter_retweets=filter_retweets, languages=languages,
    )
    print("Fetching tweets...")
    if full_text:
        corpus = [tweet.full_text for tweet in tweets]
    else:
        corpus = [tweet.text for tweet in tweets]
    return corpus


def make_graph(request: GraphRequest):
    corpus = get_tweets_text(
        hashtags=request.hashtags,
        filter_retweets=request.filter_retweets,
        languages=request.languages,
    )
    print("Building the graph...")
    network_builder = NetworkBuilder()
    network_builder.load_clean_corpus(corpus)
    keywords_to_remove = request.hashtags if len(request.hashtags) == 1 else []
    graph = network_builder.build_graph(
        filter_node_frequency=request.filter_node_frequency,
        filter_link_frequency=request.filter_link_frequency,
        keywords_to_remove=keywords_to_remove,
    )
    return graph


@app.post("/get-graph")
async def root(request: GraphRequest):
    print("received")
    print(request)
    return make_graph(request)
