#!/usr/bin/env python3

import aiohttp
import asyncio
import logging
import os
import praw

import utils
from utils import async_generator_to_list

log = logging.getLogger(__name__)

def make_reddit():
    client_id = os.getenv('WRITERBOT_CLIENT_ID')
    client_secret = os.getenv('WRITERBOT_CLIENT_SECRET')
    username = os.getenv('WRITERBOT_USERNAME')
    password = os.getenv('WRITERBOT_PASSWORD')
    if not (client_id and client_secret and username and password):
        raise Exception("Please set the environment variables WRITERBOT_CLIENT_ID, WRITERBOT_CLIENT_SECRET, WRITERBOT_USERNAME, and WRITERBOT_PASSWORD.")

    return praw.Reddit(client_id=client_id,
                       client_secret=client_secret,
                       username=username,
                       password=password,
                       user_agent='writerbot by /u/writerbot_app')

async def get_writing_prompts(reddit):
    async with aiohttp.ClientSession() as session:
        posts = await reddit.subreddit('writingprompts').get_submissions(session)
        for post in posts:
            if post.link_flair_text == "Writing Prompt":
                yield post

def get_stories(reddit, prompts):
    mods = reddit.subreddit('writingprompts').moderator()
    mod_names = [mod.name for mod in mods]

    for prompt in prompts:
        prompt.comment_sort = 'top'
        top_level_comments = list(prompt.comments)

        for comment in top_level_comments:
            is_mod_comment = comment.author.name in mod_names
            sufficiently_long = (len(comment.body) >= 300)
            above_score_threshold = (comment.score >= 5)

            if not above_score_threshold:
                break
            elif not is_mod_comment and sufficiently_long:
                yield comment.body

async def main():
    logging.basicConfig(level=logging.DEBUG)

    reddit = make_reddit()
    prompts = await async_generator_to_list(get_writing_prompts(reddit))
    log.debug("len(prompts): %s", len(prompts))
    stories = get_stories(reddit, prompts)
    log.debug("len(stories): %s", len(stories))
    print(stories)

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main())
    finally:
        loop.close()
