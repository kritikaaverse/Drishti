"""Bound streaming request bodies before multipart parsing, including chunked uploads."""
from starlette.exceptions import HTTPException
class BodyLimitMiddleware:
    def __init__(self, app, max_bytes): self.app,self.max_bytes=app,max_bytes
    async def __call__(self,scope,receive,send):
        if scope['type']!='http' or scope['method'] not in {'POST','PUT','PATCH'}:
            await self.app(scope,receive,send); return
        total=0
        async def limited_receive():
            nonlocal total
            message=await receive()
            if message['type']=='http.request':
                total+=len(message.get('body',b''))
                if total>self.max_bytes: raise HTTPException(413,'Request body exceeds configured byte limit.')
            return message
        await self.app(scope,limited_receive,send)
