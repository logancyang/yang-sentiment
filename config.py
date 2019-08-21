"""
A Pythonic config for yaml config file
"""
import json
import yaml


"""
Handling configs for the service
"""


class BaseConfig:
    """ A base class for all Configs """
    @classmethod
    def from_file(cls, filename: str) -> 'Config':
        """
        Create a Config object from a file. Should be either yaml or json.

        Args:
          filename: the name of the file to read from
        """
        if filename.endswith('.json'):
            reader = json.load
        elif filename.endswith('.yml') or filename.endswith('.yaml'):
            reader = yaml.load

        with open(filename) as openfile:
            return cls.from_dict(reader(openfile))

    @classmethod
    def from_dict(cls, dictionary: dict):
        """
        Create a Config object from a dictionary

        Args:
          dictionary: The dictionary representation of the Config
        """
        raise NotImplementedError


class Config(BaseConfig):
    """
    A Pythonic config representation. Will also setup the app's config if you use .init_app
    """
    secret_key = None
    db_url = None

    @classmethod
    def from_dict(cls, dictionary: dict) -> 'Config':
        """
        Create a Config object from a dictionary

        Args:
          dictionary: The dictionary representation of the Config
        """
        config = cls(
            secret_key=dictionary['flask']['secret_key'],
            db_url=dictionary['db']['url']
        )
        return config

    @classmethod
    def init_app(cls, app: 'flask.Flask'):
        """ Initialize the app according to this config """
        app.config['SECRET_KEY'] = cls.secret_key
        app.config['SQLALCHEMY_DATABASE_URI'] = cls.db_url
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
