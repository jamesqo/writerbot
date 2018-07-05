import aiohttp
import logging
from praw.models import Subreddit
import time

log = logging.getLogger(__name__)

def unique(items, key):
    keys = set()
    for item in items:
        k = key(item)
        if k not in keys:
            keys.add(k)
            yield item

async def fetch_json(session, url):
    log.debug("GET %s", url)
    async with session.get(url) as response:
        return await response.json()

# Partially copied from https://www.reddit.com/r/redditdev/comments/8r756k/a_dropin_pushshift_replacement_for_the_deprecated/
async def get_submissions(self, session, start=None, end=None, limit=None, extra_query=""):
    """
    A simple function that returns a list of PRAW submission objects during a particular period from a defined sub.
    This function serves as a replacement for the now deprecated PRAW `submissions()` method.
    
    :param session: The aiohttp session from which to make requests.
    :param subreddit: A subreddit name to fetch submissions from.
    :param start: A Unix time integer. Posts fetched will be AFTER this time. (default: None)
    :param end: A Unix time integer. Posts fetched will be BEFORE this time. (default: None)
    :param limit: There needs to be a defined limit of results, or Pushshift will return only 25.
                  By default, this function does not impose a limit; it makes as many HTTP requests
                  as necessary to return all submissions within the time period.
    :param extra_query: A query string is optional. If an extra_query string is not supplied, 
                        the function will just grab everything from the defined time period. (default: empty string)
    
    Submissions are yielded newest first.
    
    For more information on PRAW, see: https://github.com/praw-dev/praw 
    For more information on Pushshift, see: https://github.com/pushshift/api
    """

    async def make_request(start, end, limit):
        # Format our search link properly.
        search_link = ('https://api.pushshift.io/reddit/submission/search/'
                       '?subreddit={}&after={}&before={}&sort_type=score&sort=asc&limit={}&q={}')
        search_link = search_link.format(self, start, end, limit, extra_query)

        # Get the data from Pushshift as JSON.
        retrieved_data = await fetch_json(session, search_link)
        returned_submissions = retrieved_data['data']

        # Iterate over the returned submissions to convert them to PRAW submission objects.
        return [self._reddit.submission(id=submission['id']) for submission in returned_submissions]

    # Default time values if none are defined (credit to u/bboe's PRAW `submissions()` for this section)
    utc_offset = 28800
    now = int(time.time())
    start = max(int(start) + utc_offset if start else 0, 0)
    end = min(int(end) if end else now, now) + utc_offset
    
    if limit is not None:
        matching_praw_submissions = await make_request(start, end, limit)
    else:
        # Currently, Pushshift only returns up to 1000 submissions in the response JSON.
        # Strategy: Keep making HTTP requests and receiving batches of 1000 until all submissions from the
        # time period have been retrieved.
        # We work our way backwards, keeping `start` fixed and decrementing `end`, since the Pushshift API
        # returns more recent posts first.
        matching_praw_submissions = []
        limit = 1000

        while True:
            batch = await make_request(start, end, limit)
            if len(batch) == 0:
                break

            matching_praw_submissions.extend(batch)
            oldest_in_batch = batch[-1]
            end = int(oldest_in_batch.created_utc)
        
        # Somehow, there are duplicate submissions after this process? Remove them.
        key = (lambda submission: submission.id)
        matching_praw_submissions = list(unique(matching_praw_submissions, key))

    # Return all PRAW submissions that were obtained.
    return matching_praw_submissions

Subreddit.get_submissions = get_submissions
