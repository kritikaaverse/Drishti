"""Short-lived, one-use browser pairing. Never put the permanent API key in a URL."""
import hashlib
import secrets
import time
from collections import OrderedDict
from fastapi import APIRouter,Request,Depends
from pydantic import BaseModel,Field
from services.errors import ServiceError

class RedeemRequest(BaseModel):
    token:str=Field(min_length=32,max_length=128,pattern=r'^[A-Za-z0-9_-]+$')
class PairResponse(BaseModel):
    success:bool=True
    token:str
    expires_in_seconds:int=300
class RedeemResponse(BaseModel):
    success:bool=True
    api_key:str

class PairingStore:
    def __init__(self):
        self.tokens={}
        self.attempts=OrderedDict()
    def create(self):
        now=time.monotonic()
        self.tokens={k:expiry for k,expiry in self.tokens.items() if expiry>now}
        if len(self.tokens)>=8:raise ServiceError(429,'pairing_limit','Too many pending connections. Wait for existing links to expire.')
        token=secrets.token_urlsafe(32)
        self.tokens[hashlib.sha256(token.encode()).hexdigest()]=now+300
        return token
    def redeem(self,token,client):
        now=time.monotonic()
        stamp,count=self.attempts.pop(client,(now,0))
        if now-stamp>60:stamp,count=now,0
        self.attempts[client]=(stamp,count+1)
        while len(self.attempts)>128:self.attempts.popitem(last=False)
        if count>=10:raise ServiceError(429,'pairing_rate_limit','Too many pairing attempts. Try again in a minute.')
        expiry=self.tokens.pop(hashlib.sha256(token.encode()).hexdigest(),0)
        if expiry<now:raise ServiceError(401,'invalid_pairing','Connection link expired or already used. Request a new link.')


def routes(auth):
    router=APIRouter(prefix='/api/connection',tags=['One-time browser connection'])
    @router.post('/pair',response_model=PairResponse,dependencies=[Depends(auth)],summary='Create one-use 5-minute connection token; requires existing API key')
    async def pair(request:Request):
        return PairResponse(token=request.app.state.pairing.create())
    @router.post('/redeem',response_model=RedeemResponse,summary='Redeem a one-use pairing token; permanent key is never placed in a URL')
    async def redeem(body:RedeemRequest,request:Request):
        request.app.state.pairing.redeem(body.token,request.client.host if request.client else 'unknown')
        return RedeemResponse(api_key=request.app.state.settings.api_key)
    return router
