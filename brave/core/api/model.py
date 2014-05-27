# encoding: utf-8

from __future__ import unicode_literals

from datetime import datetime, timedelta
from mongoengine import Document, EmbeddedDocument, EmbeddedDocumentField, StringField, EmailField, URLField, DateTimeField, BooleanField, ReferenceField, ListField, IntField

from brave.core.util.signal import update_modified_timestamp
from brave.core.application.signal import trigger_private_key_generation
from brave.core.util.field import PasswordField, IPAddressField
from brave.core.account.model import User
from brave.core.character.model import EVECharacter


log = __import__('logging').getLogger(__name__)

    
class CharacterBan(EmbeddedDocument):
    """Stores information about character bans."""
    
    meta = dict(
        allow_inheritance=False,
        indexes=[
            'n',
            '_enabled'
        ]
    )
        
    # The character this ban is for.
    character = ReferenceField('EVECharacter', db_field='n', required=True)
    
    # The date at which this character was banned.
    date = DateTimeField(db_field='c', default=datetime.utcnow)
    
    # The reason indicates how this character came to be banned.
    # 'direct' means the (overall) ban was invoked against this character in particular.
    # 'account' means the (overall) ban was invoked against the account that owned this character.
    # 'key' means this character was found on the same key as another banned character.
    reason = StringField(db_field='r', choices=((
        ('direct'),
        ('account'),
        ('key')
    )))
    
    _enabled = BooleanField(db_field='e', default=True)
    
    def enable(self, user):
        """Enables this ban."""
        
        # Don't spam logs with 'fake' enables.
        if not self._enabled:
            log.info("User %s enabled CharacterBan against %s (%s).".format((user.username, self.character, self.id)))
            self._enabled = True
            
    def disable(self, user):
        """Disables this ban."""
        
        # Don't spam logs with 'fake' disables.
        if self._enabled:
            log.info("User %s disabled ban against %s (%s).".format((user.username, self.host, self.id)))
            self._enabled = False
    
    
class IPBan(EmbeddedDocument):
    """Stores information about bans against an IP Address."""
    
    meta = dict(
        allow_inheritance=False,
        indexes=[
            'host',
            '_enabled'
        ]
    )
    
    host = StringField(db_field='IP', required=True)
    
    # The date at which this character was banned.
    date = DateTimeField(db_field='d', default=datetime.utcnow)
    
    # The reason indicates how this character came to be banned.
    # 'direct' means the (overall) ban was invoked against this IP Address in particular.
    # 'account' means the (overall) ban was invoked against the account that this IP was registered against.
    reason = StringField(db_field='r', choices=((
        ('direct'),
        ('account')
    )))
        
    _enabled = BooleanField(db_field='enabled', default=True)
    
    def enable(self, user):
        """Enables this ban."""
        
        # Don't spam logs with 'fake' enables.
        if not self._enabled:
            log.info("User %s enabled IPban against %s (%s).".format((user.username, self.host, self.id)))
            self._enabled = True
            
    def disable(self, user):
        """Disables this ban."""
        
        # Don't spam logs with 'fake' disables.
        if self._enabled:
            log.info("User %s disabled ban against %s (%s).".format((user.username, self.host, self.id)))
            self._enabled = False
    
    
class Ban(Document):
    """Holds information about a single ban.
    
    Multiple characters and/or IP addresses can be encompassed in
    one ban object."""
    
    meta = dict(
        allow_inheritance=False,
        indexes=[
            'creator',
            '_enabled',
            'charCreator'
        ]
    )
    
    characters = ListField(EmbeddedDocumentField(CharacterBan), db_field='c')
    IPs = ListField(EmbeddedDocumentField(IPBan))
    
    _enabled = BooleanField(db_field='e', default=True)
    creator = ReferenceField(User, required=True, db_field='a')  # TODO: Nullify inverse deletion rule.
    
    # Store the character that created the ban separately in case of account deletion.
    charCreator = ReferenceField(EVECharacter, db_field='cc', required=True)
    
    # Require a reason for the top-level ban. This enables better accountability.
    reason = StringField(db_field='r', required=True)
    
    def enable(self, user):
        """Enables this ban."""
        
        # Don't spam logs with 'fake' enables.
        if not self._enabled:
            log.info("User %s enabled ban %s.".format((user.username, self.id)))
            self._enabled = True
        
        # Enable all child bans (even if this ban was previously enabled)
        for b in self.characters:
            b.enable(user)
                
        for b in self.IPs:
            b.enable(user)
            
    def disable(self, user):
        """Disables this ban."""
        
        # Don't spam logs with 'fake' disables.
        if self._enabled:
            log.info("User %s disabled ban %s.".format((user.username, self.id)))
            self._enabled = False
        
        # Disable all child bans (even if this ban was previously disabled)
        for b in self.characters:
            b.disable(user)
                
        for b in self.IPs:
            b.disable(user)
    
    
class AuthenticationBlacklist(Document):
    """Blacklist for applications and servers."""
    
    meta = dict(
            allow_inheritance = False,
            indexes = [
                    'scheme',
                    'protocol',
                    'domain',
                    'port'
                ]
        )
    
    scheme = StringField('s')
    protocol = StringField('p')
    domain = StringField('d')
    port = StringField('o')
    
    creator = ReferenceField('User')  # TODO: Nullify inverse deletion rule.
        

class AuthenticationRequest(Document):
    meta = dict(
            allow_inheritance = False,
            indexes = [
                    dict(fields=['expires'], expireAfterSeconds=0)
                ]
        )
    
    application = ReferenceField('Application', db_field='a')
    user = ReferenceField('User', db_field='u')
    grant = ReferenceField('ApplicationGrant', db_field='g')
    
    success = URLField(db_field='s')
    failure = URLField(db_field='f')
    
    expires = DateTimeField(db_field='e', default=lambda: datetime.utcnow() + timedelta(minutes=10))
    
    def __repr__(self):
        return 'AuthenticationRequest({0}, {1}, {2}, {3})'.format(self.id, self.application, self.user, self.grant)
