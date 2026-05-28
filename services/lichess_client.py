import requests
import os
from dotenv import load_dotenv
import logging

load_dotenv()

logger = logging.getLogger(__name__)


class LichessClient:
    def __init__(self):
        self.api_token = os.getenv('LICHESS_API_TOKEN')
        self.base_url = 'https://lichess.org/api'
        self.headers = {
            'Authorization': f'Bearer {self.api_token}'
        }
        logger.info("LichessClient initialized")

    def create_challenge_ai(self, level=1):
        """
        Challenge Lichess AI (Stockfish)
        level: 1-8 (1 is easiest, 8 is hardest)
        Creates unlimited time game (no clock)
        """
        url = f'{self.base_url}/challenge/ai'
        data = {
            'level': level,
            'color': 'white'  # Player always plays as white
        }
        logger.info(f"Creating AI challenge - level: {level}, color: white")
        logger.debug(f"POST {url} with data: {data}")

        response = requests.post(url, headers=self.headers, json=data)

        if response.status_code == 201:
            result = response.json()
            logger.info(f"AI challenge created successfully - game_id: {result.get('id')}")
            logger.debug(f"Response: {result}")
            return result
        else:
            logger.error(f"Failed to create AI challenge - status: {response.status_code}, response: {response.text}")
            raise Exception(f"Failed to create game: {response.text}")

    def make_move(self, game_id, move):
        """
        Make a move in UCI format (e.g., 'e2e4')
        """
        url = f'{self.base_url}/board/game/{game_id}/move/{move}'
        logger.info(f"Making move: {move} in game {game_id}")
        logger.debug(f"POST {url}")

        response = requests.post(url, headers=self.headers)

        if response.status_code == 200:
            result = response.json()
            logger.info(f"Move made successfully: {move}")
            logger.debug(f"Response: {result}")
            return result
        else:
            logger.error(f"Failed to make move - status: {response.status_code}, response: {response.text}")
            raise Exception(f"Failed to make move: {response.text}")

    def get_game_stream(self, game_id):
        """
        Get game state stream (returns generator)
        """
        url = f'{self.base_url}/board/game/stream/{game_id}'
        logger.info(f"Opening game stream for game: {game_id}")
        logger.debug(f"GET {url}")

        response = requests.get(url, headers=self.headers, stream=True)

        if response.status_code != 200:
            logger.error(f"Failed to open game stream - status: {response.status_code}")

        event_count = 0
        for line in response.iter_lines():
            if line:
                import json
                try:
                    event = json.loads(line.decode('utf-8'))
                    event_count += 1
                    logger.debug(f"Game stream event #{event_count}: type={event.get('type')}")
                    yield event
                except json.JSONDecodeError:
                    logger.warning(f"Failed to decode JSON from game stream: {line}")
                    continue

        logger.info(f"Game stream closed for game: {game_id} (processed {event_count} events)")

    def get_game_state(self, game_id):
        """
        Get current game state (non-streaming)
        """
        url = f'{self.base_url}/board/game/{game_id}'
        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to get game state: {response.text}")

    def resign_game(self, game_id):
        """
        Resign the game
        """
        url = f'{self.base_url}/board/game/{game_id}/resign'
        logger.info(f"Resigning game: {game_id}")
        logger.debug(f"POST {url}")

        response = requests.post(url, headers=self.headers)

        if response.status_code == 200:
            logger.info(f"Game resigned successfully: {game_id}")
            return True
        else:
            logger.error(f"Failed to resign game - status: {response.status_code}, response: {response.text}")
            return False

    def get_cloud_evaluation(self, fen, multiPv=1):
        """
        Get cloud evaluation for a position
        fen: FEN string of the position
        multiPv: Number of principal variations (1-5)
        """
        url = 'https://lichess.org/api/cloud-eval'
        params = {
            'fen': fen,
            'multiPv': min(multiPv, 5)  # Max 5 variations
        }
        logger.info(f"Requesting cloud evaluation - multiPv: {multiPv}")
        logger.debug(f"GET {url} with params: {params}")

        response = requests.get(url, params=params)

        if response.status_code == 200:
            result = response.json()
            logger.info("Cloud evaluation received successfully")
            logger.debug(f"Response: {result}")
            return result
        else:
            logger.warning(f"Cloud evaluation unavailable - status: {response.status_code}")
            return None
