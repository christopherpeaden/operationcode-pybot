import logging

from slack import methods

from pybot.endpoints.slack.utils.command_utils import get_slash_here_messages, get_slash_repeat_messages
from pybot.endpoints.slack.utils.slash_lunch import split_params, get_random_lunch, build_response_text
from pybot.endpoints.slack.utils import PYBACK_HOST, PYBACK_PORT, PYBACK_TOKEN
from sirbot.plugins.slack import SlackPlugin
logger = logging.getLogger(__name__)


def create_endpoints(plugin:SlackPlugin):
    plugin.on_command('/here', slash_here, wait=False)
    plugin.on_command('/lunch', slash_lunch, wait=False)
    plugin.on_command('/repeat', slash_repeat, wait=False)


async def slash_here(command:dict, app:SlackPlugin):
    channel_id = command['channel_id']
    slack_id = command['user_id']
    slack = app["plugins"]["slack"].api

    params = {'slack_id': slack_id, 'channel_id': channel_id}
    headers = {'Authorization': f'Token {PYBACK_TOKEN}'}

    logger.debug(f'/here params: {params}, /here headers {headers}')
    async with app.http_session.get(f'http://{PYBACK_HOST}:{PYBACK_PORT}/api/mods/',
                                    params=params, headers=headers) as r:

        logger.debug(f'pyback response status: {r.status}')
        if r.status >= 400:
            return

        response = await r.json()
        logger.debug(f'pyback response: {response}')
        if not len(response):
            return

    message, member_list = await get_slash_here_messages(slack_id, channel_id, slack, command['text'])

    response = await slack.query(methods.CHAT_POST_MESSAGE, {'channel': channel_id, 'text': message})
    timestamp = response['ts']
    await slack.query(methods.CHAT_POST_MESSAGE, {'channel': channel_id, 'text': member_list, 'thread_ts': timestamp})


async def slash_lunch(command: dict, app:SlackPlugin):
    channel_id = command['channel_id']
    user_id = command['user_id']
    slack = app["plugins"]["slack"].api

    param_dict = split_params(command.get('text'))

    params = (
        ('zip', f'{param_dict["location"]}'),
        ('query', 'lunch'),
        ('radius', f'{param_dict["range"]}'),
    )

    async with app.http_session.get('https://wheelof.com/lunch/yelpProxyJSON.php', params=params) as r:
        r.raise_for_status()
        message = get_random_lunch(await r.json(), command['user_name'])

        await slack.query(methods.CHAT_POST_EPHEMERAL, {'user': user_id, 'channel': channel_id, 'text': message})


async def slash_repeat(command:dict, app:SlackPlugin):
    channel_id = command['channel_id']
    slack_id = command['user_id']
    slack = app["plugins"]["slack"].api

    params = {'slack_id': slack_id, 'channel_id': channel_id}
    headers = {'Authorization': f'Token {PYBACK_TOKEN}'}

    logger.debug(f'/repeat params: {params}, /repeat headers {headers}')
    async with slack.query(methods.USERS_INFO, data={'user': slack_id})as r:

        logger.debug(f'pyback response status: {r.status}')
        if r.status >= 400:
            return

        response = await r.json()
        logger.debug(f'pyback response: {response}')
        if not len(response):
            return

        method_type, message = await get_slash_repeat_messages(slack_id, channel_id, slack, command['text'])

        await slack.query(method_type, message)
